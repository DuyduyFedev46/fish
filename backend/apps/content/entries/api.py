"""API bài viết và trang nội dung (§8.3 02b-tech-design)."""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import StandardPagination
from apps.content.entries.serializers import EntryDetailSerializer, EntryListSerializer
from apps.content.entries.services import delete_draft, save_draft
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
    custom_perm_actions = ("counts",)
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
