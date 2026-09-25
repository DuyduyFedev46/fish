"""
API nội bộ — hoá đơn bán (READ-ONLY, BR-PQ-11) + hàng chờ giao dịch lệch.
Tầng 2: confirm_payment_manual (chỉ Chủ, E-05).
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, require_perm
from apps.sales.models import PaymentTransaction, SalesInvoice

from . import services
from .serializers import PaymentTransactionSerializer, SalesInvoiceSerializer


class SalesInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesInvoice.objects.select_related("customer", "sales_order").all()
    serializer_class = SalesInvoiceSerializer
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("confirm_payment",)

    @action(detail=True, methods=["post"], url_path="confirm-payment")
    def confirm_payment(self, request, pk=None):
        """Xác nhận thanh toán thủ công khi webhook không tới (E-05) — chỉ Chủ."""
        require_perm(request.user, "sales.confirm_payment_manual")
        invoice = self.get_object()
        order = invoice.sales_order
        amount = Decimal(str(request.data.get("amount", order.total_amount)))
        payment = services.confirm_payment(
            order=order,
            bank_txn_id=request.data["bank_txn_id"],
            amount=amount,
            received_at=timezone.now(),
            source=PaymentTransaction.Source.MANUAL,
            actor=request.user,
        )
        return Response({"match_status": payment.match_status})


class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """Hàng chờ Chủ xử lý case lệch (UNDERPAID/ORPHAN/UNMATCHED)."""

    queryset = PaymentTransaction.objects.select_related("sales_order").all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [BusinessModelPermissions]
