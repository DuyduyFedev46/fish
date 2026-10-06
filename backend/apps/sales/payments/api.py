"""
API nội bộ — hoá đơn bán (READ-ONLY, BR-PQ-11) + hàng chờ giao dịch lệch.

Xác nhận thanh toán thủ công (E-05, BR-TT-08) nay gắn vào ĐƠN:
`POST /api/sales/orders/{id}/confirm-payment` (orders/api.py, S11). Action cũ trên hoá đơn
đã gỡ — đơn chưa trả thì chưa có hoá đơn để bấm (A2).
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ai.declare import AiDeclarable, AiMeta
from apps.common.api import (
    VIEW_COSTPRICE_PERM, BusinessModelPermissions, NoStoreMixin, StandardPagination, require_perm,
)
from apps.sales.models import PaymentTransaction, SalesInvoice
from apps.sales.utils import money_str

from . import services
from .late_serializers import RecordLatePaymentInput
from .invoice_list import build_totals, filter_invoices, scope_invoices_for, with_cogs
from .serializers import PaymentTransactionSerializer, SalesInvoiceListSerializer, SalesInvoiceSerializer


class SalesInvoiceViewSet(NoStoreMixin, viewsets.ReadOnlyModelViewSet):
    """
    Hoá đơn bán (read-only, BR-PQ-11).

    R13: `GET /api/sales/invoices/?status=ISSUED[,CANCELLED]&date_from=&date_to=&q=&page=` (20 dòng/trang) trả
    `{"count","next","previous","results":[…],"totals":{"amount","gross_profit"}}`. `cogs`, `gross_profit` (dòng và
    tổng) chỉ khi có `view_costprice`. Có tên khách nên mọi response `no-store`; hoá đơn lọc theo phạm vi dòng.
    `customer_name` chỉ có giá trị khi người gọi có `sales.view_customer_list` (M1); người khác nhận null.
    `GET …/{id}/` giữ serializer cũ.
    """

    queryset = SalesInvoice.objects.select_related("customer", "sales_order").all()
    serializer_class = SalesInvoiceSerializer
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        return SalesInvoiceListSerializer if self.action == "list" else SalesInvoiceSerializer

    def get_queryset(self):
        queryset = scope_invoices_for(self.request.user, super().get_queryset())
        if self.action == "list":
            queryset = with_cogs(queryset)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            queryset = filter_invoices(queryset, self.request.query_params)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())  # dựng đúng một lần, dùng cho cả trang và tổng
        page = self.paginate_queryset(queryset)
        response = self.get_paginated_response(self.get_serializer(page, many=True).data)
        totals = build_totals(queryset, with_profit=request.user.has_perm(VIEW_COSTPRICE_PERM))
        response.data["totals"] = {key: money_str(value) for key, value in totals.items()}
        return response


class PaymentTransactionViewSet(AiDeclarable, viewsets.ReadOnlyModelViewSet):
    """
    S12 — hàng chờ thanh toán lệch (UNDERPAID/ORPHAN/UNMATCHED/OVERPAID), BR-TT-09.

    `GET /api/sales/payments/?resolution_status=OPEN[,RESOLVED]&match_status=…&page=`
    `GET /api/sales/payments/{id}/`
    `POST /api/sales/payments/{id}/resolve` {"action": "ATTACH_TO_ORDER"|"CONFIRM_ORDER", "order_id", "note"}

    Mọi thao tác (kể cả xem) đòi `sales.confirm_payment_manual` — hàng chờ lệch là việc của
    Chủ (BR-TT-07, S12-AC7). Quản lý vẫn thấy giao dịch của đơn trong chi tiết đơn (S10).
    """

    queryset = PaymentTransaction.objects.select_related(
        "sales_order", "resolved_by__staff_profile"
    ).all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [BusinessModelPermissions]
    pagination_class = StandardPagination
    custom_perm_actions = ("resolve",)

    def check_permissions(self, request):
        super().check_permissions(request)  # 401 khi chưa đăng nhập
        require_perm(request.user, services.RESOLVE_PERM)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action != "list":
            return queryset
        params = self.request.query_params
        for name in ("resolution_status", "match_status", "source", "environment"):
            values = [v.strip().upper() for v in params.get(name, "").split(",") if v.strip()]
            if values:
                queryset = queryset.filter(**{f"{name}__in": values})
        return queryset

    @action(detail=True, methods=["post"], required_perms=("sales.confirm_payment_manual",))
    def resolve(self, request, pk=None):
        """Xử lý giao dịch thanh toán chuyển khoản lệch (BR-TT-09)."""
        data = request.data if hasattr(request.data, "get") else {}
        result = services.resolve_payment(
            payment=self.get_object(),
            action=data.get("action"),
            order_id=data.get("order_id"),
            note=data.get("note", ""),
            actor=request.user,
        )
        return Response(result)

    @action(
        detail=False, methods=["post"], url_path="record-late",
        required_perms=("sales.confirm_payment_manual",),
        input_serializer=RecordLatePaymentInput,
        ai=AiMeta(keywords=("ghi tiền về muộn",), max_level="C"),
    )
    def record_late(self, request):
        """
        Ghi tay khoản tiền về muộn khi webhook/IPN không báo (BR-TT-18, #15): 201 dòng mới, 200 `duplicate: true`.
        Không đổi đơn, kho hay hoá đơn; không có ô ghi chú.
        """
        payload = RecordLatePaymentInput(data=request.data if hasattr(request.data, "get") else {})
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        payment, duplicate = services.record_late_payment(
            bank_txn_id=data.get("bank_txn_id"), amount=data.get("amount"), received_at=data.get("received_at"),
            order_code=data.get("order_code"), actor=request.user,
            acknowledge_possible_duplicate=data.get("acknowledge_possible_duplicate", False),
        )
        payment = self.get_queryset().get(pk=payment.pk)
        body = {"duplicate": duplicate, "payment": self.get_serializer(payment).data}
        return Response(body, status=200 if duplicate else 201)
