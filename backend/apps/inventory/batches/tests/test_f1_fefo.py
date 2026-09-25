"""
F1 — Chọn lô theo FEFO (doc/features/2026-09-26-fefo, decisions 2026-09-26).

BR-BH-05 (sửa): trong các lô bán được (BR-LO-02), lô hạn dùng sớm nhất xuất trước; cùng hạn
thì lô nhập sớm hơn; vẫn trùng thì lô tạo trước (id nhỏ hơn).
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup
from apps.common.exceptions import BusinessError
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier


class FefoBase(TestCase):
    def setUp(self):
        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=g)
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.today = timezone.localdate()

    def _lot(self, *, received, expiry, qty="5", status=Batch.Status.SELLING, item=None):
        """Lô bán được với ngày nhập/hạn chỉ định (hạn có thể sửa tay xuống, BR-MH-02)."""
        b = batch_services.create_batch(
            item=item or self.item, supplier=self.sup, warehouse=self.wh,
            received_date=received, qty=Decimal(qty), purchase_rate=Decimal("80000"),
        )
        b.expiry_date = expiry
        b.status = status
        b.save(update_fields=["expiry_date", "status"])
        return b

    def _d(self, days):
        return self.today + datetime.timedelta(days=days)


class F1AllocateFefoTests(FefoBase):
    def test_f1_ac1_lo_nhap_sau_nhung_han_som_hon_ra_truoc(self):
        a = self._lot(received=self._d(-10), expiry=self._d(60))   # nhập trước, hạn muộn
        b = self._lot(received=self._d(-5), expiry=self._d(20))    # nhập sau, hạn sớm
        alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("1"))
        self.assertEqual([(x.pk, q) for x, q in alloc], [(b.pk, Decimal("1"))])
        self.assertNotEqual(alloc[0][0].pk, a.pk)

    def test_f1_ac1_sellable_batches_sap_theo_han(self):
        a = self._lot(received=self._d(-10), expiry=self._d(60))
        b = self._lot(received=self._d(-5), expiry=self._d(20))
        c = self._lot(received=self._d(-1), expiry=self._d(40))
        ids = list(batch_services.sellable_batches(item=self.item).values_list("pk", flat=True))
        self.assertEqual(ids, [b.pk, c.pk, a.pk])

    def test_f1_ac2_cung_han_thi_lo_nhap_som_hon_roi_lo_tao_truoc(self):
        late = self._lot(received=self._d(-2), expiry=self._d(30))
        first_same_day = self._lot(received=self._d(-8), expiry=self._d(30))
        second_same_day = self._lot(received=self._d(-8), expiry=self._d(30))
        ids = list(batch_services.sellable_batches(item=self.item).values_list("pk", flat=True))
        self.assertEqual(ids, [first_same_day.pk, second_same_day.pk, late.pk])
        alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("7"))
        self.assertEqual([(x.pk, q) for x, q in alloc],
                         [(first_same_day.pk, Decimal("5")), (second_same_day.pk, Decimal("2"))])

    def test_f1_ac3_vuot_ton_lo_han_som_nhat_thi_lay_tiep_lo_han_ke_tiep(self):
        far = self._lot(received=self._d(-9), expiry=self._d(80), qty="10")
        soon = self._lot(received=self._d(-3), expiry=self._d(10), qty="4")
        mid = self._lot(received=self._d(-1), expiry=self._d(30), qty="3")
        alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("9"))
        self.assertEqual([(x.pk, q) for x, q in alloc],
                         [(soon.pk, Decimal("4")), (mid.pk, Decimal("3")), (far.pk, Decimal("2"))])

    def test_f1_ac3_bo_qua_phan_da_giu_cho(self):
        soon = self._lot(received=self._d(-3), expiry=self._d(10), qty="4")
        later = self._lot(received=self._d(-9), expiry=self._d(50), qty="10")
        batch_services.reserve(batch=soon, qty=Decimal("4"))  # lô hạn sớm đã bị giữ hết
        alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("2"))
        self.assertEqual([(x.pk, q) for x, q in alloc], [(later.pk, Decimal("2"))])

    def test_f1_ac3_khong_du_ton_van_bao_thieu(self):
        self._lot(received=self._d(-3), expiry=self._d(10), qty="2")
        with self.assertRaises(BusinessError):
            batch_services.allocate_fefo(item=self.item, qty=Decimal("3"))

    def test_f1_ac4_lo_qua_han_khong_duoc_chon_du_han_som_nhat(self):
        expired = self._lot(received=self._d(-30), expiry=self._d(-1), qty="50")
        expired_job_done = self._lot(received=self._d(-30), expiry=self._d(-2), qty="50",
                                     status=Batch.Status.EXPIRED)
        ok = self._lot(received=self._d(-1), expiry=self._d(45), qty="5")
        alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("5"))
        self.assertEqual([(x.pk, q) for x, q in alloc], [(ok.pk, Decimal("5"))])
        ids = set(batch_services.sellable_batches(item=self.item).values_list("pk", flat=True))
        self.assertNotIn(expired.pk, ids)
        self.assertNotIn(expired_job_done.pk, ids)

    def test_f1_ac4_lo_het_han_hom_nay_van_ban_va_ra_dau_tien(self):
        # C1: expiry_date là ngày cuối còn bán -> FEFO chọn nó trước (R-3 đã chấp nhận).
        far = self._lot(received=self._d(-1), expiry=self._d(45))
        today_lot = self._lot(received=self._d(-90), expiry=self.today)
        alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("1"))
        self.assertEqual(alloc[0][0].pk, today_lot.pk)
        self.assertNotEqual(alloc[0][0].pk, far.pk)

    def test_f1_ac4_lo_nhap_chua_publish_khong_duoc_chon(self):
        self._lot(received=self._d(-1), expiry=self._d(3), status=Batch.Status.DRAFT)
        ok = self._lot(received=self._d(-1), expiry=self._d(45))
        alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("1"))
        self.assertEqual(alloc[0][0].pk, ok.pk)

    def test_f1_alias_allocate_fifo_van_goi_duoc_va_theo_fefo(self):
        self._lot(received=self._d(-10), expiry=self._d(60))
        b = self._lot(received=self._d(-5), expiry=self._d(20))
        alloc = batch_services.allocate_fifo(item=self.item, qty=Decimal("1"))
        self.assertEqual(alloc[0][0].pk, b.pk)


class F1BatchListApiTests(FefoBase):
    """AC8 / UC-6: danh sách Kho & lô theo thứ tự xuất FEFO; không lộ giá vốn."""

    def setUp(self):
        super().setUp()
        self.a = self._lot(received=self._d(-10), expiry=self._d(60))
        self.b = self._lot(received=self._d(-5), expiry=self._d(20))
        self.kho = User.objects.create_user("kho", password="x")
        self.kho.groups.add(Group.objects.get(name="nv_kho"))
        self.giao = User.objects.create_user("giao", password="x")
        self.giao.groups.add(Group.objects.get(name="nv_giao"))

    def _get(self, user):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client.get("/api/inventory/batches/")

    def test_f1_ac8_danh_sach_lo_theo_thu_tu_fefo_nv_kho_khong_thay_gia_von(self):
        resp = self._get(self.kho)
        self.assertEqual(resp.status_code, 200)
        rows = resp.json()["results"]
        self.assertEqual([r["id"] for r in rows], [self.b.pk, self.a.pk])
        for r in rows:
            self.assertNotIn("landed_unit_cost", r)
            self.assertNotIn("purchase_rate", r)

    def test_f1_ac8_danh_sach_lo_chua_dang_nhap_401(self):
        self.assertEqual(self._get(None).status_code, 401)
