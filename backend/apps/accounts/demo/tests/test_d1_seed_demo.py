"""
D1 (Duy 2026-09-24) — dữ liệu demo trên hệ thống thật: thêm được, gỡ sạch được, thêm lại được.

- `manage.py seed_demo`            thêm (idempotent), mọi bản ghi seed TẠO MỚI được ghi vào
                                   sổ đánh dấu `DemoRecord` (kể cả bản ghi do signal sinh ra).
- `manage.py seed_demo --remove`   gỡ CHỈ bản ghi có trong sổ; bản ghi dữ liệu thật đang tham
                                   chiếu tới thì giữ lại (báo "giữ lại"), không xoá lan sang
                                   dữ liệu thật. Ngoại lệ có chủ đích của BR-PQ-10 (chỉ cho demo).
- `--dry-run`                      liệt kê, không xoá.
- `--adopt-legacy`                 nhận diện dữ liệu demo đã seed bằng bản cũ (chưa có sổ) theo
                                   chữ ký chính xác (mã + tên/SĐT) rồi mới gỡ.
"""
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import AuditLog, DemoRecord
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.delivery.models import DeliveryNote
from apps.inventory.models import Batch, StockLedgerEntry, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesInvoice, SalesOrder, SalesOrderLine

DEMO_ITEM_CODES = ["CA-THU", "TOM-SU-1", "MUC-ONG", "CA-HOI-NU", "GHE-XANH", "BACH-TUOC"]
DEMO_BATCH_IDS = ["LO-0912", "LO-0907", "LO-0903", "LO-0915", "LO-0918", "LO-0921", "LO-0922"]
DEMO_ORDER_CODES = [
    "DH-2609-118", "DH-2609-117", "DH-2609-116", "DH-2609-119", "DH-2609-115", "DH-2609-114",
]
MODELS = (Item, ItemGroup, ItemPrice, PriceList, Warehouse, Supplier, Batch, StockLedgerEntry,
          Customer, SalesOrder, SalesOrderLine, SalesInvoice, DeliveryNote)


def run(*args):
    out = StringIO()
    call_command("seed_demo", *args, stdout=out)
    return out.getvalue()


def snapshot():
    return {m.__name__: set(m.objects.values_list("pk", flat=True)) for m in MODELS}


def make_real_data():
    """Dữ liệu thật có trước: kho + bảng giá (bootstrap), 1 mặt hàng, 1 lô, 1 khách, 1 đơn + HĐ."""
    wh = Warehouse.objects.create(name="Kho chính")
    pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
    grp = ItemGroup.objects.create(name="Cá biển")
    item = Item.objects.create(code="REAL-01", name="Cá bớp thật", item_group=grp)
    ItemPrice.objects.create(price_list=pl, item=item, rate=Decimal("200000"),
                             valid_from=timezone.localdate() - timedelta(days=5))
    sup = Supplier.objects.create(name="Vựa thật")
    batch = Batch.objects.create(
        batch_id="REAL-LO-1", item=item, supplier=sup, warehouse=wh,
        received_date=timezone.localdate(), expiry_date=timezone.localdate() + timedelta(days=5),
        qty_received=Decimal("10"), qty_available=Decimal("10"), qty_reserved=Decimal("0"),
        purchase_rate=Decimal("150000"), landed_unit_cost=Decimal("150000"),
        status=Batch.Status.SELLING,
    )
    StockLedgerEntry.objects.create(batch=batch, movement_type="RECEIPT",
                                    qty_change=Decimal("10"), reference="Nhập lô REAL-LO-1")
    cust = Customer.objects.create(phone="0900000001", name="Khách thật", default_address="HCM")
    order = SalesOrder.objects.create(code="DH-REAL-1", customer=cust,
                                      status=SalesOrder.Status.PROCESSING,
                                      delivery_address="HCM", phone="0900000001",
                                      total_amount=Decimal("200000"))
    SalesOrderLine.objects.create(order=order, item=item, qty=Decimal("1"),
                                  rate=Decimal("200000"), amount=Decimal("200000"))
    SalesInvoice.objects.create(code="HD-REAL-1", sales_order=order, customer=cust,
                                issued_at=timezone.now(), amount=Decimal("200000"),
                                payment_method="VIETQR")
    return item


