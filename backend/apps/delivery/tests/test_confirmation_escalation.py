"""
Kiểm thử tự động Lô 3 CSKH: Không liên lạc được, tự huỷ, báo khách (2026-09-28-cskh-xac-nhan-in-tem).
Bao phủ:
- CS-07: 3 lần trong 30' chuyển Quản lý quyết định (DELIVER_WITHOUT_CONFIRM, EXTEND, CANCEL)
- CS-08: Hệ thống tự huỷ khi Quản lý không xử lý trong 30' (cờ CONFIRMATION_AUTO_CANCEL_ENABLED), chặn BR-LO-05
- CS-09: Nhắc việc gọi báo huỷ & hoàn tiền (REFUND_CALL, NOTIFIED, guidance D5)
- CS-10: Shop báo trước luật gọi (site-info) và báo lý do khi đơn bị tự huỷ (cancel_notice)
- Bất biến 1 (không rò giá vốn) & Bất biến 9 (không rò PII)
"""
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.cost_keys import COST_KEYS
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, StockLedgerEntry, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, Refund, SalesInvoice, SalesInvoiceLine, SalesOrder
from apps.sales.models.invoices import SalesInvoiceLineBatch
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services
from apps.sales.refunds import services as refund_services
from apps.accounts import roles


class ConfirmationL3BaseTestCase(TestCase):
    def setUp(self):
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.sup = Supplier.objects.create(name="Tàu cá Long Hải")
        self.pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        grp = ItemGroup.objects.create(name="Hải sản")

        self.item = Item.objects.create(code="CA-THU", name="Cá thu", item_group=grp)
        today = timezone.localdate()
        ItemPrice.objects.create(
            price_list=self.pl, item=self.item, rate=Decimal("150000"),
            valid_from=today - timedelta(days=1),
        )
        self.batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=today, qty=Decimal("100"), purchase_rate=Decimal("110000"),
        )
        batch_services.publish_batch(batch=self.batch, actor=None)

        self.chu = make_user("chu1", roles.OWNER)
        self.ql = make_user("ql1", roles.MANAGER)
        self.cs1 = make_user("cs1", roles.CUSTOMER_SERVICE)
        self.cs2 = make_user("cs2", roles.CUSTOMER_SERVICE)
        self.kho = make_user("kho1", roles.WAREHOUSE_STAFF)

    def _create_order_with_confirmation(self, *, phone="0900000123", name="Khách Thử A", qty=Decimal("2")):
        order = order_services.create_order(
            customer_phone=phone,
            customer_name=name,
            delivery_address="Số 1 Đường Thử, P. Thử, Lâm Đồng",
            phone=phone,
            lines=[{"item_code": self.item.code, "qty": qty}],
        )
        payment_services.confirm_payment(
            order=order,
            bank_txn_id=f"TXN-{uuid.uuid4().hex[:8]}",
            amount=order.total_amount,
            received_at=timezone.now(),
        )
        order.refresh_from_db()
        note = DeliveryNote.objects.get(sales_invoice__sales_order=order)
        task = ConfirmationTask.objects.get(note=note)
        return order, note, task


