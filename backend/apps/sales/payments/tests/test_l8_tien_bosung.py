"""
Lô L8 — bổ sung tiền theo quyết định của Duy (2026-09-26):

1. BR-TT-08: số tiền TỐI THIỂU 1đ (VND không có số lẻ). Mọi đường nhận số tiền — xác nhận
   tay, webhook nội bộ, phiếu hoàn (BR-HT-04) — từ chối số < 1đ SAU khi làm tròn 0,01.
2. BR-TT-10 (mở rộng P5): khách chuyển NHIỀU HƠN tổng đơn ngay lần đầu (đơn Giữ chỗ) → đơn
   vẫn thanh toán như cũ (hoá đơn = tổng đơn); phần THỪA tách thành một giao dịch OVERPAID
   riêng (`<mã GD>-THUA`), OPEN trong hàng chờ để Chủ hoàn (S12/S13). Idempotent theo mã GD.
"""
from decimal import Decimal

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.sales.models import PaymentTransaction, Refund, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import SENSITIVE_KEYS, OrderApiBase, find_keys
from apps.sales.payments import services as payment_services

WEBHOOK_URL = "/api/internal/payments/sepay-webhook/"
QUEUE_URL = "/api/sales/payments/"
REFUND_URL = "/api/sales/refunds/create/"
MIN_MSG = "Số tiền tối thiểu 1đ."


class L8MinAmountParseTests(SimpleTestCase):
    def test_l8_br_tt_08_duoi_1d_sau_lam_tron_bi_tu_choi(self):
        p = payment_services.parse_positive_amount
        for raw in ("0.5", "0.99", "0.994", "0.01", "0.005", 0.5):
            self.assertIsNone(p(raw), raw)

    def test_l8_br_tt_08_tu_1d_tro_len_hop_le(self):
        p = payment_services.parse_positive_amount
        self.assertEqual(p("1"), Decimal("1.00"))
        self.assertEqual(p("0.995"), Decimal("1.00"))  # làm tròn trước rồi mới so 1đ
        self.assertEqual(p(1), Decimal("1.00"))

    def test_l8_br_tt_08_thong_diep_toi_thieu(self):
        with self.assertRaisesMessage(ValueError, MIN_MSG):
            payment_services.validate_amount("0.5")


