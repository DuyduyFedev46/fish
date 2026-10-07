"""
Dịch vụ CSKH: Xác nhận đơn hàng, ghi kết quả gọi, quản lý hàng chờ gọi (2026-09-28-cskh-xac-nhan-in-tem).
Tuân thủ:
- Thứ tự khoá cố định (§1.5): SalesOrder -> DeliveryNote -> ConfirmationTask
- Bất biến 1: Không tính toán hay trả về giá vốn
- Bất biến 9: Chặn PII trong ghi chú tự do (BR-GH-19, has_long_digit_run)
"""
from datetime import timedelta
import logging
import uuid
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from apps.common.audit import note_marker, record_audit
from apps.common.exceptions import BusinessError, ConflictError
from apps.common.formatting import format_local_time
from apps.common.pii import has_long_digit_run, normalize_phone
from apps.delivery import services as delivery_services
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote, LabelPrint

logger = logging.getLogger("cangca.delivery.confirmation")


def start_confirmation(invoice) -> tuple[DeliveryNote, ConfirmationTask]:
    """
    Tự động gọi khi SalesInvoice ở trạng thái ISSUED (từ signal hoặc IPN).
    Tạo DeliveryNote (CONFIRMING) + ConfirmationTask (PENDING) trong một transaction (CS-04-AC1, §1.3).
    Idempotent: nếu đã có phiếu cho hoá đơn này thì không sinh mục thứ hai (CS-04-AC3, §1.6).
    """
    with transaction.atomic():
        existing_note = DeliveryNote.objects.select_for_update().filter(sales_invoice=invoice).first()
        if existing_note:
            task, _ = ConfirmationTask.objects.get_or_create(
                note=existing_note,
                defaults={"state": ConfirmationTask.State.PENDING},
            )
            return existing_note, task

        note = delivery_services.create_delivery_note(
            invoice=invoice,
            status=DeliveryNote.Status.CONFIRMING,
        )
        task, _ = ConfirmationTask.objects.get_or_create(
            note=note,
            defaults={"state": ConfirmationTask.State.PENDING},
        )
        return note, task


def close_task_on_cancel(note: DeliveryNote):
    """
    Đóng task xác nhận khi đơn/phiếu bị huỷ (S14 / CS-04-AC5 / §1.4).
    """
    task = ConfirmationTask.objects.filter(note=note).first()
    if task and task.state != ConfirmationTask.State.DONE:
        task.state = ConfirmationTask.State.DONE
        task.claimed_by = None
        task.claimed_until = None
        task.save(update_fields=["state", "claimed_by", "claimed_until", "updated_at"])


def claim_task(task_id: int, user, *, now=None) -> ConfirmationTask:
    """
    CSKH nhận đơn để gọi — khoá mềm trong CONFIRMATION_CLAIM_MINUTES (CS-05-AC3, CS-05-AC4, §1.4).
    """
    now = now or timezone.now()
    with transaction.atomic():
        # Khoá dòng ConfirmationTask. Không select_related trong câu khoá: sau khi chờ khoá, Postgres không nạp lại
        # phía nối (claimed_by nối ngoài thành None), nên quan hệ đọc SAU khoá bằng truy vấn mới (B1, QA 08/10).
        task = ConfirmationTask.objects.select_for_update(of=("self",)).get(pk=task_id)
        note = DeliveryNote.objects.get(pk=task.note_id)

        if note.status == DeliveryNote.Status.CANCELLED and task.state != ConfirmationTask.State.REFUND_CALL:
            raise BusinessError("Đơn đã huỷ.", code="BR-GH-07")

        if task.state == ConfirmationTask.State.DONE:
            raise ConflictError("Đơn đã hoàn tất xử lý xác nhận.", code="STALE_STATE")

        # Kiểm tra người khác đang claim còn hạn
        if task.claimed_by_id and task.claimed_by_id != user.pk:
            if task.claimed_until and task.claimed_until > now:
                claimer = User.objects.get(pk=task.claimed_by_id)
                claimer_name = claimer.get_full_name() or claimer.username
                time_str = format_local_time(task.claimed_until)
                raise ConflictError(
                    f"Đơn đang được {claimer_name} xử lý tới {time_str}.",
                    code="CLAIMED",
                    extra={"claimed_until": task.claimed_until.isoformat()},
                )

        claim_mins = getattr(settings, "CONFIRMATION_CLAIM_MINUTES", 5)
        task.claimed_by = user
        task.claimed_until = now + timedelta(minutes=claim_mins)
        task.save(update_fields=["claimed_by", "claimed_until", "updated_at"])
        return task