class TestCS07EscalationAndDecide(ConfirmationL3BaseTestCase):
    def test_cs07_ac1_unreachable_recording_and_window(self):
        """09:00 cs1 ghi UNREACHABLE -> attempts=1, next_call_after=09:10, window_ends_at=09:30, PENDING."""
        t0 = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()

        call, dup = confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0)
        self.assertFalse(dup)
        task.refresh_from_db()
        self.assertEqual(task.attempts, 1)
        self.assertEqual(task.state, ConfirmationTask.State.PENDING)
        self.assertEqual(task.first_unreachable_at, t0)
        self.assertEqual(task.last_unreachable_at, t0)

    def test_cs07_ac2_retry_interval_blocked(self):
        """09:05 ghi UNREACHABLE -> 400 BR-GH-13, attempts giữ 1."""
        t0 = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0)

        t1 = t0 + timedelta(minutes=5)
        with self.assertRaises(BusinessError) as ctx:
            confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t1)
        self.assertEqual(ctx.exception.code, "BR-GH-13")

        task.refresh_from_db()
        self.assertEqual(task.attempts, 1)

    def test_cs07_ac3_max_attempts_escalates(self):
        """attempts=2 (09:00, 09:12), 09:25 ghi UNREACHABLE -> attempts=3, ESCALATED, escalated_at=09:25."""
        t0 = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()

        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0)
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0 + timedelta(minutes=12))
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0 + timedelta(minutes=25))

        task.refresh_from_db()
        self.assertEqual(task.attempts, 3)
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)
        self.assertEqual(task.escalation_reason, ConfirmationTask.EscalationReason.UNREACHABLE)
        self.assertEqual(task.escalated_at, t0 + timedelta(minutes=25))

    def test_cs07_ac4_job_escalates_expired_window_idempotent(self):
        """attempts=1 lúc 09:00, không gọi thêm, job chạy lúc 09:31 -> ESCALATED, escalated_at=09:31. Lần 2 không đổi."""
        t0 = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0)

        audit_count_before = AuditLog.objects.count()
        t_job = t0 + timedelta(minutes=31)
        n = confirmation_services.escalate_expired_windows(now=t_job)
        self.assertEqual(n, 1)

        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)
        self.assertEqual(task.escalated_at, t_job)

        # Chạy lần 2
        n2 = confirmation_services.escalate_expired_windows(now=t_job)
        self.assertEqual(n2, 0)
        self.assertEqual(AuditLog.objects.count(), audit_count_before + 1)

    def test_cs07_ac5_wrong_number_escalates_immediately(self):
        """Phiếu PENDING, ghi WRONG_NUMBER -> ESCALATED ngay."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WRONG_NUMBER")

        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)
        self.assertEqual(task.escalation_reason, ConfirmationTask.EscalationReason.WRONG_NUMBER)

    @override_settings(CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS=2)
    def test_cs07_ac6_config_max_attempts(self):
        """CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS=2 -> ghi UNREACHABLE lần 2 chuyển ESCALATED."""
        t0 = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()

        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0)
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0 + timedelta(minutes=15))

        task.refresh_from_db()
        self.assertEqual(task.attempts, 2)
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)

    def test_cs07_ac7_callback_not_escalated_by_window(self):
        """Phiếu CALLBACK qua 30 phút, job chạy -> không đổi."""
        t0 = timezone.now()
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CALLBACK", callback_at=t0 + timedelta(hours=2), now=t0)

        n = confirmation_services.escalate_expired_windows(now=t0 + timedelta(minutes=40))
        self.assertEqual(n, 0)
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.CALLBACK)

    def test_cs07_ac8_decide_deliver_without_confirm(self):
        """Quản lý chọn DELIVER_WITHOUT_CONFIRM có lý do -> PREPARING, confirm_skipped=True, AuditLog."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WRONG_NUMBER")

        client_ql = client_for(self.ql)
        resp = client_ql.post(
            f"/api/confirmation/queue/{note.pk}/decide/",
            {"decision": "DELIVER_WITHOUT_CONFIRM", "reason": "Khách quen, địa chỉ đã giao 2 lần"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["note_status"], "PREPARING")
        self.assertIsNone(data["confirm_state"])

        note.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        self.assertTrue(note.confirm_skipped)
        self.assertEqual(task.state, ConfirmationTask.State.DONE)

        audit = AuditLog.objects.filter(action="delivery_confirm_skipped").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.ql)
        self.assertEqual(audit.note, "Có ghi chú")  # TL-D3-L4: nhãn trung tính, chữ tự do không vào Nhật ký

    def test_cs07_ac9_decide_extend(self):
        """Quản lý chọn EXTEND tới +3 giờ -> confirm_state=CALLBACK, attempts=0."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WRONG_NUMBER")

        client_ql = client_for(self.ql)
        future_time = timezone.now() + timedelta(hours=3)
        resp = client_ql.post(
            f"/api/confirmation/queue/{note.pk}/decide/",
            {"decision": "EXTEND", "until": future_time.isoformat(), "reason": "Khách nhắn đang họp"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["note_status"], "CONFIRMING")
        self.assertEqual(data["confirm_state"], "CALLBACK")

        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.CALLBACK)
        self.assertEqual(task.attempts, 0)

    def test_cs07_ac10_decide_validation_errors(self):
        """EXTEND vượt quá max hours (>24h) hoặc thiếu reason ở DELIVER_WITHOUT_CONFIRM -> 400."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WRONG_NUMBER")

        client_ql = client_for(self.ql)
        # Thiếu reason
        resp1 = client_ql.post(
            f"/api/confirmation/queue/{note.pk}/decide/",
            {"decision": "DELIVER_WITHOUT_CONFIRM", "reason": ""},
            format="json",
        )
        self.assertEqual(resp1.status_code, 400)

        # EXTEND quá 24h
        resp2 = client_ql.post(
            f"/api/confirmation/queue/{note.pk}/decide/",
            {"decision": "EXTEND", "until": (timezone.now() + timedelta(hours=25)).isoformat()},
            format="json",
        )
        self.assertEqual(resp2.status_code, 400)

    def test_cs07_ac11_decide_cancel(self):
        """Quản lý chọn CANCEL -> đơn CANCELLED, hoàn kho đúng lô gốc, phiếu CANCELLED, suggest_refund_amount."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WRONG_NUMBER")

        batch_initial_qty = Batch.objects.get(pk=self.batch.pk).qty_available

        client_ql = client_for(self.ql)
        resp = client_ql.post(
            f"/api/confirmation/queue/{note.pk}/decide/",
            {"decision": "CANCEL", "reason_code": "UNREACHABLE", "note": "Không liên lạc được"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["note_status"], "CANCELLED")
        self.assertEqual(data["suggest_refund_amount"], str(int(order.total_amount)))

        order.refresh_from_db()
        note.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)

        # Hoàn kho về đúng lô gốc
        batch_fresh = Batch.objects.get(pk=self.batch.pk)
        self.assertEqual(batch_fresh.qty_available, batch_initial_qty + Decimal("2"))

    def test_cs07_ac12_decide_permissions(self):
        """cs1 và kho1 gọi POST decide -> 403."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WRONG_NUMBER")

        client_cs1 = client_for(self.cs1)
        resp1 = client_cs1.post(
            f"/api/confirmation/queue/{note.pk}/decide/",
            {"decision": "DELIVER_WITHOUT_CONFIRM", "reason": "test"},
            format="json",
        )
        self.assertEqual(resp1.status_code, 403)

        client_kho = client_for(self.kho)
        resp2 = client_kho.post(
            f"/api/confirmation/queue/{note.pk}/decide/",
            {"decision": "DELIVER_WITHOUT_CONFIRM", "reason": "test"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 403)


class TestCS08AutoCancel(ConfirmationL3BaseTestCase):
    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
    def test_cs08_ac1_auto_cancel_overdue_when_enabled(self):
        """ESCALATED 09:25. Job chạy 09:56 -> đơn CANCELLED UNREACHABLE_AUTO; phiếu hoàn created_by=None; REFUND_CALL."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        batch_initial_qty = Batch.objects.get(pk=self.batch.pk).qty_available

        t_job = t0 + timedelta(minutes=31)
        res = confirmation_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res["cancelled"], 1)
        self.assertEqual(res["blocked"], 0)

        order.refresh_from_db()
        note.refresh_from_db()
        task.refresh_from_db()

        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)
        self.assertEqual(task.state, ConfirmationTask.State.REFUND_CALL)
        self.assertEqual(task.auto_cancelled_at, t_job)
        self.assertIsNotNone(task.refund)
        self.assertIsNone(task.refund.created_by)
        self.assertEqual(task.refund.amount, order.total_amount)
        self.assertEqual(task.refund.status, Refund.Status.PENDING)

        # Kiểm tra hoàn kho
        batch_fresh = Batch.objects.get(pk=self.batch.pk)
        self.assertEqual(batch_fresh.qty_available, batch_initial_qty + Decimal("2"))

        # AuditLog
        audit = AuditLog.objects.filter(action="order_auto_cancelled").first()
        self.assertIsNotNone(audit)
        self.assertIsNone(audit.actor)
        self.assertEqual(audit.changes.get("reason_code"), "UNREACHABLE_AUTO")

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
    def test_cs08_ac2_job_does_not_cancel_before_deadline(self):
        """Job chạy 09:54 (< 30') -> không đổi gì."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        t_job = t0 + timedelta(minutes=29)
        res = confirmation_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res["cancelled"], 0)

        order.refresh_from_db()
        self.assertNotEqual(order.status, SalesOrder.Status.CANCELLED)

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
    def test_cs08_ac3_job_idempotent(self):
        """AC1 đã chạy, job chạy thêm 2 lần -> vẫn 1 lần huỷ, 1 phiếu hoàn, 1 AuditLog."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        t_job = t0 + timedelta(minutes=31)
        res1 = confirmation_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res1["cancelled"], 1)

        refund_count = Refund.objects.count()
        audit_count = AuditLog.objects.filter(action="order_auto_cancelled").count()

        res2 = confirmation_services.auto_cancel_overdue(now=t_job)
        res3 = confirmation_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res2["cancelled"], 0)
        self.assertEqual(res3["cancelled"], 0)
        self.assertEqual(Refund.objects.count(), refund_count)
        self.assertEqual(AuditLog.objects.filter(action="order_auto_cancelled").count(), audit_count)

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
    def test_cs08_ac4_job_skips_resolved_task(self):
        """Quản lý đã chọn DELIVER_WITHOUT_CONFIRM -> job chạy không huỷ."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        confirmation_services.decide(task.pk, self.ql, decision="DELIVER_WITHOUT_CONFIRM", reason="Khách quen")

        t_job = t0 + timedelta(minutes=31)
        res = confirmation_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res["cancelled"], 0)
        order.refresh_from_db()
        self.assertNotEqual(order.status, SalesOrder.Status.CANCELLED)

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
    def test_cs08_ac5_job_skips_manually_cancelled_order(self):
        """Đơn đã bị Quản lý huỷ tay -> job chạy không tạo phiếu hoàn thứ hai."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        order_services.cancel_paid_order(order=order, actor=self.ql, reason="Huỷ tay")

        t_job = t0 + timedelta(minutes=31)
        res = confirmation_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res["cancelled"], 0)

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
    def test_cs08_ac7_job_blocks_auto_cancel_when_batch_closed(self):
        """Lô L đã CLOSED -> không huỷ, auto_cancel_blocked_code=BR-LO-05, AuditLog."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        # Đánh dấu lô đã đóng
        self.batch.status = Batch.Status.CLOSED
        self.batch.save()

        t_job = t0 + timedelta(minutes=31)
        res = confirmation_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res["cancelled"], 0)
        self.assertEqual(res["blocked"], 1)

        task.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(task.auto_cancel_blocked_code, "BR-LO-05")
        self.assertNotEqual(order.status, SalesOrder.Status.CANCELLED)

        audit = AuditLog.objects.filter(action="order_auto_cancel_blocked").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes.get("code"), "BR-LO-05")

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True, CONFIRMATION_MANAGER_DECISION_MINUTES=60)
    def test_cs08_ac8_configurable_decision_minutes(self):
        """CONFIRMATION_MANAGER_DECISION_MINUTES=60 -> 09:56 không huỷ, 10:26 thì huỷ."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        # 09:56 (31 phút sau)
        res1 = confirmation_services.auto_cancel_overdue(now=t0 + timedelta(minutes=31))
        self.assertEqual(res1["cancelled"], 0)

        # 10:26 (61 phút sau)
        res2 = confirmation_services.auto_cancel_overdue(now=t0 + timedelta(minutes=61))
        self.assertEqual(res2["cancelled"], 1)

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
    def test_cs08_ac10_want_cancel_does_not_auto_cancel(self):
        """Phiếu ESCALATED vì WANT_CANCEL -> quá hạn không tự huỷ."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.WANT_CANCEL
        task.escalated_at = t0
        task.save()

        t_job = t0 + timedelta(minutes=35)
        res = confirmation_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res["cancelled"], 0)

        order.refresh_from_db()
        self.assertNotEqual(order.status, SalesOrder.Status.CANCELLED)

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=False)
    def test_cs08_flag_disabled_does_not_cancel(self):
        """Khi cờ tự huỷ tắt -> quá hạn không huỷ."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        t_job = t0 + timedelta(minutes=35)
        res = confirmation_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res["cancelled"], 0)


class TestCS09RefundCalls(ConfirmationL3BaseTestCase):
    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
    def _create_auto_cancelled_order(self):
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        # cs1 gọi ghi nhận
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0)
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        confirmation_services.auto_cancel_overdue(now=t0 + timedelta(minutes=31))
        task.refresh_from_db()
        note.refresh_from_db()
        order.refresh_from_db()
        return order, note, task

    def test_cs09_ac1_cskh_queue_refund_call(self):
        """cs1 (người đã gọi) mở lọc Báo huỷ & hoàn -> có đơn, số tiền, hạn hoàn, phone đầy đủ."""
        order, note, task = self._create_auto_cancelled_order()

        client_cs1 = client_for(self.cs1)
        resp = client_cs1.get("/api/confirmation/queue/?state=REFUND_CALL")
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)

        item = results[0]
        self.assertEqual(item["note_id"], note.pk)
        self.assertEqual(item["confirm_state"], "REFUND_CALL")
        self.assertTrue(item["in_scope"])
        self.assertEqual(item["phone"], "0900000123")
        self.assertEqual(item["customer_name"], "Khách Thử A")
        self.assertIsNotNone(item.get("refund"))
        self.assertEqual(item["refund"]["amount"], str(int(order.total_amount)))
        self.assertEqual(item["refund"]["status_label"], "Chờ hoàn")

    def test_cs09_ac2_record_notified(self):
        """cs1 ghi NOTIFIED -> task DONE (confirm_state=None), bản ghi gọi + AuditLog."""
        order, note, task = self._create_auto_cancelled_order()

        client_cs1 = client_for(self.cs1)
        resp = client_cs1.post(
            f"/api/confirmation/queue/{note.pk}/calls/",
            {"result": "NOTIFIED", "note": "Đã gọi thông báo khách"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIsNone(data["confirm_state"])

        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.DONE)

    def test_cs09_ac3_record_unreachable_in_refund_call(self):
        """Ghi UNREACHABLE trong REFUND_CALL -> task vẫn mở, attempts tăng, không tự huỷ thêm."""
        order, note, task = self._create_auto_cancelled_order()

        client_cs1 = client_for(self.cs1)
        for i in range(3):
            resp = client_cs1.post(
                f"/api/confirmation/queue/{note.pk}/calls/",
                {"result": "UNREACHABLE", "note": f"Gọi lần {i+1} không nghe"},
                format="json",
            )
            self.assertEqual(resp.status_code, 201)

        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.REFUND_CALL)
        self.assertEqual(task.attempts, 3)

    def test_cs09_ac4_pii_out_of_scope(self):
        """cs2 chưa từng gọi đơn này -> in_scope=False, phone_masked, không có customer_name hay address."""
        order, note, task = self._create_auto_cancelled_order()

        client_cs2 = client_for(self.cs2)
        resp = client_cs2.get("/api/confirmation/queue/?state=REFUND_CALL")
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)

        item = results[0]
        self.assertFalse(item["in_scope"])
        self.assertIsNone(item["customer_name"])
        self.assertIsNone(item["phone"])
        self.assertIsNone(item["address"])
        self.assertIn("09xx xxx 123", item["phone_masked"])

    def test_cs09_ac5_refund_confirmed_display(self):
        """Chủ xác nhận phiếu hoàn -> queue hiện Đã hoàn."""
        order, note, task = self._create_auto_cancelled_order()
        refund = task.refund

        refund_services.confirm_refund(refund=refund, bank_txn_ref="VNPAY123456", actor=self.chu)

        client_cs1 = client_for(self.cs1)
        resp = client_cs1.get("/api/confirmation/queue/?state=REFUND_CALL")
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertEqual(results[0]["refund"]["status"], "REFUNDED")
        self.assertEqual(results[0]["refund"]["status_label"], "Đã hoàn")

    def test_cs09_ac6_cs1_cannot_confirm_refund(self):
        """cs1 gọi confirm_refund -> 403."""
        order, note, task = self._create_auto_cancelled_order()
        client_cs1 = client_for(self.cs1)
        resp = client_cs1.post(f"/api/sales/refunds/{task.refund.pk}/confirm/", {"bank_txn_ref": "123"})
        self.assertEqual(resp.status_code, 403)

    def test_cs09_ac7_pii_note_blocked(self):
        """Ghi note có 12 chữ số -> 400 BR-GH-19."""
        order, note, task = self._create_auto_cancelled_order()
        client_cs1 = client_for(self.cs1)
        resp = client_cs1.post(
            f"/api/confirmation/queue/{note.pk}/calls/",
            {"result": "NOTIFIED", "note": "STK 123456789012 Techcombank"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-GH-19")

    def test_cs09_ac8_guidance_displayed(self):
        """Chi tiết mục chờ gọi REFUND_CALL có guidance D5."""
        order, note, task = self._create_auto_cancelled_order()
        client_cs1 = client_for(self.cs1)
        resp = client_cs1.get(f"/api/confirmation/queue/{note.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Không ghi số tài khoản khách vào hệ thống", resp.json()["guidance"])


class TestCS10ShopNotices(ConfirmationL3BaseTestCase):
    def test_cs10_ac1_site_info_api(self):
        """GET /api/public/site-info/ trả confirmation_policy (khoá `cskh_notice` đã gỡ ở Lô 5); đổi max_attempts trả đúng số."""
        client = client_for(None)
        resp = client.get("/api/public/site-info/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "public, max-age=300")
        self.assertNotIn("cskh_notice", resp.json())
        notice = resp.json()["confirmation_policy"]
        self.assertIn("working_hours", notice)
        self.assertEqual(notice["max_attempts"], 3)
        self.assertEqual(notice["window_minutes"], 30)

        with override_settings(CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS=2):
            resp2 = client.get("/api/public/site-info/")
            self.assertEqual(resp2.json()["confirmation_policy"]["max_attempts"], 2)

    def test_cs10_ac2_order_lookup_confirming(self):
        """Đơn CONFIRMING -> Shop tra đơn thấy status_label Chờ vựa gọi xác nhận."""
        order, note, task = self._create_order_with_confirmation(phone="0900000123")
        client = client_for(None)
        resp = client.get(f"/api/shop/orders/{order.code}/?phone_last4=0123")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status_label"], "Đã thanh toán – chờ vựa gọi xác nhận")
        self.assertEqual(data["delivery"]["status"], "CONFIRMING")
        self.assertEqual(data["delivery"]["status_label"], "Chờ vựa gọi xác nhận")
        self.assertIsNone(data["cancel_notice"])

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
    def test_cs10_ac3_order_lookup_auto_cancelled(self):
        """Đơn tự huỷ -> Shop tra đơn có cancel_notice đủ 4 phần."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation(phone="0900000123")
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        confirmation_services.auto_cancel_overdue(now=t0 + timedelta(minutes=31))

        client = client_for(None)
        resp = client.get(f"/api/shop/orders/{order.code}/?phone_last4=0123")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "CANCELLED")
        self.assertIsNotNone(data["cancel_notice"])

        notice = data["cancel_notice"]
        self.assertEqual(notice["reason_code"], "UNREACHABLE_AUTO")
        self.assertIn("3 lần trong 30 phút", notice["message"])
        self.assertEqual(notice["refund"]["amount"], str(int(order.total_amount)))
        self.assertEqual(notice["refund"]["status_label"], "Đang chờ hoàn")

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
    def test_cs10_ac4_order_lookup_refunded(self):
        """Chủ xác nhận hoàn -> status_label Đã hoàn."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation(phone="0900000123")
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()

        confirmation_services.auto_cancel_overdue(now=t0 + timedelta(minutes=31))
        task.refresh_from_db()
        refund_services.confirm_refund(refund=task.refund, bank_txn_ref="TX123", actor=self.chu)

        client = client_for(None)
        resp = client.get(f"/api/shop/orders/{order.code}/?phone_last4=0123")
        data = resp.json()
        self.assertEqual(data["cancel_notice"]["refund"]["status_label"], "Đã hoàn")
        self.assertIsNotNone(data["cancel_notice"]["refund"]["refunded_at"])

    def test_cs10_ac5_order_lookup_manual_cancelled(self):
        """Đơn do Quản lý huỷ tay -> không hiện câu không liên lạc được."""
        order, note, task = self._create_order_with_confirmation(phone="0900000123")
        order_services.cancel_paid_order(order=order, actor=self.ql, reason="Khách đổi ý")

        client = client_for(None)
        resp = client.get(f"/api/shop/orders/{order.code}/?phone_last4=0123")
        data = resp.json()
        self.assertIsNotNone(data["cancel_notice"])
        self.assertIsNone(data["cancel_notice"]["reason_code"])
        self.assertNotIn("không liên lạc được", data["cancel_notice"]["message"])

    def test_cs10_ac6_no_pii_in_lookup(self):
        """Tra đơn AllowAny không có key tên, SĐT, địa chỉ, người nhận hộ, ghi chú gọi (Bất biến 9)."""
        order, note, task = self._create_order_with_confirmation(phone="0900000123", name="Khách Bí Mật")
        client = client_for(None)
        resp = client.get(f"/api/shop/orders/{order.code}/?phone_last4=0123")
        data = resp.json()

        def _assert_no_pii(val):
            if isinstance(val, dict):
                for k, v in val.items():
                    self.assertNotIn(k, {"customer", "customer_name", "phone", "address", "delivery_address", "recipient_name", "recipient_phone", "note", "calls"})
                    _assert_no_pii(v)
            elif isinstance(val, list):
                for v in val:
                    _assert_no_pii(v)
            elif isinstance(val, str):
                self.assertNotIn("Khách Bí Mật", val)
                self.assertNotIn("0900000123", val)

        _assert_no_pii(data)

    def test_cs10_ac7_wrong_phone_404(self):
        """Sai 4 số cuối SĐT -> 404."""
        order, note, task = self._create_order_with_confirmation(phone="0900000123")
        client = client_for(None)
        resp = client.get(f"/api/shop/orders/{order.code}/?phone_last4=9999")
        self.assertEqual(resp.status_code, 404)

    def test_cs10_ac8_no_cost_keys(self):
        """Tra đơn không chứa bất kỳ khoá giá vốn nào (Bất biến 1)."""
        order, note, task = self._create_order_with_confirmation(phone="0900000123")
        client = client_for(None)
        resp = client.get(f"/api/shop/orders/{order.code}/?phone_last4=0123")
        data = resp.json()

        def _assert_no_cost(val):
            if isinstance(val, dict):
                for k, v in val.items():
                    self.assertNotIn(k, {"unit_cost", "purchase_rate", "landed_unit_cost", "cost", "profit", "margin"})
                    _assert_no_cost(v)
            elif isinstance(val, list):
                for v in val:
                    _assert_no_cost(v)

        _assert_no_cost(data)