class D1SeedTests(TestCase):
    def test_d1_seed_tao_du_lieu_va_danh_dau_moi_ban_ghi_tao_moi(self):
        run()
        self.assertEqual(
            set(Item.objects.values_list("code", flat=True)), set(DEMO_ITEM_CODES)
        )
        self.assertEqual(Batch.objects.count(), 7)
        self.assertEqual(SalesOrder.objects.count(), 6)
        self.assertEqual(SalesInvoice.objects.count(), 3)
        # Phiếu giao do signal sinh cũng được đánh dấu.
        self.assertEqual(DeliveryNote.objects.count(), 3)
        for model in MODELS:
            with self.subTest(model=model.__name__):
                marked = DemoRecord.objects.filter(
                    content_type__model=model._meta.model_name
                ).count()
                self.assertEqual(marked, model.objects.count())

    def test_d1_seed_chay_lai_khong_nhan_doi(self):
        run()
        before, marks = snapshot(), DemoRecord.objects.count()
        run()
        self.assertEqual(snapshot(), before)
        self.assertEqual(DemoRecord.objects.count(), marks)

    def test_d1_seed_khong_danh_dau_du_lieu_that_co_san(self):
        make_real_data()
        real = snapshot()
        run()
        for model in MODELS:
            ids = real[model.__name__]
            marked = DemoRecord.objects.filter(
                content_type__model=model._meta.model_name, object_id__in=[str(i) for i in ids]
            )
            self.assertFalse(marked.exists(), model.__name__)


class D1RemoveTests(TestCase):
    def test_d1_remove_go_sach_demo_giu_nguyen_du_lieu_that(self):
        make_real_data()
        real = snapshot()
        run()
        out = run("--remove")
        self.assertEqual(snapshot(), real)
        self.assertFalse(DemoRecord.objects.exists())
        self.assertFalse(Item.objects.filter(code__in=DEMO_ITEM_CODES).exists())
        self.assertFalse(SalesOrder.objects.filter(code__in=DEMO_ORDER_CODES).exists())
        self.assertIn("Đã gỡ", out)

    def test_d1_remove_roi_seed_lai_duoc(self):
        run()
        first = {m.__name__: m.objects.count() for m in MODELS}
        run("--remove")
        self.assertEqual(Batch.objects.count(), 0)
        run()
        self.assertEqual({m.__name__: m.objects.count() for m in MODELS}, first)
        self.assertEqual(set(Batch.objects.values_list("batch_id", flat=True)),
                         set(DEMO_BATCH_IDS))

    def test_d1_remove_chay_hai_lan_khong_loi(self):
        run()
        run("--remove")
        out = run("--remove")
        self.assertIn("Đã gỡ 0", out)

    def test_d1_remove_giu_ban_ghi_demo_ma_du_lieu_that_dang_dung(self):
        # Người dùng tạo lô THẬT cho mặt hàng demo "Cá thu" → mặt hàng đó phải giữ lại.
        run()
        ca_thu = Item.objects.get(code="CA-THU")
        wh = Warehouse.objects.get()
        sup = Supplier.objects.create(name="Vựa thật")
        real_batch = Batch.objects.create(
            batch_id="REAL-LO-9", item=ca_thu, supplier=sup, warehouse=wh,
            received_date=timezone.localdate(),
            expiry_date=timezone.localdate() + timedelta(days=5),
            qty_received=Decimal("5"), qty_available=Decimal("5"), qty_reserved=Decimal("0"),
            purchase_rate=Decimal("1"), landed_unit_cost=Decimal("1"),
            status=Batch.Status.DRAFT,
        )
        out = run("--remove")
        self.assertTrue(Batch.objects.filter(pk=real_batch.pk).exists())
        self.assertTrue(Item.objects.filter(pk=ca_thu.pk).exists())
        self.assertTrue(Warehouse.objects.filter(pk=wh.pk).exists())
        self.assertFalse(Batch.objects.filter(batch_id__in=DEMO_BATCH_IDS).exists())
        self.assertFalse(Item.objects.filter(code="MUC-ONG").exists())
        self.assertIn("Giữ lại", out)
        self.assertIn("CA-THU", out)
        # Vẫn còn đánh dấu → lần sau hết bị dùng thì gỡ tiếp được.
        self.assertTrue(DemoRecord.objects.filter(object_id=str(ca_thu.pk),
                                                  content_type__model="item").exists())

    def test_d1_remove_khong_xoa_lan_sang_ban_ghi_that_qua_cascade(self):
        # Dòng đơn THẬT gắn vào đơn demo (CASCADE) → đơn demo phải giữ, dòng thật không mất.
        run()
        order = SalesOrder.objects.get(code="DH-2609-119")
        real_line = SalesOrderLine.objects.create(
            order=order, item=Item.objects.get(code="CA-THU"), qty=Decimal("1"),
            rate=Decimal("1"), amount=Decimal("1"),
        )
        run("--remove")
        self.assertTrue(SalesOrderLine.objects.filter(pk=real_line.pk).exists())
        self.assertTrue(SalesOrder.objects.filter(pk=order.pk).exists())
        self.assertFalse(SalesOrder.objects.filter(code="DH-2609-118").exists())

    def test_d1_remove_dry_run_khong_xoa(self):
        run()
        before = snapshot()
        out = run("--remove", "--dry-run")
        self.assertEqual(snapshot(), before)
        self.assertIn("Chạy thử", out)

    def test_d1_remove_ghi_audit_khong_xoa_audit(self):
        AuditLog.objects.create(action="truoc_demo")
        run()
        run("--remove")
        self.assertTrue(AuditLog.objects.filter(action="truoc_demo").exists())
        self.assertTrue(AuditLog.objects.filter(action="demo_remove").exists())


