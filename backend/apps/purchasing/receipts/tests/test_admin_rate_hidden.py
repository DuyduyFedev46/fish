"""
Không rò giá mua trong Django Admin phiếu nhập (bất biến #1, §1.6, BR-MH-06).

Lỗi có từ trước (ghi nợ ở L3–L4): inline dòng phiếu nhập hiện cột `rate` và chuỗi mô tả dòng
(`__str__` có `@ rate`) cho mọi staff xem được phiếu nhập. Người thiếu `inventory.view_costprice`
không được thấy giá mua — không input, không chữ, không sửa được.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.common.tests.fixtures import make_master, make_user
from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine

SECRET_RATE = "81234.56"


def admin_staff(username, *groups):
    user = make_user(username, *groups)
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return User.objects.get(pk=user.pk)


class ReceiptAdminRateHiddenTests(TestCase):
    def setUp(self):
        self.item, self.sup, self.wh = make_master()
        self.chu = admin_staff("loc", "chu")
        self.receipt = PurchaseReceipt.objects.create(
            supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            created_by=self.chu,
        )
        self.line = PurchaseReceiptLine.objects.create(
            receipt=self.receipt, item=self.item, qty=Decimal("12.5"), rate=Decimal(SECRET_RATE),
        )
        self.url = reverse("admin:purchasing_purchasereceipt_change", args=[self.receipt.pk])

    def page(self, user):
        self.client.force_login(user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_quan_ly_nv_kho_khong_thay_rate_trong_inline_phieu_nhap(self):
        for username, group in (("ql1", "quan_ly"), ("kho1", "nv_kho")):
            html = self.page(admin_staff(username, group))
            self.assertNotIn(SECRET_RATE, html, username)
            self.assertNotIn("81234", html, username)
            self.assertNotIn('name="lines-0-rate"', html, username)
            self.assertNotIn("Đơn giá mua", html, username)

    def test_chu_van_thay_rate(self):
        html = self.page(self.chu)
        self.assertIn('name="lines-0-rate"', html)
        self.assertIn(SECRET_RATE, html)

    def test_str_dong_nhap_khong_chua_gia_mua(self):
        self.assertNotIn(SECRET_RATE, str(self.line))
        self.assertNotIn("81234", str(self.line))

    def test_quan_ly_luu_phieu_nhap_khong_doi_rate_khong_them_dong(self):
        ql1 = admin_staff("ql1", "quan_ly")
        self.client.force_login(ql1)
        data = {
            "supplier": str(self.sup.pk), "warehouse": str(self.wh.pk),
            "received_date": timezone.localdate().isoformat(), "note": "",
            "lines-TOTAL_FORMS": "2", "lines-INITIAL_FORMS": "1",
            "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
            "lines-0-id": str(self.line.pk), "lines-0-receipt": str(self.receipt.pk),
            "lines-0-item": str(self.item.pk), "lines-0-qty": "12.5",
            "lines-0-rate": "1", "lines-0-shelf_life_days": "",
            "lines-1-receipt": str(self.receipt.pk), "lines-1-item": str(self.item.pk),
            "lines-1-qty": "3", "lines-1-rate": "2", "lines-1-shelf_life_days": "",
        }
        self.client.post(self.url, data)
        self.line.refresh_from_db()
        self.assertEqual(self.line.rate, Decimal(SECRET_RATE))
        self.assertEqual(self.receipt.lines.count(), 1)
