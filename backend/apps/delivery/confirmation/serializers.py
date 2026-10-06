"""
Serializers cho hàng chờ CSKH (2026-09-28-cskh-xac-nhan-in-tem).
Tuân thủ:
- Bất biến 1: Không tính hay trả về giá vốn (unit_cost, rate, landed_unit_cost, profit...)
- Bất biến 9: Phân định in_scope (ngoài scope ẩn tên/SĐT/địa chỉ, chỉ trả phone_masked)
- Liệt kê fields tường minh, không dùng fields="__all__"
"""
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.common.formatting import format_local_date
from apps.common.pii import mask_phone
from apps.delivery.confirmation.scope import note_in_customer_service_scope
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote
from apps.sales.models.invoices import SalesInvoiceLineBatch

# T43: nhãn chữ cho mã chặn tự huỷ (hằng, không ghép dữ liệu khách). Khoá `auto_cancel_blocked` giữ mã thô.
AUTO_CANCEL_BLOCKED_LABELS = {
    "BR-LO-05": "Lô đã chốt, không tự huỷ được",
}


class CustomerCallSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    at = serializers.DateTimeField(source="created_at", read_only=True)
    by = serializers.SerializerMethodField()
    result_label = serializers.CharField(source="get_result_display", read_only=True)
    note = serializers.SerializerMethodField()

    class Meta:
        model = CustomerCall
        fields = ["id", "at", "by", "result", "result_label", "note"]
        read_only_fields = fields

    def get_by(self, obj):
        user = obj.created_by
        if not user:
            return None
        return {
            "id": user.pk,
            "display_name": user.get_full_name() or user.username,
        }

    def get_note(self, obj):
        in_scope = self.context.get("in_scope", True)
        return obj.note_text if in_scope else ""


