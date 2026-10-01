"""
API endpoints cho Việc AI (02b §6.4, DW-11).
"""
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts import roles
from apps.ai.actions.serializers import AiActionSerializer
from apps.ai.actions import services
from apps.ai.actions.targets import MAX_TARGET_IDS, resolve_target_label, stored_variants
from apps.ai.models import AiAction
from apps.common.exceptions import BusinessError


class AiActionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AiActionViewSet(viewsets.GenericViewSet):
    """
    ViewSet quản lý Việc AI:
    - GET /api/ai/actions/?status=&scope=&target_model=&target_id=&page=
    - GET /api/ai/actions/counts/?status=&scope=  (đếm theo chứng từ đích, R1)
    - GET /api/ai/actions/<id>/
    - POST /api/ai/actions/escalate/
    - POST /api/ai/actions/<id>/confirm/
    - POST /api/ai/actions/<id>/reject/
    - POST /api/ai/actions/<id>/undo/
    """

    permission_classes = [IsAuthenticated]
    pagination_class = AiActionPagination
    serializer_class = AiActionSerializer

    def get_queryset(self):
        user = self.request.user
        scope = self.request.query_params.get("scope", "mine")
        user_groups = set(user.groups.values_list("name", flat=True))
        if user.has_perm("ai.manage_ai_policy"):
            user_groups.add(roles.OWNER)

        if scope == "all":
            if not user.has_perm("ai.manage_ai_policy"):
                return AiAction.objects.none()
            qs = AiAction.objects.all()
        else:
            qs = AiAction.objects.filter(
                Q(owner=user) | Q(status=AiAction.Status.ESCALATED, assignee_group__in=user_groups)
            )

        status_param = self.request.query_params.get("status")
        if status_param:
            statuses = [s.strip().upper() for s in status_param.split(",") if s.strip()]
            qs = qs.filter(status__in=statuses)

        # R1: lọc theo chứng từ đích. Chỉ THU HẸP tập đã giới hạn ở trên, không bao giờ mở rộng phạm vi.
        qs = self._filter_by_target(qs)

        return qs.order_by("-created_at")

    def _filter_by_target(self, qs):
        params = self.request.query_params
        target_model = (params.get("target_model") or "").strip()
        target_id = (params.get("target_id") or "").strip()
        if target_id and not target_model:
            # `target_id` chỉ có nghĩa trong một loại chứng từ (phiếu nhập 12 khác lô 12).
            raise BusinessError(
                "Cần gửi kèm loại chứng từ khi lọc theo mã chứng từ.",
                code="TARGET_MODEL_REQUIRED",
                status_code=400,
            )
        if target_model:
            label = resolve_target_label(target_model)
            if label is None:
                # Không lặp lại giá trị người gọi gửi lên.
                raise BusinessError(
                    "Loại chứng từ không hợp lệ.", code="INVALID_TARGET_MODEL", status_code=400
                )
            qs = qs.annotate(_target_model_lower=Lower("target_model")).filter(
                _target_model_lower__in=stored_variants(label)
            )
        if target_id:
            ids = [part.strip() for part in target_id.split(",") if part.strip()]
            if len(ids) > MAX_TARGET_IDS:
                raise BusinessError(
                    f"Chỉ lọc tối đa {MAX_TARGET_IDS} mã chứng từ một lần.",
                    code="INVALID_TARGET_ID",
                    status_code=400,
                )
            qs = qs.filter(target_id__in=ids)
        return qs

    @staticmethod
    def _deny_scope_all(request):
        """`scope=all` chỉ cho người có `ai.manage_ai_policy`; còn lại 403 (dùng chung list và counts)."""
        if request.query_params.get("scope", "mine") == "all" and not request.user.has_perm("ai.manage_ai_policy"):
            return Response(
                {"detail": "Bạn không có quyền xem toàn bộ việc AI.", "code": "PERMISSION_DENIED"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    @action(detail=False, methods=["get"], url_path="counts")
    def counts(self, request):
        """
        GET /api/ai/actions/counts/?status=PENDING,ESCALATED[&scope=mine|all]
        -> {"by_target_model": {"purchasing.purchasereceipt": 2, "inventory.batch": 1}}
        Đếm trên đúng tập `get_queryset` (cùng phạm vi "mine"/"all" và cùng bộ lọc với danh sách), nên không
        thể đếm việc ngoài phạm vi người xem. Việc không gắn chứng từ bị bỏ qua.
        """
        denied = self._deny_scope_all(request)
        if denied is not None:
            return denied
        rows = self.get_queryset().order_by().values("target_model").annotate(n=Count("id"))
        by_target_model: dict[str, int] = {}
        for row in rows:
            raw = row["target_model"]
            if not raw:
                continue
            key = resolve_target_label(raw) or raw.lower()
            by_target_model[key] = by_target_model.get(key, 0) + row["n"]
        return Response({"by_target_model": by_target_model})

    def list(self, request, *args, **kwargs):
        denied = self._deny_scope_all(request)
        if denied is not None:
            return denied

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        user = request.user
        user_groups = set(user.groups.values_list("name", flat=True))
        if user.has_perm("ai.manage_ai_policy"):
            user_groups.add(roles.OWNER)
            action_obj = AiAction.objects.filter(id=pk).first()
        else:
            action_obj = AiAction.objects.filter(
                Q(id=pk) & (Q(owner=user) | Q(status=AiAction.Status.ESCALATED, assignee_group__in=user_groups))
            ).first()

        if not action_obj:
            return Response(
                {"detail": "Không tìm thấy hành động AI.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Ghi nhận viewed_at (02b §6.4: ghi viewed_at để tính 3s)
        action_obj.viewed_at = timezone.now()
        action_obj.save(update_fields=["viewed_at"])

        serializer = self.get_serializer(action_obj)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        confirm_nonce = request.data.get("confirm_nonce")
        res = services.confirm_ai_action(
            action_id=pk,
            user=request.user,
            confirm_nonce=confirm_nonce,
            request=request,
        )
        return Response(res, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        reason_code = request.data.get("reason_code", "")
        res = services.reject_ai_action(
            action_id=pk,
            user=request.user,
            reason_code=reason_code,
            request=request,
        )
        return Response(res, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="escalate")
    def escalate(self, request):
        """
        POST /api/ai/actions/escalate/
        Body: {"doc_type": "batch", "doc_id": "123", "step_key": "close"}
        -> 201 {"action_id": "...", "assignee_group": "owner"}
        DW-23-AC1, AC6, AC7
        """
        doc_type = request.data.get("doc_type")
        doc_id = request.data.get("doc_id")
        step_key = request.data.get("step_key")

        res = services.escalate_guidance_step(
            doc_type=doc_type,
            doc_id=doc_id,
            step_key=step_key,
            user=request.user,
        )
        return Response(res, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="undo")
    def undo(self, request, pk=None):
        res = services.undo_ai_action(
            action_id=pk,
            user=request.user,
            request=request,
        )
        return Response(res, status=status.HTTP_200_OK)
