"""
Pipeline xử lý POST /api/ai/commands/<id>/call/ (02b §4.2, DW-10, DW-11).
"""
import datetime
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import SimpleRateThrottle

from apps.common.audit import record_audit, set_ai_audit_scope
from apps.ai.models import AiAction
from apps.ai.policy.effective import effective_level
from apps.ai.registry.discovery import get_registry
from apps.ai.execution.dispatch import dispatch_command
from apps.ai.execution.scrub import scrub_data, truncate_read_result


class AiCallRateThrottle(SimpleRateThrottle):
    """Throttle gọi lệnh AI theo user (02b §4.2, DW-10-AC8)."""

    scope = "ai_call"

    def parse_rate(self, rate):
        if not rate or not isinstance(rate, str) or "/" not in rate:
            return (None, None)
        return super().parse_rate(rate)

    def get_rate(self):
        if getattr(settings, "TESTING", False) and not getattr(settings, "AI_CALL_RATE_TESTING", False):
            return None
        return getattr(settings, "AI_CALL_RATE", "30/min")

    def allow_request(self, request, view):
        self.rate = self.get_rate()
        if self.rate is None:
            return True
        self.num_requests, self.duration = self.parse_rate(self.rate)
        if self.num_requests is None:
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = str(request.user.pk)
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AiCommandCallView(APIView):
    """
    POST /api/ai/commands/<id>/call/
    Thực thi lệnh đọc (mức A) hoặc tạo nháp đề xuất (mức C).
    """

    throttle_classes = [AiCallRateThrottle]

    def throttled(self, request, wait):
        from apps.common.exceptions import BusinessError
        raise BusinessError(
            "Yêu cầu quá nhanh, vui lòng thử lại sau.",
            code="THROTTLED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def post(self, request, command_id: str):
        # 1. Kiểm tra cờ AI_ENABLED
        if not getattr(settings, "AI_ENABLED", False):
            return Response(
                {"detail": "Hệ thống AI đang tắt.", "code": "AI_DISABLED"},
                status=status.HTTP_410_GONE,
            )

        # 2. Lấy spec từ registry & kiểm tra effective_level
        spec = get_registry().get(command_id)
        if not spec or effective_level(request.user, spec) == "OFF":
            return Response(
                {"detail": "Không có lệnh này.", "code": "COMMAND_UNKNOWN"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Kênh: endpoint này chỉ nhận lệnh kênh local
        if getattr(spec, "channel", "local") == "cloud":
            return Response(
                {"detail": "Lệnh cloud không chạy ở kênh này.", "code": "BR-AI-02"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        args = request.data.get("args") or {}
        if not isinstance(args, dict):
            return Response(
                {"detail": "Dữ liệu lệnh không hợp lệ.", "code": "BR-AI-01", "errors": {"args": "Phải là dict"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_id = request.data.get("target_id")
        idempotency_key = (request.data.get("idempotency_key") or "").strip()
        client = (request.data.get("client") or "erp-console").strip()

        # 4. Idempotency kiểm tra
        if idempotency_key:
            existing = AiAction.objects.filter(owner=request.user, idempotency_key=idempotency_key).first()
            if existing:
                if existing.args != args:
                    return Response(
                        {"detail": "Trùng idempotency_key nhưng khác tham số.", "code": "AI_IDEMPOTENCY_CONFLICT"},
                        status=status.HTTP_409_CONFLICT,
                    )
                if existing.kind == AiAction.Kind.READ:
                    return Response({
                        "outcome": "done",
                        "level": "A",
                        "action_id": str(existing.id),
                        "result": {"rows": [], "total": 0, "truncated": False},
                    })
                else:
                    return Response({
                        "outcome": "proposal",
                        "level": existing.level,
                        "action_id": str(existing.id),
                        "expires_at": existing.expires_at.isoformat() if existing.expires_at else None,
                        "downgrade_reason": existing.downgrade_reason,
                        "preview": {
                            "target": {"type": existing.target_model, "code": existing.target_id}
                        },
                    })

        # 5. Validate args nếu có input_serializer_cls
        if spec.input_serializer_cls:
            serializer = spec.input_serializer_cls(data=args)
            if not serializer.is_valid():
                return Response(
                    {
                        "detail": "Dữ liệu lệnh không hợp lệ.",
                        "code": "BR-AI-01",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # 6. Kiểm tra target scope nếu spec.detail=True
        target_model_label = ""
        if spec.view_cls and hasattr(spec.view_cls, "queryset") and spec.view_cls.queryset is not None:
            target_model_label = spec.view_cls.queryset.model._meta.model_name
        elif spec.view_cls and hasattr(spec.view_cls, "serializer_class") and spec.view_cls.serializer_class is not None:
            meta = getattr(spec.view_cls.serializer_class, "Meta", None)
            if meta and hasattr(meta, "model"):
                target_model_label = meta.model._meta.model_name

        if spec.detail:
            if target_id is None:
                return Response(
                    {"detail": "Lệnh yêu cầu target_id.", "code": "BR-AI-01"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if spec.view_cls:
                view_instance = spec.view_cls()
                view_instance.action = spec.action
                view_instance.request = request
                lookup_field = getattr(spec.view_cls, "lookup_url_kwarg", None) or getattr(
                    spec.view_cls, "lookup_field", "pk"
                )
                view_instance.kwargs = {lookup_field: target_id}
                view_instance.format_kwarg = None
                try:
                    view_instance.get_object()
                except Http404:
                    return Response(
                        {"detail": "Không tìm thấy đối tượng.", "code": "NOT_FOUND"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                except PermissionDenied:
                    return Response(
                        {"detail": "Không có quyền truy cập đối tượng.", "code": "PERMISSION_DENIED"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        current_level = effective_level(request.user, spec)

        # 7. Theo mức hiệu lực (Lô 3a: A cho đọc, C cho ghi)
        if spec.kind == "read":
            # Chạy lệnh đọc trong ai_audit_scope để đảm bảo audit không bị nhầm lẫn
            with set_ai_audit_scope(ai_actor=request.user, level="A"):
                dispatch_res = dispatch_command(
                    spec,
                    user=request.user,
                    args=args,
                    target_id=target_id,
                    request_origin=request,
                )

            if dispatch_res.is_error:
                return Response(dispatch_res.data, status=dispatch_res.status_code)

            # Lọc dữ liệu qua scrub_data
            cleaned_data = scrub_data(dispatch_res.data, user=request.user, is_ai_read=True)
            rows, total, truncated = truncate_read_result(cleaned_data)

            # Lưu AiAction mức A (không lưu kết quả data để tuân thủ BR-AI-09)
            action = AiAction.objects.create(
                command=spec.id,
                kind=AiAction.Kind.READ,
                level=AiAction.Level.A,
                status=AiAction.Status.DONE,
                owner=request.user,
                idempotency_key=idempotency_key,
                channel="ai_local",
                client=client,
                args=args,
                target_model=target_model_label,
                target_id=str(target_id or ""),
                executed_at=timezone.now(),
            )

            return Response({
                "outcome": "done",
                "level": "A",
                "action_id": str(action.id),
                "result": {
                    "rows": rows,
                    "total": total,
                    "truncated": truncated,
                },
            })

        else:
            # Lệnh ghi: Mức C (Proposal)
            ttl_minutes = getattr(settings, "AI_ACTION_TTL_MINUTES", 15)
            expires_at = timezone.now() + datetime.timedelta(minutes=ttl_minutes)

            action = AiAction.objects.create(
                command=spec.id,
                kind=AiAction.Kind.WRITE,
                level=AiAction.Level.C,
                status=AiAction.Status.PENDING,
                owner=request.user,
                idempotency_key=idempotency_key,
                channel="ai_local",
                client=client,
                args=args,
                target_model=target_model_label,
                target_id=str(target_id or ""),
                expires_at=expires_at,
            )

            # Ghi AuditLog propose_<id> (DW-11-AC1)
            with set_ai_audit_scope(
                ai_actor=request.user,
                level="C",
                action_ref=str(action.id),
                is_proposal=True,
            ):
                record_audit(
                    f"propose_{spec.id}",
                    actor=None,
                    actor_kind="ai",
                    ai_actor=request.user,
                    proposal_ref=str(action.id),
                    note=f"AI đề xuất lệnh {spec.title}",
                )

            return Response({
                "outcome": "proposal",
                "level": "C",
                "action_id": str(action.id),
                "expires_at": action.expires_at.isoformat(),
                "downgrade_reason": None,
                "preview": {
                    "target": {
                        "type": target_model_label or "document",
                        "code": str(target_id or ""),
                    }
                },
            })