class ConfirmationQueueItemSerializer(serializers.ModelSerializer):
    """
    Serializer cho từng dòng trong hàng chờ CSKH (02b §4.3).
    """

    class Meta:
        model = ConfirmationTask
        fields = [
            "id",  # task id
        ]

    def _get_allocations(self, note):
        if not hasattr(note, "_cached_allocations"):
            invoice = note.sales_invoice
            if not invoice:
                note._cached_allocations = []
            else:
                note._cached_allocations = list(
                    SalesInvoiceLineBatch.objects.filter(invoice_line__invoice=invoice)
                    .select_related("component_item", "batch")
                    .order_by("id")
                )
        return note._cached_allocations

    def _calc_lines_summary(self, note):
        allocs = self._get_allocations(note)
        if not allocs:
            return ""
        summary_map = {}
        for a in allocs:
            name = a.component_item.name
            summary_map[name] = summary_map.get(name, 0) + float(a.qty)
        parts = [f"{name} {qty:.3f} kg" for name, qty in summary_map.items()]
        return " · ".join(parts)

    def _calc_total_kg(self, note):
        allocs = self._get_allocations(note)
        total = sum(float(a.qty) for a in allocs)
        return f"{total:.3f}"

    def to_representation(self, obj: ConfirmationTask):
        request = self.context.get("request")
        user = request.user if request else None
        now = self.context.get("now") or timezone.now()

        note = obj.note
        invoice = getattr(note, "sales_invoice", None)
        order = getattr(invoice, "sales_order", None) if invoice else None
        customer = getattr(order, "customer", None) if order else None

        in_scope = note_in_customer_service_scope(user, note, now=now)

        # Trạng thái hiển thị
        confirm_state = None if obj.state == ConfirmationTask.State.DONE else obj.state

        # Escalation
        escalation_reason = obj.escalation_reason or None
        escalation_label = None
        if obj.escalation_reason:
            # T36/T37: một chữ cho mọi nơi; hướng dẫn xử lý nằm ở dòng gợi ý của màn, không trong nhãn.
            escalation_label = obj.get_escalation_reason_display()

        # Next call after
        min_retry = getattr(settings, "CONFIRMATION_MIN_RETRY_MINUTES", 10)
        next_call_after = None
        if obj.state == ConfirmationTask.State.PENDING and obj.attempts >= 1 and obj.last_unreachable_at:
            next_call_after = (obj.last_unreachable_at + timedelta(minutes=min_retry)).isoformat()

        # Window ends at
        window_mins = getattr(settings, "CONFIRMATION_UNREACHABLE_WINDOW_MINUTES", 30)
        window_ends_at = None
        if obj.first_unreachable_at:
            window_ends_at = (obj.first_unreachable_at + timedelta(minutes=window_mins)).isoformat()

        # Decide deadline (CS-07, CS-13)
        decision_mins = getattr(settings, "CONFIRMATION_MANAGER_DECISION_MINUTES", 30)
        decide_deadline = None
        if (
            obj.state == ConfirmationTask.State.ESCALATED
            and obj.escalated_at
            and obj.escalation_reason in (
                ConfirmationTask.EscalationReason.UNREACHABLE,
                ConfirmationTask.EscalationReason.WRONG_NUMBER,
            )
        ):
            decide_deadline = (obj.escalated_at + timedelta(minutes=decision_mins)).isoformat()

        # Claimed by / until
        claimed_by_data = None
        claimed_until_data = None
        if obj.claimed_by and obj.claimed_until and obj.claimed_until > now:
            claimed_by_data = {
                "id": obj.claimed_by.pk,
                "display_name": obj.claimed_by.get_full_name() or obj.claimed_by.username,
            }
            claimed_until_data = obj.claimed_until.isoformat()

        # Tiền và kg
        total_amount = str(int(order.total_amount)) if order else (str(int(invoice.amount)) if invoice else "0")

        # PII fields
        phone_raw = (order.phone if order else (customer.phone if customer else ""))
        phone_masked = mask_phone(phone_raw)

        if in_scope:
            customer_name = customer.name if customer else (order.customer.name if order and order.customer else "")
            phone = phone_raw
            address = order.delivery_address if order else ""
            recipient_name = note.recipient_name or None
            recipient_phone = note.recipient_phone or None
        else:
            customer_name = None
            phone = None
            address = None
            recipient_name = None
            recipient_phone = None

        data = {
            "note_id": note.pk,
            "order_id": order.pk if order else None,
            "order_code": order.code if order else "",
            "note_status": note.status,
            "paid_at": invoice.issued_at.isoformat() if invoice and invoice.issued_at else None,
            "confirm_state": confirm_state,
            "escalation_reason": escalation_reason,
            "escalation_label": escalation_label,
            "attempts": obj.attempts,
            "max_attempts": getattr(settings, "CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS", 3),
            "next_call_after": next_call_after,
            "window_ends_at": window_ends_at,
            "callback_at": obj.callback_at.isoformat() if obj.callback_at else None,
            "escalated_at": obj.escalated_at.isoformat() if obj.escalated_at else None,
            "decide_deadline": decide_deadline,
            "auto_cancel_blocked": obj.auto_cancel_blocked_code or None,
            "auto_cancel_blocked_label": AUTO_CANCEL_BLOCKED_LABELS.get(obj.auto_cancel_blocked_code) or None,  # T43
            "claimed_by": claimed_by_data,
            "claimed_until": claimed_until_data,
            "lines_summary": self._calc_lines_summary(note),
            "total_kg": self._calc_total_kg(note),
            "total_amount": total_amount,
            "in_scope": in_scope,
            "customer_name": customer_name,
            "phone": phone,
            "address": address,
            "recipient_name": recipient_name,
            "recipient_phone": recipient_phone,
            "phone_masked": phone_masked,
        }

        # Nếu là REFUND_CALL
        if obj.state == ConfirmationTask.State.REFUND_CALL:
            data["cancelled_at"] = obj.auto_cancelled_at.isoformat() if obj.auto_cancelled_at else None
            refund = obj.refund
            if refund:
                refund_days = getattr(settings, "REFUND_DEADLINE_DAYS", 30)
                deadline_date = format_local_date(refund.created_at + timedelta(days=refund_days))
                data["refund"] = {
                    "id": refund.pk,
                    "amount": str(int(refund.amount)),
                    "status": refund.status,
                    "status_label": refund.get_status_display(),
                    "deadline": deadline_date,
                    "refunded_at": refund.confirmed_at.isoformat() if refund.confirmed_at else None,
                }
            else:
                data["refund"] = None

        return data


