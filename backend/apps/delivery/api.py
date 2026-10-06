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
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api import (
    BusinessModelPermissions,
    DocumentViewSet,
    NoStoreMixin,
    StandardPagination,
    has_full_delivery_scope,
    require_perm,
)

from apps.common.exceptions import BusinessError
from apps.common.params import parse_positive_id
from apps.sales.orders import completion

from . import services
from .models import DeliveryNote
from .serializers import CourierDeliveryNoteListSerializer, DeliveryNoteDetailSerializer, DeliveryNoteSerializer

INVALID_FILTER = "INVALID_FILTER"


def _positive_int_param(raw, name):
    """Giá trị lọc là số nguyên dương; rỗng nghĩa là không lọc (trả None); sai thì 400 INVALID_FILTER."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return parse_positive_id(raw)  # chỉ chữ số ASCII, tối đa int64 (apps/common/params.py)
    except ValueError:
        raise BusinessError(f"Giá trị lọc `{name}` không hợp lệ.", code=INVALID_FILTER)


class DeliveryNoteViewSet(NoStoreMixin, DocumentViewSet):
    queryset = DeliveryNote.objects.select_related(
        "sales_invoice__sales_order__customer",
        "assigned_to__staff_profile",
        "confirmed_by",
    ).prefetch_related(
        "label_prints",
        "sales_invoice__lines__batch_allocations__component_item",
        "sales_invoice__lines__batch_allocations__batch",
    ).all()
    serializer_class = DeliveryNoteSerializer
    pagination_class = StandardPagination
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("set_status", "label", "label_print", "label_void", "lookup")

    # BR-PQ-14 / BR-GH-06: trạng thái & người giao chỉ đổi qua action nghiệp vụ.
    locked_fields = (
        "status", "assigned_to", "failed_attempts", "completed_at", "sales_invoice",
        "confirmed_at", "confirmed_by", "confirm_skipped", "recipient_name", "recipient_phone",
        "failure_reason", "failure_note",  # BR-GH-22: chỉ ghi qua `status` (mark_failed)
        "delivery_started_at", "failed_at",  # #18: hệ thống ghi khi đổi trạng thái
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DeliveryNoteDetailSerializer
        if self.action == "list" and (self.request.query_params.get("assigned_to") or "").strip() == "me":
            return CourierDeliveryNoteListSerializer  # #17 (R4b): chỉ phiếu của chính người gọi, có `phone`
        return DeliveryNoteSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # SR-PII-02: người không có full scope (NV giao) bị ẩn dữ liệu khách của phiếu quá cửa sổ.
        context["pii_restricted"] = not has_full_delivery_scope(self.request.user)
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if has_full_delivery_scope(user):
            return qs
        return qs.filter(assigned_to=user)  # nv_giao: chỉ phiếu của mình (dữ liệu khách: pii_scope.py)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            # S14-AC2 / CS-02: lọc theo trạng thái (nhiều, cách dấu phẩy)
            status_param = self.request.query_params.get("status", "")
            statuses = [s.strip() for s in status_param.split(",") if s.strip()]
            if statuses:
                queryset = queryset.filter(status__in=statuses)

            # R4: assigned_to=me|<id>, order=<id>. Phạm vi dòng (Tầng 3) đã áp ở get_queryset.
            queryset = self._filter_assigned_to(queryset)
            order_id = _positive_int_param(self.request.query_params.get("order"), "order")
            if order_id is not None:
                queryset = queryset.filter(sales_invoice__sales_order_id=order_id)

            # ED-07-BE (Lô 17a): `code` khớp ĐÚNG mã phiếu (không phân biệt hoa thường), trên queryset đã có phạm vi:
            # người giao tra mã phiếu của người khác nhận `count: 0`, giống mã không tồn tại.
            code = (self.request.query_params.get("code") or "").strip()
            if code:
                queryset = queryset.filter(code__iexact=code)

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

    def _filter_assigned_to(self, queryset):
        raw = (self.request.query_params.get("assigned_to") or "").strip()
        if not raw:
            return queryset
        user = self.request.user
        if raw == "me":
            return queryset.filter(assigned_to=user)
        target = _positive_int_param(raw, "assigned_to")
        # NV giao chỉ được lọc theo chính mình; hỏi người khác là 403 (không tiết lộ phiếu của họ).
        if not has_full_delivery_scope(user) and target != user.pk:
            raise PermissionDenied("Bạn chỉ xem được phiếu giao của mình.")
        return queryset.filter(assigned_to_id=target)

    @action(
        detail=True,
        methods=["post"],
        url_path="assign",
        required_perms=("delivery.assign_deliverynote",),
    )
    def assign(self, request, pk=None):
        """BR-GH-23 (B6): giao hoặc đổi người giao. Body: `assigned_to` (id), tuỳ chọn `expected_assigned_to`."""
        note = self.get_object()
        data = request.data if hasattr(request.data, "get") else {}
        assignee = services.resolve_assignee(data.get("assigned_to"))
        kwargs = {}
        if "expected_assigned_to" in data:
            kwargs["expected_assignee_id"] = services.validate_expected_assignee(data.get("expected_assigned_to"))
        note, already = services.assign_deliverer(
            note=note, assignee=assignee, actor=request.user, **kwargs
        )
        note = self.get_queryset().get(pk=note.pk)
        body = self.get_serializer(note).data
        body["already"] = already
        return Response(body)

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
            data_in = request.data if hasattr(request.data, "get") else {}
            # API luôn kiểm lý do (BR-GH-22): thiếu hoặc null đều là "chưa chọn", không đi đường nội bộ cũ.
            note, needs_decision = services.mark_failed(
                note=note, actor=request.user,
                reason=data_in.get("failure_reason") or "",
                reason_note=data_in.get("failure_note"),
            )
        else:
            note, already = services.advance_status(
                note=note, to_status=to_status, actor=request.user, from_status=from_status
            )

        data = self.get_serializer(note).data
        data["already"] = already
        data["order_status"] = completion.current_order_status(note)  # W37: đọc mới từ DB, mọi nhánh
        if needs_decision is not None:
            data["needs_decision"] = needs_decision
        return Response(data)

    @action(
        detail=False,
        methods=["get"],
        url_path="lookup",
        required_perms=("delivery.print_label",),
    )
    def lookup(self, request):
        """Tra mã trên tem để mở đúng phiếu soạn (CS-17). Chỉ trả mã phiếu, trạng thái, số lần in."""
        if not request.user.has_perm("delivery.print_label"):
            raise PermissionDenied("Bạn không có quyền tra tem giao hàng.")
        if not request.user.has_perm("delivery.view_deliverynote"):
            raise PermissionDenied("Bạn không có quyền xem phiếu giao.")
        from apps.delivery.labels import services as label_services
        return Response(label_services.lookup_label(request.query_params.get("code"), queryset=self.get_queryset()))

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

    @action(
        detail=True,
        methods=["post"],
        url_path="label/void",
        required_perms=("delivery.print_label",),
    )
    def label_void(self, request, pk=None):
        """Xác nhận đã huỷ tem giấy (CS-14, 02b §4.5)."""
        if not request.user.has_perm("delivery.print_label"):
            raise PermissionDenied("Bạn không có quyền huỷ tem giao hàng.")
        note = self.get_object()
        print_no = request.data.get("print_no") if request.data else None
        from apps.delivery.labels import services as label_services
        res = label_services.void_label(note, request.user, print_no=print_no)
        return Response(res, status=status.HTTP_200_OK)



class DeliverersView(APIView):
    """
    GET /api/delivery/deliverers/ (BR-GH-23, T7): người giao đang làm kèm số phiếu DELIVERING và READY.
    Chỉ người có quyền giao phiếu mới xem. Không trả SĐT hay tên đăng nhập (bất biến 9).
    """

    permission_classes = [IsAuthenticated]
    # Khai ở mức lớp để registry AI chỉ đưa lệnh `delivery.deliverers` cho người có quyền (mẫu apps/reports/api.py).
    required_perms = ("delivery.assign_deliverynote",)

    def get(self, request):
        require_perm(request.user, "delivery.assign_deliverynote")
        rows = [
            {
                "id": u.pk,
                "display_name": services.staff_display_name(u),
                "delivering_count": u.delivering_count,
                "ready_count": u.ready_count,
            }
            for u in services.list_deliverers()
        ]
        response = Response(rows)
        response["Cache-Control"] = "no-store"
        return response
