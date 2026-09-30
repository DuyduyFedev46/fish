"""Test tái hiện lỗi review P1–P7 (R1–R6). Đỏ trên code hiện tại — không đặt trong backend/ để suite vẫn xanh. Cách chạy: xem README.md cùng thư mục."""
import datetime
from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.execution.safety import check_ai_close_batch_conditions
from apps.ai.execution.tests.test_dw25_close_batch import CloseBatchAiTests
from apps.ai.models import AiAction, AiPolicyVersion
from apps.delivery.models import ConfirmationTask, DeliveryNote
from apps.delivery.tests.test_cskh_l3 import CskhL3BaseTestCase
from apps.delivery.cskh import services as cskh_services
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch
from apps.purchasing.models import PurchaseReceipt
from apps.purchasing.receipts import services as receipt_services
from apps.sales.models import (
    PaymentTransaction, SalesOrder, SalesOrderLine, SalesOrderLineBatch,
)
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services
from apps.sales.payments.auto_confirm import process_exact_payment_matches


class R1AiCloseBatchSoldBatch(CloseBatchAiTests):
    """Lô đã từng bán (có SalesOrderLineBatch của đơn COMPLETED) -> safety.py FieldError."""

    def _add_completed_sale(self, batch):
        from apps.sales.models import Customer
        c = Customer.objects.create(phone="0900000999", name="Gia", default_address="x")
        o = SalesOrder.objects.create(code="SO-R1", customer=c, total_amount=Decimal("1"),
                                      status=SalesOrder.Status.COMPLETED)
        line = SalesOrderLine.objects.create(order=o, item=self.item, qty=Decimal("1"), rate=Decimal("1"),
                                             amount=Decimal("1"))
        SalesOrderLineBatch.objects.create(order_line=line, batch=batch, component_item=self.item, qty=Decimal("1"),
                                           unit_cost=Decimal("1"))

    def test_r1_safety_crashes_for_sold_batch(self):
        batch = self._create_fully_eligible_batch()
        self._add_completed_sale(batch)
        self.assertEqual(batch_services.check_close_batch(batch), [])
        with self.assertRaises(Exception) as ctx:
            check_ai_close_batch_conditions(batch)
        print("\nR1 safety:", type(ctx.exception).__name__, ctx.exception)

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_r1_job_poison_pill(self):
        batch = self._create_fully_eligible_batch()
        self._add_completed_sale(batch)
        act = AiAction.objects.create(
            command="inventory.batch.close", kind="write", level="B", status="SCHEDULED",
            owner=self.u_chu, target_model="batch", target_id=str(batch.id),
            execute_after=timezone.now() - timedelta(seconds=1),
        )
        AiPolicyVersion.objects.create(version=1, global_mode="on",
                                       red_zone_open={"inventory.close_batch": True}, created_by=self.u_chu)
        from apps.ai.models import AiConfigVersion
        AiConfigVersion.objects.create(user=self.u_chu, version=1, overrides={"inventory.batch.close": "B"}, created_by=self.u_chu)
        try:
            call_command("run_due_ai_actions")
            print("\nR1 job: no crash")
        except Exception as e:
            print("\nR1 job crashed:", type(e).__name__, e)
        act.refresh_from_db()
        print("R1 action status after job:", act.status)


class R2CskhConfirmAfterAutoCancel(CskhL3BaseTestCase):
    @override_settings(CSKH_AUTO_CANCEL_ENABLED=True)
    def test_r2_confirm_on_refund_call_task(self):
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_cskh()
        cskh_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0)
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()
        res = cskh_services.auto_cancel_overdue(now=t0 + timedelta(minutes=31))
        self.assertEqual(res["cancelled"], 1)
        order.refresh_from_db(); note.refresh_from_db(); task.refresh_from_db()
        print("\nR2 after auto-cancel:", order.status, note.status, task.state)
        # CSKH bấm "Đã xác nhận" trên màn hình cũ (hoặc tranh với job)
        cskh_services.record_call(task.pk, self.cs1, result="CONFIRMED", now=t0 + timedelta(minutes=32))
        order.refresh_from_db(); note.refresh_from_db(); task.refresh_from_db()
        print("R2 after CONFIRMED:", order.status, note.status, task.state)


