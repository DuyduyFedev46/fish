"""
P8 Lô 1 — SR-03 (F01, DW-25, DW-21): AI chốt lô với lô ĐÃ TỪNG BÁN, và job `run_due_ai_actions`
không chết cứng vì một việc lỗi.

Chuyển từ test tái hiện R1 của review 30/09 (repro/review_repro_tests.py): bỏ print, dùng assert theo
hành vi đúng. Dữ liệu hoàn toàn giả (SĐT 0900000xxx, tên "Khách Giả").
"""
import datetime
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.execution import safety
from apps.ai.execution.dispatch import DispatchResult
from apps.ai.execution.tests import test_dw25_close_batch as dw25
from apps.ai.models import AiAction, AiConfigVersion, AiPolicyVersion
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch
from apps.sales.models import (
    Customer, PaymentTransaction, Refund, SalesInvoice, SalesOrder, SalesOrderLine, SalesOrderLineBatch,
)
from apps.accounts import roles

CMD = "inventory.batch.close"
PII_SENTINEL = "SECRET-KHACH-GIA-0900000123"
DISPATCH_PATH = "apps.ai.management.commands.run_due_ai_actions.dispatch_command"


class _SoldBatchBase(TestCase):
    """Dựng fixture nhờ hàm của DW-25 mà KHÔNG kế thừa (kế thừa sẽ chạy lại các test cũ)."""

    _create_fully_eligible_batch = dw25.CloseBatchAiTests._create_fully_eligible_batch

    def setUp(self):
        dw25.CloseBatchAiTests.setUp(self)
        self.u_cskh = make_user("cskh_p8l1", roles.CUSTOMER_SERVICE)
        self.u_giao = make_user("giao_p8l1", roles.DELIVERY_STAFF)

    def _add_sale(self, batch, *, status=SalesOrder.Status.COMPLETED, code="SO-P8L1"):
        cust, _ = Customer.objects.get_or_create(
            phone="0900000999", defaults={"name": "Khách Giả A", "default_address": "Số 1 Đường Giả"},
        )
        order = SalesOrder.objects.create(
            code=code, customer=cust, total_amount=Decimal("1000"), status=status,
        )
        line = SalesOrderLine.objects.create(
            order=order, item=self.item, qty=Decimal("1"), rate=Decimal("1000"), amount=Decimal("1000"),
        )
        SalesOrderLineBatch.objects.create(
            order_line=line, batch=batch, component_item=self.item, qty=Decimal("1"), unit_cost=Decimal("1"),
        )
        return order

    def _open_ai(self):
        AiPolicyVersion.objects.create(
            version=1, global_mode="on", red_zone_open={"inventory.close_batch": True}, created_by=self.u_chu,
        )
        AiConfigVersion.objects.create(
            user=self.u_chu, version=1, overrides={CMD: "B"}, created_by=self.u_chu,
        )

    def _scheduled(self, batch, *, seconds_ago=1):
        return AiAction.objects.create(
            command=CMD, kind="write", level="B", status="SCHEDULED", owner=self.u_chu,
            target_model="batch", target_id=str(batch.id),
            execute_after=timezone.now() - timedelta(seconds=seconds_ago),
        )


class P8Sr03SafetyTests(_SoldBatchBase):
    def test_sr03_ac1_lo_da_ban_khong_van_field_error(self):
        batch = self._create_fully_eligible_batch()
        self._add_sale(batch)
        ok, reason = safety.check_ai_close_batch_conditions(batch)
        self.assertTrue(ok, reason)
        self.assertIsNone(reason)

    def test_sr03_ac2a_phieu_hoan_pending_theo_hoa_don_chan_chot(self):
        batch = self._create_fully_eligible_batch()
        order = self._add_sale(batch)
        inv = SalesInvoice.objects.create(
            code="HD-P8L1", sales_order=order, customer=order.customer,
            issued_at=timezone.now(), amount=Decimal("1000"),
        )
        Refund.objects.create(sales_invoice=inv, amount=Decimal("1000"), status=Refund.Status.PENDING)
        ok, reason = safety.check_ai_close_batch_conditions(batch)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")

    def test_sr03_ac2a_phieu_hoan_pending_theo_giao_dich_chan_chot(self):
        batch = self._create_fully_eligible_batch()
        order = self._add_sale(batch)
        txn = PaymentTransaction.objects.create(
            bank_txn_id="TXN-P8L1-A", sales_order=order, amount=Decimal("1000"),
            match_status=PaymentTransaction.MatchStatus.MATCHED, received_at=timezone.now(),
        )
        Refund.objects.create(payment_transaction=txn, amount=Decimal("1000"), status=Refund.Status.PENDING)
        ok, reason = safety.check_ai_close_batch_conditions(batch)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")

    def test_sr03_ac2b_giao_dich_open_cua_don_chan_chot(self):
        batch = self._create_fully_eligible_batch()
        order = self._add_sale(batch)
        PaymentTransaction.objects.create(
            bank_txn_id="TXN-P8L1-B", sales_order=order, amount=Decimal("500"),
            match_status=PaymentTransaction.MatchStatus.UNDERPAID,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN, received_at=timezone.now(),
        )
        ok, reason = safety.check_ai_close_batch_conditions(batch)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")

    def test_sr03_ac2_giao_dich_da_xu_ly_khong_chan(self):
        """Đối chứng: giao dịch RESOLVED và phiếu hoàn đã REFUNDED không chặn (điều kiện sàn không chặn nhầm)."""
        batch = self._create_fully_eligible_batch()
        order = self._add_sale(batch)
        txn = PaymentTransaction.objects.create(
            bank_txn_id="TXN-P8L1-C", sales_order=order, amount=Decimal("500"),
            match_status=PaymentTransaction.MatchStatus.UNDERPAID,
            resolution_status=PaymentTransaction.ResolutionStatus.RESOLVED, received_at=timezone.now(),
        )
        Refund.objects.create(payment_transaction=txn, amount=Decimal("500"), status=Refund.Status.REFUNDED)
        ok, reason = safety.check_ai_close_batch_conditions(batch)
        self.assertTrue(ok, reason)


