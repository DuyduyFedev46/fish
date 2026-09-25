"""
Sửa lỗi QA lô L7 (04-qa-report.md):

- B12 (High, BR-TT-03): mã GD của webhook và của Chủ phải cùng hệ. Adapter gửi
  `bank_txn_id` = referenceCode (FT…) đã chuẩn hoá; Django chuẩn hoá mã GD ở CẢ hai
  đường bằng cùng hàm `normalize_bank_txn_id` (bỏ mọi khoảng trắng, viết hoa) nên
  "ft 880003" nhập tay trùng với "FT880003" của webhook → 1 giao dịch.
- B13 (Medium, BR-TT-08): số tiền làm tròn về 0,01 VND (ROUND_HALF_UP); ≤ 0 sau làm tròn
  hoặc vượt miền cột `amount` (max_digits=14, decimal_places=2) → 400, không bao giờ 500,
  không ghi giao dịch 0 ₫.
"""
from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from apps.common.tests.fixtures import client_for
from apps.sales.models import PaymentTransaction, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.sales.payments import services as payment_services
from django.utils import timezone

WEBHOOK_URL = "/api/internal/payments/sepay-webhook/"


def manual_url(order):
    return f"/api/sales/orders/{order.pk}/confirm-payment"


class NormalizeBankTxnIdTests(SimpleTestCase):
    def test_b12_chuan_hoa_trim_bo_khoang_trang_viet_hoa(self):
        n = payment_services.normalize_bank_txn_id
        self.assertEqual(n("  ft880003 "), "FT880003")
        self.assertEqual(n("FT 8800\t03"), "FT880003")
        self.assertEqual(n(880003), "880003")
        self.assertEqual(n(None), "")
        self.assertEqual(n("   "), "")


class ParseAmountTests(SimpleTestCase):
    def test_b13_lam_tron_0_01_round_half_up(self):
        p = payment_services.parse_positive_amount
        self.assertEqual(p("100.005"), Decimal("100.01"))
        self.assertEqual(p("100.004"), Decimal("100.00"))
        self.assertEqual(p(540000), Decimal("540000.00"))
        # L8 (quyết định Duy 2026-09-26): tối thiểu 1đ → "0.005" (→ 0,01) nay bị từ chối,
        # xem test_l8_tien_bosung; vẫn làm tròn 0,01 trước khi so 1đ.
        self.assertIsNone(p("0.005"))
        self.assertEqual(p("0.995"), Decimal("1.00"))

    def test_b13_tu_choi_sau_lam_tron_le_0_hoac_vuot_mien(self):
        p = payment_services.parse_positive_amount
        for raw in ("0.001", "0.004", "0", "-1", "1e20", "123456789012345",
                    "1000000000000", "999999999999.995", "1e-30", "1e999999", "abc",
                    "NaN", "Infinity", True, [], {}, None):
            self.assertIsNone(p(raw), raw)
        self.assertEqual(p("999999999999.99"), Decimal("999999999999.99"))


