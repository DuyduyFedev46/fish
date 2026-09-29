"""API bài viết và trang nội dung (§8.3 02b-tech-design)."""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import StandardPagination
from apps.content.entries.serializers import EntryDetailSerializer, EntryListSerializer
from apps.content.entries.services import (
    delete_draft,
    discard_changes,
    publish_entry,
    save_draft,
    unpublish_entry,
)
from apps.content.models.entries import Entry
from apps.content.permissions import ContentPermissions


class EntryViewSet(viewsets.ModelViewSet):
    """
    API bài viết và trang nội dung (§8.3 02b-tech-design).
    Hỗ trợ GET (list/detail), POST (create draft), PATCH (update draft), DELETE (delete draft chưa từng đăng).
    PUT không được hỗ trợ (trả 405).
    """

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    permission_classes = [ContentPermissions]
    serializer_class = EntryListSerializer
    queryset = Entry.objects.all()
    pagination_class = StandardPagination
    custom_perm_actions = ("counts", "publish", "unpublish", "discard_changes")
    required_perms: tuple = ()

    def get_queryset(self):
        qs = Entry.objects.all().select_related("category", "published_version", "cover_image")
        if self.action == "retrieve":
            qs = qs.prefetch_related("images")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        kind_param = self.request.query_params.get("kind")
        if kind_param:
            qs = qs.filter(kind=kind_param)
        category_param = self.request.query_params.get("category")
        if category_param:
            qs = qs.filter(category_id=category_param)
        return qs.order_by("-updated_at", "-id")

    def create(self, request, *args, **kwargs):
        """Tạo nháp bài viết/trang (§8.3)."""
        entry = save_draft(entry=None, data=request.data, actor=request.user)
        return Response(EntryDetailSerializer(entry).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """Xem chi tiết bài viết/trang (§8.3)."""
        instance = self.get_object()
        serializer = EntryDetailSerializer(instance)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Cập nhật nháp bài viết/trang (§8.3)."""
        instance = self.get_object()
        entry = save_draft(entry=instance, data=request.data, actor=request.user)
        return Response(EntryDetailSerializer(entry).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Xoá nháp chưa từng đăng (§8.3, CMS-03-AC8, BR-ND-02)."""
        instance = self.get_object()
        delete_draft(entry=instance, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], required_perms=("content.publish_entry",))
    def publish(self, request, pk=None):
        """Xuất bản bài viết hoặc trang (§8.5, CMS-07)."""
        from apps.content.entries.services import publish_entry

        instance = self.get_object()
        req_version = request.data.get("row_version")
        if req_version is not None:
            try:
                req_version = int(req_version)
            except (ValueError, TypeError):
                pass
        checklist_raw = request.data.get("checklist_confirmed")
        if isinstance(checklist_raw, str):
            checklist_confirmed = checklist_raw.strip().lower() in ("true", "1")
        else:
            checklist_confirmed = bool(checklist_raw)

        ack_raw = request.data.get("acknowledge_warnings")
        if isinstance(ack_raw, str):
            acknowledge_warnings = ack_raw.strip().lower() in ("true", "1")
        else:
            acknowledge_warnings = bool(ack_raw)

        res = publish_entry(
            entry=instance,
            actor=request.user,
            row_version=req_version,
            checklist_confirmed=checklist_confirmed,
            acknowledge_warnings=acknowledge_warnings,
        )
        return Response(res, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], required_perms=("content.publish_entry",))
    def unpublish(self, request, pk=None):
        """Gỡ bài viết/trang khỏi web công khai (CMS-12, §8.3)."""
        instance = self.get_object()
        req_version = request.data.get("row_version")
        if req_version is not None:
            try:
                req_version = int(req_version)
            except (ValueError, TypeError):
                pass
        reason = request.data.get("reason", "")
        res = unpublish_entry(
            entry=instance,
            actor=request.user,
            row_version=req_version,
            reason=reason,
        )
        return Response(res, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="discard-changes",
        required_perms=("content.change_entry",),
    )
    def discard_changes(self, request, pk=None):
        """Huỷ các thay đổi nháp, khôi phục lại bản đã đăng (CMS-10, §8.3, §8.5)."""
        instance = self.get_object()
        req_version = request.data.get("row_version")
        if req_version is not None:
            try:
                req_version = int(req_version)
            except (ValueError, TypeError):
                pass
        entry = discard_changes(
            entry=instance,
            actor=request.user,
            row_version=req_version,
        )
        return Response(
            EntryDetailSerializer(entry, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )


    @action(detail=False, methods=["get"], required_perms=("content.view_entry",))
    def counts(self, request):
        """Đếm số bài viết/trang theo từng trạng thái (§8.3)."""
        qs = Entry.objects.all()
        kind_param = request.query_params.get("kind")
        if kind_param:
            qs = qs.filter(kind=kind_param)

        counts = {
            "draft": qs.filter(status="draft").count(),
            "pending_review": qs.filter(status="pending_review").count(),
            "published": qs.filter(status="published").count(),
            "unpublished": qs.filter(status="unpublished").count(),
        }
        return Response(counts)

