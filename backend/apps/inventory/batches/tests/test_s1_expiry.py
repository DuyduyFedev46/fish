"""
S1 — Lô quá ngày hạn không bán được nữa (BR-LO-02, BR-BH-02/05).

Ngày ghi trên `expiry_date` là NGÀY CUỐI còn bán (C1). "Hôm nay" theo giờ
Asia/Ho_Chi_Minh. Lọc ở tầng truy vấn, KHÔNG phụ thuộc job S2.
"""
import datetime
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.exceptions import BusinessError
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesOrder, SalesOrderLineBatch
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services


class S1Base(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="X", name="Cá X", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(
            price_list=pl, item=self.item, rate=Decimal("100000"),
            valid_from=self.today - datetime.timedelta(days=60),
        )
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")

    def _batch(self, *, received, expiry, qty="5", status=Batch.Status.SELLING):
        b = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=received, qty=Decimal(qty), purchase_rate=Decimal("80000"),
        )
        b.expiry_date = expiry
        b.status = status
        b.save(update_fields=["expiry_date", "status"])
        return b

    def _ab(self):
        """Lô A cũ, hạn hôm qua (vẫn SELLING); lô B mới, hạn +10 ngày."""
        a = self._batch(
            received=self.today - datetime.timedelta(days=23),
            expiry=self.today - datetime.timedelta(days=1),
        )
        b = self._batch(
            received=self.today - datetime.timedelta(days=14),
            expiry=self.today + datetime.timedelta(days=10),
        )
        return a, b

    def _order(self, qty):
        return order_services.create_order(
            customer_phone="0900000001", customer_name="Anh A",
            delivery_address="1 Cảng", phone="0900000001",
            lines=[{"item_code": "X", "qty": Decimal(qty)}],
        )


class S1ServiceTests(S1Base):
    def test_s1_ac1_lo_qua_han_bi_bo_qua_phan_bo_lo_con_han(self):
        a, b = self._ab()
        alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("2"))
        self.assertEqual([(x.pk, q) for x, q in alloc], [(b.pk, Decimal("2"))])

        order = self._order("2")
        allocs = SalesOrderLineBatch.objects.filter(order_line__order=order)
        self.assertEqual([x.batch_id for x in allocs], [b.pk])
        a.refresh_from_db()
        self.assertEqual(a.qty_reserved, Decimal("0"))

    def test_s1_ac2_han_bang_hom_nay_van_ban(self):
        a = self._batch(
            received=self.today - datetime.timedelta(days=20), expiry=self.today,
        )
        self._batch(
            received=self.today - datetime.timedelta(days=5),
            expiry=self.today + datetime.timedelta(days=10),
        )
        alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("2"))
        self.assertEqual(alloc[0][0].pk, a.pk)
        self.assertEqual(alloc[0][1], Decimal("2"))

    def test_s1_ac3_chi_con_lo_qua_han_thi_bao_thieu_ton(self):
        a = self._batch(
            received=self.today - datetime.timedelta(days=20),
            expiry=self.today - datetime.timedelta(days=1),
        )
        with self.assertRaisesMessage(BusinessError, "Không đủ tồn khả dụng"):
            self._order("1")
        self.assertEqual(SalesOrder.objects.count(), 0)
        a.refresh_from_db()
        self.assertEqual(a.qty_reserved, Decimal("0"))

    def test_s1_ac5_nua_dem_gio_vn_la_sang_ngay_moi(self):
        d = datetime.date(2026, 9, 24)
        self._batch(received=d - datetime.timedelta(days=10), expiry=d)
        # 17:30 UTC ngày D = 00:30 ngày D+1 giờ VN
        fake_now = datetime.datetime(2026, 9, 24, 17, 30, tzinfo=datetime.timezone.utc)
        with mock.patch("django.utils.timezone.now", return_value=fake_now):
            with self.assertRaises(BusinessError):
                batch_services.allocate_fefo(item=self.item, qty=Decimal("1"))
        # Cùng thời điểm tính theo UTC vẫn là ngày D -> trước 00:00 VN (16:59 UTC) bán được
        before_midnight = datetime.datetime(2026, 9, 24, 16, 59, tzinfo=datetime.timezone.utc)
        with mock.patch("django.utils.timezone.now", return_value=before_midnight):
            alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("1"))
        self.assertEqual(alloc[0][1], Decimal("1"))

    def test_s1_sellable_batches_la_nguon_chung(self):
        a, b = self._ab()
        self.assertEqual(
            list(batch_services.sellable_batches(item=self.item).values_list("pk", flat=True)),
            [b.pk],
        )

    def test_s1_c1_don_giu_cho_truoc_nua_dem_thanh_toan_sau_van_xac_nhan(self):
        d = datetime.date(2026, 9, 24)
        lot = self._batch(received=d - datetime.timedelta(days=10), expiry=d)
        at_2350 = datetime.datetime(2026, 9, 24, 16, 50, tzinfo=datetime.timezone.utc)
        with mock.patch("django.utils.timezone.now", return_value=at_2350):
            order = self._order("2")
        at_0010 = datetime.datetime(2026, 9, 24, 17, 10, tzinfo=datetime.timezone.utc)
        with mock.patch("django.utils.timezone.now", return_value=at_0010):
            batch_services.update_batch_statuses()  # job S2 chạy lúc 00:05 cũng không phá đơn
            payment_services.confirm_payment(
                order=order, bank_txn_id="FT-C1", amount=order.total_amount,
                received_at=at_0010,
            )
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        lot.refresh_from_db()
        self.assertEqual(lot.status, Batch.Status.EXPIRED)
        self.assertEqual(lot.qty_available, Decimal("3"))
        self.assertEqual(lot.qty_reserved, Decimal("0"))