@override_settings(INTERNAL_SERVICE_TOKEN="tok")
class QaL7FixApiTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.order = self._order()  # BOOKED 540.000đ

    def _manual(self, data, order=None):
        return client_for(self.chu).post(manual_url(order or self.order), data, format="json")

    def _webhook(self, bank_txn_id, amount="540000", order_code=None):
        # Đúng shape adapter gửi (adapter/app/sepay.py:to_internal_payload): bank_txn_id =
        # referenceCode đã chuẩn hoá, id SePay nằm trong raw.
        return client_for(None).post(
            WEBHOOK_URL,
            {"bank_txn_id": bank_txn_id, "order_code": order_code or self.order.code,
             "amount": amount, "received_at": "2026-09-25T10:00:00+07:00",
             "raw": {"id": 880003, "referenceCode": bank_txn_id}},
            format="json", HTTP_X_INTERNAL_TOKEN="tok",
        )

    # --- B12 ---------------------------------------------------------------
    def test_b12_webhook_truoc_roi_tay_cung_ma_khac_hoa_thuong_khoang_trang_duplicate(self):
        self.assertEqual(self._webhook("FT880003").status_code, 200)
        resp = self._manual({"bank_txn_id": "  ft 880003 ", "amount": "540000"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["duplicate"])
        self.assertEqual(resp.json()["result"], "PAID")
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.assertEqual(PaymentTransaction.objects.get().source, PaymentTransaction.Source.WEBHOOK)
        self.assertEqual(SalesInvoice.objects.count(), 1)

    def test_b12_tay_truoc_roi_webhook_khong_tao_giao_dich_thu_hai(self):
        resp = self._manual({"bank_txn_id": "ft880003", "amount": "540000"})
        self.assertEqual(resp.json()["result"], "PAID")
        pay = PaymentTransaction.objects.get()
        self.assertEqual(pay.bank_txn_id, "FT880003")  # lưu dạng chuẩn hoá

        resp = self._webhook("FT880003")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["match_status"], "MATCHED")
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.assertEqual(PaymentTransaction.objects.get().source, PaymentTransaction.Source.MANUAL)
        self.assertEqual(SalesInvoice.objects.count(), 1)

    def test_b12_don_tu_huy_tay_orphan_roi_webhook_chi_mot_dong_orphan(self):
        order_services.cancel_unpaid_expired(now=timezone.now() + timezone.timedelta(hours=2))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.AUTO_CANCELLED)
        self.assertEqual(self._manual({"bank_txn_id": "FT880004"}).json()["result"], "ORPHAN")
        resp = self._webhook(" ft880004")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(
            PaymentTransaction.objects.filter(match_status="ORPHAN").count(), 1
        )

    def test_b12_webhook_ma_chua_chuan_hoa_van_luu_dang_chuan(self):
        self._webhook("ft 880005")
        self.assertEqual(PaymentTransaction.objects.get().bank_txn_id, "FT880005")

    def test_b12_webhook_khong_co_ma_don_roi_gui_lai_khac_hoa_thuong_khong_ghi_them(self):
        self._webhook("FT880006", order_code="SO-KHONGCO")
        self._webhook("ft880006", order_code="SO-KHONGCO")
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    # --- B13 ---------------------------------------------------------------
    def test_b13_tay_so_tien_qua_lon_hoac_qua_nho_400_br_tt_08(self):
        for amount in ("123456789012345", "1e20", "99999999999999", "0.001", "0.004",
                       123456789012345):
            resp = self._manual({"bank_txn_id": "FTB13", "amount": amount})
            self.assertEqual(resp.status_code, 400, (amount, resp.content))
            self.assertEqual(resp.json()["code"], "BR-TT-08")
            self.assertTrue(resp.json()["detail"])
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_b13_tay_so_tien_qua_lon_bao_ro_qua_lon(self):
        resp = self._manual({"bank_txn_id": "FTB13", "amount": "1e20"})
        self.assertIn("quá lớn", resp.json()["detail"])

    def test_b13_tay_so_tien_le_duoc_lam_tron(self):
        resp = self._manual({"bank_txn_id": "FTB13", "amount": "300000.005"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(PaymentTransaction.objects.get().amount, Decimal("300000.01"))

    def test_b13_webhook_so_tien_ngoai_mien_400_webhook_invalid_input(self):
        for amount in ("100000000000000", "1e20", "0.001", "0.004"):
            resp = self._webhook(f"FTW{len(amount)}", amount=amount)
            self.assertEqual(resp.status_code, 400, (amount, resp.content))
            self.assertEqual(resp.json()["code"], "WEBHOOK_INVALID_INPUT")
        # cả nhánh không khớp đơn cũng không ghi
        resp = self._webhook("FTW0", amount="0.001", order_code="SO-KHONGCO")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(PaymentTransaction.objects.exists())
