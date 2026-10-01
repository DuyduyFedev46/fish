"""
QA P8 Lô 7 — F08 (`escalate_expired_windows`): job chạy 2 lần, hai thao tác tranh chấp (A->B, B->A), biên cửa sổ.
Chỉ dữ liệu giả.
"""
from datetime import timedelta
from unittest import mock

from django.db.models.query import QuerySet
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.models import ConfirmationTask, DeliveryNote
from apps.delivery.tests import test_cskh_l3


class QaF08Tests(test_cskh_l3.ConfirmationL3BaseTestCase):
    def setUp(self):
        super().setUp()
        self.t0 = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        self.order, self.note, self.task = self._create_order_with_confirmation()
        confirmation_services.record_call(self.task.pk, self.cs1, result="UNREACHABLE", now=self.t0)

    def _audits(self):
        return AuditLog.objects.filter(action="delivery_escalated").count()

    def test_qa_f08_chay_job_2_lan_lan_hai_khong_lam_gi_khong_ghi_audit_them(self):
        self.assertEqual(confirmation_services.escalate_expired_windows(now=self.t0 + timedelta(minutes=31)), 1)
        self.assertEqual(confirmation_services.escalate_expired_windows(now=self.t0 + timedelta(minutes=32)), 0)
        self.assertEqual(self._audits(), 1)
        self.task.refresh_from_db()
        self.assertEqual(self.task.state, ConfirmationTask.State.ESCALATED)
        self.assertEqual(self.task.escalated_at, self.t0 + timedelta(minutes=31))

    def test_qa_f08_bien_cua_so_29p59_khong_30p00_co(self):
        self.assertEqual(confirmation_services.escalate_expired_windows(now=self.t0 + timedelta(minutes=29, seconds=59)), 0)
        self.task.refresh_from_db()
        self.assertEqual(self.task.state, ConfirmationTask.State.PENDING)
        self.assertEqual(confirmation_services.escalate_expired_windows(now=self.t0 + timedelta(minutes=30)), 1)

    def _race(self, mutate):
        """Chạy job, nhưng ngay khi nó xin khoá phiếu giao thì một người khác đã đổi dữ liệu (đọc cũ -> khoá mới)."""
        real = QuerySet.select_for_update
        fired = []

        def spy(qs, *a, **k):
            if qs.model is DeliveryNote and not fired:
                fired.append(1)
                mutate()
            return real(qs, *a, **k)

        with mock.patch.object(QuerySet, "select_for_update", spy):
            n = confirmation_services.escalate_expired_windows(now=self.t0 + timedelta(minutes=31))
        self.assertTrue(fired, "job không xin khoá phiếu giao")
        return n

    def test_qa_f08_tranh_chap_A_nhan_vien_da_xac_nhan_xong_truoc_khi_job_khoa_thi_job_bo_qua(self):
        def mutate():
            ConfirmationTask.objects.filter(pk=self.task.pk).update(state=ConfirmationTask.State.DONE)
        self.assertEqual(self._race(mutate), 0)
        self.task.refresh_from_db()
        self.assertEqual(self.task.state, ConfirmationTask.State.DONE)
        self.assertEqual(self._audits(), 0)

    def test_qa_f08_tranh_chap_B_phieu_da_huy_truoc_khi_job_khoa_thi_job_bo_qua(self):
        def mutate():
            DeliveryNote.objects.filter(pk=self.note.pk).update(status=DeliveryNote.Status.CANCELLED)
        self.assertEqual(self._race(mutate), 0)
        self.task.refresh_from_db()
        self.assertEqual(self.task.state, ConfirmationTask.State.PENDING)
        self.assertEqual(self._audits(), 0)

    def test_qa_f08_nhieu_task_mot_task_loi_khong_chan_task_khac(self):
        order2, note2, task2 = self._create_order_with_confirmation(phone="0900000124", name="Khách Thử B")
        confirmation_services.record_call(task2.pk, self.cs1, result="UNREACHABLE", now=self.t0)
        real = QuerySet.select_for_update
        calls = []

        def spy(qs, *a, **k):
            if qs.model is DeliveryNote:
                calls.append(1)
                if len(calls) == 1:
                    raise RuntimeError("giả lập lỗi khoá lần đầu")
            return real(qs, *a, **k)

        with mock.patch.object(QuerySet, "select_for_update", spy):
            with self.assertLogs("cangca.delivery.confirmation", level="ERROR") as cm:
                n = confirmation_services.escalate_expired_windows(now=self.t0 + timedelta(minutes=31))
        self.assertEqual(n, 1)
        self.assertEqual(ConfirmationTask.objects.filter(state=ConfirmationTask.State.ESCALATED).count(), 1)
        self.assertNotIn("0900000", "\n".join(cm.output))
        # chạy lại: task bị lỗi lần trước được xử lý tiếp (idempotent)
        self.assertEqual(confirmation_services.escalate_expired_windows(now=self.t0 + timedelta(minutes=32)), 1)

    def test_qa_f08_audit_khong_chua_pii_hay_gia_von(self):
        confirmation_services.escalate_expired_windows(now=self.t0 + timedelta(minutes=31))
        blob = " ".join(f"{a.note}|{a.changes}" for a in AuditLog.objects.filter(action="delivery_escalated"))
        for bad in ("Khách Thử A", "0900000123", "Đường Thử", "110000", "150000", "unit_cost", "purchase_rate"):
            self.assertNotIn(bad, blob)
