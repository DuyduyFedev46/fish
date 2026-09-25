"""
API nội bộ — hoá đơn bán (READ-ONLY, BR-PQ-11) + hàng chờ giao dịch lệch.

Xác nhận thanh toán thủ công (E-05, BR-TT-08) nay gắn vào ĐƠN:
`POST /api/sales/orders/{id}/confirm-payment` (orders/api.py, S11). Action cũ trên hoá đơn
đã gỡ — đơn chưa trả thì chưa có hoá đơn để bấm (A2).
"""
from rest_framework import viewsets

from apps.common.api import BusinessModelPermissions
from apps.sales.models import PaymentTransaction, SalesInvoice

from .serializers import PaymentTransactionSerializer, SalesInvoiceSerializer


class SalesInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesInvoice.objects.select_related("customer", "sales_order").all()
    serializer_class = SalesInvoiceSerializer
    permission_classes = [BusinessModelPermissions]


class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """Hàng chờ Chủ xử lý case lệch (UNDERPAID/ORPHAN/UNMATCHED)."""

    queryset = PaymentTransaction.objects.select_related("sales_order").all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [BusinessModelPermissions]
