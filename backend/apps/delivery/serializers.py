"""
Serializer giao hàng (P-06 và CSKH xác nhận đơn).
Tuân thủ Bất biến 1 (không rò giá vốn) và Bất biến 9 (phạm vi dữ liệu cá nhân).
"""
from decimal import Decimal

from rest_framework import serializers

from .models import DeliveryNote, LabelPrint
from . import services

from .pii_scope import is_note_pii_expired


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
    assigned_to_name = serializers.SerializerMethodField()
    failure_reason_label = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNote
        fields = [
            "id", "code", "status", "status_label",
            "sales_invoice", "invoice_code", "order",
            "paid_at", "confirmed_at", "confirm_skipped",
            "assigned_to", "assigned_to_name", "failed_attempts", "note",
            "failure_reason", "failure_reason_label",
            "created_at", "completed_at", "delivery_started_at", "failed_at",
            "lines_summary", "total_kg", "label",
            "customer_name", "address",
            "available_actions",
        ]
        read_only_fields = [
            "code", "sales_invoice", "status", "assigned_to", "failed_attempts", "failure_reason",
            "created_at", "completed_at", "confirmed_at", "confirmed_by", "confirm_skipped",
            "delivery_started_at", "failed_at",
        ]

    def _customer_data_hidden(self, obj) -> bool:
        """Ẩn dữ liệu khách của phiếu (tên, SĐT, địa chỉ, ghi chú) bằng giá trị `null`, giữ nguyên khoá JSON.

        V2 không áp cho phiếu giao (Duy 08/10 câu 7): ai được D3 cho xem phiếu thì thấy đủ tên, SĐT, địa chỉ. Một luật cho
        danh sách, chi tiết, "Việc giao của tôi" và phản hồi của đổi trạng thái, giao người (QA W37 N2):
        phạm vi D3 khác `all` (view đặt `pii_restricted`, PV-04) và phiếu đã quá cửa sổ SR-PII-02 thì ẩn."""
        return bool(self.context.get("pii_restricted")) and is_note_pii_expired(obj)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if self._customer_data_hidden(instance):
            ret["note"] = None
        return ret

    def _full_phone(self, obj):
        """SĐT đủ của người nhận (SR-PII-02): None nếu quá cửa sổ cho người giao. `recipient_phone` > SĐT đơn > SĐT khách."""
        if self._customer_data_hidden(obj):
            return None
        if obj.recipient_phone:
            return obj.recipient_phone
        invoice = obj.sales_invoice
        order = invoice.sales_order if invoice and invoice.sales_order_id else None
        if order is not None:
            return order.phone or (order.customer.phone if order.customer_id else "") or ""
        return ""

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to_id:
            return None
        return services.staff_display_name(obj.assigned_to)

    def get_failure_reason_label(self, obj):
        return obj.get_failure_reason_display() if obj.failure_reason else ""

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
                # Đọc qua prefetch của viewset (`lines__batch_allocations__...`), không truy vấn thêm theo từng phiếu.
                allocs = [alloc for line in invoice.lines.all() for alloc in line.batch_allocations.all()]
                allocs.sort(key=lambda alloc: alloc.pk)
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
        if self._customer_data_hidden(obj):
            return None
        if obj.recipient_name:
            return obj.recipient_name
        invoice = obj.sales_invoice
        if invoice and invoice.sales_order_id and invoice.sales_order.customer_id:
            return invoice.sales_order.customer.name
        return ""

    def get_address(self, obj):
        if self._customer_data_hidden(obj):
            return None
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
        actions = []
        # BR-GH-23: giao / đổi người giao khi chưa lên xe (T6). Chủ và Quản lý.
        if status in services.ASSIGNABLE_STATUSES and user.has_perm("delivery.assign_deliverynote"):
            actions.append("assign")
        if status == DeliveryNote.Status.CONFIRMING:
            return actions

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


class CourierDeliveryNoteListSerializer(DeliveryNoteSerializer):
    """
    #17 (R4b): dòng danh sách cho `GET /notes/?assigned_to=me` — thêm `phone` để người giao gọi khách ngay từ danh sách.
    `phone` khác null chỉ khi phiếu ĐANG GIAO hoặc GIAO THẤT BẠI và còn trong cửa sổ SR-PII-02 (cùng điều kiện với chi tiết).
    View chỉ dùng lớp này khi `assigned_to=me`, nên chỉ phiếu gán cho chính người gọi; các truy vấn khác không có khoá `phone`.
    """

    phone = serializers.SerializerMethodField()

    class Meta(DeliveryNoteSerializer.Meta):
        fields = DeliveryNoteSerializer.Meta.fields + ["phone"]

    def get_phone(self, obj):
        if obj.status not in (DeliveryNote.Status.DELIVERING, DeliveryNote.Status.FAILED):
            return None
        return self._full_phone(obj)


class DeliveryNoteDetailSerializer(DeliveryNoteSerializer):
    lines = serializers.SerializerMethodField()
    recipient_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    failure_note = serializers.SerializerMethodField()

    class Meta(DeliveryNoteSerializer.Meta):
        fields = DeliveryNoteSerializer.Meta.fields + ["lines", "recipient_name", "phone", "failure_note"]

    def get_phone(self, obj):
        """R4: SĐT đủ của người nhận, chỉ ở chi tiết và chỉ cho người trong phạm vi (SR-PII-02). Tem vẫn che."""
        return self._full_phone(obj)

    def get_failure_note(self, obj):
        """BR-GH-22: chữ tự do, có thể chứa dữ liệu cá nhân; chỉ ở chi tiết, theo cửa sổ SR-PII-02."""
        if self._customer_data_hidden(obj):
            return None
        return obj.failure_note or ""

    def get_recipient_name(self, obj):
        if self._customer_data_hidden(obj):
            return None
        return obj.recipient_name or None

    def get_lines(self, obj):
        """Lô 9: `batch_pk` (pk lô, để tạo phiếu hoàn khi không có quyền xem lô) và `returned_qty` (kg đã hoàn của lô
        đó trên phiếu này, Chờ duyệt + Đã duyệt; một truy vấn gộp cho cả phiếu). Không phải giá vốn hay dữ liệu cá nhân."""
        from apps.inventory.returns.creation import returned_qty_by_batch  # import trễ: tránh vòng delivery <-> inventory

        allocs = self._get_allocations(obj)
        returned = returned_qty_by_batch(obj) if allocs else {}
        results = []
        for a in allocs:
            results.append({
                "item_name": a.component_item.name,
                "qty_kg": f"{float(a.qty):.3f}",
                "batch_id": a.batch.batch_id,
                "expiry_date": a.batch.expiry_date.isoformat() if a.batch.expiry_date else None,
                "batch_pk": a.batch_id,
                "returned_qty": f"{returned.get(a.batch_id, Decimal('0')):.3f}",
            })
        return results
