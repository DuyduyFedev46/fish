"""
API nội bộ — đơn hàng. READ-ONLY (Hệ thống tạo, BR-PQ-11).
Tầng 2: cancel_paid_order; confirm_payment_manual (S11, BR-TT-07/08).
Tầng 3: nv_giao chỉ thấy đơn của phiếu giao gán cho mình (BR-PQ-12, S5).

S10: `GET /api/sales/orders/?status=BOOKED,PAID&date_from=&date_to=&q=&page=` (20 dòng/trang)
và `GET /api/sales/orders/{id}/` (chi tiết + `available_actions`).
S11: `POST /api/sales/orders/{id}/confirm-payment` (chạy chung service với webhook SePay).
ERP theo design Lô 3 (R3, 02b §3.8): mỗi dòng danh sách có `reason`; thêm lọc `customer=<id>` (đòi quyền xem
khách hàng, 403 nếu thiếu) và `batch=<pk>` (đơn có phân bổ từ lô). Sai định dạng → 400 `INVALID_FILTER`.
"""
import datetime

from django.db.models import Exists, OuterRef, Q, Subquery
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ai.declare import AiDeclarable, AiMeta
from apps.common.api import (
    BusinessModelPermissions,
    NoStoreMixin,
    StandardPagination,
    has_full_delivery_scope,
    require_perm,
)
from apps.common.exceptions import BusinessError
from apps.common.params import parse_positive_id
from apps.delivery.models import DeliveryNote
from apps.delivery.pii_scope import annotate_order_pii_visible
from apps.sales.models import Customer, PaymentTransaction, SalesOrder, SalesOrderLineBatch
from apps.sales.payments import services as payment_services
from apps.sales.utils import ZERO, fold_text, money_str

from . import services
from .scope import can_filter_orders_by_customer, scope_orders_for
from .serializers import SalesOrderDetailSerializer, SalesOrderListSerializer

INVALID_FILTER = "INVALID_FILTER"
# Giao dịch lệch CÒN MỞ trong hàng chờ Chủ (BR-TT-04/05/10, S12 BR-TT-09: đã xử lý thì bỏ)
# hoặc phiếu giao thất bại (BR-GH-04) → cần chú ý.


class InvalidFilter(Exception):
    pass


def _parse_date(raw, name):
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        raise InvalidFilter(f"Tham số {name} phải là ngày dạng YYYY-MM-DD.")


def _parse_positive_int(raw, name):
    """Tham số id: số nguyên dương (chuỗi rỗng đã được bỏ qua trước khi gọi). Quy tắc ở `apps/common/params.py`."""
    try:
        return parse_positive_id(raw)
    except ValueError:
        raise InvalidFilter(f"Tham số {name} phải là số nguyên dương.")


def _customer_ids_by_name(q):
    """L7: tên khách chứa `q`, không dấu + không phân biệt hoa thường (chạy giống nhau trên
    SQLite/Postgres, không cần extension `unaccent`). Quét tên khách ở Python — đủ cho quy mô
    vựa; phạm vi NV giao (S5) vẫn do get_queryset lọc sau."""
    needle = fold_text(q)
    return [pk for pk, name in Customer.objects.values_list("pk", "name") if needle in fold_text(name)]