def record_call(
    task_id: int,
    user,
    result: str,
    *,
    note_text: str = "",
    callback_at=None,
    request_id=None,
    now=None,
) -> tuple[CustomerCall, bool]:
    """
    Ghi kết quả cuộc gọi — append-only (CS-06, §1.4, §1.5).
    Thứ tự khoá: DeliveryNote -> ConfirmationTask.
    Chống trùng theo request_id (CS-06-AC2, §1.6).
    """
    now = now or timezone.now()

    # 1. Kiểm tra chống trùng lặp request_id (idempotent)
    if request_id:
        existing_call = CustomerCall.objects.filter(request_id=request_id).select_related("note__confirmation").first()
        if existing_call:
            task = getattr(existing_call.note, "confirmation", None)
            if task and (task.pk == task_id or existing_call.note_id == task_id):
                return existing_call, True
            raise BusinessError("request_id đã tồn tại cho phiếu khác.", code="BR-GH-12")

    # 2. Kiểm tra tính hợp lệ của note_text (BR-GH-19)
    clean_note = (note_text or "").strip()
    if len(clean_note) > 200:
        raise BusinessError("Ghi chú không được vượt quá 200 ký tự.", code="BR-GH-19")
    if has_long_digit_run(clean_note):
        raise BusinessError("Không ghi SĐT hay số tài khoản vào ghi chú.", code="BR-GH-19")

    # 3. Khoá dòng theo thứ tự chuẩn: DeliveryNote -> ConfirmationTask (§1.5)
    with transaction.atomic():
        try:
            task = ConfirmationTask.objects.select_related("note").get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            raise BusinessError("Không tìm thấy mục chờ gọi.", code="NOT_FOUND")

        note = DeliveryNote.objects.select_for_update().get(pk=task.note_id)
        task = ConfirmationTask.objects.select_for_update().get(pk=task_id)

        # 4. Kiểm tra trạng thái note / task
        # SR-09 (BR-GH-18, CS-08/CS-09): đơn đã bị huỷ (hệ thống tự huỷ hoặc huỷ tay) thì màn hình
        # của CSKH đang cũ -> 409 STALE_STATE, KHÔNG được đưa phiếu về PREPARING. Task REFUND_CALL
        # (báo huỷ & hoàn tiền) chỉ nhận UNREACHABLE / NOTIFIED; giá trị rác vẫn rơi xuống INVALID_INPUT.
        stale_error = ConflictError("Đơn đã bị huỷ — tải lại màn hình.", code="STALE_STATE")
        if task.state == ConfirmationTask.State.REFUND_CALL:
            refund_call_results = (CustomerCall.Result.UNREACHABLE, CustomerCall.Result.NOTIFIED)
            if result in CustomerCall.Result.values and result not in refund_call_results:
                raise stale_error
        elif note.status == DeliveryNote.Status.CANCELLED:
            raise stale_error

        open_states = (
            ConfirmationTask.State.PENDING,
            ConfirmationTask.State.CALLBACK,
            ConfirmationTask.State.ESCALATED,
            ConfirmationTask.State.REFUND_CALL,
        )
        if task.state not in open_states:
            raise ConflictError(
                "Đơn vừa được xác nhận bởi người khác.",
                code="STALE_STATE",
                extra={"current_status": note.status, "confirm_state": None},
            )

        # Kiểm tra claim của người khác
        if task.claimed_by_id and task.claimed_by_id != user.pk:
            if task.claimed_until and task.claimed_until > now:
                claimer = User.objects.get(pk=task.claimed_by_id)
                claimer_name = claimer.get_full_name() or claimer.username
                time_str = format_local_time(task.claimed_until)
                raise ConflictError(
                    f"Đơn đang được {claimer_name} xử lý tới {time_str}.",
                    code="CLAIMED",
                    extra={"claimed_until": task.claimed_until.isoformat()},
                )

        # 5. Máy trạng thái (§1.4)
        if result in (CustomerCall.Result.CONFIRMED, CustomerCall.Result.CONFIRMED_CHANGED):
            note.status = DeliveryNote.Status.PREPARING
            note.confirmed_at = now
            note.confirmed_by = user
            note.save(update_fields=["status", "confirmed_at", "confirmed_by"])

            task.state = ConfirmationTask.State.DONE
            task.claimed_by = None
            task.claimed_until = None
            task.save(update_fields=["state", "claimed_by", "claimed_until", "updated_at"])

            record_audit(
                "delivery_confirmed",
                actor=user,
                obj=note,
                changes={"status": {"from": "CONFIRMING", "to": "PREPARING"}},
            )

        elif result == CustomerCall.Result.CALLBACK:
            if not callback_at or callback_at <= now:
                raise BusinessError("Giờ hẹn gọi lại phải ở tương lai.", code="INVALID_INPUT")

            task.state = ConfirmationTask.State.CALLBACK
            task.callback_at = callback_at
            task.attempts = 0
            task.first_unreachable_at = None
            task.claimed_by = None
            task.claimed_until = None
            task.save(update_fields=[
                "state", "callback_at", "attempts", "first_unreachable_at",
                "claimed_by", "claimed_until", "updated_at"
            ])

            record_audit(
                "delivery_call_recorded",
                actor=user,
                obj=note,
                changes={"result": "CALLBACK"},
            )

        elif result == CustomerCall.Result.UNREACHABLE:
            min_retry = getattr(settings, "CONFIRMATION_MIN_RETRY_MINUTES", 10)
            max_attempts = getattr(settings, "CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS", 3)
            window_mins = getattr(settings, "CONFIRMATION_UNREACHABLE_WINDOW_MINUTES", 30)

            if task.state != ConfirmationTask.State.REFUND_CALL:
                # Kiểm tra khoảng cách tối thiểu giữa 2 lần không liên lạc được (BR-GH-13)
                if task.attempts >= 1 and task.last_unreachable_at:
                    if now < task.last_unreachable_at + timedelta(minutes=min_retry):
                        raise BusinessError(
                            f"Chưa đủ {min_retry} phút kể từ lần gọi trước.",
                            code="BR-GH-13",
                        )

                task.attempts += 1
                if task.attempts == 1:
                    task.first_unreachable_at = now
                task.last_unreachable_at = now

                # Chuyển ESCALATED nếu đủ N lần hoặc hết cửa sổ W phút
                reached_max = task.attempts >= max_attempts
                window_expired = bool(
                    task.first_unreachable_at and now >= task.first_unreachable_at + timedelta(minutes=window_mins)
                )

                if reached_max or window_expired:
                    task.state = ConfirmationTask.State.ESCALATED
                    task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
                    task.escalated_at = now
                    record_audit(
                        "delivery_escalated",
                        actor=user,
                        obj=note,
                        changes={"reason": "UNREACHABLE", "attempts": task.attempts},
                    )
                else:
                    task.state = ConfirmationTask.State.PENDING
                    record_audit(
                        "delivery_call_recorded",
                        actor=user,
                        obj=note,
                        changes={"result": "UNREACHABLE", "attempts": task.attempts},
                    )
            else:
                # REFUND_CALL không áp dụng luật M phút hay tự huỷ
                task.attempts += 1
                task.last_unreachable_at = now
                record_audit(
                    "delivery_call_recorded",
                    actor=user,
                    obj=note,
                    changes={"result": "UNREACHABLE", "attempts": task.attempts},
                )

            task.claimed_by = None
            task.claimed_until = None
            task.save(update_fields=[
                "state", "escalation_reason", "escalated_at", "attempts",
                "first_unreachable_at", "last_unreachable_at",
                "claimed_by", "claimed_until", "updated_at"
            ])

        elif result == CustomerCall.Result.WRONG_NUMBER:
            task.state = ConfirmationTask.State.ESCALATED
            task.escalation_reason = ConfirmationTask.EscalationReason.WRONG_NUMBER
            task.escalated_at = now
            task.claimed_by = None
            task.claimed_until = None
            task.save(update_fields=[
                "state", "escalation_reason", "escalated_at",
                "claimed_by", "claimed_until", "updated_at"
            ])

            record_audit(
                "delivery_escalated",
                actor=user,
                obj=note,
                changes={"reason": "WRONG_NUMBER"},
            )

        elif result in (CustomerCall.Result.WANT_CANCEL, CustomerCall.Result.WANT_CHANGE):
            task.state = ConfirmationTask.State.ESCALATED
            task.escalation_reason = result
            task.escalated_at = now
            task.claimed_by = None
            task.claimed_until = None
            task.save(update_fields=[
                "state", "escalation_reason", "escalated_at",
                "claimed_by", "claimed_until", "updated_at"
            ])

            record_audit(
                "delivery_escalated",
                actor=user,
                obj=note,
                changes={"reason": result},
            )

        elif result == CustomerCall.Result.NOTIFIED:
            if task.state != ConfirmationTask.State.REFUND_CALL:
                raise ConflictError("Kết quả này chỉ áp dụng cho đơn gọi báo hoàn tiền.", code="STALE_STATE")

            task.state = ConfirmationTask.State.DONE
            task.claimed_by = None
            task.claimed_until = None
            task.save(update_fields=["state", "claimed_by", "claimed_until", "updated_at"])

            record_audit(
                "delivery_call_recorded",
                actor=user,
                obj=note,
                changes={"result": "NOTIFIED"},
            )
        else:
            raise BusinessError(f"Kết quả gọi không hợp lệ: {result}", code="INVALID_INPUT")

        # 6. Ghi bản ghi cuộc gọi (append-only)
        call = CustomerCall.objects.create(
            note=note,
            result=result,
            note_text=clean_note,
            callback_at=callback_at,
            created_by=user,
            request_id=request_id,
        )

        return call, False


