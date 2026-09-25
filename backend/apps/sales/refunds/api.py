"""
API nội bộ — phiếu hoàn tiền (P-07). Tầng 2: create_refund (Chủ + Quản lý) ≠
confirm_refund (chỉ Chủ, tiền rời túi) — BR-HT-07.
"""
from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, reject_protected_fields, require_perm
from apps.sales.models import Refund, SalesInvoice

from . import services
from .serializers import RefundSerializer


class RefundViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Refund.objects.select_related("sales_invoice").all()
    serializer_class = RefundSerializer
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("create_refund", "confirm")

    @action(detail=False, methods=["post"], url_path="create")
    def create_refund(self, request):
        require_perm(request.user, "sales.create_refund")
        reject_protected_fields(request.data, actor=("created_by", "confirmed_by"))  # BR-PQ-16
        invoice = get_object_or_404(SalesInvoice, pk=request.data["sales_invoice"])
        refund = services.create_refund(
            invoice=invoice,
            amount=Decimal(str(request.data["amount"])),
            is_partial=bool(request.data.get("is_partial", False)),
            reason=request.data.get("reason", ""),
            actor=request.user,
        )
        return Response(self.get_serializer(refund).data, status=201)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        require_perm(request.user, "sales.confirm_refund")
        refund = services.confirm_refund(
            refund=self.get_object(),
            bank_txn_ref=request.data.get("bank_txn_ref", ""),
            actor=request.user,
        )
        return Response(self.get_serializer(refund).data)
