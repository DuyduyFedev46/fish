"""API endpoints cho ảnh bài viết (§8.4 02b-tech-design)."""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.images.serializers import (
    ContentImageSerializer,
    ContentImageUpdateSerializer,
    ContentImageUploadSerializer,
)
from apps.content.images.services import update_image_alt, upload_content_image
from apps.content.models.entries import Entry
from apps.content.models.images import ContentImage
from apps.content.permissions import ContentPermissions


class EntryImageUploadView(APIView):
    """Tải ảnh cho bài viết qua multipart form (§8.4)."""

    permission_classes = [ContentPermissions]
    required_perms: tuple = ("content.change_entry",)

    def post(self, request, pk=None):
        entry = get_object_or_404(Entry, pk=pk)
        serializer = ContentImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = upload_content_image(
            entry=entry,
            file=serializer.validated_data["file"],
            alt=serializer.validated_data.get("alt", ""),
            actor=request.user,
        )
        return Response(ContentImageSerializer(image).data, status=status.HTTP_201_CREATED)


class ContentImageViewSet(viewsets.GenericViewSet):
    """Cập nhật alt text cho ảnh bài viết (§8.4)."""

    queryset = ContentImage.objects.all()
    permission_classes = [ContentPermissions]
    required_perms: tuple = ("content.change_entry",)
    custom_perm_actions = ("partial_update",)

    def partial_update(self, request, pk=None):
        image = get_object_or_404(ContentImage, pk=pk)
        serializer = ContentImageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_image_alt(
            image=image,
            alt=serializer.validated_data["alt"],
            actor=request.user,
        )
        return Response(ContentImageSerializer(updated).data, status=status.HTTP_200_OK)
