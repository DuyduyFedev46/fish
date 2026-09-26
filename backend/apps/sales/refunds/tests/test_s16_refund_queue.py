"""
S16 — Phiếu hoàn chờ chuyển: xác nhận, báo thất bại, thử lại (UC-07, A6, A7, BR-HT-09 mới).

Contract:
    GET  /api/sales/refunds/?status=PENDING,FAILED
    POST /api/sales/refunds/{id}/confirm/      {"bank_txn_ref": "..."}
    POST /api/sales/refunds/{id}/mark-failed/  {"reason": "..."}
    POST /api/sales/refunds/{id}/retry/        {}

Chỉ Chủ (`sales.confirm_refund` — "tiền rời túi", BR-HT-07/BR-PQ boundary); Quản lý xem được
danh sách (đã có từ S13/S15) nhưng không đổi được trạng thái phiếu.
"""
from decimal import Decimal

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.sales.models import Refund
from apps.sales.orders.tests.test_s10_api import SENSITIVE_KEYS, OrderApiBase, find_keys
from apps.sales.refunds import services as refund_services


class S16RefundQueueTests(OrderApiBase):
    def _order_refund(self, amount="540000", phone="0901234567", txn="FT2626712345"):
        order = self._paid_order(phone=phone, txn=txn)
        refund, _dup = refund_services.create_invoice_refund(
            invoice=order.invoice, amount=Decimal(amount), is_partial=False,
            reason="Huỷ đơn — khách đổi ý", actor=self.ql,
        )
        return order, refund

    def test_s16_ac1_xac_nhan_voi_ma_gd(self):
        order, refund = self._order_refund()
        resp = client_for(self.chu).post(
            f"/api/sales/refunds/{refund.pk}/confirm/", {"bank_txn_ref": "FT2626799999"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], "REFUNDED")
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.REFUNDED)
        self.assertEqual(refund.confirmed_by, self.chu)
        self.assertIsNotNone(refund.confirmed_at)
        self.assertTrue(AuditLog.objects.filter(action="confirm_refund").exists())

    def test_s16_ac2_hoan_tru_vao_ky_xac_nhan(self):
        import datetime

        from django.utils import timezone

        from apps.sales.models import SalesInvoice

        order, refund = self._order_refund()
        SalesInvoice.objects.filter(pk=order.invoice.pk).update(
            issued_at=datetime.datetime(2026, 8, 15, 8, 0, tzinfo=datetime.timezone.utc)
        )
        confirmed_at = datetime.datetime(2026, 9, 2, 8, 0, tzinfo=datetime.timezone.utc)
        client_for(self.chu).post(
            f"/api/sales/refunds/{refund.pk}/confirm/", {"bank_txn_ref": "FT99"}, format="json",
        )
        Refund.objects.filter(pk=refund.pk).update(confirmed_at=confirmed_at)
        resp = client_for(self.chu).get("/api/reports/period/", {"year": 2026, "month": 9})
        self.assertEqual(Decimal(str(resp.json()["refunds"])), Decimal("540000"))
        resp8 = client_for(self.chu).get("/api/reports/period/", {"year": 2026, "month": 8})
        self.assertEqual(Decimal(str(resp8.json()["refunds"])), Decimal("0"))

    def test_s16_ac3_bao_that_bai_roi_thu_lai(self):
        order, refund = self._order_refund()
        failed = client_for(self.chu).post(
            f"/api/sales/refunds/{refund.pk}/mark-failed/", {"reason": "Sai số tài khoản"}, format="json",
        )
        self.assertEqual(failed.status_code, 200, failed.content)
        self.assertEqual(failed.json()["status"], "FAILED")
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.FAILED)
        self.assertEqual(refund.failure_reason, "Sai số tài khoản")
        self.assertTrue(AuditLog.objects.filter(action="mark_refund_failed").exists())

        retried = client_for(self.chu).post(f"/api/sales/refunds/{refund.pk}/retry/", {}, format="json")
        self.assertEqual(retried.status_code, 200, retried.content)
        self.assertEqual(retried.json()["status"], "PENDING")
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.PENDING)
        self.assertEqual(refund.failure_reason, "")
        self.assertTrue(AuditLog.objects.filter(action="retry_refund").exists())

    def test_s16_ac4_confirm_thieu_ma_gd(self):
        order, refund = self._order_refund()
        resp = client_for(self.chu).post(f"/api/sales/refunds/{refund.pk}/confirm/", {}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-HT-03")
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.PENDING)

    def test_s16_ac5_phieu_da_hoan_khong_doi_trang_thai(self):
        order, refund = self._order_refund()
        refund_services.confirm_refund(refund=refund, bank_txn_ref="FTOK", actor=self.chu)
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.REFUNDED)

        for path, payload in (
            ("confirm", {"bank_txn_ref": "FTAGAIN"}),
            ("mark-failed", {"reason": "x"}),
            ("retry", {}),
        ):
            resp = client_for(self.chu).post(
                f"/api/sales/refunds/{refund.pk}/{path}/", payload, format="json",
            )
            self.assertEqual(resp.status_code, 400, (path, resp.content))
            self.assertEqual(resp.json()["code"], "BR-HT-09")
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.REFUNDED)

    def test_s16_ac6_retry_vuot_so_con_hoan_vi_phieu_khac_lap_day(self):
        order, refund1 = self._order_refund(amount="300000")
        client_for(self.chu).post(
            f"/api/sales/refunds/{refund1.pk}/mark-failed/", {"reason": "sai STK"}, format="json",
        )
        refund2, _dup = refund_services.create_invoice_refund(
            invoice=order.invoice, amount=Decimal("400000"), is_partial=True,
            reason="Hoàn phần còn lại", actor=self.chu,
        )
        resp = client_for(self.chu).post(f"/api/sales/refunds/{refund1.pk}/retry/", {}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-HT-04")
        refund1.refresh_from_db()
        self.assertEqual(refund1.status, Refund.Status.FAILED)

    def test_s16_ac7_quan_ly_403_ba_thao_tac(self):
        order, refund = self._order_refund()
        for path, payload in (
            ("confirm", {"bank_txn_ref": "FT1"}),
            ("mark-failed", {"reason": "x"}),
            ("retry", {}),
        ):
            resp = client_for(self.ql).post(
                f"/api/sales/refunds/{refund.pk}/{path}/", payload, format="json",
            )
            self.assertEqual(resp.status_code, 403, (path, resp.content))
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.PENDING)

        row = client_for(self.ql).get("/api/sales/refunds/").json()["results"][0]
        self.assertEqual(row["available_actions"], [])  # FE không hiện nút

    def test_s16_danh_sach_hang_cho_du_field_va_loc_trang_thai(self):
        order, refund = self._order_refund()
        client_for(self.chu).post(
            f"/api/sales/refunds/{refund.pk}/mark-failed/", {"reason": "Sai số tài khoản"}, format="json",
        )
        other_order, other_refund = self._order_refund(phone="0908888888", txn="FTX2")
        refund_services.confirm_refund(refund=other_refund, bank_txn_ref="FTZ", actor=self.chu)

        resp = client_for(self.chu).get("/api/sales/refunds/", {"status": "PENDING,FAILED"})
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        ids = {r["id"] for r in body["results"]}
        self.assertEqual(ids, {refund.pk})  # REFUNDED không nằm trong hàng chờ

        row = body["results"][0]
        self.assertEqual(row["order_code"], order.code)
        self.assertEqual(row["customer_name"], "Chị Hoa")
        self.assertEqual(row["customer_phone"], "0901234567")
        self.assertEqual(row["status"], "FAILED")
        self.assertEqual(row["failure_reason"], "Sai số tài khoản")
        self.assertEqual(row["available_actions"], ["retry"])
        self.assertIn("created_at", row)
        self.assertEqual(find_keys(body, SENSITIVE_KEYS), set())

    def test_s16_timeline_hien_that_bai_va_thu_lai(self):
        order, refund = self._order_refund()
        client_for(self.chu).post(
            f"/api/sales/refunds/{refund.pk}/mark-failed/", {"reason": "Sai số tài khoản"}, format="json",
        )
        client_for(self.chu).post(f"/api/sales/refunds/{refund.pk}/retry/", {}, format="json")
        body = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()
        kinds = [r["kind"] for r in body["timeline"]]
        self.assertIn("refund_failed", kinds)
        self.assertIn("refund_retry", kinds)
        failed_row = next(r for r in body["timeline"] if r["kind"] == "refund_failed")
        self.assertIn("Sai số tài khoản", failed_row["label"])
        self.assertEqual(failed_row["actor_display"], "chu1")

    def test_s16_ac8_khong_ro_gia_von(self):
        order, refund = self._order_refund()
        for user in (self.kho, self.giao):
            resp = client_for(user).get("/api/sales/refunds/")
            self.assertIn(resp.status_code, (200, 403))
            if resp.status_code == 200:
                self.assertEqual(find_keys(resp.json(), SENSITIVE_KEYS), set())