@override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
class P8Sr03JobTests(_SoldBatchBase):
    def setUp(self):
        super().setUp()
        self._open_ai()

    def _overdue_pending(self):
        act = AiAction.objects.create(
            command="sales.salesorder.partial_update", kind="write", level="C", status="PENDING",
            owner=self.u_chu, assignee_group=roles.CUSTOMER_SERVICE,
        )
        AiAction.objects.filter(pk=act.pk).update(created_at=timezone.now() - timedelta(hours=3))
        return act

    def test_sr03_ac3_job_khong_chet_voi_lo_da_ban_viec_sau_van_chay(self):
        sold = self._create_fully_eligible_batch()
        self._add_sale(sold)
        other = self._create_fully_eligible_batch()
        a = self._scheduled(sold, seconds_ago=60)
        b = self._scheduled(other, seconds_ago=30)
        overdue = self._overdue_pending()

        call_command("run_due_ai_actions")  # không được văng exception

        a.refresh_from_db()
        b.refresh_from_db()
        overdue.refresh_from_db()
        self.assertEqual(a.status, AiAction.Status.DONE)
        sold.refresh_from_db()
        self.assertEqual(sold.status, Batch.Status.CLOSED)
        self.assertEqual(b.status, AiAction.Status.DONE)  # việc xếp sau vẫn được xử lý
        self.assertEqual(overdue.status, AiAction.Status.ESCALATED)  # bước đẩy quá hạn 2 giờ vẫn chạy
        self.assertEqual(overdue.assignee_group, roles.OWNER)

    def test_sr03_ac3_lo_da_ban_con_phieu_hoan_pending_thi_escalated(self):
        sold = self._create_fully_eligible_batch()
        order = self._add_sale(sold)
        inv = SalesInvoice.objects.create(
            code="HD-P8L1B", sales_order=order, customer=order.customer,
            issued_at=timezone.now(), amount=Decimal("1000"),
        )
        Refund.objects.create(sales_invoice=inv, amount=Decimal("1000"), status=Refund.Status.PENDING)
        other = self._create_fully_eligible_batch()
        a = self._scheduled(sold, seconds_ago=60)
        b = self._scheduled(other, seconds_ago=30)

        call_command("run_due_ai_actions")

        a.refresh_from_db()
        b.refresh_from_db()
        sold.refresh_from_db()
        self.assertEqual(a.status, AiAction.Status.ESCALATED)
        self.assertEqual(a.assignee_group, roles.OWNER)
        self.assertEqual(a.downgrade_reason["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")
        self.assertNotEqual(sold.status, Batch.Status.CLOSED)
        self.assertEqual(b.status, AiAction.Status.DONE)

    def test_sr03_ac4_exception_bat_ky_thanh_failed_viec_sau_van_chay_idempotent(self):
        first = self._create_fully_eligible_batch()
        second = self._create_fully_eligible_batch()
        a = self._scheduled(first, seconds_ago=60)
        b = self._scheduled(second, seconds_ago=30)
        overdue = self._overdue_pending()

        boom = RuntimeError(f"loi gia {PII_SENTINEL}")
        ok_result = DispatchResult({"id": second.id}, 200, False)
        with mock.patch(DISPATCH_PATH, side_effect=[boom, ok_result]) as disp:
            with self.assertLogs(level="DEBUG") as logs:
                call_command("run_due_ai_actions")  # không văng exception
            self.assertEqual(disp.call_count, 2)

        a.refresh_from_db()
        b.refresh_from_db()
        overdue.refresh_from_db()
        self.assertEqual(a.status, AiAction.Status.FAILED)
        self.assertEqual(a.downgrade_reason["code"], "AI_JOB_ERROR")
        self.assertEqual(b.status, AiAction.Status.DONE)
        self.assertEqual(overdue.status, AiAction.Status.ESCALATED)

        # Log chỉ có id việc + mã lệnh + tên lớp exception; không str(exc), không args.
        text = "\n".join(logs.output)
        self.assertNotIn(PII_SENTINEL, text)
        self.assertNotIn("loi gia", text)
        self.assertIn(str(a.id), text)
        self.assertIn(CMD, text)
        self.assertIn("RuntimeError", text)
        # Dấu vết audit/DB cũng không chứa nội dung exception.
        fail_rows = AuditLog.objects.filter(action=f"fail_{CMD}")
        self.assertEqual(fail_rows.count(), 1)
        self.assertEqual(fail_rows[0].actor_kind, "ai")
        self.assertEqual(fail_rows[0].proposal_ref, str(a.id))
        self.assertEqual(fail_rows[0].changes, {})
        self.assertNotIn(PII_SENTINEL, fail_rows[0].note)
        self.assertNotIn(PII_SENTINEL, str(a.downgrade_reason))

        # Chạy lần 2: không xử lý lại việc FAILED / DONE.
        with mock.patch(DISPATCH_PATH, side_effect=AssertionError("không được dispatch lại")) as disp2:
            call_command("run_due_ai_actions")
            self.assertEqual(disp2.call_count, 0)
        a.refresh_from_db()
        self.assertEqual(a.status, AiAction.Status.FAILED)
        self.assertEqual(AuditLog.objects.filter(action=f"fail_{CMD}").count(), 1)

    def test_sr03_ac4_thay_doi_dang_do_cua_viec_loi_bi_rollback(self):
        """Việc lỗi giữa chừng: thay đổi dở dang trong atomic bị rollback, chỉ còn FAILED."""
        batch = self._create_fully_eligible_batch()
        a = self._scheduled(batch)

        def partial_then_raise(*args, **kwargs):
            AuditLog.objects.create(action="partial_should_rollback", actor_kind="system")
            raise ValueError("gia")

        with mock.patch(DISPATCH_PATH, side_effect=partial_then_raise):
            call_command("run_due_ai_actions")
        a.refresh_from_db()
        self.assertEqual(a.status, AiAction.Status.FAILED)
        self.assertFalse(AuditLog.objects.filter(action="partial_should_rollback").exists())

    def test_sr03_ac4_mark_failed_khong_de_len_viec_da_doi_trang_thai(self):
        """_mark_failed chỉ đổi khi còn SCHEDULED (đọc lại có khoá)."""
        from apps.ai.management.commands import run_due_ai_actions as job

        batch = self._create_fully_eligible_batch()
        a = self._scheduled(batch)
        AiAction.objects.filter(pk=a.pk).update(status=AiAction.Status.DONE)
        job._mark_failed(a.pk, RuntimeError("x"))
        a.refresh_from_db()
        self.assertEqual(a.status, AiAction.Status.DONE)
        self.assertFalse(AuditLog.objects.filter(action=f"fail_{CMD}").exists())


@override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
class P8Sr03ApiTests(_SoldBatchBase):
    def _call(self, client, batch):
        return client.post(
            f"/api/ai/commands/{CMD}/call/", {"args": {}, "target_id": str(batch.id)}, format="json",
        )

    def test_sr03_ac5_api_chu_lo_da_ban_khong_500(self):
        self._open_ai()
        batch = self._create_fully_eligible_batch()
        self._add_sale(batch)
        res = self._call(self.client_chu, batch)
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data["outcome"], "scheduled")
        self.assertEqual(data["level"], "B")

    def test_sr03_ac5_api_chu_lo_da_ban_con_giao_dich_open_ha_muc_c(self):
        self._open_ai()
        batch = self._create_fully_eligible_batch()
        order = self._add_sale(batch)
        PaymentTransaction.objects.create(
            bank_txn_id="TXN-P8L1-D", sales_order=order, amount=Decimal("500"),
            match_status=PaymentTransaction.MatchStatus.UNDERPAID,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN, received_at=timezone.now(),
        )
        res = self._call(self.client_chu, batch)
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data["outcome"], "proposal")
        self.assertEqual(data["downgrade_reason"]["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")

    def test_sr03_ma_tran_group_lenh_chot_lo(self):
        batch = self._create_fully_eligible_batch()
        self._add_sale(batch)
        for user in (self.u_quanly, self.u_kho, self.u_giao, self.u_cskh):
            res = self._call(client_for(user), batch)
            # Registry cố ý ẩn lệnh với người thiếu quyền: 404 COMMAND_UNKNOWN (AI-DW 02b; chốt Tech Lead 30/09).
            self.assertEqual(res.status_code, 404, (user.username, res.content))
            self.assertEqual(res.json()["code"], "COMMAND_UNKNOWN")
        self.assertEqual(self._call(client_for(None), batch).status_code, 401)
        self.assertFalse(AiAction.objects.exists())

        # Đối chứng dương: cùng lô, cùng lệnh, Chủ được 200 -> 404 ở trên đến từ quyền, không phải lệnh bị tắt.
        self._open_ai()
        res = self._call(self.client_chu, batch)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["outcome"], "scheduled")
