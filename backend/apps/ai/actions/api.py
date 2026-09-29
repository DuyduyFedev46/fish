"""
API endpoints cho Việc AI (02b §6.4, DW-11).
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.ai.actions.serializers import AiActionSerializer
from apps.ai.actions import services
from apps.ai.models import AiAction


class AiActionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AiActionViewSet(viewsets.GenericViewSet):
    """
    ViewSet quản lý Việc AI:
    - GET /api/ai/actions/?status=&scope=&page=
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
            user_groups.add("chu")

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

        return qs.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        scope = request.query_params.get("scope", "mine")
        if scope == "all" and not request.user.has_perm("ai.manage_ai_policy"):
            return Response(
                {"detail": "Bạn không có quyền xem toàn bộ việc AI.", "code": "PERMISSION_DENIED"},
                status=status.HTTP_403_FORBIDDEN,
            )

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
            user_groups.add("chu")
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
        -> 201 {"action_id": "...", "assignee_group": "chu"}
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