def unconfirm(task_id: int, user, *, reason: str = "") -> tuple[DeliveryNote, ConfirmationTask]:
    """
    Huỷ xác nhận phiếu PREPARING khi chưa in tem (CS-06-AC8, UC-CS-2 4a).
    Phiếu -> CONFIRMING, task -> PENDING.
    """
    clean_reason = (reason or "").strip()
    if len(clean_reason) > 200:
        raise BusinessError("Lý do không được vượt quá 200 ký tự.", code="BR-GH-19")
    if has_long_digit_run(clean_reason):
        raise BusinessError("Không ghi SĐT hay số tài khoản vào lý do huỷ xác nhận.", code="BR-GH-19")

    with transaction.atomic():
        try:
            task = ConfirmationTask.objects.select_related("note").get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            raise BusinessError("Không tìm thấy mục chờ gọi.", code="NOT_FOUND")

        note = DeliveryNote.objects.select_for_update().get(pk=task.note_id)
        task = ConfirmationTask.objects.select_for_update().get(pk=task_id)

        if note.status != DeliveryNote.Status.PREPARING or task.state != ConfirmationTask.State.DONE:
            raise ConflictError(
                "Phiếu không ở trạng thái Đang soạn hàng để huỷ xác nhận.",
                code="STALE_STATE",
                extra={"current_status": note.status, "confirm_state": task.state},
            )

        if note.label_prints.exists():
            raise BusinessError("Tem đã in — nhờ Quản lý xử lý.", code="BR-GH-16")

        note.status = DeliveryNote.Status.CONFIRMING
        note.confirmed_at = None
        note.confirmed_by = None
        note.save(update_fields=["status", "confirmed_at", "confirmed_by"])

        task.state = ConfirmationTask.State.PENDING
        task.claimed_by = None
        task.claimed_until = None
        if clean_reason:  # không ghi đè lý do cũ bằng chuỗi rỗng
            task.decision_note = clean_reason
        task.save(update_fields=["state", "claimed_by", "claimed_until", "decision_note", "updated_at"])

        record_audit(
            "delivery_unconfirmed",
            actor=user,
            obj=note,
            changes={"status": {"from": "PREPARING", "to": "CONFIRMING"}},
            note=note_marker(clean_reason),
        )

        return note, task


