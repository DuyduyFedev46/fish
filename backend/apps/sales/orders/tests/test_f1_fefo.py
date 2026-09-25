"""
F1 — FEFO ở luồng bán (doc/features/2026-09-26-fefo): tạo đơn, combo, thanh toán không chọn
lại lô (BR-BH-11), hàng về kho trả lô gốc (BR-HV-01, BR-HT-05), Shop/Tổng quan (AC8).
"""
import datetime
from decimal import Decimal

from django.utils import timezone

from apps.catalog.models import BundleLine, Item
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery import services as delivery_services
from apps.delivery.models import DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, ReturnToStock
from apps.inventory.returns import services as return_services
from apps.sales.models import SalesInvoiceLineBatch, SalesOrder, SalesOrderLineBatch
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.base import SalesServiceBase
from apps.sales.payments import services as payment_services

COST_KEYS = {"inventory_value", "unit_cost", "landed_unit_cost", "purchase_rate", "rate", "cost"}


class F1FefoSalesBase(SalesServiceBase):
    def _d(self, days):
        return self.today + datetime.timedelta(days=days)

    def _lot(self, item, qty, *, received, expiry, rate="80000"):
        """Lô đang bán; hạn chỉ định (vd NV kho sửa hạn xuống lúc nhập, BR-MH-02)."""
        b = batch_services.create_batch(
            item=item, supplier=self.sup, warehouse=self.wh, received_date=received,
            qty=Decimal(qty), purchase_rate=Decimal(rate),
        )
        batch_services.publish_batch(batch=b, actor=None)
        Batch.objects.filter(pk=b.pk).update(expiry_date=expiry)
        b.refresh_from_db()
        return b

    def _order(self, code, qty, phone="0900000901"):
        return order_services.create_order(
            customer_phone=phone, customer_name="Khách F1", delivery_address="1 Cảng",
            phone=phone, lines=[{"item_code": code, "qty": Decimal(qty)}],
        )

    @staticmethod
    def _alloc(order):
        return [(a.batch_id, a.qty) for a in
                SalesOrderLineBatch.objects.filter(order_line__order=order).order_by("id")]


class F1CreateOrderTests(F1FefoSalesBase):
    def test_f1_ac1_khach_dat_1kg_phan_bo_lo_han_som_du_nhap_sau(self):
        ca = self._item("F1A", price="100000")
        a = self._lot(ca, "10", received=self._d(-25), expiry=self._d(65))  # "01/09 hạn 30/11"
        b = self._lot(ca, "10", received=self._d(-21), expiry=self._d(24))  # "05/09 hạn 20/10"
        order = self._order("F1A", "1")
        self.assertEqual(self._alloc(order), [(b.pk, Decimal("1"))])
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual((a.qty_reserved, b.qty_reserved), (Decimal("0"), Decimal("1")))

    def test_f1_ac2_cung_han_lo_nhap_som_hon_ra_truoc(self):
        ca = self._item("F1B", price="100000")
        later = self._lot(ca, "5", received=self._d(-1), expiry=self._d(30))
        earlier = self._lot(ca, "5", received=self._d(-6), expiry=self._d(30))
        order = self._order("F1B", "6")
        self.assertEqual(self._alloc(order), [(earlier.pk, Decimal("5")), (later.pk, Decimal("1"))])

    def test_f1_ac3_don_vuot_ton_lo_han_som_lay_tiep_lo_han_ke(self):
        ca = self._item("F1C", price="100000")
        far = self._lot(ca, "10", received=self._d(-20), expiry=self._d(70))
        soon = self._lot(ca, "3", received=self._d(-2), expiry=self._d(8))
        mid = self._lot(ca, "4", received=self._d(-1), expiry=self._d(40))
        order = self._order("F1C", "9")
        self.assertEqual(self._alloc(order),
                         [(soon.pk, Decimal("3")), (mid.pk, Decimal("4")), (far.pk, Decimal("2"))])

    def test_f1_ac4_lo_qua_han_han_som_nhat_khong_duoc_chon(self):
        ca = self._item("F1D", price="100000")
        expired = self._lot(ca, "50", received=self._d(-40), expiry=self._d(-1))  # job chưa chạy
        ok = self._lot(ca, "5", received=self._d(-1), expiry=self._d(60))
        order = self._order("F1D", "2")
        self.assertEqual(self._alloc(order), [(ok.pk, Decimal("2"))])
        expired.refresh_from_db()
        self.assertEqual(expired.qty_reserved, Decimal("0"))

    def test_f1_ac5_combo_moi_thanh_phan_tu_chon_lo_fefo(self):
        tom = self._item("F1TOM")
        muc = self._item("F1MUC")
        tom_old = self._lot(tom, "10", received=self._d(-9), expiry=self._d(50))
        tom_soon = self._lot(tom, "10", received=self._d(-2), expiry=self._d(12))
        muc_soon = self._lot(muc, "10", received=self._d(-9), expiry=self._d(15))
        muc_late = self._lot(muc, "10", received=self._d(-2), expiry=self._d(80))
        combo = self._item("F1SET", price="500000", item_type=Item.ItemType.BUNDLE)
        BundleLine.objects.create(bundle=combo, component=tom, qty_per_bundle=Decimal("1"))
        BundleLine.objects.create(bundle=combo, component=muc, qty_per_bundle=Decimal("0.5"))
        order = self._order("F1SET", "2")
        by_component = {
            a.component_item_id: (a.batch_id, a.qty)
            for a in SalesOrderLineBatch.objects.filter(order_line__order=order)
        }
        self.assertEqual(by_component[tom.pk], (tom_soon.pk, Decimal("2")))
        self.assertEqual(by_component[muc.pk], (muc_soon.pk, Decimal("1.0")))
        for lot in (tom_old, muc_late):
            lot.refresh_from_db()
            self.assertEqual(lot.qty_reserved, Decimal("0"))