class D1LegacyTests(TestCase):
    def seed_legacy(self):
        """Giả lập DB production đã seed bằng bản cũ: có dữ liệu demo nhưng chưa có sổ đánh dấu."""
        run()
        DemoRecord.objects.all().delete()

    def test_d1_legacy_khong_adopt_thi_khong_go_gi(self):
        self.seed_legacy()
        before = snapshot()
        run("--remove")
        self.assertEqual(snapshot(), before)

    def test_d1_legacy_adopt_go_theo_chu_ky(self):
        real_item = make_real_data()
        self.seed_legacy()
        run("--remove", "--adopt-legacy")
        self.assertFalse(Item.objects.filter(code__in=DEMO_ITEM_CODES).exists())
        self.assertFalse(Batch.objects.filter(batch_id__in=DEMO_BATCH_IDS).exists())
        self.assertFalse(SalesOrder.objects.filter(code__in=DEMO_ORDER_CODES).exists())
        self.assertFalse(Supplier.objects.filter(name="Vựa Ba Hòn").exists())
        # Dữ liệu thật còn nguyên; tên chung (kho, bảng giá, nhóm) không bao giờ bị nhận nhầm.
        self.assertTrue(Item.objects.filter(pk=real_item.pk).exists())
        self.assertTrue(SalesOrder.objects.filter(code="DH-REAL-1").exists())
        self.assertTrue(Warehouse.objects.filter(name="Kho chính").exists())
        self.assertTrue(PriceList.objects.filter(name="Bán lẻ").exists())

    def test_d1_legacy_khong_nhan_mat_hang_that_trung_ma_khac_ten(self):
        grp = ItemGroup.objects.create(name="Cá")
        real = Item.objects.create(code="CA-THU", name="Cá thu Phan Thiết", item_group=grp)
        self.seed_legacy()
        run("--remove", "--adopt-legacy")
        self.assertTrue(Item.objects.filter(pk=real.pk).exists())