def change_recipient(
    task_id: int,
    user,
    *,
    delivery_address: str | None = None,
    recipient_name: str | None = None,
    recipient_phone: str | None = None,
) -> dict:
    """
    Đổi thông tin người nhận hộ và địa chỉ giao hàng (CS-06, CS-12, 02b §4.5).
    Nếu tem đã in: vô hiệu tem cũ (superseded_at = now), label_invalidated = True.
    Nếu không đổi: trả changed=[], không AuditLog, không vô hiệu tem.
    """
    import re
    from apps.sales.orders import services as order_services

    with transaction.atomic():
        try:
            task = ConfirmationTask.objects.select_related("note__sales_invoice__sales_order").get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            raise BusinessError("Không tìm thấy mục chờ gọi.", code="NOT_FOUND")

        note = DeliveryNote.objects.select_for_update().get(pk=task.note_id)

        if note.status in (DeliveryNote.Status.READY, DeliveryNote.Status.DELIVERING):
            raise BusinessError("Hàng đã soạn xong/đang đi giao — liên hệ Quản lý.", code="BR-GH-15")

        if note.status == DeliveryNote.Status.CANCELLED:
            raise BusinessError("Đơn đã huỷ.", code="BR-GH-07")

        if note.status not in (DeliveryNote.Status.CONFIRMING, DeliveryNote.Status.PREPARING):
            raise ConflictError(
                "Chỉ đổi thông tin nhận khi đơn ở Chờ gọi xác nhận hoặc Đang soạn hàng.",
                code="STALE_STATE",
                extra={"current_status": note.status},
            )

        changed_fields = []
        now = timezone.now()

        # 1. Đổi địa chỉ giao hàng (ghi đè SalesOrder.delivery_address)
        if delivery_address is not None:
            clean_address = delivery_address.strip()
            if not clean_address:
                raise BusinessError("Địa chỉ giao hàng không được để trống.", code="INVALID_INPUT")
            if len(clean_address) > 500:
                raise BusinessError("Địa chỉ giao hàng không được vượt quá 500 ký tự.", code="INVALID_INPUT")

            order = note.sales_invoice.sales_order if (note.sales_invoice and note.sales_invoice.sales_order) else None
            if order and clean_address != (order.delivery_address or "").strip():
                order_services.update_delivery_address(order, clean_address)
                changed_fields.append("delivery_address")

        # 2. Đổi người nhận hộ (recipient_name, recipient_phone)
        save_note_fields = []

        if recipient_name is not None:
            clean_name = recipient_name.strip()
            if clean_name != (note.recipient_name or ""):
                note.recipient_name = clean_name
                changed_fields.append("recipient_name")
                save_note_fields.append("recipient_name")

        if recipient_phone is not None:
            raw_phone = recipient_phone.strip()
            if raw_phone:
                clean_phone = normalize_phone(raw_phone)
                if not re.match(r"^0\d{9}$", clean_phone):
                    raise BusinessError("Số điện thoại người nhận không hợp lệ.", code="BR-BH-14")
            else:
                clean_phone = ""

            if clean_phone != (note.recipient_phone or ""):
                note.recipient_phone = clean_phone
                changed_fields.append("recipient_phone")
                save_note_fields.append("recipient_phone")

        if save_note_fields:
            note.save(update_fields=save_note_fields)

        # 3. Vô hiệu tem cũ nếu đã in và có thay đổi (§1.6, §2.4, CS-12-AC3)
        label_invalidated = False
        if changed_fields:
            active_prints = note.label_prints.filter(superseded_at__isnull=True, voided_at__isnull=True)
            if active_prints.exists():
                active_prints.update(superseded_at=now)
                label_invalidated = True

            record_audit(
                "recipient_changed",
                actor=user,
                obj=note,
                changes={"fields": changed_fields},
            )

        return {
            "changed": changed_fields,
            "label_invalidated": label_invalidated,
            "note": note,
        }