class R3PublishAfterCancelReceipt(CskhL3BaseTestCase):
    def test_r3_publish_stale_after_cancel(self):
        receipt, batches = receipt_services.create_and_submit_receipt(
            supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            lines=[{"item_code": self.item, "qty": Decimal("5"), "rate": Decimal("1000")}],
            actor=self.kho,
        )
        stale = Batch.objects.get(pk=batches[0].pk)  # get_object() của request publish
        receipt_services.cancel_receipt(receipt=receipt, actor=self.kho)  # request huỷ chạy xong trước
        batch_services.publish_batch(batch=stale, actor=self.chu)
        b = Batch.objects.get(pk=stale.pk)
        receipt.refresh_from_db()
        print("\nR3 receipt:", receipt.status, "batch:", b.status, "qty:", b.qty_available)


class R4AutoConfirmNag(CskhL3BaseTestCase):
    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True)
    def test_r4_escalate_repeats(self):
        AiPolicyVersion.objects.create(version=1, global_mode="on",
                                       red_zone_open={"system.auto_confirm_exact_match": True},
                                       created_by=self.chu)
        PaymentTransaction.objects.create(
            bank_txn_id="TXN-R4", amount=Decimal("1"), match_status="UNMATCHED",
            resolution_status="OPEN", received_at=timezone.now(), raw_payload={},
        )
        process_exact_payment_matches()
        process_exact_payment_matches()
        n = AuditLog.objects.filter(action="escalate_unmatched_payment").count()
        act = AiAction.objects.get(command="sales.paymenttransaction.resolve")
        act.status = AiAction.Status.REJECTED
        act.save()
        process_exact_payment_matches()
        act.refresh_from_db()
        print("\nR4 audit rows after 2 runs:", n, "| action after reject + run:", act.status)


class R5CancelExpiredWithReservation(CskhL3BaseTestCase):
    def test_r5(self):
        order = order_services.create_order(
            customer_phone="0900000111", customer_name="A", delivery_address="x", phone="0900000111",
            lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )
        b = Batch.objects.get(pk=self.batch.pk)
        Batch.objects.filter(pk=b.pk).update(status=Batch.Status.EXPIRED)
        b.refresh_from_db()
        print("\nR5 before cancel: avail", b.qty_available, "reserved", b.qty_reserved)
        batch_services.cancel_expired_batch(batch=b, actor=self.chu)
        b.refresh_from_db()
        print("R5 after cancel: status", b.status, "avail", b.qty_available, "reserved", b.qty_reserved)
        try:
            payment_services.confirm_payment(order=order, bank_txn_id="TXN-R5", amount=order.total_amount,
                                             received_at=timezone.now())
        except Exception as e:
            print("R5 confirm_payment raised:", type(e).__name__, e)
        order.refresh_from_db()
        p = PaymentTransaction.objects.filter(bank_txn_id="TXN-R5").first()
        print("R5 order:", order.status, "| txn:", p and (p.match_status, p.resolution_status))


class R6PnlAfterAutoCancel(CskhL3BaseTestCase):
    @override_settings(CSKH_AUTO_CANCEL_ENABLED=True)
    def test_r6(self):
        from apps.reports.services import batch_pnl
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_cskh()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()
        cskh_services.auto_cancel_overdue(now=t0 + timedelta(minutes=31))
        b = Batch.objects.get(pk=self.batch.pk)
        order.refresh_from_db()
        inv = order.invoice
        p = batch_pnl(batch=b)
        print("\nR6 order", order.status, "invoice", inv.status, "| batch avail", b.qty_available,
              "| pnl revenue", p["revenue"], "qty_sold", p["qty_sold"])
