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
            # Lệnh ghi
            import uuid
            from decimal import Decimal
            from django.db import transaction
            from apps.ai.settings.services import get_cap_for_command
            from apps.ai.models import AiPolicyVersion, AiConfigVersion

            latest_policy = AiPolicyVersion.objects.order_by("-version").first()
            policy_caps = latest_policy.caps if latest_policy else {}
            cap_cfg = get_cap_for_command(policy_caps, spec.id)

            user_cfg = AiConfigVersion.objects.filter(user=request.user).order_by("-version").first()
            user_limits = user_cfg.limits if user_cfg else {}
            user_lim = get_cap_for_command(user_limits, spec.id)

            cap_kg = None
            if cap_cfg and cap_cfg.get("kg") is not None:
                try:
                    cap_kg = Decimal(str(cap_cfg["kg"]))
                except Exception:
                    pass

            limit_kg = None
            if user_lim and user_lim.get("kg") is not None:
                try:
                    limit_kg = Decimal(str(user_lim["kg"]))
                except Exception:
                    pass

            effective_cap_kg = min([x for x in [cap_kg, limit_kg] if x is not None], default=None)

            cap_vnd = None
            if cap_cfg and cap_cfg.get("vnd") is not None:
                try:
                    cap_vnd = Decimal(str(cap_cfg["vnd"]))
                except Exception:
                    pass

            limit_vnd = None
            if user_lim and user_lim.get("vnd") is not None:
                try:
                    limit_vnd = Decimal(str(user_lim["vnd"]))
                except Exception:
                    pass

            effective_cap_vnd = min([x for x in [cap_vnd, limit_vnd] if x is not None], default=None)

            # Hạn mức ngày
            cap_daily = None
            if cap_cfg and cap_cfg.get("daily") is not None:
                try:
                    cap_daily = int(cap_cfg["daily"])
                except Exception:
                    pass

            limit_daily = None
            if user_lim and user_lim.get("daily") is not None:
                try:
                    limit_daily = int(user_lim["daily"])
                except Exception:
                    pass

            default_daily = getattr(settings, "AI_DAILY_LIMIT_DEFAULT", 20)
            daily_candidates = [x for x in [cap_daily, limit_daily] if x is not None]
            effective_daily = min(daily_candidates) if daily_candidates else default_daily

            downgrade_reason = None

            # 1. Kiểm tra số kg và tiền
            total_qty = Decimal("0")
            total_amount = Decimal("0")
            if "lines" in args and isinstance(args["lines"], list):
                try:
                    for l in args["lines"]:
                        if isinstance(l, dict):
                            q = Decimal(str(l.get("qty", 0)))
                            r = Decimal(str(l.get("rate", 0)))
                            total_qty += q
                            total_amount += q * r
                except Exception:
                    pass

                if effective_cap_kg is not None and total_qty > effective_cap_kg:
                    is_over_owner_cap = (cap_kg is not None and total_qty > cap_kg)
                    downgrade_reason = {
                        "code": "AI_LIMIT_KG",
                        "text": "Vượt trần của Chủ" if is_over_owner_cap else "Vượt ngưỡng bạn đặt",
                    }
                elif effective_cap_vnd is not None and total_amount > effective_cap_vnd:
                    is_over_owner_cap = (cap_vnd is not None and total_amount > cap_vnd)
                    downgrade_reason = {
                        "code": "AI_LIMIT_VND",
                        "text": "Vượt trần của Chủ" if is_over_owner_cap else "Vượt ngưỡng bạn đặt",
                    }

            # 2. Kiểm tra hạn mức ngày (DW-19-AC5)
            if not downgrade_reason and current_level == "B":
                today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                daily_count = AiAction.objects.filter(
                    owner=request.user,
                    kind=AiAction.Kind.WRITE,
                    created_at__gte=today_start,
                    status__in=[
                        AiAction.Status.DONE,
                        AiAction.Status.CONFIRMED,
                        AiAction.Status.SCHEDULED,
                    ],
                ).count()
                if daily_count >= effective_daily:
                    downgrade_reason = {
                        "code": "AI_DAILY_LIMIT",
                        "text": "Vượt hạn mức trong ngày",
                    }

            # Nếu có downgrade_reason hoặc current_level == "C": tạo đề xuất nháp PENDING
            if downgrade_reason or current_level == "C":
                ttl_minutes = getattr(settings, "AI_ACTION_TTL_MINUTES", 15)
                expires_at = timezone.now() + datetime.timedelta(minutes=ttl_minutes)

                action = AiAction.objects.create(
                    command=spec.id,
                    kind=AiAction.Kind.WRITE,
                    level=AiAction.Level.C,
                    status=AiAction.Status.PENDING,
                    owner=request.user,
                    config_version=user_cfg.version if user_cfg else None,
                    policy_version=latest_policy.version if latest_policy else None,
                    idempotency_key=idempotency_key,
                    channel="ai_local",
                    client=client,
                    args=args,
                    target_model=target_model_label,
                    target_id=str(target_id or ""),
                    downgrade_reason=downgrade_reason,
                    expires_at=expires_at,
                )

                # Ghi AuditLog propose_<id> (DW-11-AC1)
                with set_ai_audit_scope(
                    ai_actor=request.user,
                    level="C",
                    config_version=user_cfg.version if user_cfg else None,
                    policy_version=latest_policy.version if latest_policy else None,
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
                    "downgrade_reason": downgrade_reason,
                    "preview": {
                        "target": {
                            "type": target_model_label or "document",
                            "code": str(target_id or ""),
                        }
                    },
                })

            # Đến đây: current_level == "B" và không bị hạ mức
            undo_attr = getattr(spec, "undo", "") or ""

            # TRƯỜNG HỢP 1: Lệnh trì hoãn ghi (DW-21)
            if undo_attr == "defer":
                delay_minutes = getattr(spec, "delay_minutes", None) or getattr(settings, "AI_DEFERRED_DELAY_MINUTES", 10)
                execute_after = timezone.now() + datetime.timedelta(minutes=delay_minutes)
                undo_until = execute_after

                action = AiAction.objects.create(
                    command=spec.id,
                    kind=AiAction.Kind.WRITE,
                    status=AiAction.Status.SCHEDULED,
                    level=AiAction.Level.B,
                    owner=request.user,
                    config_version=user_cfg.version if user_cfg else None,
                    policy_version=latest_policy.version if latest_policy else None,
                    target_model=target_model_label,
                    target_id=str(target_id or ""),
                    args=args,
                    idempotency_key=idempotency_key,
                    channel="ai_local",
                    client=client,
                    execute_after=execute_after,
                    undo_until=undo_until,
                )

                # Ghi AuditLog schedule_<spec.id>
                with set_ai_audit_scope(
                    ai_actor=request.user,
                    level="B",
                    config_version=user_cfg.version if user_cfg else None,
                    policy_version=latest_policy.version if latest_policy else None,
                    action_ref=str(action.id),
                ):
                    record_audit(
                        f"schedule_{spec.id}",
                        actor=None,
                        actor_kind="ai",
                        ai_actor=request.user,
                        proposal_ref=str(action.id),
                        note=f"AI xếp lịch lệnh {spec.title} chạy sau {delay_minutes} phút",
                    )

                return Response({
                    "outcome": "scheduled",
                    "level": "B",
                    "action_id": str(action.id),
                    "execute_after": execute_after.isoformat(),
                    "undo_until": undo_until.isoformat(),
                })

            # TRƯỜNG HỢP 2: Lệnh hoàn tác bằng trạng thái (DW-19)
            # Toàn bộ bọc trong transaction.atomic() (H5, DW-19-AC6)
            with transaction.atomic():
                action_id = uuid.uuid4()

                # 1. Gọi view trong ai_audit_scope
                with set_ai_audit_scope(
                    ai_actor=request.user,
                    level="B",
                    config_version=user_cfg.version if user_cfg else None,
                    policy_version=latest_policy.version if latest_policy else None,
                    action_ref=str(action_id),
                ):
                    dispatch_res = dispatch_command(
                        spec,
                        user=request.user,
                        args=args,
                        target_id=target_id,
                        request_origin=request,
                    )

                if dispatch_res.is_error:
                    transaction.set_rollback(True)
                    return Response(dispatch_res.data, status=dispatch_res.status_code)

                # 2. Lấy result_ref
                result_ref = None
                if isinstance(dispatch_res.data, dict):
                    if "receipt" in dispatch_res.data and isinstance(dispatch_res.data["receipt"], dict):
                        result_ref = {
                            "model": "purchasereceipt",
                            "id": dispatch_res.data["receipt"].get("id"),
                        }
                    elif "id" in dispatch_res.data:
                        result_ref = {
                            "model": target_model_label or "",
                            "id": dispatch_res.data.get("id"),
                        }

                target_final_id = str(target_id or (result_ref.get("id") if result_ref else "") or "")

                undo_window_minutes = getattr(settings, "AI_UNDO_WINDOW_MINUTES", 10)
                undo_until = timezone.now() + datetime.timedelta(minutes=undo_window_minutes)

                action = AiAction.objects.create(
                    id=action_id,
                    command=spec.id,
                    kind=AiAction.Kind.WRITE,
                    status=AiAction.Status.DONE,
                    level=AiAction.Level.B,
                    owner=request.user,
                    config_version=user_cfg.version if user_cfg else None,
                    policy_version=latest_policy.version if latest_policy else None,
                    target_model=target_model_label,
                    target_id=target_final_id,
                    args=args,
                    idempotency_key=idempotency_key,
                    channel="ai_local",
                    client=client,
                    executed_at=timezone.now(),
                    undo_until=undo_until,
                    result_ref=result_ref,
                )

                # 3. Ghi AuditLog execute_<spec.id> (H5: nếu lỗi AuditLog -> rollback toàn bộ!)
                with set_ai_audit_scope(
                    ai_actor=request.user,
                    level="B",
                    config_version=user_cfg.version if user_cfg else None,
                    policy_version=latest_policy.version if latest_policy else None,
                    action_ref=str(action.id),
                ):
                    record_audit(
                        f"execute_{spec.id}",
                        actor=None,
                        actor_kind="ai",
                        ai_actor=request.user,
                        proposal_ref=str(action.id),
                        note=f"AI tự ghi lệnh {spec.title} mức B",
                    )

                clean_result = scrub_data(dispatch_res.data, user=request.user)

                return Response({
                    "outcome": "done",
                    "level": "B",
                    "action_id": str(action.id),
                    "result": clean_result,
                    "undo_until": action.undo_until.isoformat(),
                })