class SalesOrderViewSet(NoStoreMixin, AiDeclarable, viewsets.ReadOnlyModelViewSet):
    ai = AiMeta(keywords=("tra đơn",))
    queryset = SalesOrder.objects.select_related("customer").all()
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    custom_perm_actions = ("cancel", "confirm_payment")

    def get_serializer_class(self):
        return SalesOrderListSerializer if self.action == "list" else SalesOrderDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            latest_note = DeliveryNote.objects.filter(
                sales_invoice__sales_order=OuterRef("pk")
            ).order_by("-id")
            # `reason` (R3) đọc payments / phiếu giao / chứng từ đảo qua prefetch: không N+1.
            qs = qs.select_related("invoice").prefetch_related(
                "payments", "invoice__credit_notes", "invoice__delivery_notes",
            ).annotate(
                delivery_status=Subquery(latest_note.values("status")[:1]),
                needs_attention=Exists(
                    PaymentTransaction.objects.filter(
                        sales_order=OuterRef("pk"),
                        resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
                    )
                ) | Exists(latest_note.filter(status=DeliveryNote.Status.FAILED)),
            )
        else:
            qs = qs.select_related("invoice").prefetch_related(
                "lines__item",
                "lines__batch_allocations__batch",
                "payments",
                "invoice__lines__batch_allocations__batch",
                "invoice__refunds__created_by__staff_profile",
                "invoice__refunds__confirmed_by__staff_profile",
                "invoice__delivery_notes__assigned_to__staff_profile",
                "invoice__delivery_notes__returns",
            )
        # S5 / BR-PQ-12 (nv_giao) và CS-01 / BR-GH-18 (cskh): phạm vi dòng dùng chung, xem scope.py.
        user = self.request.user
        qs = scope_orders_for(user, qs)
        if not has_full_delivery_scope(user):
            # SR-PII-02: đơn của phiếu đã kết thúc quá cửa sổ thì serializer ẩn dữ liệu khách.
            qs = annotate_order_pii_visible(user, qs)
        return qs

    def list(self, request, *args, **kwargs):
        if request.query_params.get("customer", "").strip() and not can_filter_orders_by_customer(request.user):
            # R3: lọc theo khách là xem dữ liệu khách, kiểm quyền TRƯỚC khi đọc tham số khác.
            raise PermissionDenied("Thiếu quyền xem khách hàng.")
        try:
            self.queryset_filters = self._filters(
                request.query_params, restrict_customer_search=not has_full_delivery_scope(request.user)
            )
        except InvalidFilter as exc:
            return Response({"detail": str(exc), "code": INVALID_FILTER}, status=400)
        return super().list(request, *args, **kwargs)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            queryset = queryset.filter(self.queryset_filters)
        return queryset

    @staticmethod
    def _filters(params, *, restrict_customer_search=False):
        """UC-02: lọc trạng thái (nhiều, cách dấu phẩy), theo ngày tạo (giờ VN), tìm mã đơn/SĐT/tên khách.

        `restrict_customer_search` (SR-PII-02): tìm theo SĐT/tên chỉ khớp đơn mà người gọi còn được xem dữ liệu
        khách (`pii_visible`), để không dò ra SĐT của đơn đã quá cửa sổ. Tìm theo mã đơn không bị giới hạn."""
        cond = Q()
        statuses = [s.strip() for s in params.get("status", "").split(",") if s.strip()]
        if statuses:
            cond &= Q(status__in=statuses)
        if params.get("date_from"):
            cond &= Q(created_at__date__gte=_parse_date(params["date_from"], "date_from"))
        if params.get("date_to"):
            cond &= Q(created_at__date__lte=_parse_date(params["date_to"], "date_to"))
        customer = params.get("customer", "").strip()
        if customer:
            cond &= Q(customer_id=_parse_positive_int(customer, "customer"))
        batch = params.get("batch", "").strip()
        if batch:
            # Exists (không join) để đơn nhiều dòng cùng lô chỉ hiện một lần.
            cond &= Exists(SalesOrderLineBatch.objects.filter(
                order_line__order=OuterRef("pk"), batch_id=_parse_positive_int(batch, "batch"),
            ))
        q = params.get("q", "").strip()
        if q:
            by_customer = (
                Q(phone__contains=q) | Q(customer__phone__contains=q)
                | Q(customer_id__in=_customer_ids_by_name(q))
            )
            if restrict_customer_search:
                by_customer &= Q(pii_visible=True)
            cond &= Q(code__icontains=q) | by_customer
        return cond

    @action(detail=True, methods=["post"], required_perms=("sales.cancel_paid_order",))
    def cancel(self, request, pk=None):
        """Huỷ đơn hàng đã thanh toán và sinh phiếu hoàn tiền (BR-GH-07/05)."""
        require_perm(request.user, "sales.cancel_paid_order")
        data = request.data if isinstance(request.data, dict) else {}
        reason_code = data.get("reason_code")
        note_text = (data.get("note") or "").strip()
        if reason_code not in services.CANCEL_REASON_CODES:
            raise BusinessError("Lý do huỷ không hợp lệ.", code="BR-HT-05")
        if reason_code == "OTHER" and not note_text:
            raise BusinessError(
                "Bắt buộc nhập ghi chú khi chọn lý do khác (OTHER).", code="BR-HT-05",
            )
        label = services.CANCEL_REASON_LABELS[reason_code]
        reason = f"{label} — {note_text}" if note_text else label

        result = services.cancel_paid_order(
            order=self.get_object(), actor=request.user, reason=reason, reason_code=reason_code,
            cancel_note=note_text,
        )
        order = result["order"]
        note = result["delivery_note"]
        invoice = getattr(order, "invoice", None)
        from apps.sales.refunds.services import refundable_amount

        suggest = refundable_amount(invoice=invoice) if invoice is not None else ZERO
        return Response({
            "order_status": order.status,
            "stock_restored": result["stock_restored"],
            "delivery_status": note.status if note is not None else None,
            "suggest_refund_amount": money_str(suggest),
            "invoice_id": invoice.pk if invoice is not None else None,
        })

    @action(detail=True, methods=["post"], url_path="confirm-payment", required_perms=("sales.confirm_payment_manual",))
    def confirm_payment(self, request, pk=None):
        """Xác nhận thanh toán thủ công cho đơn hàng (BR-TT-07/08)."""
        require_perm(request.user, "sales.confirm_payment_manual")
        data = request.data if isinstance(request.data, dict) else {}
        payment, duplicate = payment_services.confirm_payment_manual(
            order=self.get_object(),
            bank_txn_id=data.get("bank_txn_id"),
            amount=data.get("amount"),
            actor=request.user,
        )
        outcome = payment_services.payment_outcome(payment)
        body = {"result": outcome.pop("result"), "duplicate": duplicate, **outcome}
        for key in ("paid_total", "missing", "overpaid_amount"):
            if key in body:
                body[key] = money_str(body[key])
        return Response(body)
