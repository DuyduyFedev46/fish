"""API bài viết và trang nội dung (§8.3 02b-tech-design)."""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import StandardPagination
from apps.common.exceptions import BusinessError
from apps.content.entries.serializers import (
    EntryDetailSerializer,
    EntryListSerializer,
    EntryVersionDetailSerializer,
    EntryVersionListSerializer,
)
from apps.content.entries.services import (
    delete_draft,
    discard_changes,
    golive_missing_roles,
    publish_entry,
    restore_entry_version,
    return_entry,
    save_draft,
    submit_entry,
    unpublish_entry,
)
from apps.content.models.entries import Entry, EntryVersion
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
    custom_perm_actions = (
        "counts",
        "publish",
        "unpublish",
        "discard_changes",
        "submit",
        "return_action",
        "versions",
        "version_detail",
        "restore_version",
    )
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

    @action(detail=True, methods=["post"], required_perms=("content.change_entry",))
    def submit(self, request, pk=None):
        """Gửi duyệt bài viết hoặc trang (§8.5, CMS-09)."""
        instance = self.get_object()
        req_version = request.data.get("row_version")
        if req_version is not None:
            try:
                req_version = int(req_version)
            except (ValueError, TypeError):
                pass
        ack_raw = request.data.get("acknowledge_warnings")
        if isinstance(ack_raw, str):
            acknowledge_warnings = ack_raw.strip().lower() in ("true", "1")
        else:
            acknowledge_warnings = bool(ack_raw)

        res = submit_entry(
            entry=instance,
            actor=request.user,
            row_version=req_version,
            acknowledge_warnings=acknowledge_warnings,
        )
        return Response(res, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="return", required_perms=("content.publish_entry",))
    def return_action(self, request, pk=None):
        """Trả bài viết/trang về nháp kèm lý do (§8.5, CMS-09)."""
        instance = self.get_object()
        req_version = request.data.get("row_version")
        if req_version is not None:
            try:
                req_version = int(req_version)
            except (ValueError, TypeError):
                pass
        reason = request.data.get("reason", "")
        res = return_entry(
            entry=instance,
            actor=request.user,
            row_version=req_version,
            reason=reason,
        )
        return Response(res, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="versions", required_perms=("content.view_entry",))
    def versions(self, request, pk=None):
        """Danh sách các phiên bản đã xuất bản của bài (§8.5, CMS-11-AC1)."""
        instance = self.get_object()
        qs = (
            EntryVersion.objects.filter(entry=instance)
            .select_related("published_by", "published_by__staff_profile")
            .order_by("-version")
        )
        serializer = EntryVersionListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"versions/(?P<version_no>\d+)",
        required_perms=("content.view_entry",),
    )
    def version_detail(self, request, pk=None, version_no=None):
        """Chi tiết một phiên bản đã xuất bản (§8.5, CMS-11)."""
        instance = self.get_object()
        ver = (
            EntryVersion.objects.filter(entry=instance, version=int(version_no))
            .select_related("published_by", "published_by__staff_profile")
            .first()
        )
        if not ver:
            raise BusinessError("Không tìm thấy phiên bản yêu cầu.", code="NOT_FOUND", status_code=404)
        serializer = EntryVersionDetailSerializer(ver)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"versions/(?P<version_no>\d+)/restore",
        required_perms=("content.change_entry",),
    )
    def restore_version(self, request, pk=None, version_no=None):
        """Khôi phục nội dung từ phiên bản cũ vào bản đang soạn (§8.5, CMS-11)."""
        instance = self.get_object()
        req_version = request.data.get("row_version")
        if req_version is not None:
            try:
                req_version = int(req_version)
            except (ValueError, TypeError):
                pass
        entry = restore_entry_version(
            entry=instance,
            actor=request.user,
            version_no=int(version_no),
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


class GoliveStatusView(APIView):
    """
    GET /api/content/golive-status/
    Kiểm tra tình trạng đủ 4 trang bắt buộc go-live (CMS-15-AC7, AC9).
    Quyền: content.view_entry.
    """

    permission_classes = [ContentPermissions]
    required_perms = ("content.view_entry",)
    http_method_names = ["get", "head", "options"]
    parser_classes = []

    def get(self, request):
        roles = golive_missing_roles()
        return Response({"missing_roles": roles}, status=status.HTTP_200_OK)


