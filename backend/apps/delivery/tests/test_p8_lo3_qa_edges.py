"""
QA P8 Lô 3 — ca biên/ngoại lệ bổ sung cho SR-09 (CSKH bấm trên màn hình cũ sau khi đơn đã huỷ).
Không sửa code sản phẩm. Dữ liệu giả.

Phủ: huỷ tay (Chủ) thay vì job; chạy job tự huỷ 2 lần; người đang giữ (claim) bị job huỷ ngang; phiếu đã
xác nhận rồi bấm lần 2 (màn hình cũ, không phải huỷ); request_id chống bấm đúp; log/console không có PII;
tranh chấp job <-> CSKH theo cả 2 thứ tự (A: CSKH trước; B: job trước).
"""
import logging
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.exceptions import BusinessError, ConflictError
from apps.common.tests.fixtures import client_for
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote
from apps.delivery.tests.test_cskh_l3 import ConfirmationL3BaseTestCase
from apps.sales.models import Refund, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services

STALE = "Đơn đã bị huỷ — tải lại màn hình."
ALL_RESULTS = ("CONFIRMED", "CONFIRMED_CHANGED", "CALLBACK", "UNREACHABLE", "WRONG_NUMBER", "WANT_CANCEL", "WANT_CHANGE")
PII = ("0900000123", "Khách Thử A", "Số 1 Đường Thử")


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.lines = []

    def emit(self, record):
        try:
            self.lines.append(record.getMessage())
        except Exception:  # pragma: no cover
            self.lines.append(str(record.msg))