def decide(
    task_id: int,
    user,
    decision: str,
    *,
    reason: str = "",
    until=None,
    reason_code: str = "",
    note: str = "",
    now=None,
) -> dict:
    """
    Quản lý quyết định cho đơn ESCALATED (CS-07, §1.4, §1.5).
    Thứ tự khoá chuẩn: SalesOrder -> DeliveryNote -> ConfirmationTask.
    Các lựa chọn:
    - DELIVER_WITHOUT_CONFIRM: giao luôn không cần xác nhận
    - EXTEND: gia hạn thêm (tối đa CONFIRMATION_EXTEND_MAX_HOURS)
    - CANCEL: huỷ đơn + hoàn kho lô gốc
    """
    now = now or timezone.now()
    clean_reason = (reason or "").strip()
    clean_note = (note or "").strip()

    # Kiểm tra PII BR-GH-19 trên ghi chú / lý do
    for txt in (clean_reason, clean_note):
        if len(txt) > 200:
            raise BusinessError("Ghi chú/lý do không được vượt quá 200 ký tự.", code="BR-GH-19")
        if has_long_digit_run(txt):
            raise BusinessError("Không ghi SĐT hay số tài khoản vào ghi chú.", code="BR-GH-19")

    try:
        t = ConfirmationTask.objects.select_related("note__sales_invoice__sales_order").get(pk=task_id)
    except ConfirmationTask.DoesNotExist:
        raise BusinessError("Không tìm thấy mục chờ gọi.", code="NOT_FOUND")

    order_pk = t.note.sales_invoice.sales_order_id if (t.note and t.note.sales_invoice) else None
    if not order_pk:
        raise BusinessError("Phiếu giao chưa gắn đơn hàng hợp lệ.", code="NOT_FOUND")

    from apps.sales.models import SalesOrder
    from apps.sales.orders import services as order_services

    # Khoá dòng theo thứ tự chuẩn §1.5: SalesOrder -> DeliveryNote -> ConfirmationTask
    with transaction.atomic():
        order = SalesOrder.objects.select_for_update().get(pk=order_pk)
        note_obj = DeliveryNote.objects.select_for_update().get(pk=t.note_id)
        task = ConfirmationTask.objects.select_for_update().get(pk=task_id)

        if task.state != ConfirmationTask.State.ESCALATED or note_obj.status != DeliveryNote.Status.CONFIRMING:
            raise ConflictError(
                "Đơn đã được xử lý.",
                code="STALE_STATE",
                extra={
                    "current_status": note_obj.status,
                    "confirm_state": None if task.state == ConfirmationTask.State.DONE else task.state,
                },
            )

        if decision == "DELIVER_WITHOUT_CONFIRM":
            if not clean_reason:
                raise BusinessError("Lý do bỏ qua xác nhận bắt buộc.", code="INVALID_INPUT")

            note_obj.status = DeliveryNote.Status.PREPARING
            note_obj.confirmed_at = now
            note_obj.confirmed_by = user
            note_obj.confirm_skipped = True
            note_obj.save(update_fields=["status", "confirmed_at", "confirmed_by", "confirm_skipped"])

            task.state = ConfirmationTask.State.DONE
            task.claimed_by = None
            task.claimed_until = None
            if clean_reason:  # không ghi đè lý do cũ bằng chuỗi rỗng
                task.decision_note = clean_reason
            task.save(update_fields=["state", "claimed_by", "claimed_until", "decision_note", "updated_at"])

            record_audit(
                "delivery_confirm_skipped",
                actor=user,
                obj=note_obj,
                changes={"decision": "DELIVER_WITHOUT_CONFIRM"},
                note=note_marker(clean_reason),
            )
            return {
                "note_status": "PREPARING",
                "confirm_state": None,
                "order_id": order.pk,
                "suggest_refund_amount": None,
            }

        elif decision == "EXTEND":
            if not until:
                raise BusinessError("Giờ gia hạn bắt buộc.", code="INVALID_INPUT")
            if until <= now:
                raise BusinessError("Giờ gia hạn phải ở tương lai.", code="BR-GH-13")

            max_hours = getattr(settings, "CONFIRMATION_EXTEND_MAX_HOURS", 24)
            if until > now + timedelta(hours=max_hours):
                raise BusinessError(f"Gia hạn tối đa {max_hours} giờ.", code="BR-GH-13")

            task.state = ConfirmationTask.State.CALLBACK
            task.callback_at = until
            task.attempts = 0
            task.first_unreachable_at = None
            task.claimed_by = None
            task.claimed_until = None
            if clean_reason:  # không ghi đè lý do cũ bằng chuỗi rỗng
                task.decision_note = clean_reason
            task.save(update_fields=[
                "state", "callback_at", "attempts", "first_unreachable_at",
                "claimed_by", "claimed_until", "decision_note", "updated_at"
            ])

            record_audit(
                "delivery_extended",
                actor=user,
                obj=note_obj,
                changes={"decision": "EXTEND", "until": until.isoformat()},
                note=note_marker(clean_reason),
            )
            return {
                "note_status": "CONFIRMING",
                "confirm_state": "CALLBACK",
                "order_id": order.pk,
                "suggest_refund_amount": None,
            }

        elif decision == "CANCEL":
            cancel_code = reason_code or "UNREACHABLE"
            if cancel_code not in order_services.CANCEL_REASON_CODES:
                cancel_code = "UNREACHABLE"

            order_services.cancel_paid_order(
                order=order,
                actor=user,
                reason_code=cancel_code,
                cancel_note=clean_reason or clean_note,
            )
            task.state = ConfirmationTask.State.DONE
            task.claimed_by = None
            task.claimed_until = None
            task.save(update_fields=["state", "claimed_by", "claimed_until", "updated_at"])

            return {
                "note_status": "CANCELLED",
                "confirm_state": None,
                "order_id": order.pk,
                "suggest_refund_amount": str(int(order.total_amount)),
            }
        else:
            raise BusinessError(f"Quyết định không hợp lệ: {decision}", code="INVALID_INPUT")