class S1ShopApiTests(S1Base):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_s1_ac4_catalog_chi_tinh_ton_lo_con_han(self):
        self._ab()
        rows = self.client.get("/api/shop/catalog/").json()
        row = next(r for r in rows if r["item_code"] == "X")
        self.assertEqual(Decimal(row["sellable_qty"]), Decimal("5"))
        detail = self.client.get("/api/shop/catalog/X/").json()
        self.assertEqual(Decimal(detail["sellable_qty"]), Decimal("5"))
        # Shop công khai không lộ giá vốn (bất biến #1)
        for key in ("landed_unit_cost", "purchase_rate", "unit_cost"):
            self.assertNotIn(key, row)
            self.assertNotIn(key, detail)

    def _post_order(self, item_extra=None, body_extra=None):
        item = {"item_code": "X", "qty": "1"}
        item.update(item_extra or {})
        body = {
            "customer": {"phone": "0912345678", "name": "Anh A"},
            "delivery_address": "1 Bến Cảng", "phone": "0912345678",
            "items": [item],
        }
        body.update(body_extra or {})
        return self.client.post("/api/shop/orders/", body, format="json")

    def test_s1_ac3_api_chi_con_lo_qua_han_tra_400(self):
        a = self._batch(
            received=self.today - datetime.timedelta(days=20),
            expiry=self.today - datetime.timedelta(days=1),
        )
        resp = self._post_order()
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("Không đủ tồn khả dụng", resp.json()["detail"])
        self.assertEqual(SalesOrder.objects.count(), 0)
        a.refresh_from_db()
        self.assertEqual(a.qty_reserved, Decimal("0"))

    def test_s1_ac6_khach_khong_chon_duoc_lo(self):
        a, b = self._ab()
        resp = self._post_order(
            item_extra={"batch": a.pk, "batch_id": a.batch_id},
            body_extra={"batch": a.pk},
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        allocs = SalesOrderLineBatch.objects.all()
        self.assertEqual([x.batch_id for x in allocs], [b.pk])
        a.refresh_from_db()
        self.assertEqual(a.qty_reserved, Decimal("0"))