@override_settings(INTERNAL_SERVICE_TOKEN="tok")
class L8Base(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.order = self._order()  # BOOKED 540.000đ

    def _webhook(self, txn, amount, order_code=None):
        return client_for(None).post(
            WEBHOOK_URL,
            {"bank_txn_id": txn, "order_code": self.order.code if order_code is None else order_code,
             "amount": amount, "received_at": "2026-09-26T10:00:00+07:00"},
            format="json", HTTP_X_INTERNAL_TOKEN="tok",
        )

    def _manual(self, data, user=None):
        return client_for(user or self.chu).post(
            f"/api/sales/orders/{self.order.pk}/confirm-payment", data, format="json",
        )


class L8MinAmountApiTests(L8Base):
    def test_l8_br_tt_08_xac_nhan_tay_duoi_1d_400(self):
        for amount in ("0.5", "0.99", "0.994"):
            resp = self._manual({"bank_txn_id": "FTMIN", "amount": amount})
            self.assertEqual(resp.status_code, 400, (amount, resp.content))
            self.assertEqual(resp.json(), {"code": "BR-TT-08", "detail": MIN_MSG})
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_l8_br_tt_08_xac_nhan_tay_1d_hop_le(self):
        resp = self._manual({"bank_txn_id": "FTONE", "amount": "1"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["result"], "UNDERPAID")

    def test_l8_br_tt_08_webhook_duoi_1d_400_ca_hai_nhanh(self):
        resp = self._webhook("FTW1", "0.99")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "WEBHOOK_INVALID_INPUT")
        self.assertIn(MIN_MSG, resp.json()["detail"])
        resp = self._webhook("FTW2", "0.5", order_code="SO-KHONGCO")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_l8_br_ht_04_phieu_hoan_duoi_1d_400_ca_hai_nhanh(self):
        # nhánh giao dịch: ORPHAN của đơn tự huỷ
        other = self._order(phone="0902222222")
        order_services.cancel_unpaid_expired(now=timezone.now() + timezone.timedelta(hours=2))
        orphan = payment_services.confirm_payment(
            order=other, bank_txn_id="FTORPHAN", amount=Decimal("300000"), received_at=timezone.now(),
        )
        # nhánh hoá đơn
        paid = self._paid_order(phone="0903333333", txn="FTPAID")
        invoice = SalesInvoice.objects.get(sales_order=paid)
        for source in ({"payment_transaction": orphan.pk}, {"sales_invoice": invoice.pk}):
            resp = client_for(self.chu).post(
                REFUND_URL, {**source, "amount": "0.5", "reason": "x"}, format="json",
            )
            self.assertEqual(resp.status_code, 400, (source, resp.content))
            self.assertEqual(resp.json(), {"code": "BR-HT-04", "detail": "Số tiền hoàn tối thiểu 1đ."})
        self.assertFalse(Refund.objects.exists())

    def test_l8_br_ht_04_service_hoa_don_duoi_1d_bi_tu_choi(self):
        from apps.common.exceptions import BusinessError
        from apps.sales.refunds import services as refund_services

        paid = self._paid_order(phone="0903333333", txn="FTPAID")
        invoice = SalesInvoice.objects.get(sales_order=paid)
        with self.assertRaisesMessage(BusinessError, "Số tiền hoàn tối thiểu 1đ."):
            refund_services.create_refund(invoice=invoice, amount=Decimal("0.5"), is_partial=True,
                                          reason="x", actor=self.chu)
        self.assertFalse(Refund.objects.exists())


class L8OverpaidFirstTimeTests(L8Base):
    """BR-TT-10 mở rộng: chuyển thừa ngay lần đầu cho đơn Giữ chỗ."""

    def _rows(self):
        return {p.bank_txn_id: p for p in PaymentTransaction.objects.all()}

    def test_l8_thua_lan_dau_webhook_don_paid_phan_thua_vao_hang_cho(self):
        resp = self._webhook("FT600", "600000")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json(), {
            "matched": True, "order_status": "PROCESSING", "match_status": "MATCHED",
            "overpaid_amount": "60000",
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.PROCESSING)
        invoice = SalesInvoice.objects.get(sales_order=self.order)
        self.assertEqual(invoice.amount, Decimal("540000"))
        self.assertEqual(invoice.payment_txn_ref, "FT600")

        rows = self._rows()
        self.assertEqual(set(rows), {"FT600", "FT600-THUA"})
        main, extra = rows["FT600"], rows["FT600-THUA"]
        self.assertEqual((main.amount, main.match_status, main.resolution_status),
                         (Decimal("540000"), "MATCHED", None))
        self.assertEqual((extra.amount, extra.match_status, extra.resolution_status),
                         (Decimal("60000"), "OVERPAID", "OPEN"))
        self.assertEqual(extra.sales_order_id, self.order.pk)
        self.assertEqual(extra.source, main.source)
        self.assertEqual(extra.received_at, main.received_at)
        self.assertEqual(extra.raw_payload["split_from"], "FT600")
        self.assertEqual(Decimal(extra.raw_payload["bank_amount"]), Decimal("600000"))
        # tổng tiền trên 2 dòng = đúng số ngân hàng báo
        self.assertEqual(main.amount + extra.amount, Decimal("600000"))
        self.assertEqual(payment_services.order_paid_total(self.order), Decimal("540000"))

        log = AuditLog.objects.get(action="split_overpaid_payment")
        self.assertIsNone(log.actor)  # Hệ thống
        self.assertEqual(log.object_id, str(extra.pk))
        self.assertEqual(log.changes["bank_txn_id"], "FT600")
        self.assertEqual(Decimal(log.changes["overpaid_amount"]), Decimal("60000"))

    def test_l8_thua_lan_dau_gui_lai_khong_nhan_doi(self):
        self._webhook("FT600", "600000")
        resp = self._webhook("ft 600", "600000")  # B12: dạng khác của cùng mã GD
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["overpaid_amount"], "60000")
        resp = self._webhook("FT600", "600000", order_code="")  # gửi lại thiếu mã đơn
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(PaymentTransaction.objects.count(), 2)
        self.assertEqual(SalesInvoice.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="split_overpaid_payment").count(), 1)
        # xác nhận tay cùng mã → duplicate, không tách thêm
        resp = self._manual({"bank_txn_id": "FT600", "amount": "600000"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["duplicate"])
        self.assertEqual(resp.json()["overpaid_amount"], "60000")
        self.assertEqual(PaymentTransaction.objects.count(), 2)

    def test_l8_thua_lan_dau_xac_nhan_tay(self):
        resp = self._manual({"bank_txn_id": "FTM600", "amount": "600000"})
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["result"], "PAID")
        self.assertFalse(body["duplicate"])
        self.assertEqual(body["overpaid_amount"], "60000")
        extra = PaymentTransaction.objects.get(bank_txn_id="FTM600-THUA")
        self.assertEqual(extra.source, PaymentTransaction.Source.MANUAL)
        log = AuditLog.objects.get(action="split_overpaid_payment")
        self.assertEqual(log.actor, self.chu)

    def test_l8_dung_tong_don_khong_tach(self):
        resp = self._webhook("FT540", "540000")
        self.assertNotIn("overpaid_amount", resp.json())
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.assertFalse(AuditLog.objects.filter(action="split_overpaid_payment").exists())

    def test_l8_hang_cho_phan_thua_hoan_duoc_toi_da_phan_thua(self):
        self._webhook("FT600", "600000")
        extra = PaymentTransaction.objects.get(bank_txn_id="FT600-THUA")
        resp = client_for(self.chu).get(QUEUE_URL, {"resolution_status": "OPEN"})
        self.assertEqual(resp.status_code, 200)
        rows = resp.json()["results"]
        self.assertEqual([r["id"] for r in rows], [extra.pk])
        row = rows[0]
        self.assertEqual(row["amount"], "60000")
        self.assertEqual(row["refundable_amount"], "60000")
        self.assertEqual(row["available_actions"], ["refund"])
        self.assertEqual(row["order"]["paid_total"], "540000")
        self.assertEqual(find_keys(resp.json(), SENSITIVE_KEYS), set())

        orders = client_for(self.chu).get("/api/sales/orders/").json()["results"]
        self.assertTrue({r["id"]: r["needs_attention"] for r in orders}[self.order.pk])

        resp = client_for(self.chu).post(
            REFUND_URL, {"payment_transaction": extra.pk, "amount": "60001", "reason": "thừa"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["detail"], "Vượt số tiền còn được hoàn: tối đa 60.000đ.")

        resp = client_for(self.chu).post(
            REFUND_URL, {"payment_transaction": extra.pk, "amount": "60000", "reason": "thừa"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        resp = client_for(self.chu).post(
            f"/api/sales/refunds/{resp.json()['id']}/confirm/", {"bank_txn_ref": "FTREF"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        extra.refresh_from_db()
        self.assertEqual((extra.resolution_status, extra.resolution), ("RESOLVED", "REFUNDED"))
        # hoá đơn không bị động tới: vẫn hoàn theo hoá đơn tối đa 540.000đ
        from apps.sales.refunds.services import refundable_amount
        invoice = SalesInvoice.objects.get(sales_order=self.order)
        self.assertEqual(refundable_amount(invoice=invoice), Decimal("540000"))

    def test_l8_phan_thua_quyen_quan_ly_nv_kho_403(self):
        self._webhook("FT600", "600000")
        extra = PaymentTransaction.objects.get(bank_txn_id="FT600-THUA")
        for user in (self.ql, self.kho, self.giao):
            self.assertEqual(client_for(user).get(QUEUE_URL).status_code, 403)
            resp = client_for(user).post(
                REFUND_URL, {"payment_transaction": extra.pk, "amount": "60000", "reason": "x"},
                format="json",
            )
            self.assertEqual(resp.status_code, 403, (user, resp.content))
        self.assertFalse(Refund.objects.exists())

    def test_l8_gan_giao_dich_khong_khop_thua_cung_tach(self):
        resp = self._webhook("FTNOCODE", "700000", order_code="")
        self.assertEqual(resp.status_code, 200)
        pay = PaymentTransaction.objects.get(bank_txn_id="FTNOCODE")
        resp = client_for(self.chu).post(
            f"/api/sales/payments/{pay.pk}/resolve",
            {"action": "ATTACH_TO_ORDER", "order_id": self.order.pk}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["order_status"], "PROCESSING")
        self.assertEqual(resp.json()["overpaid_amount"], "160000")
        pay.refresh_from_db()
        self.assertEqual((pay.amount, pay.match_status, pay.resolution_status, pay.resolution),
                         (Decimal("540000"), "MATCHED", "RESOLVED", "ATTACHED"))
        extra = PaymentTransaction.objects.get(bank_txn_id="FTNOCODE-THUA")
        self.assertEqual((extra.amount, extra.match_status, extra.resolution_status),
                         (Decimal("160000"), "OVERPAID", "OPEN"))
        self.assertEqual(extra.sales_order_id, self.order.pk)
        log = AuditLog.objects.get(action="split_overpaid_payment")
        self.assertEqual(log.actor, self.chu)
        self.assertEqual(Decimal(log.changes["bank_amount"]), Decimal("700000"))

    def test_l8_ma_gd_dai_100_ky_tu_van_tach_duoc(self):
        txn = "F" * 100
        resp = self._webhook(txn, "600000")
        self.assertEqual(resp.status_code, 200, resp.content)
        extra = PaymentTransaction.objects.get(match_status="OVERPAID")
        self.assertLessEqual(len(extra.bank_txn_id), 100)
        self.assertTrue(extra.bank_txn_id.endswith("-THUA"))
        self.assertEqual(extra.raw_payload["split_from"], txn)
