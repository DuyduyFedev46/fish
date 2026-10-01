"""
P8 Lô 3 — SR-09: CSKH không "xác nhận" được đơn hệ thống đã tự huỷ (F03, BR-GH-18, CS-08/CS-09).
Chuyển từ test tái hiện R2 (repro/review_repro_tests.py). Dữ liệu giả.

- SR-09-AC1: đơn bị auto_cancel_overdue, record_call(CONFIRMED) -> 409 STALE_STATE, phiếu vẫn CANCELLED, task vẫn REFUND_CALL.
- SR-09-AC2: task REFUND_CALL chỉ nhận UNREACHABLE, NOTIFIED; mọi kết quả khác -> 409 STALE_STATE.
- SR-09-AC3: tranh chấp hai chiều (a) CSKH trước, job sau -> job bỏ qua; (b) job trước, CSKH bấm sau -> như AC1.
- SR-09-AC4: POST /api/confirmation/queue/<id>/calls/ trả 409 body {"detail", "code": "STALE_STATE"}.
- Ma trận: có quyền confirm_with_customer: CONFIRMED 409, NOTIFIED/UNREACHABLE 2xx; không quyền 403; khách 401.
"""
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.exceptions import ConflictError
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote
from apps.delivery.tests.test_confirmation_escalation import ConfirmationL3BaseTestCase
from apps.sales.models import SalesOrder
from apps.accounts import roles

STALE_TEXT = "Đơn đã bị huỷ — tải lại màn hình."
PII_SENTINELS = ("0900000123", "Khách Thử A", "Số 1 Đường Thử")


