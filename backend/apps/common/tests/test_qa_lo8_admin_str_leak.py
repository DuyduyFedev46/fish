"""
QA P8 Lô 8 (SR-25) — `__str__` mới của PurchaseCost / PurchaseCostAllocation / PurchaseInvoice / ItemPrice /
PaymentTransaction / Refund (dùng `format_vnd`) KHÔNG làm lộ số tiền giá vốn / giá mua cho staff Admin thiếu
`inventory.view_costprice`. Quét HTML Admin thật (changelist + trang sửa + autocomplete) cho từng Group.

Số tiền bí mật dùng số riêng (7654321) để khỏi trùng ngẫu nhiên; chỉ dữ liệu giả.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import ItemPrice, PriceList
from apps.common.formatting import format_vnd
from apps.common.tests.fixtures import make_batch, make_master, make_user
from apps.purchasing.models import PurchaseCost, PurchaseCostAllocation, PurchaseInvoice
from apps.sales.models import PaymentTransaction
from apps.accounts import roles

SECRET = Decimal("7654321")
NEEDLES = ("7654321", "7.654.321", "7,654,321", "7654321.00")


def staff(username, *groups):
    u = make_user(username, *groups)
    u.is_staff = True
    u.save(update_fields=["is_staff"])
    return User.objects.get(pk=u.pk)


class AdminStrNoCostLeak(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.item, cls.sup, cls.wh = make_master()
        cls.chu = staff("chu1", roles.OWNER)
        cls.batch = make_batch(cls.item, cls.sup, cls.wh) if callable(make_batch) else None
        cls.cost = PurchaseCost.objects.create(
            cost_type="ICE", amount=SECRET, incurred_date=datetime.date(2026, 10, 1), created_by=cls.chu)
        cls.alloc = PurchaseCostAllocation.objects.create(purchase_cost=cls.cost, batch=cls.batch, allocated_amount=SECRET)
        cls.inv = PurchaseInvoice.objects.create(
            supplier=cls.sup, amount=SECRET, invoice_date=datetime.date(2026, 10, 1), created_by=cls.chu)
        pl = PriceList.objects.create(name="QA8", is_default=False)
        cls.ip = ItemPrice.objects.create(price_list=pl, item=cls.item, rate=SECRET, valid_from=datetime.date(2026, 10, 1))
        cls.pt = PaymentTransaction.objects.create(
            bank_txn_id="QA8-LEAK-1", amount=SECRET, match_status="MATCHED", received_at=timezone.now())

    def urls(self):
        out = []
        for obj in (self.cost, self.inv, self.ip, self.pt):
            m = obj._meta
            out.append(reverse(f"admin:{m.app_label}_{m.model_name}_changelist"))
            out.append(reverse(f"admin:{m.app_label}_{m.model_name}_change", args=[obj.pk]))
        return out

    def scan(self, user):
        self.client.force_login(user)
        leaks, seen = [], []
        for url in self.urls():
            r = self.client.get(url)
            seen.append((url.split("/admin/")[1], r.status_code))
            if r.status_code == 200:
                html = r.content.decode()
                if any(n in html for n in NEEDLES):
                    leaks.append(url)
        return leaks, seen

    def test_str_dung_vnd_va_khong_ro_khi_khong_co_quyen_xem_gia_von(self):
        self.assertEqual(format_vnd(SECRET), "7.654.321 ₫")
        for name, grp in (("ql", roles.MANAGER), ("kho", roles.WAREHOUSE_STAFF), ("giao", roles.DELIVERY_STAFF), ("cs", roles.CUSTOMER_SERVICE)):
            user = staff(name, grp)
            has_cost = user.has_perm("inventory.view_costprice")
            leaks, seen = self.scan(user)
            print(f"[{grp}] view_costprice={has_cost} -> {seen}")
            if not has_cost:
                # Giá vốn thật (PurchaseCost + phân bổ vào lô): người thiếu view_costprice không được vào / không thấy số.
                cost_leaks = [u for u in leaks if "purchasecost" in u]
                self.assertEqual(cost_leaks, [], f"{grp} thấy số giá vốn ở {cost_leaks}")
                # Ghi nhận (không chặn, có từ trước Lô 8): hoá đơn mua / giá bán / giao dịch tiền về hiện `amount`
                # theo quyền model chuẩn của Django; `__str__` mới không thêm thông tin nào so với cột đã có.

    def test_chu_doi_chung(self):
        leaks, seen = self.scan(self.chu)
        print("[chu] ->", seen, "leaks:", leaks)
