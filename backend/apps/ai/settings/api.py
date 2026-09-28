"""
API views cho màn AI của tôi (DW-12).
"""
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.models.config import AiConfigVersion
from apps.common.api import StandardPagination
from .serializers import (
    AiConfigVersionListSerializer,
    MyConfigKillSerializer,
    MyConfigUpdateSerializer,
)
from .services import get_user_config_data, kill_user_config, update_user_config


class MyConfigView(APIView):
    """
    GET /api/ai/my-config/
    PUT /api/ai/my-config/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_user_config_data(request.user)
        return Response(data)

    def put(self, request):
        serializer = MyConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data

        update_user_config(
            request.user,
            base_version=vdata["base_version"],
            groups=vdata.get("groups", {}),
            overrides=vdata.get("overrides", {}),
            limits=vdata.get("limits", {}),
            acknowledge_responsibility=vdata["acknowledge_responsibility"],
            created_by=request.user,
        )

        data = get_user_config_data(request.user)
        return Response(data, status=status.HTTP_200_OK)


class MyConfigKillView(APIView):
    """
    POST /api/ai/my-config/kill/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MyConfigKillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data

        config = kill_user_config(
            request.user,
            killed=vdata["killed"],
            created_by=request.user,
        )
        return Response({"version": config.version, "killed": config.killed}, status=status.HTTP_200_OK)


class MyConfigVersionsView(generics.ListAPIView):
    """
    GET /api/ai/my-config/versions/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AiConfigVersionListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        return AiConfigVersion.objects.filter(user=self.request.user).order_by("-version")