class F1PaymentKeepsReservedBatchTests(F1FefoSalesBase):
    def test_f1_ac6_nhap_lo_han_som_hon_sau_khi_giu_cho_thanh_toan_van_tru_lo_da_giu(self):
        ca = self._item("F1E", price="100000")
        held = self._lot(ca, "10", received=self._d(-3), expiry=self._d(60))
        order = self._order("F1E", "3")
        self.assertEqual(self._alloc(order), [(held.pk, Decimal("3"))])
        # Sau khi giữ chỗ, nhập thêm một lô hạn SỚM HƠN -> FEFO sẽ chọn lô này cho đơn MỚI.
        newer = self._lot(ca, "10", received=self.today, expiry=self._d(5))
        chu = make_user("loc", "chu")
        payment_services.confirm_payment_manual(order=order, bank_txn_id="F1-AC6", actor=chu)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        inv_alloc = [(x.batch_id, x.qty) for x in
                     SalesInvoiceLineBatch.objects.filter(invoice_line__invoice=order.invoice)]
        self.assertEqual(inv_alloc, [(held.pk, Decimal("3"))])  # BR-BH-11: không chọn lại
        held.refresh_from_db()
        newer.refresh_from_db()
        self.assertEqual((held.qty_available, held.qty_reserved), (Decimal("7"), Decimal("0")))
        self.assertEqual((newer.qty_available, newer.qty_reserved), (Decimal("10"), Decimal("0")))
        # Đơn mới sau đó mới đi lô hạn sớm hơn.
        self.assertEqual(self._alloc(self._order("F1E", "1", phone="0900000902")),
                         [(newer.pk, Decimal("1"))])


