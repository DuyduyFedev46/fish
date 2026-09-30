"""
QA P8 Lô 1 — SR-03: ca NGOÀI đường thuận do QA bổ sung. Dữ liệu giả (0900000xxx, "Khách Giả A").
Dùng lại fixture của dev (`_SoldBatchBase`) nhưng qua module để không bị discover chạy lại lớp gốc.
"""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.execution import safety
from apps.ai.execution.dispatch import DispatchResult
from apps.ai.execution.tests import test_p8_close_batch_sold as dev
from apps.ai.models import AiAction
from apps.inventory.models import Batch
from apps.sales.models import (
    Customer, PaymentTransaction, Refund, SalesInvoice, SalesOrder, SalesOrderLine, SalesOrderLineBatch,
)

CMD = dev.CMD
DISPATCH_PATH = dev.DISPATCH_PATH


@override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
class P8Lo1QaSr03Edges(dev._SoldBatchBase):
    def setUp(self):
        super().setUp()
        self._open_ai()

    # -- an toàn: phạm vi đúng lô -------------------------------------------------
    def test_qa_phieu_hoan_pending_cua_don_KHAC_lo_khong_chan(self):
        """Refund PENDING gắn đơn không bán từ lô này thì không được chặn chốt lô (không chặn nhầm)."""
        batch = self._create_fully_eligible_batch()
        self._add_sale(batch, code="SO-QA-A")
        other_batch = self._create_fully_eligible_batch()
        order_b = self._add_sale(other_batch, code="SO-QA-B")
        inv = SalesInvoice.objects.create(code="HD-QA-B", sales_order=order_b, customer=order_b.customer,
                                          issued_at=timezone.now(), amount=Decimal("1000"))
        Refund.objects.create(sales_invoice=inv, amount=Decimal("1000"), status=Refund.Status.PENDING)
        ok, reason = safety.check_ai_close_batch_conditions(batch)
        self.assertTrue(ok, reason)
        ok2, reason2 = safety.check_ai_close_batch_conditions(other_batch)
        self.assertFalse(ok2)

    def test_qa_lo_ban_qua_nhieu_don_chi_can_mot_don_vuong_la_chan(self):
        batch = self._create_fully_eligible_batch()
        self._add_sale(batch, code="SO-QA-C1")
        order2 = self._add_sale(batch, code="SO-QA-C2")
        PaymentTransaction.objects.create(
            bank_txn_id="TXN-QA-C2", sales_order=order2, amount=Decimal("1"),
            match_status=PaymentTransaction.MatchStatus.UNDERPAID,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN, received_at=timezone.now())
        ok, reason = safety.check_ai_close_batch_conditions(batch)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")

    def test_qa_lo_chua_tung_ban_van_dung(self):
        """Hồi quy nhánh không có đơn (order_ids rỗng)."""
        ok, reason = safety.check_ai_close_batch_conditions(self._create_fully_eligible_batch())
        self.assertTrue(ok, reason)

    # -- job: chạy 2 lần, đổi trạng thái, exception thật (không mock dispatch) -----
    def test_qa_job_chay_2_lan_viec_escalated_khong_nhan_doi(self):
        sold = self._create_fully_eligible_batch()
        order = self._add_sale(sold)
        inv = SalesInvoice.objects.create(code="HD-QA-D", sales_order=order, customer=order.customer,
                                          issued_at=timezone.now(), amount=Decimal("1000"))
        Refund.objects.create(sales_invoice=inv, amount=Decimal("1000"), status=Refund.Status.PENDING)
        a = self._scheduled(sold)
        call_command("run_due_ai_actions")
        n1 = AuditLog.objects.filter(action=f"escalate_{CMD}").count()
        call_command("run_due_ai_actions")
        a.refresh_from_db()
        self.assertEqual(a.status, AiAction.Status.ESCALATED)
        self.assertEqual(n1, 1)
        self.assertEqual(AuditLog.objects.filter(action=f"escalate_{CMD}").count(), 1)
        sold.refresh_from_db()
        self.assertNotEqual(sold.status, Batch.Status.CLOSED)

    def test_qa_job_chay_2_lan_viec_done_khong_chot_lai(self):
        sold = self._create_fully_eligible_batch()
        self._add_sale(sold)
        a = self._scheduled(sold)
        call_command("run_due_ai_actions")
        call_command("run_due_ai_actions")
        a.refresh_from_db()
        self.assertEqual(a.status, AiAction.Status.DONE)
        self.assertEqual(AuditLog.objects.filter(action=f"execute_{CMD}").count(), 1)

    def test_qa_viec_da_bi_huy_giua_chung_khong_bi_job_chay(self):
        """Màn hình cũ: người dùng đã đổi trạng thái việc (CANCELLED/DONE) sau khi job đọc danh sách."""
        batch = self._create_fully_eligible_batch()
        a = self._scheduled(batch)
        cancel_status = next(v for v in AiAction.Status.values if v not in ("SCHEDULED", "PENDING", "FAILED"))
        real_get = AiAction.objects.select_for_update

        def flip_then_lock(*args, **kwargs):
            AiAction.objects.filter(pk=a.pk).update(status=cancel_status)
            return real_get(*args, **kwargs)

        with mock.patch(DISPATCH_PATH, side_effect=AssertionError("không được dispatch")) as disp:
            with mock.patch.object(type(AiAction.objects), "select_for_update", side_effect=flip_then_lock):
                call_command("run_due_ai_actions")
            self.assertEqual(disp.call_count, 0)
        a.refresh_from_db()
        self.assertEqual(a.status, cancel_status)

    def test_qa_exception_that_khong_mock_target_khong_ton_tai_thanh_failed(self):
        """Poison pill THẬT: target_id lô không tồn tại -> không được làm chết job; việc sau vẫn chạy."""
        bad = AiAction.objects.create(
            command=CMD, kind="write", level="B", status="SCHEDULED", owner=self.u_chu,
            target_model="batch", target_id="999999999", execute_after=timezone.now() - timedelta(seconds=90))
        good_batch = self._create_fully_eligible_batch()
        good = self._scheduled(good_batch, seconds_ago=10)
        call_command("run_due_ai_actions")  # không được văng
        bad.refresh_from_db()
        good.refresh_from_db()
        self.assertIn(bad.status, (AiAction.Status.FAILED, AiAction.Status.ESCALATED))
        self.assertEqual(good.status, AiAction.Status.DONE)

    def test_qa_hai_poison_pill_o_giua_va_cuoi_viec_tot_o_giua_van_done(self):
        b1, b2, b3 = (self._create_fully_eligible_batch() for _ in range(3))
        a1 = self._scheduled(b1, seconds_ago=90)
        a2 = self._scheduled(b2, seconds_ago=60)
        a3 = self._scheduled(b3, seconds_ago=30)
        seq = [RuntimeError("SECRET-KHACH-GIA-0900000123"), DispatchResult({"id": b2.id}, 200, False),
               KeyError("SECRET-KHACH-GIA-0900000123")]
        with mock.patch(DISPATCH_PATH, side_effect=seq):
            with self.assertLogs(level="DEBUG") as logs:
                call_command("run_due_ai_actions")
        for x in (a1, a2, a3):
            x.refresh_from_db()
        self.assertEqual((a1.status, a2.status, a3.status),
                         (AiAction.Status.FAILED, AiAction.Status.DONE, AiAction.Status.FAILED))
        self.assertNotIn("SECRET", "\n".join(logs.output))
        self.assertEqual(AuditLog.objects.filter(action=f"fail_{CMD}").count(), 2)
        for row in AuditLog.objects.filter(action=f"fail_{CMD}"):
            self.assertNotIn("SECRET", row.note + str(row.changes))
        for x in (a1, a3):
            self.assertNotIn("SECRET", str(x.downgrade_reason) + str(x.args) + str(x.result_ref))

    def test_qa_mark_failed_loi_thi_job_van_chay_tiep(self):
        """Nếu chính bước ghi FAILED lỗi (DB), job vẫn tiếp tục việc sau và không văng."""
        b1 = self._create_fully_eligible_batch()
        b2 = self._create_fully_eligible_batch()
        a1 = self._scheduled(b1, seconds_ago=60)
        a2 = self._scheduled(b2, seconds_ago=30)
        seq = [RuntimeError("x"), DispatchResult({"id": b2.id}, 200, False)]
        with mock.patch(DISPATCH_PATH, side_effect=seq), \
                mock.patch("apps.ai.management.commands.run_due_ai_actions._mark_failed",
                           side_effect=RuntimeError("db down")):
            call_command("run_due_ai_actions")
        a1.refresh_from_db()
        a2.refresh_from_db()
        self.assertEqual(a1.status, AiAction.Status.SCHEDULED)  # còn SCHEDULED: lần sau thử lại, không mất việc
        self.assertEqual(a2.status, AiAction.Status.DONE)

    # -- API ---------------------------------------------------------------------
    def test_qa_api_lo_da_ban_co_phieu_hoan_pending_ha_muc_C_khong_500(self):
        batch = self._create_fully_eligible_batch()
        order = self._add_sale(batch)
        inv = SalesInvoice.objects.create(code="HD-QA-E", sales_order=order, customer=order.customer,
                                          issued_at=timezone.now(), amount=Decimal("1000"))
        Refund.objects.create(sales_invoice=inv, amount=Decimal("1000"), status=Refund.Status.PENDING)
        res = self.client_chu.post(f"/api/ai/commands/{CMD}/call/", {"args": {}, "target_id": str(batch.id)},
                                   format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["outcome"], "proposal")
        self.assertEqual(res.json()["downgrade_reason"]["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")
        # Response không chứa dữ liệu khách
        body = res.content.decode()
        for pii in ("Khách Giả A", "0900000999", "Số 1 Đường Giả"):
            self.assertNotIn(pii, body)

    def test_qa_api_bam_dup_khong_tao_2_viec_khi_cung_khoa(self):
        """Bấm đúp cùng idempotency_key (body) -> 1 AiAction, lần 2 không 5xx."""
        batch = self._create_fully_eligible_batch()
        self._add_sale(batch)
        payload = {"args": {}, "target_id": str(batch.id), "idempotency_key": "qa-lo1-dup-1"}
        r1 = self.client_chu.post(f"/api/ai/commands/{CMD}/call/", payload, format="json")
        r2 = self.client_chu.post(f"/api/ai/commands/{CMD}/call/", payload, format="json")
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertEqual(AiAction.objects.filter(command=CMD).count(), 1)