def escalate_expired_windows(*, now=None) -> int:
    """
    PENDING, attempts ≥ 1, first_unreachable_at + W ≤ now → ESCALATED[UNREACHABLE], escalated_at = now.
    Idempotent. (CS-07-AC4, §5.1)
    """
    now = now or timezone.now()
    window_mins = getattr(settings, "CONFIRMATION_UNREACHABLE_WINDOW_MINUTES", 30)
    cutoff = now - timedelta(minutes=window_mins)

    task_rows = list(
        ConfirmationTask.objects.filter(
            state=ConfirmationTask.State.PENDING,
            attempts__gte=1,
            first_unreachable_at__isnull=False,
            first_unreachable_at__lte=cutoff,
            note__status=DeliveryNote.Status.CONFIRMING,
        ).values_list("pk", "note_id")
    )

    escalated_count = 0
    for task_id, note_id in task_rows:
        try:
            with transaction.atomic():
                # P8 F08: thứ tự khoá đơn -> phiếu -> task (02b CSKH §1.5): khoá phiếu trước, rồi task.
                note_obj = DeliveryNote.objects.select_for_update().get(pk=note_id)
                task = ConfirmationTask.objects.select_for_update().get(pk=task_id)
                if (
                    task.state != ConfirmationTask.State.PENDING
                    or note_obj.status != DeliveryNote.Status.CONFIRMING
                    or not task.first_unreachable_at
                    or task.first_unreachable_at > cutoff
                ):
                    continue

                task.state = ConfirmationTask.State.ESCALATED
                task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
                task.escalated_at = now
                task.claimed_by = None
                task.claimed_until = None
                task.save(update_fields=[
                    "state", "escalation_reason", "escalated_at", "claimed_by", "claimed_until", "updated_at"
                ])

                record_audit(
                    "delivery_escalated",
                    actor=None,
                    obj=note_obj,
                    changes={"reason": "UNREACHABLE", "window_expired": True, "attempts": task.attempts},
                )
                escalated_count += 1
        except Exception:
            logger.exception("Lỗi khi chuyển Quản lý task #%s", task_id)

    return escalated_count


