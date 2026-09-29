from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import StandardPagination
from apps.content.entries.serializers import EntryListSerializer
from apps.content.models.entries import Entry
from apps.content.permissions import ContentPermissions


class EntryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API bài viết và trang nội dung (§8.3 02b-tech-design).
    Lô 1: Khung danh sách bài viết + action counts.
    """

    permission_classes = [ContentPermissions]
    serializer_class = EntryListSerializer
    queryset = Entry.objects.all()
    pagination_class = StandardPagination
    custom_perm_actions = ("counts",)
    required_perms: tuple = ()

    def get_queryset(self):
        qs = Entry.objects.all().select_related("category", "published_version")
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
