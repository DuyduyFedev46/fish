"""
Serializer giao hàng (P-06 và CSKH xác nhận đơn).
Tuân thủ Bất biến 1 (không rò giá vốn) và Bất biến 9 (phạm vi dữ liệu cá nhân).
"""
from rest_framework import serializers

from .models import DeliveryNote, LabelPrint


class DeliveryNoteLineSerializer(serializers.Serializer):
    item_name = serializers.CharField()
    qty_kg = serializers.CharField()
    batch_id = serializers.CharField()
    expiry_date = serializers.DateField(allow_null=True)


class DeliveryNoteSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    invoice_code = serializers.CharField(source="sales_invoice.code", read_only=True)
    order = serializers.SerializerMethodField()
    paid_at = serializers.SerializerMethodField()
    lines_summary = serializers.SerializerMethodField()
    total_kg = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNote
        fields = [
            "id", "code", "status", "status_label",
            "sales_invoice", "invoice_code", "order",
            "paid_at", "confirmed_at", "confirm_skipped",
            "assigned_to", "failed_attempts", "note",
            "created_at", "completed_at",
            "lines_summary", "total_kg", "label",
            "customer_name", "address",
            "available_actions",
        ]
        read_only_fields = [
            "code", "sales_invoice", "status", "assigned_to", "failed_attempts",
            "created_at", "completed_at", "confirmed_at", "confirmed_by", "confirm_skipped",
        ]

    def get_order(self, obj):
        invoice = obj.sales_invoice
        if invoice and invoice.sales_order_id:
            return {"id": invoice.sales_order_id, "code": invoice.sales_order.code}
        return None

    def get_paid_at(self, obj):
        invoice = obj.sales_invoice
        if invoice and invoice.issued_at:
            return invoice.issued_at.isoformat()
        return None

    def _get_allocations(self, obj):
        if not hasattr(obj, "_cached_allocations"):
            invoice = obj.sales_invoice
            if not invoice:
                obj._cached_allocations = []
            else:
                from apps.sales.models.invoices import SalesInvoiceLineBatch
                allocs = list(
                    SalesInvoiceLineBatch.objects.filter(invoice_line__invoice=invoice)
                    .select_related("component_item", "batch")
                    .order_by("id")
                )
                obj._cached_allocations = allocs
        return obj._cached_allocations

    def get_lines_summary(self, obj):
        allocs = self._get_allocations(obj)
        if not allocs:
            return ""
        # Gộp số kg theo component_item.name
        summary_map = {}
        for a in allocs:
            name = a.component_item.name
            summary_map[name] = summary_map.get(name, 0) + float(a.qty)
        parts = [f"{name} {qty:.3f} kg" for name, qty in summary_map.items()]
        return " · ".join(parts)

    def get_total_kg(self, obj):
        allocs = self._get_allocations(obj)
        total = sum(float(a.qty) for a in allocs)
        return f"{total:.3f}"

    def get_label(self, obj):
        prints = list(obj.label_prints.all()) if hasattr(obj, "label_prints") else []
        printed = len(prints) > 0
        valid_print = None
        if obj.status != DeliveryNote.Status.CANCELLED:
            active_prints = [p for p in prints if p.superseded_at is None and p.voided_at is None]
            if active_prints:
                valid_print = max(active_prints, key=lambda p: p.print_no).print_no

        to_void = [
            p.print_no for p in prints
            if p.voided_at is None and (valid_print is None or p.print_no != valid_print)
        ]
        return {
            "printed": printed,
            "valid_print_no": valid_print,
            "needs_void": len(to_void),
            "to_void": to_void,
        }

    def get_customer_name(self, obj):
        if obj.recipient_name:
            return obj.recipient_name
        invoice = obj.sales_invoice
        if invoice and invoice.sales_order_id and invoice.sales_order.customer_id:
            return invoice.sales_order.customer.name
        return ""

    def get_address(self, obj):
        invoice = obj.sales_invoice
        if invoice and invoice.sales_order_id:
            return invoice.sales_order.delivery_address or ""
        return ""

    def get_available_actions(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return []

        status = obj.status
        if status == DeliveryNote.Status.CONFIRMING:
            return []

        actions = []
        has_pack = user.has_perm("delivery.pack_deliverynote")
        has_print = user.has_perm("delivery.print_label")
        has_change = user.has_perm("delivery.change_deliverynote")

        label_info = self.get_label(obj)

        if status == DeliveryNote.Status.PREPARING:
            if has_pack:
                actions.append("set_status:READY")
            if has_print:
                actions.append("reprint_label" if label_info["printed"] else "print_label")
        elif status == DeliveryNote.Status.READY:
            if has_change:
                actions.append("set_status:DELIVERING")
            if has_print:
                actions.append("reprint_label" if label_info["printed"] else "print_label")
        elif status == DeliveryNote.Status.DELIVERING:
            if has_change:
                actions.append("set_status:COMPLETED")
                actions.append("set_status:FAILED")
        elif status == DeliveryNote.Status.FAILED:
            if has_change:
                actions.append("set_status:DELIVERING")

        if label_info["needs_void"] > 0 and has_print:
            actions.append("void_label")

        return actions


class DeliveryNoteDetailSerializer(DeliveryNoteSerializer):
    lines = serializers.SerializerMethodField()
    recipient_name = serializers.SerializerMethodField()

    class Meta(DeliveryNoteSerializer.Meta):
        fields = DeliveryNoteSerializer.Meta.fields + ["lines", "recipient_name"]

    def get_recipient_name(self, obj):
        return obj.recipient_name or None

    def get_lines(self, obj):
        allocs = self._get_allocations(obj)
        results = []
        for a in allocs:
            results.append({
                "item_name": a.component_item.name,
                "qty_kg": f"{float(a.qty):.3f}",
                "batch_id": a.batch.batch_id,
                "expiry_date": a.batch.expiry_date.isoformat() if a.batch.expiry_date else None,
            })
        return results
