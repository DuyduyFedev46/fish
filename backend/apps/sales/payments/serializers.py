"""
Serializer hoá đơn bán & giao dịch thanh toán. `unit_cost` trên SalesInvoiceLineBatch là
nhạy cảm (giá vốn) — ẩn với ai không có view_costprice (spec 1.6). Read-only (BR-PQ-11).
"""
from rest_framework import serializers

from apps.common.api import CostFieldSerializerMixin
from apps.sales.customers.permissions import customer_hidden_reason
from apps.sales.utils import money_str
from apps.sales.models import (
    PaymentTransaction,
    SalesInvoice,
    SalesInvoiceLine,
    SalesInvoiceLineBatch,
)


class SalesInvoiceLineBatchSerializer(CostFieldSerializerMixin, serializers.ModelSerializer):
    sensitive_fields = ("unit_cost",)

    class Meta:
        model = SalesInvoiceLineBatch
        fields = ["id", "invoice_line", "batch", "component_item", "qty", "unit_cost"]


class SalesInvoiceLineSerializer(serializers.ModelSerializer):
    batch_allocations = SalesInvoiceLineBatchSerializer(many=True, read_only=True)
    item_code = serializers.CharField(source="item.code", read_only=True)

    class Meta:
        model = SalesInvoiceLine
        fields = ["id", "item", "item_code", "qty", "rate", "amount", "batch_allocations"]


class SalesInvoiceSerializer(serializers.ModelSerializer):
    lines = SalesInvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = SalesInvoice
        fields = [
            "id", "code", "sales_order", "customer", "issued_at", "amount",
            "payment_txn_ref", "payment_method", "status", "lines",
        ]
        read_only_fields = fields


class SalesInvoiceListSerializer(CostFieldSerializerMixin, serializers.ModelSerializer):
    """
    R13 — một dòng danh sách hoá đơn bán (W5j). Cần queryset có annotate `cogs` (xem `invoice_list.with_cogs`).

    `cogs` và `gross_profit` (= amount − cogs, không làm tròn — cùng cách tính với báo cáo) là giá vốn/lãi: chỉ người có `view_costprice` thấy, người khác KHÔNG có key
    (BR-PQ-15). `customer_name` là dữ liệu khách: null khi thiếu V2 `sales.view_order_customer_info` (PV-07, thay `view_customer_list` của M1) hoặc `pii_visible=False` (SR-PII-02); `customer_hidden_reason` cho biết lý do. Không có SĐT/địa chỉ.
    """

    sensitive_fields = ("cogs", "gross_profit")

    order_code = serializers.CharField(source="sales_order.code", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    amount = serializers.SerializerMethodField()
    cogs = serializers.SerializerMethodField()
    gross_profit = serializers.SerializerMethodField()
    customer_hidden_reason = serializers.SerializerMethodField()

    class Meta:
        model = SalesInvoice
        fields = [
            "id", "code", "sales_order", "order_code", "customer_name", "customer_hidden_reason", "issued_at",
            "amount", "status", "status_label", "cogs", "gross_profit",
        ]
        read_only_fields = fields

    def get_amount(self, invoice):
        return money_str(invoice.amount)

    def get_cogs(self, invoice):
        return money_str(invoice.cogs)

    def get_gross_profit(self, invoice):
        return money_str(invoice.amount - invoice.cogs)

    def get_customer_hidden_reason(self, invoice):
        request = self.context.get("request")
        return customer_hidden_reason(getattr(request, "user", None), invoice)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # PV-07: tên khách chỉ cho người có V2, rồi mới tới cửa sổ (`pii_visible`).
        if ret["customer_hidden_reason"] is not None:
            ret["customer_name"] = None
        return ret


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """
    S12 — một dòng hàng chờ thanh toán lệch (và chi tiết giao dịch). Chỉ Chủ đọc được endpoint.
    Không có field giá vốn nào (chỉ tiền khách trả / tổng đơn).
    `order` = null khi giao dịch chưa gắn đơn (UNMATCHED). `resolution_status` = null khi khớp.
    """

    amount = serializers.SerializerMethodField()
    match_status_label = serializers.CharField(source="get_match_status_display", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    resolution_label = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    resolved_by = serializers.SerializerMethodField()
    refundable_amount = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = PaymentTransaction
        fields = [
            "id", "bank_txn_id", "amount", "received_at", "match_status", "match_status_label",
            "source", "source_label", "environment", "duplicate_warning", "order",
            "resolution_status", "resolution", "resolution_label", "resolved_by", "resolved_at",
            "resolution_note", "refundable_amount", "available_actions",
        ]
        read_only_fields = fields

    def get_amount(self, obj):
        return money_str(obj.amount)

    def get_resolution_label(self, obj):
        return obj.get_resolution_display() if obj.resolution else ""

    def get_order(self, obj):
        from .services import order_paid_total

        order = obj.sales_order
        if order is None:
            return None
        return {
            "id": order.pk, "code": order.code, "status": order.status,
            "total_amount": money_str(order.total_amount),
            "paid_total": money_str(order_paid_total(order)),
        }

    def get_resolved_by(self, obj):
        user = obj.resolved_by
        if user is None:
            return None
        profile = getattr(user, "staff_profile", None)
        return {"id": user.pk, "display_name": getattr(profile, "display_name", "") or user.username}

    def get_refundable_amount(self, obj):
        from apps.sales.refunds.services import payment_refundable_amount

        return money_str(payment_refundable_amount(payment=obj))

    def get_available_actions(self, obj):
        from .services import payment_available_actions

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None:
            return []
        return payment_available_actions(payment=obj, user=user)