@override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True)
class SR09RecordCallStaleTests(ConfirmationL3BaseTestCase):
    def setUp(self):
        super().setUp()
        self.t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        self.giao = make_user("giao_sr09", roles.DELIVERY_STAFF)

    def _auto_cancelled(self):
        """Đơn bị `auto_cancel_overdue`: đơn/phiếu CANCELLED, task REFUND_CALL."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=self.t0)
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = self.t0
        task.save()
        res = confirmation_services.auto_cancel_overdue(now=self.t0 + timedelta(minutes=31))
        self.assertEqual(res["cancelled"], 1)
        order.refresh_from_db(); note.refresh_from_db(); task.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)
        self.assertEqual(task.state, ConfirmationTask.State.REFUND_CALL)
        return order, note, task

    def _assert_unchanged(self, order, note, task, calls_before, audits_before):
        order.refresh_from_db(); note.refresh_from_db(); task.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)
        self.assertIsNone(note.confirmed_at)
        self.assertEqual(task.state, ConfirmationTask.State.REFUND_CALL)
        self.assertEqual(CustomerCall.objects.filter(note=note).count(), calls_before)
        self.assertEqual(AuditLog.objects.filter(action="delivery_confirmed").count(), audits_before)

    # --- AC1 (R2) ------------------------------------------------------------
    def test_sr09_ac1_r2_confirmed_sau_tu_huy_409_stale_state(self):
        order, note, task = self._auto_cancelled()
        calls = CustomerCall.objects.filter(note=note).count()
        audits = AuditLog.objects.filter(action="delivery_confirmed").count()

        with self.assertRaises(ConflictError) as ctx:
            confirmation_services.record_call(
                task.pk, self.cs1, result="CONFIRMED", now=self.t0 + timedelta(minutes=32),
            )
        self.assertEqual(ctx.exception.code, "STALE_STATE")
        self.assertEqual(ctx.exception.http_status, 409)
        self.assertEqual(str(ctx.exception), STALE_TEXT)
        self._assert_unchanged(order, note, task, calls, audits)

    # --- AC2 -----------------------------------------------------------------
    def test_sr09_ac2_refund_call_chi_nhan_unreachable_notified(self):
        from datetime import timedelta as td
        order, note, task = self._auto_cancelled()
        calls = CustomerCall.objects.filter(note=note).count()
        audits = AuditLog.objects.filter(action="delivery_confirmed").count()
        now = self.t0 + timedelta(minutes=32)
        for result in ("CONFIRMED", "CONFIRMED_CHANGED", "CALLBACK", "WRONG_NUMBER", "WANT_CANCEL", "WANT_CHANGE"):
            with self.subTest(result=result):
                with self.assertRaises(ConflictError) as ctx:
                    confirmation_services.record_call(
                        task.pk, self.cs1, result=result, now=now,
                        callback_at=now + td(hours=1) if result == "CALLBACK" else None,
                    )
                self.assertEqual(ctx.exception.code, "STALE_STATE")
                self.assertEqual(str(ctx.exception), STALE_TEXT)
                self._assert_unchanged(order, note, task, calls, audits)

    def test_sr09_ac2_unreachable_va_notified_van_nhan(self):
        order, note, task = self._auto_cancelled()
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=self.t0 + timedelta(minutes=32))
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.REFUND_CALL)
        confirmation_services.record_call(task.pk, self.cs1, result="NOTIFIED", now=self.t0 + timedelta(minutes=33))
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.DONE)

    def test_sr09_ac2_ket_qua_rac_van_la_invalid_input_khong_phai_stale(self):
        from apps.common.exceptions import BusinessError
        order, note, task = self._auto_cancelled()
        with self.assertRaises(BusinessError) as ctx:
            confirmation_services.record_call(task.pk, self.cs1, result="KHONG_CO", now=self.t0 + timedelta(minutes=32))
        self.assertEqual(ctx.exception.code, "INVALID_INPUT")

    def test_sr09_phieu_cancelled_task_khong_phai_refund_call_cung_409(self):
        """Phiếu đã huỷ (vd Chủ huỷ tay) mà task còn mở, không phải REFUND_CALL -> 409 STALE_STATE."""
        order, note, task = self._create_order_with_confirmation()
        DeliveryNote.objects.filter(pk=note.pk).update(status=DeliveryNote.Status.CANCELLED)
        for result in ("CONFIRMED", "UNREACHABLE", "NOTIFIED"):
            with self.subTest(result=result):
                with self.assertRaises(ConflictError) as ctx:
                    confirmation_services.record_call(task.pk, self.cs1, result=result, now=self.t0)
                self.assertEqual(ctx.exception.code, "STALE_STATE")
                self.assertEqual(str(ctx.exception), STALE_TEXT)
        note.refresh_from_db(); task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)
        self.assertNotEqual(task.state, ConfirmationTask.State.DONE)

    # --- AC3 -----------------------------------------------------------------
    def test_sr09_ac3a_cskh_xac_nhan_truoc_job_chay_sau_thi_job_bo_qua(self):
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=self.t0)
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = self.t0
        task.save()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED", now=self.t0 + timedelta(minutes=10))

        res = confirmation_services.auto_cancel_overdue(now=self.t0 + timedelta(minutes=31))
        self.assertEqual(res["cancelled"], 0)
        order.refresh_from_db(); note.refresh_from_db(); task.refresh_from_db()
        self.assertNotEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        self.assertEqual(task.state, ConfirmationTask.State.DONE)

    def test_sr09_ac3b_job_truoc_cskh_bam_sau_man_hinh_cu_nhu_ac1(self):
        order, note, task = self._auto_cancelled()
        calls = CustomerCall.objects.filter(note=note).count()
        audits = AuditLog.objects.filter(action="delivery_confirmed").count()
        with self.assertRaises(ConflictError):
            confirmation_services.record_call(
                task.pk, self.cs1, result="CONFIRMED_CHANGED", now=self.t0 + timedelta(minutes=40),
            )
        self._assert_unchanged(order, note, task, calls, audits)

    # --- AC4 (API) -----------------------------------------------------------
    def test_sr09_ac4_api_409_body_detail_code(self):
        order, note, task = self._auto_cancelled()
        resp = client_for(self.cs1).post(
            f"/api/confirmation/queue/{note.pk}/calls/", {"result": "CONFIRMED"}, format="json",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json(), {"detail": STALE_TEXT, "code": "STALE_STATE"})
        raw = resp.content.decode()
        for sentinel in PII_SENTINELS:
            self.assertNotIn(sentinel, raw)
        note.refresh_from_db(); task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)
        self.assertEqual(task.state, ConfirmationTask.State.REFUND_CALL)

    def test_sr09_ac4_api_moi_ket_qua_sai_cho_refund_call_deu_409(self):
        order, note, task = self._auto_cancelled()
        client = client_for(self.cs1)
        for result in ("CONFIRMED", "CONFIRMED_CHANGED", "WRONG_NUMBER", "WANT_CANCEL", "WANT_CHANGE"):
            with self.subTest(result=result):
                resp = client.post(f"/api/confirmation/queue/{note.pk}/calls/", {"result": result}, format="json")
                self.assertEqual(resp.status_code, 409)
                self.assertEqual(resp.json()["code"], "STALE_STATE")

    # --- Ma trận Group -------------------------------------------------------
    def test_sr09_ma_tran_group_refund_call_confirmed(self):
        order, note, task = self._auto_cancelled()
        url = f"/api/confirmation/queue/{note.pk}/calls/"
        # có delivery.confirm_with_customer (cskh đã gọi, chu, quan_ly): CONFIRMED -> 409
        for user in (self.cs1, self.chu, self.ql):
            with self.subTest(user=user.username):
                resp = client_for(user).post(url, {"result": "CONFIRMED"}, format="json")
                self.assertEqual(resp.status_code, 409)
                self.assertEqual(resp.json()["code"], "STALE_STATE")
        # không quyền -> 403; khách -> 401
        for user in (self.kho, self.giao):
            with self.subTest(user=user.username):
                self.assertEqual(client_for(user).post(url, {"result": "CONFIRMED"}, format="json").status_code, 403)
        self.assertEqual(client_for(None).post(url, {"result": "CONFIRMED"}, format="json").status_code, 401)
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.REFUND_CALL)

    def test_sr09_ma_tran_group_refund_call_notified_unreachable(self):
        order, note, task = self._auto_cancelled()
        url = f"/api/confirmation/queue/{note.pk}/calls/"
        for user in (self.chu, self.ql):
            resp = client_for(user).post(url, {"result": "UNREACHABLE"}, format="json")
            self.assertIn(resp.status_code, (200, 201), user.username)
        for user in (self.kho, self.giao):
            self.assertEqual(client_for(user).post(url, {"result": "NOTIFIED"}, format="json").status_code, 403)
        self.assertEqual(client_for(None).post(url, {"result": "NOTIFIED"}, format="json").status_code, 401)
        resp = client_for(self.cs1).post(url, {"result": "NOTIFIED"}, format="json")
        self.assertIn(resp.status_code, (200, 201))
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.DONE)