# --- Sửa lỗi QA lần 2 — B2 (Medium) + B5 (Low) --------------------------------------------
# B2: bản ghi demo bị GIỮ LẠI vì dữ liệu thật dùng thì mọi bản ghi demo là "một phần" của nó
# (giá của mặt hàng, sổ kho của lô, dòng đơn/hoá đơn, giữ chỗ/phân bổ lô, hoá đơn/phiếu giao/
# thanh toán của đơn) cũng phải giữ — chứng từ giữ nguyên cả cụm hoặc gỡ cả cụm.
# B5: --adopt-legacy không gỡ phiếu giao đã bắt đầu (khác PREPARING hoặc đã gán người giao).

CATALOG = "/api/shop/catalog/"


def real_selling_batch(item, batch_id="LO-THAT-1", qty="10"):
    """Lô THẬT đang bán trên mặt hàng `item` (có bút toán nhập thật)."""
    sup, _ = Supplier.objects.get_or_create(name="Vựa thật B2")
    batch = Batch.objects.create(
        batch_id=batch_id, item=item, supplier=sup, warehouse=Warehouse.objects.first(),
        received_date=timezone.localdate(),
        expiry_date=timezone.localdate() + timedelta(days=5),
        qty_received=Decimal(qty), qty_available=Decimal(qty), qty_reserved=Decimal("0"),
        purchase_rate=Decimal("150000"), landed_unit_cost=Decimal("150000"),
        status=Batch.Status.SELLING,
    )
    StockLedgerEntry.objects.create(batch=batch, movement_type="RECEIPT",
                                    qty_change=Decimal(qty), reference=f"Nhập lô {batch_id}")
    return batch


def real_order(item_code, qty="1", phone="0911222333"):
    from apps.sales.orders import services as order_services
    return order_services.create_order(
        customer_phone=phone, customer_name="Khách thật", delivery_address="Q3",
        phone=phone, lines=[{"item_code": item_code, "qty": Decimal(qty)}],
    )


def children_snapshot():
    """Con của từng cha còn sống: giá/mặt hàng, sổ kho/lô, dòng/đơn, dòng/HĐ, phiếu giao/HĐ."""
    from apps.sales.models import SalesInvoiceLine, SalesOrderLineBatch
    return {
        "price": {i.pk: set(ItemPrice.objects.filter(item=i).values_list("pk", flat=True))
                  for i in Item.objects.all()},
        "ledger": {b.pk: set(b.ledger_entries.values_list("pk", flat=True))
                   for b in Batch.objects.all()},
        "reserve": {b.pk: set(SalesOrderLineBatch.objects.filter(batch=b)
                              .values_list("pk", flat=True)) for b in Batch.objects.all()},
        "order_lines": {o.pk: set(o.lines.values_list("pk", flat=True))
                        for o in SalesOrder.objects.all()},
        "invoice": {o.pk: set(SalesInvoice.objects.filter(sales_order=o)
                              .values_list("pk", flat=True)) for o in SalesOrder.objects.all()},
        "invoice_lines": {v.pk: set(SalesInvoiceLine.objects.filter(invoice=v)
                                    .values_list("pk", flat=True))
                          for v in SalesInvoice.objects.all()},
        "notes": {v.pk: set(v.delivery_notes.values_list("pk", flat=True))
                  for v in SalesInvoice.objects.all()},
    }


