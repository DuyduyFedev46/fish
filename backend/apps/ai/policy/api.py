"""
API views cho chính sách AI của Chủ (DW-13).
"""
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.models.policy import AiPolicyVersion
from apps.ai.settings.services import get_user_config_data
from apps.common.api import StandardPagination
from .serializers import (
    AdminUserKillSerializer,
    AiPolicyVersionListSerializer,
    PolicyUpdateSerializer,
)
from .services import get_policy_data, kill_user_by_admin, update_policy


User = get_user_model()


class HasManageAiPolicy(BasePermission):
    """Yêu cầu quyền ai.manage_ai_policy (chỉ Chủ có, DW-13-AC5)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm("ai.manage_ai_policy")
        )


class AiPolicyView(APIView):
    """
    GET /api/ai/policy/
    PUT /api/ai/policy/
    """
    permission_classes = [IsAuthenticated, HasManageAiPolicy]

    def get(self, request):
        return Response(get_policy_data())

    def put(self, request):
        serializer = PolicyUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data

        update_policy(
            base_version=vdata["base_version"],
            global_mode=vdata.get("global_mode"),
            red_zone=vdata.get("red_zone"),
            caps=vdata.get("caps"),
            acknowledge_responsibility=vdata["acknowledge_responsibility"],
            created_by=request.user,
        )

        return Response(get_policy_data(), status=status.HTTP_200_OK)


class AiPolicyUserKillView(APIView):
    """
    POST /api/ai/policy/users/<id>/kill/
    """
    permission_classes = [IsAuthenticated, HasManageAiPolicy]

    def post(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)
        serializer = AdminUserKillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data

        config = kill_user_by_admin(
            request.user,
            target_user,
            killed=vdata["killed"],
        )
        return Response({
            "version": config.version,
            "killed": config.killed,
            "user_id": target_user.id,
        }, status=status.HTTP_200_OK)


class AiPolicyUserConfigView(APIView):
    """
    GET /api/ai/policy/users/<id>/config/
    Chỉ đọc cấu hình của user khác (DW-12-AC8, DW-13-AC4).
    Không hỗ trợ PUT / PATCH (trả về 405).
    """
    permission_classes = [IsAuthenticated, HasManageAiPolicy]

    def get(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)
        data = get_user_config_data(target_user)
        return Response(data)


class AiPolicyVersionsView(generics.ListAPIView):
    """
    GET /api/ai/policy/versions/
    """
    permission_classes = [IsAuthenticated, HasManageAiPolicy]
    serializer_class = AiPolicyVersionListSerializer
    pagination_class = StandardPagination
    queryset = AiPolicyVersion.objects.order_by("-version")
