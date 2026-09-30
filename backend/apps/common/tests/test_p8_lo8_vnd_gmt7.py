"""
P8 Lô 8 — SR-25 (BE): tiền VNĐ dạng `x.xxx ₫` và giờ hiển thị GMT+7 trong mọi CHUỖI người đọc do BE dựng.
ISO trả qua API giữ nguyên (có offset); chỉ câu chữ/nhãn/CSV/`__str__` mới phải theo giờ VN.
"""
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemPrice
from apps.common import formatting
from apps.inventory.models import Batch
from apps.purchasing.models import Supplier, PurchaseCost, PurchaseCostAllocation, PurchaseInvoice
from apps.sales.models import PaymentTransaction, Refund
from apps.sales.utils import gen_code, vnd_display

# 17:30Z ngày 30/09 = 00:30 ngày 01/10 giờ VN (GMT+7)
LATE_UTC = datetime(2026, 9, 30, 17, 30, tzinfo=dt_timezone.utc)


class VndFormatTests(SimpleTestCase):
    def test_sr25_ac1_format_vnd_dau_cham_va_dau_cach_thuong_truoc_dong(self):
        self.assertEqual(formatting.format_vnd(Decimal("300000")), "300.000 ₫")
        self.assertEqual(formatting.format_vnd("260000.00"), "260.000 ₫")
        self.assertEqual(formatting.format_vnd(Decimal("1234567")), "1.234.567 ₫")
        self.assertEqual(formatting.format_vnd(0), "0 ₫")
        self.assertNotIn(" ", formatting.format_vnd(Decimal("300000")))

    def test_sr25_ac1_format_vnd_lam_tron_half_up_khong_float(self):
        self.assertEqual(formatting.format_vnd(Decimal("18812.50")), "18.813 ₫")
        self.assertEqual(formatting.format_vnd(Decimal("999.49")), "999 ₫")

    def test_n8_3_format_vnd_none_ra_gach_ngang(self):
        self.assertEqual(formatting.format_vnd(None), "—")
        self.assertEqual(vnd_display(None), "—")

    def test_sr25_ac1_vnd_display_giu_ten_cu_va_cung_ket_qua(self):
        self.assertEqual(vnd_display(Decimal("300000")), "300.000 ₫")
        self.assertEqual(vnd_display(Decimal("300000")), formatting.format_vnd(Decimal("300000")))

    def test_sr25_ac1_vnd_short_dang_dau_d_dinh_kem_da_bo(self):
        from apps.sales import utils

        self.assertFalse(hasattr(utils, "vnd_short"))


class LocalTimeFormatTests(SimpleTestCase):
    def test_sr25_ac2_format_local_dung_gio_vn_khong_phai_utc(self):
        self.assertEqual(formatting.format_local_time(LATE_UTC), "00:30")
        self.assertEqual(formatting.format_local_date(LATE_UTC), "2026-10-01")
        self.assertEqual(formatting.format_local_datetime(LATE_UTC), "2026-10-01 00:30")

    def test_sr25_ac2_format_local_nhan_datetime_da_o_mui_gio_khac(self):
        from zoneinfo import ZoneInfo

        ny = LATE_UTC.astimezone(ZoneInfo("America/New_York"))  # 13:30 ngày 30/09
        self.assertEqual(formatting.format_local_datetime(ny), "2026-10-01 00:30")


class ModelStrTests(TestCase):
    """`__str__` hiện trong Django admin: tiền `x.xxx ₫`, giờ theo VN."""

    def test_sr25_ac2_auditlog_str_theo_gio_vn(self):
        log = AuditLog(action="close_batch", created_at=LATE_UTC)
        self.assertEqual(str(log), "[2026-10-01 00:30] system · close_batch")

    def test_sr25_ac1_refund_str_tien_vnd(self):
        r = Refund(amount=Decimal("300000"), status=Refund.Status.PENDING)
        self.assertIn("300.000 ₫", str(r))
        self.assertNotIn("300000", str(r))

    def test_sr25_ac1_payment_str_tien_vnd(self):
        p = PaymentTransaction(bank_txn_id="TX1", amount=Decimal("540000"))
        self.assertIn("540.000 ₫", str(p))

    def test_sr25_ac1_purchase_str_tien_vnd(self):
        self.assertIn("8.000.000 ₫", str(PurchaseCost(cost_type="TRANSPORT", amount=Decimal("8000000"))))
        alloc = PurchaseCostAllocation(
            purchase_cost=PurchaseCost(cost_type="TRANSPORT", amount=Decimal("8000000")),
            batch=Batch(batch_id="LO-GIA-1", item=Item(code="CA-THU", name="Cá thu")),
            allocated_amount=Decimal("200000"),
        )
        self.assertIn("= 200.000 ₫", str(alloc))
        self.assertIn("1.500.000 ₫", str(PurchaseInvoice(supplier=Supplier(name="NCC Giả"), amount=Decimal("1500000"))))

    def test_sr25_ac1_itemprice_str_tien_vnd(self):
        price = ItemPrice(item=Item(code="CA-THU", name="Cá thu"), rate=Decimal("270000"))
        self.assertIn("CA-THU: 270.000 ₫", str(price))


class GenCodeLocalDateTests(TestCase):
    def test_sr25_ac2_ma_chung_tu_mang_ngay_theo_gio_vn(self):
        fake_model = SimpleNamespace(
            objects=SimpleNamespace(filter=lambda **kw: SimpleNamespace(exists=lambda: False)),
        )
        with patch("apps.sales.utils.now", return_value=LATE_UTC):
            self.assertTrue(gen_code("SO-", fake_model).startswith("SO-261001-"))