class F1ReturnToOriginalBatchTests(F1FefoSalesBase):
    def setUp(self):
        super().setUp()
        self.ca = self._item("F1R", price="100000")
        self.old_far = self._lot(self.ca, "10", received=self._d(-20), expiry=self._d(70))
        self.soon = self._lot(self.ca, "10", received=self._d(-2), expiry=self._d(10))
        self.order = self._order("F1R", "4")
        payment_services.confirm_payment(order=self.order, bank_txn_id="F1-AC7",
                                         amount=self.order.total_amount,
                                         received_at=timezone.now())
        self.order.refresh_from_db()

    def _state(self, lot):
        lot.refresh_from_db()
        return lot.qty_available, lot.expiry_date

    def test_f1_ac7_huy_don_da_thanh_toan_tra_ve_lo_goc_giu_han(self):
        self.assertEqual(self._state(self.soon), (Decimal("6"), self._d(10)))
        order_services.cancel_paid_order(order=self.order, actor=None, reason="F1-AC7")
        self.assertEqual(self._state(self.soon), (Decimal("10"), self._d(10)))
        self.assertEqual(self._state(self.old_far), (Decimal("10"), self._d(70)))
        self.assertEqual(Batch.objects.filter(item=self.ca).count(), 2)  # không sinh lô mới

    def test_f1_ac7_hang_giao_that_bai_tai_nhap_ve_lo_goc_giu_han(self):
        giao = make_user("giao1", "nv_giao")
        ql = make_user("ql1", "quan_ly")
        note = DeliveryNote.objects.get(sales_invoice=self.order.invoice)
        for st in (DeliveryNote.Status.READY, DeliveryNote.Status.DELIVERING):
            delivery_services.advance_status(note=note, to_status=st, actor=giao)
        delivery_services.mark_failed(note=note, actor=giao)
        rt = delivery_services.return_to_warehouse(note=note, batch=self.soon,
                                                   qty=Decimal("4"), actor=giao)
        rt.decision = ReturnToStock.Decision.RESTOCK
        rt.save(update_fields=["decision"])
        return_services.apply_return(return_to_stock=rt, approver=ql)
        self.assertEqual(self._state(self.soon), (Decimal("10"), self._d(10)))
        self.assertEqual(self._state(self.old_far), (Decimal("10"), self._d(70)))
        # Hàng hoàn không "làm mới" hạn: đơn sau vẫn gặp lô gốc theo đúng vị trí hạn của nó.
        self.assertEqual(self._alloc(self._order("F1R", "1", phone="0900000903")),
                         [(self.soon.pk, Decimal("1"))])


class F1ShopAndDashboardTests(F1FefoSalesBase):
    """AC8: tồn bán được không đổi (chỉ đổi thứ tự lô); Tổng quan sắp theo thứ tự xuất; không rò giá vốn."""

    def setUp(self):
        super().setUp()
        self.ca = self._item("F1S", price="100000")
        self.a = self._lot(self.ca, "10", received=self._d(-25), expiry=self._d(65))
        self.b = self._lot(self.ca, "7", received=self._d(-21), expiry=self._d(24))
        self._lot(self.ca, "50", received=self._d(-60), expiry=self._d(-1))  # quá hạn: không tính
        self._order("F1S", "2")

    def test_f1_ac8_shop_ton_ban_duoc_khong_doi(self):
        resp = client_for(None).get("/api/shop/catalog/")
        self.assertEqual(resp.status_code, 200)
        row = next(r for r in resp.json() if r["item_code"] == "F1S")
        self.assertEqual(Decimal(row["sellable_qty"]), Decimal("15"))  # 10 + 7 − 2 giữ chỗ
        self.assertEqual(set(row) & COST_KEYS, set())

    def test_f1_ac8_tong_quan_ton_theo_lo_sap_theo_thu_tu_xuat(self):
        body = client_for(make_user("loc", "chu")).get("/api/dashboard/summary/").json()
        wanted = {self.a.batch_id, self.b.batch_id}
        ids = [r["batch_id"] for r in body["batches"] if r["batch_id"] in wanted]
        self.assertEqual(ids, [self.b.batch_id, self.a.batch_id])  # b nhập sau nhưng hạn sớm hơn

    def test_f1_ac8_tong_quan_nv_kho_khong_thay_gia_von(self):
        resp = client_for(make_user("kho1", "nv_kho")).get("/api/dashboard/summary/")
        self.assertEqual(resp.status_code, 200)
        for row in resp.json()["batches"]:
            self.assertEqual(set(row) & COST_KEYS, set())

    def test_f1_ac8_tong_quan_nv_giao_403(self):
        resp = client_for(make_user("giao1", "nv_giao")).get("/api/dashboard/summary/")
        self.assertEqual(resp.status_code, 403)