class B2ClosureTests(TestCase):
    """Kịch bản A của QA (d1/runA.sh): DB có sổ đánh dấu."""

    def setUp(self):
        run()

    def assert_khong_go_nua_chung(self, before):
        """Mọi cha còn sống sau khi gỡ phải còn đủ con như trước khi gỡ."""
        after = children_snapshot()
        for kind, parents in after.items():
            for pk, kids in parents.items():
                with self.subTest(kind=kind, parent=pk):
                    self.assertEqual(kids, before[kind].get(pk), f"{kind} của #{pk} bị gỡ nửa chừng")

    def test_b2_lo_that_tren_mat_hang_demo_van_ban_duoc_sau_remove(self):
        muc = Item.objects.get(code="MUC-ONG")
        real_selling_batch(muc)
        before = children_snapshot()
        out = run("--remove")
        self.assert_khong_go_nua_chung(before)
        self.assertTrue(ItemPrice.objects.filter(item=muc).exists(), out)
        resp = self.client.get(CATALOG)
        codes = {d["item_code"]: d for d in resp.json()}
        self.assertIn("MUC-ONG", codes, out)
        self.assertEqual(Decimal(codes["MUC-ONG"]["price"]), Decimal("235000"))
        self.assertEqual(Decimal(codes["MUC-ONG"]["sellable_qty"]), Decimal("10"))
        order = real_order("MUC-ONG", "2")
        self.assertEqual(order.lines.count(), 1)
        self.assertIn("Giá niêm yết", out)  # báo rõ giá được giữ

    def test_b2_lo_demo_co_don_that_giu_cho_so_kho_con_nguyen(self):
        real_order("GHE-XANH", "1")  # giữ chỗ trên lô demo LO-0921
        lot = Batch.objects.get(batch_id="LO-0921")
        before = children_snapshot()
        run("--remove")
        self.assert_khong_go_nua_chung(before)
        lot.refresh_from_db()
        entries = lot.ledger_entries.all()
        self.assertTrue(entries.filter(movement_type="RECEIPT",
                                       reference="Nhập lô LO-0921").exists())
        # Sổ kho còn đủ: Σ bút toán = tồn thực (R4: demo có cả SALE của đơn đã bán trên lô).
        self.assertEqual(sum(e.qty_change for e in entries), lot.qty_available)
        self.assertEqual(sum(e.qty_change for e in entries if e.movement_type == "RECEIPT"),
                         lot.qty_received)
        # Mặt hàng của lô bị giữ còn giá → vẫn bán tiếp được phần còn lại.
        self.assertTrue(ItemPrice.objects.filter(item=lot.item).exists())

    def test_b2_don_demo_bi_giu_con_du_dong_va_ca_cum_chung_tu(self):
        # Dòng đơn thật gắn vào đơn demo có hoá đơn + phiếu giao → giữ cả cụm đơn/HĐ/phiếu giao.
        order = SalesOrder.objects.get(code="DH-2609-118")
        SalesOrderLine.objects.create(order=order, item=Item.objects.get(code="CA-THU"),
                                      qty=Decimal("1"), rate=Decimal("1"), amount=Decimal("1"))
        before = children_snapshot()
        run("--remove")
        self.assert_khong_go_nua_chung(before)
        self.assertEqual(order.lines.count(), 2)
        inv = SalesInvoice.objects.get(sales_order=order)
        self.assertEqual(inv.delivery_notes.count(), 1)

    def test_b2_dry_run_in_dung_danh_sach_giu_lai_nhu_lan_chay_that(self):
        real_selling_batch(Item.objects.get(code="MUC-ONG"))
        real_order("GHE-XANH", "1")
        dry = run("--remove", "--dry-run")
        real = run("--remove")
        self.assertIn("Giữ lại", real)
        self.assertEqual(dry.replace("Chạy thử (không xoá gì): ", ""), real)

    def test_b2_go_lai_sau_khi_du_lieu_that_het_dung(self):
        # Hết dữ liệu thật dùng → lần gỡ sau gỡ nốt được cả cụm đã giữ.
        batch = real_selling_batch(Item.objects.get(code="MUC-ONG"))
        run("--remove")
        StockLedgerEntry.objects.filter(batch=batch).delete()
        batch.delete()
        run("--remove")
        self.assertFalse(Item.objects.filter(code="MUC-ONG").exists())
        self.assertFalse(DemoRecord.objects.exists())


