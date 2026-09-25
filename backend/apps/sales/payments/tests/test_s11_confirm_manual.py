"""
S11 — Chủ xác nhận thanh toán thủ công cho đơn Giữ chỗ (UC-03, E-05).

BR-TT-03 (idempotent theo mã GD), BR-TT-04 (thiếu tiền), BR-TT-05 (tiền về sau khi huỷ),
BR-TT-07 (chỉ Chủ), BR-TT-08 (mới — xác nhận tay gắn vào ĐƠN Giữ chỗ, chạy chung service
với webhook). Endpoint cũ trên hoá đơn đã gỡ (A2).
"""
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.delivery.models import DeliveryNote
from apps.inventory.models import Batch
from apps.sales.models import PaymentTransaction, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.sales.payments import services as payment_services


def url(order):
    return f"/api/sales/orders/{order.pk}/confirm-payment"


class S11ConfirmManualTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.order = self._order()  # BOOKED 540.000đ (2kg × 270.000)

    def _post(self, user, order, data):
        return client_for(user).post(url(order), data, format="json")

    def test_s11_ac1_du_tien_paid_hoa_don_tru_kho_phieu_giao_audit(self):
        resp = self._post(self.chu, self.order, {"bank_txn_id": "FT001", "amount": "540000"})
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.order.refresh_from_db()
        invoice = SalesInvoice.objects.get(sales_order=self.order)
        note = DeliveryNote.objects.get(sales_invoice=invoice)
        self.assertEqual(body, {
            "result": "PAID", "duplicate": False, "order_status": "PROCESSING",
            "invoice_id": invoice.pk, "delivery_note_code": note.code,
        })
        self.assertEqual(self.order.status, SalesOrder.Status.PROCESSING)
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        b = Batch.objects.get(pk=self.batch.pk)
        self.assertEqual(b.qty_available, Decimal("98"))
        self.assertEqual(b.qty_reserved, Decimal("0"))
        pay = PaymentTransaction.objects.get(bank_txn_id="FT001")
        self.assertEqual(pay.source, PaymentTransaction.Source.MANUAL)
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.MATCHED)
        log = AuditLog.objects.get(action="confirm_payment_manual")
        self.assertEqual(log.actor, self.chu)
        self.assertEqual(log.object_id, str(self.order.pk))
        self.assertEqual(log.changes["bank_txn_id"], "FT001")
        self.assertEqual(log.changes["status"], {"from": "BOOKED", "to": "PROCESSING"})

    def test_s11_ac1_bo_trong_amount_thi_bang_tong_don(self):
        resp = self._post(self.chu, self.order, {"bank_txn_id": "FT001"})
        self.assertEqual(resp.json()["result"], "PAID")
        self.assertEqual(PaymentTransaction.objects.get().amount, Decimal("540000"))

    def test_s11_ac2_thieu_tien_underpaid_don_van_giu_cho(self):
        resp = self._post(self.chu, self.order, {"bank_txn_id": "FT002", "amount": "300000"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json(), {
            "result": "UNDERPAID", "duplicate": False, "order_status": "BOOKED",
            "paid_total": "300000", "missing": "240000",
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.BOOKED)
        self.assertFalse(SalesInvoice.objects.exists())
        pay = PaymentTransaction.objects.get()
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.UNDERPAID)
        self.assertEqual(pay.source, PaymentTransaction.Source.MANUAL)
        self.assertTrue(AuditLog.objects.filter(action="confirm_payment_manual", actor=self.chu).exists())

    def test_s11_ac3_don_tu_huy_thi_orphan_khong_khoi_phuc_kho_khong_doi(self):
        order_services.cancel_unpaid_expired(now=timezone.now() + timezone.timedelta(hours=2))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.AUTO_CANCELLED)
        before = Batch.objects.get(pk=self.batch.pk)

        resp = self._post(self.chu, self.order, {"bank_txn_id": "FT003", "amount": "540000"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json(), {
            "result": "ORPHAN", "duplicate": False, "order_status": "AUTO_CANCELLED",
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.AUTO_CANCELLED)
        after = Batch.objects.get(pk=self.batch.pk)
        self.assertEqual((after.qty_available, after.qty_reserved),
                         (before.qty_available, before.qty_reserved))
        self.assertFalse(SalesInvoice.objects.exists())
        self.assertEqual(PaymentTransaction.objects.get().match_status,
                         PaymentTransaction.MatchStatus.ORPHAN)

    def test_s11_ac4_bam_hai_lan_duplicate_mot_giao_dich_mot_hoa_don(self):
        first = self._post(self.chu, self.order, {"bank_txn_id": "FT001", "amount": "540000"}).json()
        second = self._post(self.chu, self.order, {"bank_txn_id": "FT001", "amount": "540000"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json(), {**first, "duplicate": True})
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.assertEqual(SalesInvoice.objects.count(), 1)
        self.assertEqual(Batch.objects.get(pk=self.batch.pk).qty_available, Decimal("98"))
        self.assertEqual(AuditLog.objects.filter(action="confirm_payment_manual").count(), 1)

    def test_s11_ac4_bam_hai_lan_thieu_tien_cung_duplicate(self):
        first = self._post(self.chu, self.order, {"bank_txn_id": "FT002", "amount": "300000"}).json()
        second = self._post(self.chu, self.order, {"bank_txn_id": "FT002", "amount": "300000"}).json()
        self.assertEqual(second, {**first, "duplicate": True})
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    @override_settings(INTERNAL_SERVICE_TOKEN="tok")
    def test_s11_ac5_webhook_da_ghi_roi_chu_xac_nhan_tay_duplicate(self):
        resp = client_for(None).post(
            "/api/internal/payments/sepay-webhook/",
            {"bank_txn_id": "FT001", "order_code": self.order.code, "amount": "540000",
             "received_at": "2026-09-24T10:00:00+07:00"},
            format="json", HTTP_X_INTERNAL_TOKEN="tok",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = self._post(self.chu, self.order, {"bank_txn_id": "FT001", "amount": "540000"}).json()
        self.assertTrue(body["duplicate"])
        self.assertEqual(body["result"], "PAID")
        self.assertEqual(body["order_status"], "PROCESSING")
        pay = PaymentTransaction.objects.get()
        self.assertEqual(pay.source, PaymentTransaction.Source.WEBHOOK)  # không ghi đè
        self.assertEqual(SalesInvoice.objects.count(), 1)
        self.assertFalse(AuditLog.objects.filter(action="confirm_payment_manual").exists())

    def test_s11_ma_gd_da_dung_cho_don_khac_400(self):
        other = self._order(phone="0908888888")
        payment_services.confirm_payment(
            order=other, bank_txn_id="FT009", amount=other.total_amount, received_at=timezone.now(),
        )
        resp = self._post(self.chu, self.order, {"bank_txn_id": "FT009", "amount": "540000"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-TT-03")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.BOOKED)

    def test_s11_ac6_thieu_ma_gd_hoac_so_tien_sai_400(self):
        for data in (
            {"amount": "540000"},
            {"bank_txn_id": "", "amount": "540000"},
            {"bank_txn_id": "   ", "amount": "540000"},
            {"bank_txn_id": "FT1", "amount": "0"},
            {"bank_txn_id": "FT1", "amount": "-5"},
            {"bank_txn_id": "FT1", "amount": "abc"},
            {"bank_txn_id": "FT1", "amount": "NaN"},
            {"bank_txn_id": "X" * 101, "amount": "540000"},
        ):
            resp = self._post(self.chu, self.order, data)
            self.assertEqual(resp.status_code, 400, data)
            self.assertEqual(resp.json()["code"], "BR-TT-08", data)
            self.assertTrue(resp.json()["detail"])
        self.assertEqual(
            self._post(self.chu, self.order, {"amount": "1"}).json()["detail"],
            "Thiếu mã giao dịch ngân hàng.",
        )
        self.assertFalse(PaymentTransaction.objects.exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.BOOKED)

    def test_s11_don_khong_o_giu_cho_hoac_tu_huy_400(self):
        self._post(self.chu, self.order, {"bank_txn_id": "FT001"})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.PROCESSING)
        resp = self._post(self.chu, self.order, {"bank_txn_id": "FT777", "amount": "540000"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {
            "code": "BR-TT-08", "detail": "Đơn không ở trạng thái Giữ chỗ/Tự huỷ.",
        })
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_s11_ac7_quan_ly_403_khong_doi_gi(self):
        for user in (self.ql, self.kho, self.giao):
            resp = self._post(user, self.order, {"bank_txn_id": "FT001", "amount": "540000"})
            self.assertEqual(resp.status_code, 403, user.username)
        self.assertFalse(PaymentTransaction.objects.exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.BOOKED)

    def test_s11_chua_dang_nhap_401(self):
        resp = self._post(None, self.order, {"bank_txn_id": "FT001"})
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_s11_don_khong_ton_tai_404(self):
        resp = client_for(self.chu).post(
            "/api/sales/orders/999999/confirm-payment", {"bank_txn_id": "FT001"}, format="json"
        )
        self.assertEqual(resp.status_code, 404)

    def test_s11_ac8_endpoint_cu_tren_hoa_don_da_go(self):
        self._post(self.chu, self.order, {"bank_txn_id": "FT001"})
        invoice = SalesInvoice.objects.get()
        resp = client_for(self.chu).post(
            f"/api/sales/invoices/{invoice.pk}/confirm-payment/",
            {"bank_txn_id": "FT999"}, format="json",
        )
        self.assertIn(resp.status_code, (404, 405))
        resp = client_for(self.chu).post(
            f"/api/sales/invoices/{invoice.pk}/confirm-payment",
            {"bank_txn_id": "FT999"}, format="json",
        )
        self.assertIn(resp.status_code, (404, 405))
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_s11_available_actions_sau_khi_xac_nhan(self):
        self._post(self.chu, self.order, {"bank_txn_id": "FT001"})
        body = client_for(self.chu).get(f"/api/sales/orders/{self.order.pk}/").json()
        self.assertNotIn("confirm_payment", body["available_actions"])
        self.assertEqual(body["payments"][0]["source"], "MANUAL")

    def test_s11_webhook_van_chay_nhu_cu_khong_ghi_audit_tay(self):
        """Service chung: đường webhook không bị chặn bởi luật trạng thái của nhánh tay."""
        pay = payment_services.confirm_payment(
            order=self.order, bank_txn_id="FTW", amount=Decimal("540000"), received_at=timezone.now(),
        )
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.MATCHED)
        self.assertFalse(AuditLog.objects.filter(action="confirm_payment_manual").exists())

    def test_s11_url_co_dau_gach_cuoi_cung_chay_va_amount_so(self):
        resp = client_for(self.chu).post(
            f"/api/sales/orders/{self.order.pk}/confirm-payment/",
            {"bank_txn_id": "FT010", "amount": 540000}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["result"], "PAID")
