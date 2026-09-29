"""
Dịch vụ CSKH: Xác nhận đơn hàng, ghi kết quả gọi, quản lý hàng chờ gọi (2026-09-28-cskh-xac-nhan-in-tem).
Tuân thủ:
- Thứ tự khoá cố định (§1.5): SalesOrder -> DeliveryNote -> ConfirmationTask
- Bất biến 1: Không tính toán hay trả về giá vốn
- Bất biến 9: Chặn PII trong ghi chú tự do (BR-GH-19, has_long_digit_run)
"""
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError, ConflictError
from apps.common.pii import has_long_digit_run, normalize_phone
from apps.delivery import services as delivery_services
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote, LabelPrint


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
    CSKH nhận đơn để gọi — khoá mềm trong CSKH_CLAIM_MINUTES (CS-05-AC3, CS-05-AC4, §1.4).
    """
    now = now or timezone.now()
    with transaction.atomic():
        # Khoá dòng ConfirmationTask
        task = ConfirmationTask.objects.select_for_update().select_related("note", "claimed_by").get(pk=task_id)

        if task.note.status == DeliveryNote.Status.CANCELLED:
            raise BusinessError("Đơn đã huỷ.", code="BR-GH-07")

        if task.state == ConfirmationTask.State.DONE:
            raise ConflictError("Đơn đã hoàn tất xử lý xác nhận.", code="STALE_STATE")

        # Kiểm tra người khác đang claim còn hạn
        if task.claimed_by_id and task.claimed_by_id != user.pk:
            if task.claimed_until and task.claimed_until > now:
                claimer_name = task.claimed_by.get_full_name() or task.claimed_by.username
                time_str = timezone.localtime(task.claimed_until).strftime("%H:%M")
                raise ConflictError(
                    f"Đơn đang được {claimer_name} xử lý tới {time_str}.",
                    code="CLAIMED",
                    extra={"claimed_until": task.claimed_until.isoformat()},
                )

        claim_mins = getattr(settings, "CSKH_CLAIM_MINUTES", 5)
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
        if note.status == DeliveryNote.Status.CANCELLED:
            raise BusinessError("Đơn đã huỷ.", code="BR-GH-07")

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
                claimer_name = task.claimed_by.get_full_name() or task.claimed_by.username
                time_str = timezone.localtime(task.claimed_until).strftime("%H:%M")
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
            min_retry = getattr(settings, "CSKH_MIN_RETRY_MINUTES", 10)
            max_attempts = getattr(settings, "CSKH_MAX_UNREACHABLE_ATTEMPTS", 3)
            window_mins = getattr(settings, "CSKH_UNREACHABLE_WINDOW_MINUTES", 30)

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
                "Phiếu không ở trạng thái Soạn hàng để huỷ xác nhận.",
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
        task.save(update_fields=["state", "claimed_by", "claimed_until", "updated_at"])

        record_audit(
            "delivery_unconfirmed",
            actor=user,
            obj=note,
            changes={"status": {"from": "PREPARING", "to": "CONFIRMING"}},
            note=clean_reason,
        )

        return note, task


def change_recipient(
    task_id: int,
    user,
    *,
    recipient_name: str = "",
    recipient_phone: str = "",
) -> dict:
    """
    Đổi thông tin người nhận hộ (CS-06, §1.6, CS-12).
    Nếu tem đã in: vô hiệu tem cũ (superseded_at = now).
    Nếu không đổi: trả changed=[], không AuditLog, không vô hiệu tem.
    """
    clean_name = (recipient_name or "").strip()
    clean_phone = normalize_phone(recipient_phone or "")

    with transaction.atomic():
        try:
            task = ConfirmationTask.objects.select_related("note").get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            raise BusinessError("Không tìm thấy mục chờ gọi.", code="NOT_FOUND")

        note = DeliveryNote.objects.select_for_update().get(pk=task.note_id)

        if note.status not in (DeliveryNote.Status.CONFIRMING, DeliveryNote.Status.PREPARING):
            raise ConflictError(
                "Chỉ đổi thông tin nhận khi đơn ở Chờ xác nhận hoặc Soạn hàng.",
                code="STALE_STATE",
                extra={"current_status": note.status},
            )

        # Kiểm tra xem có gì thay đổi không
        current_name = note.recipient_name or ""
        current_phone = note.recipient_phone or ""
        if clean_name == current_name and clean_phone == current_phone:
            return {"changed": [], "note": note}

        now = timezone.now()
        # Vô hiệu tem cũ nếu đã in (§1.6, §2.4)
        note.label_prints.filter(superseded_at__isnull=True).update(superseded_at=now)

        note.recipient_name = clean_name
        note.recipient_phone = clean_phone
        note.save(update_fields=["recipient_name", "recipient_phone"])

        changed_fields = []
        if clean_name != current_name:
            changed_fields.append("recipient_name")
        if clean_phone != current_phone:
            changed_fields.append("recipient_phone")

        record_audit(
            "recipient_changed",
            actor=user,
            obj=note,
            changes={"fields": changed_fields},
        )

        return {
            "changed": changed_fields,
            "note": note,
        }