class B2LegacyClosureTests(TestCase):
    """Kịch bản B của QA (d1/runB.sh): DB seed bằng bản cũ, gỡ bằng --adopt-legacy."""

    def setUp(self):
        run()
        DemoRecord.objects.all().delete()

    def test_b2_legacy_mat_hang_giu_lai_van_con_gia_shop_ban_duoc(self):
        ca_thu = Item.objects.get(code="CA-THU")
        real_selling_batch(ca_thu, "LO-QA-EXP")
        before = children_snapshot()
        run("--remove", "--adopt-legacy")
        self.assert_khong_go_nua_chung(before)
        detail = self.client.get(f"{CATALOG}CA-THU/").json()
        self.assertEqual(Decimal(detail["price"]), Decimal("165000"))
        self.assertIn("CA-THU", {d["item_code"] for d in self.client.get(CATALOG).json()})
        real_order("CA-THU", "1")

    def test_b2_legacy_don_that_da_thanh_toan_con_du_dong(self):
        from apps.sales.models import PaymentTransaction
        from apps.sales.payments import services as payment_services
        order = SalesOrder.objects.get(code="DH-2609-116")
        payment_services.confirm_payment(
            order=order, bank_txn_id="REAL-TXN-777", amount=order.total_amount,
            received_at=timezone.now(), source=PaymentTransaction.Source.WEBHOOK, raw_payload={},
        )
        before = children_snapshot()
        run("--remove", "--adopt-legacy")
        self.assert_khong_go_nua_chung(before)
        order.refresh_from_db()
        self.assertEqual(order.lines.count(), 1)
        self.assertEqual(sum(line.amount for line in order.lines.all()), order.total_amount)

    def test_b2_legacy_dry_run_khop_lan_chay_that(self):
        real_selling_batch(Item.objects.get(code="CA-THU"), "LO-QA-EXP")
        real_order("GHE-XANH", "1")
        dry = run("--remove", "--adopt-legacy", "--dry-run")
        self.assertFalse(DemoRecord.objects.exists())  # dry-run hoàn tác cả bước nhận legacy
        real = run("--remove", "--adopt-legacy")
        self.assertEqual(dry.replace("Chạy thử (không xoá gì): ", ""), real)

    def assert_khong_go_nua_chung(self, before):
        B2ClosureTests.assert_khong_go_nua_chung(self, before)


class B5AdoptDeliveryNoteTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        run()
        DemoRecord.objects.all().delete()
        self.giao = User.objects.create_user("giao2", password="x")

    def test_b5_adopt_khong_go_phieu_giao_dang_giao(self):
        inv = SalesInvoice.objects.get(code="HD-2609-118")
        note = inv.delivery_notes.get()
        note.status = DeliveryNote.Status.DELIVERING
        note.assigned_to = self.giao
        note.save()
        other = SalesInvoice.objects.get(code="HD-2609-117")
        dry = run("--remove", "--adopt-legacy", "--dry-run")
        self.assertIn(note.code, dry)  # được báo trong danh sách giữ lại
        run("--remove", "--adopt-legacy")
        self.assertTrue(DeliveryNote.objects.filter(pk=note.pk).exists())
        # Cả cụm chứng từ của phiếu đang giao còn nguyên.
        self.assertTrue(SalesInvoice.objects.filter(pk=inv.pk).exists())
        self.assertEqual(SalesOrder.objects.get(code="DH-2609-118").lines.count(), 1)
        # Phiếu chưa bắt đầu trên hoá đơn demo khác vẫn được gỡ cùng cụm.
        self.assertFalse(SalesInvoice.objects.filter(pk=other.pk).exists())

    def test_b5_adopt_khong_go_phieu_giao_da_gan_nguoi_giao(self):
        inv = SalesInvoice.objects.get(code="HD-2609-117")
        note = inv.delivery_notes.get()
        note.status = DeliveryNote.Status.READY
        note.assigned_to = self.giao
        note.save()
        run("--remove", "--adopt-legacy")
        self.assertTrue(DeliveryNote.objects.filter(pk=note.pk).exists())
        self.assertTrue(SalesInvoice.objects.filter(pk=inv.pk).exists())

    def test_b5_adopt_van_go_phieu_giao_chua_bat_dau(self):
        run("--remove", "--adopt-legacy")
        self.assertFalse(DeliveryNote.objects.exists())