class ConfirmationQueueDetailSerializer(ConfirmationQueueItemSerializer):
    """
    Serializer chi tiết cho một task trong hàng chờ CSKH, gồm lịch sử cuộc gọi và available_actions.
    """

    def to_representation(self, obj: ConfirmationTask):
        data = super().to_representation(obj)
        request = self.context.get("request")
        user = request.user if request else None
        now = self.context.get("now") or timezone.now()
        in_scope = data.get("in_scope", True)

        # Lịch sử cuộc gọi
        calls_qs = obj.note.calls.select_related("created_by").order_by("-created_at", "-id")
        call_serializer = CustomerCallSerializer(
            calls_qs, many=True, context={"request": request, "in_scope": in_scope}
        )
        data["calls"] = call_serializer.data
        # Lý do quyết định nằm ở chứng từ: chỉ người trong phạm vi xem được (có thể có tên khách).
        data["decision_note"] = obj.decision_note if in_scope else ""

        # Available actions
        actions = []
        if user and user.is_authenticated:
            # Kiểm tra người khác claim
            other_claimed = bool(
                obj.claimed_by_id and obj.claimed_by_id != user.pk
                and obj.claimed_until and obj.claimed_until > now
            )

            if not other_claimed:
                has_confirm_perm = user.has_perm("delivery.confirm_with_customer")
                has_change_recip = user.has_perm("delivery.change_recipient")
                has_decide = user.has_perm("delivery.decide_unconfirmed")

                if has_confirm_perm:
                    # Nút claim nếu chưa claim hoặc hết hạn
                    if not (obj.claimed_by_id == user.pk and obj.claimed_until and obj.claimed_until > now):
                        actions.append("claim")

                    if obj.note.status == DeliveryNote.Status.CONFIRMING:
                        actions.extend([
                            "call:CONFIRMED",
                            "call:UNREACHABLE",
                            "call:WRONG_NUMBER",
                            "call:CALLBACK",
                            "call:WANT_CHANGE",
                            "call:WANT_CANCEL",
                        ])
                    elif obj.state == ConfirmationTask.State.REFUND_CALL:
                        actions.extend([
                            "call:NOTIFIED",
                            "call:UNREACHABLE",
                        ])

                if has_change_recip and obj.note.status in (
                    DeliveryNote.Status.CONFIRMING, DeliveryNote.Status.PREPARING
                ):
                    actions.append("change_recipient")

                # Unconfirm: PREPARING -> CONFIRMING khi chưa in tem
                if obj.note.status == DeliveryNote.Status.PREPARING and obj.state == ConfirmationTask.State.DONE:
                    if not obj.note.label_prints.exists():
                        if has_confirm_perm and (obj.note.confirmed_by_id == user.pk or has_decide):
                            actions.append("unconfirm")

                # Decide unconfirmed (Lô 3)
                if has_decide and obj.state == ConfirmationTask.State.ESCALATED:
                    actions.extend([
                        "decide:DELIVER_WITHOUT_CONFIRM",
                        "decide:EXTEND",
                        "decide:CANCEL",
                    ])

        data["available_actions"] = actions

        # Kịch bản gọi (CS-18): chỉ kèm khi có quyền xem; không chứa dữ liệu cá nhân.
        scripts = []
        if user and user.is_authenticated and user.has_perm("delivery.view_callscript"):
            from apps.delivery.confirmation.call_scripts import scripts_for_note
            from apps.delivery.confirmation.scripts_api import serialize_script

            scripts = [serialize_script(sc, with_state=False) for sc in scripts_for_note(obj.note)]
        data["scripts"] = scripts

        # Guidance
        if obj.state == ConfirmationTask.State.REFUND_CALL:
            data["guidance"] = (
                "Không ghi số tài khoản khách vào hệ thống. Chủ sẽ lấy số tài khoản trực tiếp từ khách khi chuyển khoản."
            )
        else:
            data["guidance"] = None

        return data
