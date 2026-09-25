"""
API nội bộ — đơn hàng. READ-ONLY (Hệ thống tạo, BR-PQ-11).
Tầng 2: cancel_paid_order; confirm_payment_manual (S11, BR-TT-07/08).
Tầng 3: nv_giao chỉ thấy đơn của phiếu giao gán cho mình (BR-PQ-12, S5).

S10: `GET /api/sales/orders/?status=BOOKED,PAID&date_from=&date_to=&q=&page=` (20 dòng/trang)
và `GET /api/sales/orders/{id}/` (chi tiết + `available_actions`).
S11: `POST /api/sales/orders/{id}/confirm-payment` (chạy chung service với webhook SePay).
"""
import datetime

from django.db.models import Exists, OuterRef, Q, Subquery
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import (
    BusinessModelPermissions,
    StandardPagination,
    has_full_delivery_scope,
    require_perm,
)
from apps.delivery.models import DeliveryNote
from apps.sales.models import Customer, PaymentTransaction, SalesOrder
from apps.sales.payments import services as payment_services
from apps.sales.utils import fold_text, money_str

from . import services
from .serializers import SalesOrderDetailSerializer, SalesOrderListSerializer

INVALID_FILTER = "INVALID_FILTER"
# Giao dịch lệch chờ Chủ (BR-TT-04/05) hoặc phiếu giao thất bại (BR-GH-04) → cần chú ý.
ATTENTION_PAYMENT_STATUSES = (
    PaymentTransaction.MatchStatus.UNDERPAID,
    PaymentTransaction.MatchStatus.ORPHAN,
)


class InvalidFilter(Exception):
    pass


def _parse_date(raw, name):
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        raise InvalidFilter(f"Tham số {name} phải là ngày dạng YYYY-MM-DD.")


def _customer_ids_by_name(q):
    """L7: tên khách chứa `q`, không dấu + không phân biệt hoa thường (chạy giống nhau trên
    SQLite/Postgres, không cần extension `unaccent`). Quét tên khách ở Python — đủ cho quy mô
    vựa; phạm vi NV giao (S5) vẫn do get_queryset lọc sau."""
    needle = fold_text(q)
    return [pk for pk, name in Customer.objects.values_list("pk", "name") if needle in fold_text(name)]


class SalesOrderViewSet(viewsets.ReadOnlyModelViewSet):
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
            qs = qs.annotate(
                delivery_status=Subquery(latest_note.values("status")[:1]),
                needs_attention=Exists(
                    PaymentTransaction.objects.filter(
                        sales_order=OuterRef("pk"), match_status__in=ATTENTION_PAYMENT_STATUSES
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
        # S5 / BR-PQ-12: nv_giao chỉ thấy đơn của phiếu giao gán cho mình.
        user = self.request.user
        if has_full_delivery_scope(user):
            return qs
        return qs.filter(invoice__delivery_notes__assigned_to=user).distinct()

    def list(self, request, *args, **kwargs):
        try:
            self.queryset_filters = self._filters(request.query_params)
        except InvalidFilter as exc:
            return Response({"detail": str(exc), "code": INVALID_FILTER}, status=400)
        return super().list(request, *args, **kwargs)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            queryset = queryset.filter(self.queryset_filters)
        return queryset

    @staticmethod
    def _filters(params):
        """UC-02: lọc trạng thái (nhiều, cách dấu phẩy), theo ngày tạo (giờ VN), tìm mã đơn/SĐT/tên khách."""
        cond = Q()
        statuses = [s.strip() for s in params.get("status", "").split(",") if s.strip()]
        if statuses:
            cond &= Q(status__in=statuses)
        if params.get("date_from"):
            cond &= Q(created_at__date__gte=_parse_date(params["date_from"], "date_from"))
        if params.get("date_to"):
            cond &= Q(created_at__date__lte=_parse_date(params["date_to"], "date_to"))
        q = params.get("q", "").strip()
        if q:
            cond &= (
                Q(code__icontains=q) | Q(phone__contains=q) | Q(customer__phone__contains=q)
                | Q(customer_id__in=_customer_ids_by_name(q))
            )
        return cond

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        require_perm(request.user, "sales.cancel_paid_order")
        services.cancel_paid_order(
            order=self.get_object(), actor=request.user, reason=request.data.get("reason", "")
        )
        return Response(self.get_serializer(self.get_object()).data)  # đọc lại sau khi đổi

    @action(detail=True, methods=["post"], url_path="confirm-payment")
    def confirm_payment(self, request, pk=None):
        """S11 / E-05: Chủ xác nhận đã nhận tiền cho đơn Giữ chỗ (BR-TT-07/08)."""
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
        for key in ("paid_total", "missing"):
            if key in body:
                body[key] = money_str(body[key])
        return Response(body)
