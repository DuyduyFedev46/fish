"""
Serializer đơn hàng. Đơn read-only qua API (do Hệ thống tạo, BR-PQ-11); tạo đơn đi qua
Shop API + orders.services.create_order.

S10 (contract 02-stories.md): danh sách gọn cho thẻ/bảng, chi tiết đủ khách, dòng hàng,
phân bổ lô, hoá đơn, thanh toán, phiếu giao, hoàn tiền, `available_actions`.
L7 bổ sung (chỉ thêm key): `*_label` cạnh mã trạng thái lồng, `timeline` (xem timeline.py).
Tiền/kg là chuỗi thập phân (bất biến #7). `allocations[].unit_cost` là GIÁ VỐN — không có
key với người thiếu `inventory.view_costprice` (BR-PQ-15, CostFieldSerializerMixin).
"""
from rest_framework import serializers

from apps.common.api import CostFieldSerializerMixin
from apps.sales.models import SalesOrder
from apps.sales.utils import kg_str, money_str

from . import services
from .timeline import build_timeline


class MoneyField(serializers.Field):
    def to_representation(self, value):
        return money_str(value)


class KgField(serializers.Field):
    def to_representation(self, value):
        return kg_str(value)


class SalesOrderListSerializer(serializers.ModelSerializer):
    """Một dòng danh sách đơn. Cần queryset có annotate `delivery_status`, `needs_attention`."""

    status_label = serializers.CharField(source="get_status_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_phone = serializers.CharField(source="phone", read_only=True)
    total_amount = MoneyField(read_only=True)
    reserved_until = serializers.DateTimeField(source="booked_expires_at", read_only=True)
    delivery_status = serializers.CharField(read_only=True, allow_null=True)
    needs_attention = serializers.BooleanField(read_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            "id", "code", "status", "status_label", "customer_name", "customer_phone",
            "total_amount", "created_at", "reserved_until", "delivery_status", "needs_attention",
        ]
        read_only_fields = fields


class OrderLineSerializer(serializers.Serializer):
    no = serializers.IntegerField()
    item_code = serializers.CharField(source="line.item.code")
    item_name = serializers.CharField(source="line.item.name")
    qty_kg = KgField(source="line.qty")
    unit_price = MoneyField(source="line.rate")
    discount = MoneyField(source="line.discount_amount")
    line_total = MoneyField(source="line.amount")


class AllocationSerializer(CostFieldSerializerMixin, serializers.Serializer):
    """Phân bổ lô của đơn. `unit_cost` NHẠY CẢM — bị gỡ khỏi output khi thiếu view_costprice."""

    sensitive_fields = ("unit_cost",)

    line_no = serializers.IntegerField()
    batch_id = serializers.CharField(source="alloc.batch.batch_id")
    qty_kg = KgField(source="alloc.qty")
    unit_cost = MoneyField(source="alloc.unit_cost")


class SalesOrderDetailSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    total_amount = MoneyField(read_only=True)
    reserved_until = serializers.DateTimeField(source="booked_expires_at", read_only=True)
    customer = serializers.SerializerMethodField()
    lines = serializers.SerializerMethodField()
    allocations = serializers.SerializerMethodField()
    invoice = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()
    delivery = serializers.SerializerMethodField()
    refunds = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrder
        fields = [
            "id", "code", "status", "status_label", "total_amount", "created_at",
            "reserved_until", "customer", "lines", "allocations", "invoice", "payments",
            "delivery", "refunds", "available_actions", "timeline",
        ]
        read_only_fields = fields

    # --- helpers -------------------------------------------------------------
    @staticmethod
    def _invoice(order):
        return getattr(order, "invoice", None)

    @staticmethod
    def _numbered(rows):
        return list(enumerate(sorted(rows, key=lambda r: r.pk), start=1))

    # --- fields --------------------------------------------------------------
    def get_customer(self, order):
        return {
            "name": order.customer.name,
            "phone": order.phone,
            "address": order.delivery_address,
        }

    def get_lines(self, order):
        rows = [{"no": no, "line": line} for no, line in self._numbered(order.lines.all())]
        return OrderLineSerializer(rows, many=True).data

    def get_allocations(self, order):
        """Đã có hoá đơn → phân bổ lô ĐÃ BÁN (nguồn giá vốn, BR-BH-06); chưa → giữ chỗ theo lô."""
        invoice = self._invoice(order)
        source = invoice.lines.all() if invoice is not None else order.lines.all()
        rows = [
            {"line_no": no, "alloc": alloc}
            for no, line in self._numbered(source)
            for alloc in sorted(line.batch_allocations.all(), key=lambda a: a.pk)
        ]
        return AllocationSerializer(rows, many=True, context=self.context).data

    def get_invoice(self, order):
        invoice = self._invoice(order)
        if invoice is None:
            return None
        return {
            "id": invoice.pk,
            "code": invoice.code,
            "issued_at": serializers.DateTimeField().to_representation(invoice.issued_at),
        }

    def get_payments(self, order):
        dt = serializers.DateTimeField()
        return [
            {
                "id": p.pk,
                "bank_txn_id": p.bank_txn_id,
                "amount": money_str(p.amount),
                "match_status": p.match_status,
                "match_status_label": p.get_match_status_display(),
                "source": p.source,
                "source_label": p.get_source_display(),
                "received_at": dt.to_representation(p.received_at),
            }
            for p in sorted(order.payments.all(), key=lambda p: p.pk)
        ]

    def get_delivery(self, order):
        invoice = self._invoice(order)
        notes = sorted(invoice.delivery_notes.all(), key=lambda n: n.pk) if invoice else []
        if not notes:
            return None
        note = notes[-1]  # phiếu mới nhất của đơn
        return {
            "id": note.pk,
            "code": note.code,
            "status": note.status,
            "status_label": note.get_status_display(),
            "assigned_to": _staff(note.assigned_to),
            "failed_attempts": note.failed_attempts,
        }

    def get_refunds(self, order):
        invoice = self._invoice(order)
        if invoice is None:
            return []
        return [
            {"id": r.pk, "amount": money_str(r.amount), "status": r.status,
             "status_label": r.get_status_display(), "bank_txn_ref": r.bank_txn_ref}
            for r in sorted(invoice.refunds.all(), key=lambda r: r.pk)
        ]

    def get_available_actions(self, order):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None:
            return []
        return services.available_actions(order=order, user=user)


    def get_timeline(self, order):
        """L7: dòng thời gian tăng dần — không giá vốn, actor là tên hiển thị (None → Hệ thống)."""
        dt = serializers.DateTimeField()
        return [
            {"at": dt.to_representation(e.at), "kind": e.kind, "label": e.label,
             "actor_display": e.actor_display}
            for e in build_timeline(order)
        ]


def _staff(user):
    if user is None:
        return None
    profile = getattr(user, "staff_profile", None)
    return {
        "id": user.pk,
        "display_name": (profile.display_name if profile else "") or user.get_username(),
        "phone": profile.phone if profile else "",
    }
