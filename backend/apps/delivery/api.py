"""
API nội bộ — giao hàng. Tầng 3 phạm vi dòng: nv_giao chỉ thấy & sửa phiếu được gán
cho mình (get_queryset lọc, không phải ẩn ở giao diện — BR-PQ-12).
"""
import datetime

from django.db.models import F
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.common.api import (
    BusinessModelPermissions,
    DocumentViewSet,
    NoStoreMixin,
    StandardPagination,
    has_full_delivery_scope,
    require_perm,
)

from . import services
from .models import DeliveryNote
from .serializers import DeliveryNoteDetailSerializer, DeliveryNoteSerializer


class DeliveryNoteViewSet(NoStoreMixin, DocumentViewSet):
    queryset = DeliveryNote.objects.select_related(
        "sales_invoice__sales_order__customer",
        "assigned_to",
        "confirmed_by",
    ).prefetch_related(
        "label_prints",
        "sales_invoice__lines__batch_allocations__component_item",
        "sales_invoice__lines__batch_allocations__batch",
    ).all()
    serializer_class = DeliveryNoteSerializer
    pagination_class = StandardPagination
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("set_status", "label", "label_print")

    # BR-PQ-14 / BR-GH-06: trạng thái & người giao chỉ đổi qua action nghiệp vụ.
    locked_fields = (
        "status", "assigned_to", "failed_attempts", "completed_at", "sales_invoice",
        "confirmed_at", "confirmed_by", "confirm_skipped", "recipient_name", "recipient_phone",
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DeliveryNoteDetailSerializer
        return DeliveryNoteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if has_full_delivery_scope(user):
            return qs
        return qs.filter(assigned_to=user)  # nv_giao: chỉ phiếu của mình

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            # S14-AC2 / CS-02: lọc theo trạng thái (nhiều, cách dấu phẩy)
            status_param = self.request.query_params.get("status", "")
            statuses = [s.strip() for s in status_param.split(",") if s.strip()]
            if statuses:
                queryset = queryset.filter(status__in=statuses)

            # CS-02: completed_from YYYY-MM-DD
            completed_from = self.request.query_params.get("completed_from")
            if completed_from:
                try:
                    d = datetime.date.fromisoformat(completed_from)
                    queryset = queryset.filter(completed_at__date__gte=d)
                except ValueError:
                    pass

            # Sắp xếp theo 02b §4.2:
            # - CONFIRMING theo paid_at / created_at tăng dần
            # - PREPARING theo confirmed_at tăng dần (null trước), rồi created_at
            # - Ngược lại: -created_at
            if len(statuses) == 1:
                st = statuses[0]
                if st == DeliveryNote.Status.CONFIRMING:
                    queryset = queryset.order_by("created_at", "id")
                elif st == DeliveryNote.Status.PREPARING:
                    queryset = queryset.order_by(F("confirmed_at").asc(nulls_first=True), "created_at", "id")
                else:
                    queryset = queryset.order_by("-created_at", "-id")
            else:
                queryset = queryset.order_by("-created_at", "-id")

        return queryset

    @action(
        detail=True,
        methods=["post"],
        url_path="status",
        required_perms=("delivery.change_deliverynote",),
    )
    def set_status(self, request, pk=None):
        """Cập nhật trạng thái phiếu giao hàng."""
        # 1. Tầng 3 scope: nv_giao chỉ thấy & thao tác phiếu gán cho mình -> 404 (BR-GH-06/BR-PQ-12)
        note = self.get_object()

        to_status = request.data.get("to_status")
        from_status = request.data.get("from_status")

        # 2. Tầng 2 quyền thao tác cụ thể: đóng gói cần pack_deliverynote (CS-03-AC6)
        if to_status == DeliveryNote.Status.READY:
            if not request.user.has_perm("delivery.pack_deliverynote"):
                raise PermissionDenied("Bạn không có quyền đóng gói phiếu giao.")
        else:
            require_perm(request.user, "delivery.change_deliverynote")

        needs_decision = None
        already = False

        if to_status == DeliveryNote.Status.FAILED:
            # BR-GH-04: mark_failed trả (note, needs_decision)
            note, needs_decision = services.mark_failed(note=note, actor=request.user)
        else:
            note, already = services.advance_status(
                note=note, to_status=to_status, actor=request.user, from_status=from_status
            )

        data = self.get_serializer(note).data
        data["already"] = already
        if needs_decision is not None:
            data["needs_decision"] = needs_decision
        return Response(data)

    @action(
        detail=True,
        methods=["get"],
        url_path="label",
        required_perms=("delivery.print_label",),
    )
    def label(self, request, pk=None):
        """Xem trước hoặc lấy dữ liệu in tem."""
        if not request.user.has_perm("delivery.print_label"):
            raise PermissionDenied("Bạn không có quyền in tem giao hàng.")
        note = self.get_object()
        print_no = request.query_params.get("print_no")
        from apps.delivery.labels import services as label_services
        data = label_services.get_label_data(note, print_no=print_no)
        return Response(data)

    @action(
        detail=True,
        methods=["post"],
        url_path="label/print",
        required_perms=("delivery.print_label",),
    )
    def label_print(self, request, pk=None):
        """Ghi nhận lượt in tem (idempotent)."""
        if not request.user.has_perm("delivery.print_label"):
            raise PermissionDenied("Bạn không có quyền in tem giao hàng.")
        note = self.get_object()
        request_id = request.data.get("request_id") if request.data else None
        reason = request.data.get("reason", "FIRST") if request.data else "FIRST"
        from apps.delivery.labels import services as label_services
        lp, duplicate = label_services.record_print(
            note, request.user, request_id=request_id, reason=reason
        )
        resp_data = {
            "print_no": lp.print_no,
            "printed_at": lp.printed_at.isoformat(),
            "is_reprint": lp.print_no > 1,
            "duplicate": duplicate,
        }
        return Response(
            resp_data,
            status=status.HTTP_200_OK if duplicate else status.HTTP_201_CREATED,
        )