@override_settings(CSKH_AUTO_CANCEL_ENABLED=True)
class QaSR09Edges(ConfirmationL3BaseTestCase):
    def setUp(self):
        super().setUp()
        self.t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)

    def _escalated(self):
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=self.t0)
        task.refresh_from_db()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = self.t0
        task.save()
        return order, note, task

    def _auto_cancel(self, minutes=31):
        return confirmation_services.auto_cancel_overdue(now=self.t0 + timedelta(minutes=minutes))

    def _no_side_effects(self, note, task, calls, audits, expect_task_state):
        note.refresh_from_db(); task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)
        self.assertIsNone(note.confirmed_at)
        self.assertEqual(task.state, expect_task_state)
        self.assertEqual(CustomerCall.objects.filter(note=note).count(), calls)
        self.assertEqual(AuditLog.objects.filter(action="delivery_confirmed").count(), audits)

    # --- job chạy 2 lần --------------------------------------------------------
    def test_qa_job_tu_huy_chay_2_lan_chi_huy_1_lan(self):
        order, note, task = self._escalated()
        r1 = self._auto_cancel()
        r2 = self._auto_cancel(minutes=45)
        self.assertEqual((r1["cancelled"], r2["cancelled"]), (1, 0))
        self.assertEqual(Refund.objects.filter(sales_invoice__sales_order=order).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="order_auto_cancelled").count(), 1)
        order.refresh_from_db(); task.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(task.state, ConfirmationTask.State.REFUND_CALL)
        self.assertEqual(SalesInvoice.objects.filter(sales_order=order).count(), 1)  # chứng từ không bị xoá

    # --- huỷ tay (không phải job) ---------------------------------------------
    def test_qa_chu_huy_tay_roi_cskh_bam_moi_ket_qua_deu_409(self):
        order, note, task = self._escalated()
        order_services.cancel_paid_order(order=order, actor=self.chu, reason="Khách đổi ý", reason_code="OTHER")
        note.refresh_from_db(); task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)
        calls = CustomerCall.objects.filter(note=note).count()
        audits = AuditLog.objects.filter(action="delivery_confirmed").count()
        state_after_cancel = task.state
        now = self.t0 + timedelta(minutes=50)
        for result in ALL_RESULTS:
            with self.subTest(result=result):
                with self.assertRaises(ConflictError) as ctx:
                    confirmation_services.record_call(
                        task.pk, self.cs1, result=result, now=now,
                        callback_at=now + timedelta(hours=1) if result == "CALLBACK" else None,
                    )
                self.assertEqual(ctx.exception.code, "STALE_STATE")
                self.assertEqual(str(ctx.exception), STALE)
        self._no_side_effects(note, task, calls, audits, state_after_cancel)

    def test_qa_huy_tay_api_409_body_dung_hop_dong(self):
        order, note, task = self._escalated()
        order_services.cancel_paid_order(order=order, actor=self.chu, reason="x", reason_code="OTHER")
        resp = client_for(self.cs1).post(f"/api/cskh/queue/{note.pk}/calls/", {"result": "CONFIRMED"}, format="json")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json(), {"detail": STALE, "code": "STALE_STATE"})

    # --- người đang giữ (claim) bị job huỷ ngang, hai người cùng lúc ------------
    def test_qa_cskh_dang_giu_phieu_bi_job_huy_ngang_roi_bam_xac_nhan(self):
        order, note, task = self._escalated()
        # cs1 mở màn gọi và giữ phiếu (claim)
        confirmation_services.claim_task(task.pk, self.cs1, now=self.t0 + timedelta(minutes=29))
        task.refresh_from_db()
        self.assertEqual(task.claimed_by_id, self.cs1.pk)
        res = self._auto_cancel(minutes=31)
        self.assertEqual(res["cancelled"], 1)
        calls = CustomerCall.objects.filter(note=note).count()
        audits = AuditLog.objects.filter(action="delivery_confirmed").count()
        # cs1 (màn hình cũ) và cs2 (người khác) cùng bấm -> cả hai đều 409 STALE_STATE (không phải CLAIMED)
        for user in (self.cs1, self.cs2):
            with self.subTest(user=user.username):
                with self.assertRaises(ConflictError) as ctx:
                    confirmation_services.record_call(task.pk, user, result="CONFIRMED", now=self.t0 + timedelta(minutes=32))
                self.assertEqual(ctx.exception.code, "STALE_STATE")
        self._no_side_effects(note, task, calls, audits, ConfirmationTask.State.REFUND_CALL)

    # --- tranh chấp thứ tự A: CSKH trước, job sau --------------------------------
    def test_qa_race_cskh_xac_nhan_truoc_job_bo_qua_va_khong_hoan_tien(self):
        order, note, task = self._escalated()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED", now=self.t0 + timedelta(minutes=20))
        res = self._auto_cancel(minutes=45)
        self.assertEqual(res["cancelled"], 0)
        order.refresh_from_db(); note.refresh_from_db(); task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        self.assertNotEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(task.state, ConfirmationTask.State.DONE)
        self.assertEqual(Refund.objects.filter(sales_invoice__sales_order=order).count(), 0)
        # màn hình cũ của người thứ 2 bấm lần nữa -> STALE_STATE "đã xác nhận bởi người khác", KHÔNG đổi gì
        with self.assertRaises(ConflictError) as ctx:
            confirmation_services.record_call(task.pk, self.cs2, result="CONFIRMED", now=self.t0 + timedelta(minutes=46))
        self.assertEqual(ctx.exception.code, "STALE_STATE")
        note.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)

    # --- tranh chấp thứ tự B: job trước, CSKH sau; rồi luồng báo hoàn tiền -------
    def test_qa_race_job_truoc_roi_luong_bao_hoan_tien_van_chay(self):
        order, note, task = self._escalated()
        self._auto_cancel()
        # CSKH đúng luồng: UNREACHABLE rồi NOTIFIED trên REFUND_CALL vẫn nhận
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=self.t0 + timedelta(minutes=40))
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.REFUND_CALL)
        self.assertEqual(task.attempts, 1)
        confirmation_services.record_call(task.pk, self.cs1, result="NOTIFIED", now=self.t0 + timedelta(minutes=41))
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.DONE)
        # sau khi đã DONE (đơn vẫn CANCELLED), bấm CONFIRMED / UNREACHABLE / NOTIFIED lần nữa -> 409, không thêm cuộc gọi
        calls = CustomerCall.objects.filter(note=note).count()
        for result in ("CONFIRMED", "UNREACHABLE", "NOTIFIED"):
            with self.subTest(result=result):
                with self.assertRaises(ConflictError) as ctx:
                    confirmation_services.record_call(task.pk, self.cs1, result=result, now=self.t0 + timedelta(minutes=42))
                self.assertEqual(ctx.exception.code, "STALE_STATE")
        self.assertEqual(CustomerCall.objects.filter(note=note).count(), calls)
        note.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)

    # --- request_id chống bấm đúp ---------------------------------------------------
    def test_qa_request_id_bam_dup_tren_refund_call(self):
        import uuid
        order, note, task = self._escalated()
        self._auto_cancel()
        rid = uuid.uuid4()
        c1, dup1 = confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", request_id=rid,
                                              now=self.t0 + timedelta(minutes=40))
        c2, dup2 = confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", request_id=rid,
                                              now=self.t0 + timedelta(minutes=40))
        self.assertEqual((dup1, dup2), (False, True))
        self.assertEqual(c1.pk, c2.pk)
        task.refresh_from_db()
        self.assertEqual(task.attempts, 1)  # bấm đúp không cộng 2 lần

    def test_qa_request_id_cua_lan_bi_chan_409_khong_ghi_gi_va_thu_lai_van_409(self):
        import uuid
        order, note, task = self._escalated()
        self._auto_cancel()
        rid = uuid.uuid4()
        calls = CustomerCall.objects.filter(note=note).count()
        for _ in range(2):
            with self.assertRaises(ConflictError) as ctx:
                confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED", request_id=rid,
                                          now=self.t0 + timedelta(minutes=40))
            self.assertEqual(ctx.exception.code, "STALE_STATE")
        self.assertEqual(CustomerCall.objects.filter(request_id=rid).count(), 0)
        self.assertEqual(CustomerCall.objects.filter(note=note).count(), calls)

    # --- đường khác không phải "đã huỷ" (hồi quy) ---------------------------------
    def test_qa_da_xac_nhan_roi_bam_lan_2_van_409_da_xac_nhan_khong_doi_phieu(self):
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED", now=self.t0)
        with self.assertRaises(ConflictError) as ctx:
            confirmation_services.record_call(task.pk, self.cs2, result="CONFIRMED", now=self.t0 + timedelta(minutes=1))
        self.assertEqual(ctx.exception.code, "STALE_STATE")
        self.assertIn("vừa được xác nhận", str(ctx.exception))
        note.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        self.assertEqual(AuditLog.objects.filter(action="delivery_confirmed").count(), 1)

    def test_qa_ket_qua_rac_tren_phieu_binh_thuong_van_400_invalid_input(self):
        order, note, task = self._create_order_with_confirmation()
        with self.assertRaises(BusinessError) as ctx:
            confirmation_services.record_call(task.pk, self.cs1, result="KHONG_CO", now=self.t0)
        self.assertEqual(ctx.exception.code, "INVALID_INPUT")
        resp = client_for(self.cs1).post(f"/api/cskh/queue/{note.pk}/calls/", {"result": "KHONG_CO"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_qa_luong_thuan_confirmed_van_201(self):
        order, note, task = self._create_order_with_confirmation()
        resp = client_for(self.cs1).post(f"/api/cskh/queue/{note.pk}/calls/", {"result": "CONFIRMED"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        note.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)

    # --- rò dữ liệu cá nhân trong log / body / audit ------------------------------
    def test_qa_khong_ro_pii_trong_log_body_va_audit_khi_409(self):
        order, note, task = self._escalated()
        self._auto_cancel()
        handler = _ListHandler()
        root = logging.getLogger()
        old_level = root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            resp = client_for(self.cs1).post(f"/api/cskh/queue/{note.pk}/calls/", {"result": "CONFIRMED"}, format="json")
        finally:
            root.removeHandler(handler)
            root.setLevel(old_level)
        self.assertEqual(resp.status_code, 409)
        blob = "\n".join(handler.lines) + resp.content.decode()
        for s in PII:
            self.assertNotIn(s, blob)
        audit_blob = " ".join(f"{a.note} {a.changes}" for a in AuditLog.objects.all())
        for s in PII:
            self.assertNotIn(s, audit_blob)
        # không rò giá vốn trong body lỗi
        for k in ("unit_cost", "landed_unit_cost", "purchase_rate", "loss_amount"):
            self.assertNotIn(k, resp.content.decode())

    def test_qa_phan_quyen_stale_khach_401_va_nhom_khong_quyen_403(self):
        order, note, task = self._escalated()
        self._auto_cancel()
        url = f"/api/cskh/queue/{note.pk}/calls/"
        self.assertEqual(client_for(None).post(url, {"result": "CONFIRMED"}, format="json").status_code, 401)
        self.assertEqual(client_for(self.kho).post(url, {"result": "CONFIRMED"}, format="json").status_code, 403)
        # cs2 chưa từng gọi phiếu này -> ngoài phạm vi CSKH (BR-GH-18) -> 404, không lộ trạng thái/PII
        r = client_for(self.cs2).post(url, {"result": "CONFIRMED"}, format="json")
        self.assertEqual(r.status_code, 404)
        for s in PII:
            self.assertNotIn(s, r.content.decode())
        self.assertEqual(client_for(self.chu).post(url, {"result": "CONFIRMED"}, format="json").status_code, 409)
        self.assertEqual(client_for(self.ql).post(url, {"result": "CONFIRMED"}, format="json").status_code, 409)
        self.assertEqual(client_for(self.cs1).post("/api/cskh/queue/999999/calls/",
                                                   {"result": "CONFIRMED"}, format="json").status_code, 404)