def auto_cancel_overdue(*, now=None) -> dict:
    """
    Chỉ khi settings.CONFIRMATION_AUTO_CANCEL_ENABLED:
    ESCALATED[UNREACHABLE|WRONG_NUMBER], auto_cancel_blocked_code == "",
    escalated_at + D ≤ now → khoá đơn→phiếu→task, đọc lại, kiểm lô CLOSED (→ chặn BR-LO-05),
    cancel_paid_order(actor=None, reason="Không liên lạc được khách (Hệ thống tự huỷ)", reason_code="UNREACHABLE_AUTO"),
    create_invoice_refund(invoice=invoice, amount=refundable_amount(invoice), is_partial=False, actor=None,
                          reason="Tự huỷ: không liên lạc được khách (BR-HT-10)", request_id=uuid5(...)),
    task → REFUND_CALL (refund, auto_cancelled_at=now, attempts=0),
    record_audit("order_auto_cancelled", actor=None, obj=order, changes={"reason_code": "UNREACHABLE_AUTO", "refund_id": refund.pk}).
    Trả {"cancelled": n, "blocked": m}. (CS-08, §5.1)
    """
    now = now or timezone.now()
    if not getattr(settings, "CONFIRMATION_AUTO_CANCEL_ENABLED", False):
        return {"cancelled": 0, "blocked": 0}

    decision_mins = getattr(settings, "CONFIRMATION_MANAGER_DECISION_MINUTES", 30)
    cutoff = now - timedelta(minutes=decision_mins)

    from apps.sales.models import SalesInvoiceLineBatch, SalesOrder
    from apps.sales.orders import services as order_services
    from apps.sales.refunds import services as refund_services

    task_ids = list(
        ConfirmationTask.objects.filter(
            state=ConfirmationTask.State.ESCALATED,
            escalation_reason__in=(
                ConfirmationTask.EscalationReason.UNREACHABLE,
                ConfirmationTask.EscalationReason.WRONG_NUMBER,
            ),
            auto_cancel_blocked_code="",
            escalated_at__isnull=False,
            escalated_at__lte=cutoff,
            note__status=DeliveryNote.Status.CONFIRMING,
        ).values_list("pk", flat=True)
    )

    cancelled = 0
    blocked = 0

    for task_id in task_ids:
        try:
            with transaction.atomic():
                t = ConfirmationTask.objects.select_related("note__sales_invoice__sales_order").get(pk=task_id)
                order_pk = t.note.sales_invoice.sales_order_id if (t.note and t.note.sales_invoice) else None
                if not order_pk:
                    continue

                order = SalesOrder.objects.select_for_update().get(pk=order_pk)
                note_obj = DeliveryNote.objects.select_for_update().get(pk=t.note_id)
                task = ConfirmationTask.objects.select_for_update().get(pk=task_id)

                if (
                    task.state != ConfirmationTask.State.ESCALATED
                    or note_obj.status != DeliveryNote.Status.CONFIRMING
                    or order.status not in (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING)
                    or not task.escalated_at
                    or task.escalated_at > cutoff
                    or task.auto_cancel_blocked_code != ""
                ):
                    continue

                invoice = getattr(order, "invoice", None)
                if not invoice:
                    continue

                allocations = SalesInvoiceLineBatch.objects.filter(
                    invoice_line__invoice=invoice
                ).select_related("batch")
                has_closed_batch = any(
                    getattr(a.batch, "is_closed", False) or getattr(a.batch, "status", "") == "CLOSED"
                    for a in allocations
                )

                if has_closed_batch:
                    task.auto_cancel_blocked_code = "BR-LO-05"
                    task.save(update_fields=["auto_cancel_blocked_code", "updated_at"])
                    record_audit(
                        "order_auto_cancel_blocked",
                        actor=None,
                        obj=order,
                        changes={"code": "BR-LO-05"},
                    )
                    blocked += 1
                    continue

                order_services.cancel_paid_order(
                    order=order,
                    actor=None,
                    reason="Không liên lạc được khách (Hệ thống tự huỷ)",
                    reason_code="UNREACHABLE_AUTO",
                )

                req_id = uuid.uuid5(uuid.NAMESPACE_URL, f"caveve:auto-cancel:{order.pk}")
                refund, _ = refund_services.create_invoice_refund(
                    invoice=invoice,
                    amount=refund_services.refundable_amount(invoice=invoice),
                    is_partial=False,
                    reason="Tự huỷ: không liên lạc được khách (BR-HT-10)",
                    actor=None,
                    request_id=req_id,
                )

                task.state = ConfirmationTask.State.REFUND_CALL
                task.refund = refund
                task.auto_cancelled_at = now
                task.attempts = 0
                task.claimed_by = None
                task.claimed_until = None
                task.save(update_fields=[
                    "state", "refund", "auto_cancelled_at", "attempts",
                    "claimed_by", "claimed_until", "updated_at"
                ])

                record_audit(
                    "order_auto_cancelled",
                    actor=None,
                    obj=order,
                    changes={"reason_code": "UNREACHABLE_AUTO", "refund_id": refund.pk},
                )
                cancelled += 1
        except Exception:
            logger.exception("Lỗi khi tự huỷ đơn cho task #%s", task_id)

    return {"cancelled": cancelled, "blocked": blocked}

