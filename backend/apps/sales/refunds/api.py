"""
API nội bộ — phiếu hoàn tiền (P-07). Tầng 2: create_refund (Chủ + Quản lý) ≠
confirm_refund (chỉ Chủ, tiền rời túi) — BR-HT-07.

`POST /api/sales/refunds/create` nhận ĐÚNG MỘT trong `sales_invoice` / `payment_transaction`
(S13). Gắn giao dịch (hàng chờ lệch) đòi thêm `confirm_payment_manual` — việc của Chủ
(S13-AC6, BR-TT-09). `request_id` (UUID) gửi lại → 200 `duplicate: true`, vẫn 1 phiếu (Q12).
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, reject_protected_fields, require_perm
from apps.common.exceptions import BusinessError
from apps.sales.models import PaymentTransaction, Refund, SalesInvoice

from . import services
from .serializers import RefundSerializer


def _get_or_400(model, raw_pk, label):
    try:
        return model.objects.get(pk=int(raw_pk))
    except (TypeError, ValueError, model.DoesNotExist):
        raise BusinessError(f"{label} không tồn tại.", code=services.REFUND_SOURCE_CODE) from None


class RefundViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Refund.objects.select_related(
        "sales_invoice__sales_order__customer",
        "payment_transaction__sales_order__customer",
        "created_by__staff_profile", "confirmed_by__staff_profile",
    ).all()
    serializer_class = RefundSerializer
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("create_refund", "confirm", "mark_failed", "retry")

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            statuses = [
                s.strip().upper() for s in self.request.query_params.get("status", "").split(",")
                if s.strip()
            ]
            if statuses:
                queryset = queryset.filter(status__in=statuses)
        return queryset

    @action(detail=False, methods=["post"], url_path="create")
    def create_refund(self, request):
        require_perm(request.user, "sales.create_refund")
        data = request.data if hasattr(request.data, "get") else {}
        reject_protected_fields(data, actor=("created_by", "confirmed_by"))  # BR-PQ-16
        has_invoice = data.get("sales_invoice") not in (None, "")
        has_payment = data.get("payment_transaction") not in (None, "")
        if has_payment:
            # S13-AC6: hàng chờ lệch là việc của Chủ — kiểm quyền TRƯỚC mọi kiểm dữ liệu.
            require_perm(request.user, "sales.confirm_payment_manual")
        if has_invoice == has_payment:
            raise BusinessError(
                "Chỉ gửi một trong hai: sales_invoice hoặc payment_transaction."
                if has_invoice else "Thiếu sales_invoice hoặc payment_transaction.",
                code=services.REFUND_SOURCE_CODE,
            )
        request_id = services.parse_request_id(data.get("request_id"))
        amount = services.parse_refund_amount(data.get("amount"))
        reason = data.get("reason", "")
        if has_payment:
            payment = _get_or_400(PaymentTransaction, data.get("payment_transaction"), "Giao dịch")
            is_partial = data.get("is_partial")
            refund, duplicate = services.create_refund_for_payment(
                payment=payment, amount=amount, reason=reason, actor=request.user,
                is_partial=None if is_partial is None else bool(is_partial),
                request_id=request_id,
            )
        else:
            invoice = _get_or_400(SalesInvoice, data.get("sales_invoice"), "Hoá đơn")
            refund, duplicate = services.create_invoice_refund(
                invoice=invoice, amount=amount,
                is_partial=bool(data.get("is_partial", False)),
                reason=reason, actor=request.user, request_id=request_id,
            )
        body = self.get_serializer(refund).data
        if duplicate:
            return Response({**body, "duplicate": True}, status=200)
        return Response(body, status=201)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        require_perm(request.user, "sales.confirm_refund")
        refund = services.confirm_refund(
            refund=self.get_object(),
            bank_txn_ref=request.data.get("bank_txn_ref", ""),
            actor=request.user,
        )
        return Response(self.get_serializer(refund).data)

    @action(detail=True, methods=["post"], url_path="mark-failed")
    def mark_failed(self, request, pk=None):
        """S16: Chủ báo chuyển khoản thất bại (BR-HT-09) — tiền rời túi nên chỉ Chủ."""
        require_perm(request.user, "sales.confirm_refund")
        refund = services.mark_refund_failed(
            refund=self.get_object(), reason=request.data.get("reason", ""), actor=request.user,
        )
        return Response(self.get_serializer(refund).data)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """S16: Chủ thử chuyển lại phiếu Thất bại (BR-HT-09)."""
        require_perm(request.user, "sales.confirm_refund")
        refund = services.retry_refund(refund=self.get_object(), actor=request.user)
        return Response(self.get_serializer(refund).data)