# --- Sửa theo code review trước deploy 1 — R4: dữ liệu demo tự nhất quán ---------------------
# Đơn BOOKED demo giữ chỗ bằng SalesOrderLineBatch thật (tồn giữ chỗ = Σ phân bổ); đơn đã thanh
# toán có giao dịch khớp + hoá đơn đủ dòng + phân bổ lô + bút toán SALE (BR-BH-06, BR-TT-06);
# job TTL huỷ đơn demo nhả đúng; doanh thu/giá vốn báo cáo khớp hoá đơn.

class R4SeedConsistencyTests(TestCase):
    def setUp(self):
        run()

    def test_r4_ton_giu_cho_bang_tong_phan_bo_cua_don_booked(self):
        from apps.sales.models import SalesOrderLineBatch
        booked = SalesOrder.objects.filter(code__in=DEMO_ORDER_CODES, status="BOOKED")
        self.assertEqual(booked.count(), 2)
        for order in booked:
            for line in order.lines.all():
                with self.subTest(order=order.code):
                    self.assertEqual(
                        sum(a.qty for a in line.batch_allocations.all()), line.qty)
        for batch in Batch.objects.filter(batch_id__in=DEMO_BATCH_IDS):
            with self.subTest(batch=batch.batch_id):
                alloc = SalesOrderLineBatch.objects.filter(
                    batch=batch, order_line__order__status="BOOKED")
                self.assertEqual(batch.qty_reserved, sum((a.qty for a in alloc), Decimal("0")))
                # Sổ kho khớp tồn: Σ bút toán = tồn thực; nhập = bút toán RECEIPT.
                entries = batch.ledger_entries.all()
                self.assertEqual(sum(e.qty_change for e in entries), batch.qty_available)
                self.assertEqual(sum(e.qty_change for e in entries
                                     if e.movement_type == "RECEIPT"), batch.qty_received)
                self.assertGreaterEqual(batch.qty_available, batch.qty_reserved)

    def test_r4_don_da_thanh_toan_co_hoa_don_du_dong_phan_bo_va_but_toan(self):
        from apps.sales.models import PaymentTransaction, SalesInvoiceLineBatch
        paid = SalesOrder.objects.filter(code__in=DEMO_ORDER_CODES,
                                         status__in=["PAID", "PROCESSING", "COMPLETED"])
        self.assertEqual(paid.count(), 3)
        for order in paid:
            with self.subTest(order=order.code):
                inv = order.invoice
                self.assertEqual(inv.code, order.code.replace("DH", "HD"))
                lines = list(inv.lines.all())
                self.assertEqual(len(lines), order.lines.count())
                self.assertEqual(sum(li.amount for li in lines), inv.amount)
                self.assertEqual(inv.amount, order.total_amount)
                for li in lines:
                    allocs = SalesInvoiceLineBatch.objects.filter(invoice_line=li)
                    self.assertEqual(sum(a.qty for a in allocs), li.qty)
                    self.assertTrue(all(a.unit_cost > 0 for a in allocs))
                sale = StockLedgerEntry.objects.filter(movement_type="SALE", reference=inv.code)
                self.assertEqual(-sum(e.qty_change for e in sale),
                                 sum(li.qty for li in lines))
                pay = PaymentTransaction.objects.get(sales_order=order)
                self.assertEqual(pay.match_status, "MATCHED")
                self.assertEqual(pay.amount, inv.amount)
                self.assertEqual(inv.payment_txn_ref, pay.bank_txn_id)

    def test_r4_don_tu_huy_da_nha_giu_cho(self):
        order = SalesOrder.objects.get(code="DH-2609-114")
        self.assertEqual(order.status, "AUTO_CANCELLED")
        lot = Batch.objects.get(batch_id="LO-0922")
        self.assertEqual(lot.qty_reserved, Decimal("0"))
        self.assertFalse(SalesInvoice.objects.filter(sales_order=order).exists())

    def test_r4_job_ttl_huy_don_demo_nha_dung_giu_cho(self):
        from apps.sales.orders import services as order_services
        cancelled = order_services.cancel_unpaid_expired(
            now=timezone.now() + timedelta(hours=2))
        self.assertEqual(cancelled, 2)
        self.assertFalse(Batch.objects.filter(batch_id__in=DEMO_BATCH_IDS,
                                              qty_reserved__gt=0).exists())
        self.assertEqual(order_services.cancel_unpaid_expired(
            now=timezone.now() + timedelta(hours=2)), 0)

    def test_r4_doanh_thu_gia_von_bao_cao_khop_hoa_don(self):
        from apps.reports.services import period_pnl
        from apps.sales.models import SalesInvoiceLineBatch
        today = timezone.localdate()
        pnl = period_pnl(year=today.year, month=today.month)
        invoices = SalesInvoice.objects.filter(code__startswith="HD-2609-")
        self.assertEqual(pnl["revenue"], sum(i.amount for i in invoices))
        cogs = sum(a.qty * a.unit_cost for a in SalesInvoiceLineBatch.objects.all())
        self.assertGreater(cogs, 0)
        self.assertEqual(pnl["cogs"], cogs)

    def test_r4_seed_lai_idempotent_khong_doi_ton(self):
        before = {b.batch_id: (b.qty_available, b.qty_reserved)
                  for b in Batch.objects.all()}
        run()
        self.assertEqual({b.batch_id: (b.qty_available, b.qty_reserved)
                          for b in Batch.objects.all()}, before)

    def test_r4_remove_go_sach_ca_phan_bo_but_toan_giao_dich(self):
        from apps.sales.models import (PaymentTransaction, SalesInvoiceLineBatch,
                                       SalesOrderLineBatch)
        run("--remove")
        for model in (SalesOrderLineBatch, SalesInvoiceLineBatch, PaymentTransaction,
                      StockLedgerEntry, Batch, SalesOrder):
            with self.subTest(model=model.__name__):
                self.assertFalse(model.objects.exists())
        self.assertFalse(DemoRecord.objects.exists())

    def test_r4_adopt_legacy_go_sach_ca_phan_bo_but_toan_giao_dich(self):
        from apps.sales.models import (PaymentTransaction, SalesInvoiceLineBatch,
                                       SalesOrderLineBatch)
        DemoRecord.objects.all().delete()
        run("--remove", "--adopt-legacy")
        for model in (SalesOrderLineBatch, SalesInvoiceLineBatch, PaymentTransaction,
                      StockLedgerEntry, Batch, SalesOrder, Item):
            with self.subTest(model=model.__name__):
                self.assertFalse(model.objects.exists())
        self.assertFalse(DemoRecord.objects.exists())


class F1SeedFefoCaseTests(TestCase):
    """F1 (FEFO, 2026-09-26) — demo có sẵn ca 'cùng mặt hàng, lô nhập sau nhưng hạn sớm hơn' để QA."""

    def test_f1_seed_co_ca_lo_nhap_sau_han_som_hon_fefo_chon_lo_nay(self):
        from apps.inventory.batches import services as batch_services
        run()
        old = Batch.objects.get(batch_id="LO-0915")
        new = Batch.objects.get(batch_id="LO-0918")
        self.assertEqual(old.item_id, new.item_id)
        self.assertLess(old.received_date, new.received_date)   # LO-0915 nhập trước
        self.assertGreater(old.expiry_date, new.expiry_date)     # nhưng hạn muộn hơn
        alloc = batch_services.allocate_fefo(item=new.item, qty=Decimal("1"))
        self.assertEqual(alloc[0][0].batch_id, "LO-0918")
