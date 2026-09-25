"""
S9 — Khoá field trạng thái / tồn / giá vốn / người phụ trách trong Django Admin (BR-PQ-14, BR-PQ-05).

Người KHÔNG phải superuser (kể cả Chủ) thấy các field này ở dạng chỉ đọc; POST form có giá trị
khác thì DB không đổi. Superuser vẫn sửa được (đường cứu hộ, Duy chốt Q3) nhưng mọi thay đổi
field khoá ghi AuditLog `admin_edit` trước → sau. Master data (mặt hàng, giá, NCC) không khoá.
"""
import datetime
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemPrice, PriceList
from apps.delivery.models import DeliveryNote
from apps.inventory.models import Batch, ReturnToStock, StockReconciliation
from apps.purchasing.models import PurchaseReceipt, Supplier
from apps.sales.models import PaymentTransaction, Refund, SalesInvoice, SalesOrder

from .fixtures import make_batch, make_master, make_order_with_note, make_user

# Field khoá kỳ vọng theo S9-AC1/AC2 (khớp danh sách khoá API của S3 + người ghi của S4).
EXPECTED_LOCKED = {
    Batch: {"status", "qty_received", "qty_available", "qty_reserved", "purchase_rate",
            "landed_unit_cost", "expiry_date", "closed_at", "closed_by"},
    DeliveryNote: {"status", "assigned_to", "failed_attempts", "completed_at", "sales_invoice"},
    ReturnToStock: {"status", "decision", "approved_by", "created_by"},
    StockReconciliation: {"status", "approved_by", "approved_at", "created_by"},
    PurchaseReceipt: {"status", "created_by"},
    Refund: {"status", "amount", "is_partial", "sales_invoice", "bank_txn_ref",
             "created_by", "confirmed_by", "confirmed_at"},
    SalesOrder: {"status", "total_amount", "customer", "booked_expires_at"},
    SalesInvoice: {"status", "amount", "sales_order", "customer", "issued_at",
                   "payment_txn_ref", "payment_method"},
    PaymentTransaction: {"bank_txn_id", "sales_order", "amount", "match_status", "source",
                         "raw_payload", "received_at"},
}


def staff(username, *groups, perms=()):
    user = make_user(username, *groups, perms=perms)
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return User.objects.get(pk=user.pk)


def change_url(obj):
    return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])


def add_url(model):
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_add")


def form_data(user, obj, **overrides):
    """Dựng POST của form Admin từ giá trị hiện tại (như người dùng bấm Lưu), rồi đè `overrides`."""
    request = RequestFactory().get("/")
    request.user = user
    model_admin = admin.site._registry[type(obj)]
    form = model_admin.get_form(request, obj, change=True)(instance=obj)
    data = {}
    for name in form.fields:
        value = form[name].value()
        if value is None or value is False:
            continue
        data[name] = "on" if value is True else str(value)
    for formset, _inline in model_admin.get_formsets_with_inlines(request, obj):
        prefix = formset.get_default_prefix()
        data.update({f"{prefix}-TOTAL_FORMS": "0", f"{prefix}-INITIAL_FORMS": "0"})
    data.update({k: str(v) for k, v in overrides.items()})
    return data


class S9Base(TestCase):
    def setUp(self):
        self.item, self.sup, self.wh = make_master()
        self.batch = make_batch(self.item, self.sup, self.wh)
        self.chu = staff("loc", "chu")  # Chủ nhưng KHÔNG superuser
        self.ql = staff("ql1", "quan_ly", perms=["inventory.change_batch"])
        self.root = User.objects.create_superuser("admin", password="x")

    def post_as(self, user, obj, **overrides):
        self.client.force_login(user)
        return self.client.post(change_url(obj), form_data(user, obj, **overrides))


class S9BatchTests(S9Base):
    def test_s9_ac1_quan_ly_form_lo_field_khoa_chi_doc(self):
        self.client.force_login(self.ql)
        resp = self.client.get(change_url(self.batch))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        for name in ("status", "qty_available", "qty_reserved", "qty_received", "expiry_date"):
            self.assertNotIn(f'name="{name}"', html, name)
        self.assertIn('name="supplier"', html)  # field không khoá vẫn sửa được

    def test_s9_ac1_quan_ly_post_gia_tri_khac_db_khong_doi(self):
        before = Batch.objects.values().get(pk=self.batch.pk)
        resp = self.post_as(
            self.ql, self.batch, status=Batch.Status.CLOSED, qty_available="999",
            landed_unit_cost="1", purchase_rate="1", expiry_date="2030-01-01",
        )
        self.assertEqual(resp.status_code, 302, resp.content[:2000])
        self.assertEqual(Batch.objects.values().get(pk=self.batch.pk), before)
        self.assertFalse(AuditLog.objects.filter(action="admin_edit").exists())

    def test_s9_ac1_quan_ly_khong_thay_gia_von_trong_form_chi_doc(self):
        # Khoá chỉ đọc không được làm lộ giá vốn (bất biến #1, BR-PQ-15).
        self.client.force_login(self.ql)
        html = self.client.get(change_url(self.batch)).content.decode()
        # (help_text của qty_received có nhắc chữ "landed_unit_cost" — kiểm theo dòng field.)
        self.assertNotIn("field-landed_unit_cost", html)
        self.assertNotIn("field-purchase_rate", html)
        self.assertNotIn(str(self.batch.landed_unit_cost).replace(".", ","), html)

    def test_s9_ac4_chu_khong_superuser_khong_sua_duoc_status(self):
        self.client.force_login(self.chu)
        html = self.client.get(change_url(self.batch)).content.decode()
        self.assertNotIn('name="status"', html)
        self.assertIn("field-landed_unit_cost", html)  # Chủ có view_costprice: thấy, chỉ đọc
        old_status = self.batch.status
        resp = self.post_as(self.chu, self.batch, status=Batch.Status.CLOSED, landed_unit_cost="1")
        self.assertEqual(resp.status_code, 302, resp.content[:2000])
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, old_status)
        self.assertNotEqual(self.batch.landed_unit_cost, Decimal("1"))

    def test_s9_ac3_superuser_sua_landed_unit_cost_ghi_audit(self):
        old = self.batch.landed_unit_cost
        resp = self.post_as(self.root, self.batch, landed_unit_cost="91234")
        self.assertEqual(resp.status_code, 302, resp.content[:2000])
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.landed_unit_cost, Decimal("91234"))
        log = AuditLog.objects.get(action="admin_edit")
        self.assertEqual(log.actor, self.root)
        self.assertEqual(log.model_name, "inventory.Batch")
        self.assertEqual(log.object_id, str(self.batch.pk))
        self.assertEqual(
            log.changes, {"landed_unit_cost": {"from": str(old), "to": "91234"}}
        )

    def test_s9_ac3_superuser_sua_status_va_nguoi_ghi_audit_tung_field(self):
        resp = self.post_as(self.root, self.batch, status=Batch.Status.CLOSED, closed_by=self.root.pk)
        self.assertEqual(resp.status_code, 302, resp.content[:2000])
        log = AuditLog.objects.get(action="admin_edit")
        self.assertEqual(set(log.changes), {"status", "closed_by"})
        self.assertEqual(log.changes["closed_by"], {"from": None, "to": self.root.pk})

    def test_s9_ac3_superuser_luu_khong_doi_field_khoa_thi_khong_ghi_audit(self):
        other = Supplier.objects.create(name="Đầu mối B")
        resp = self.post_as(self.root, self.batch, supplier=other.pk)
        self.assertEqual(resp.status_code, 302, resp.content[:2000])
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.supplier, other)
        self.assertFalse(AuditLog.objects.filter(action="admin_edit").exists())

    def test_s9_ac2_nguoi_khong_superuser_khong_tao_lo_tay(self):
        # Lô chỉ sinh từ phiếu nhập (BR-MH); tạo tay trong Admin là đặt tồn/giá vốn trực tiếp.
        self.client.force_login(self.chu)
        self.assertEqual(self.client.get(add_url(Batch)).status_code, 403)


class S9DocumentsTests(S9Base):
    def setUp(self):
        super().setUp()
        self.order, self.customer, self.note = make_order_with_note("DH01", "0901000001")
        self.invoice = SalesInvoice.objects.get(sales_order=self.order)
        self.giao = staff("giao1", "nv_giao")
        self.objs = {
            Batch: self.batch,
            DeliveryNote: self.note,
            ReturnToStock: ReturnToStock.objects.create(
                batch=self.batch, qty=Decimal("1"), created_by=self.chu
            ),
            StockReconciliation: StockReconciliation.objects.create(
                count_date=timezone.localdate(), created_by=self.chu
            ),
            PurchaseReceipt: PurchaseReceipt.objects.create(
                supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
                created_by=self.chu,
            ),
            Refund: Refund.objects.create(
                sales_invoice=self.invoice, amount=Decimal("100000"), reason="thử",
                created_by=self.chu,
            ),
            SalesOrder: self.order,
            SalesInvoice: self.invoice,
            PaymentTransaction: PaymentTransaction.objects.create(
                bank_txn_id="FT001", sales_order=self.order, amount=Decimal("100000"),
                received_at=datetime.datetime(2026, 9, 1, 8, 0, tzinfo=datetime.timezone.utc),
            ),
        }

    def _readonly(self, user, obj):
        request = RequestFactory().get("/")
        request.user = user
        return set(admin.site._registry[type(obj)].get_readonly_fields(request, obj))

    def test_s9_ac2_field_trang_thai_nguoi_phu_trach_so_tien_chi_doc(self):
        for model, expected in EXPECTED_LOCKED.items():
            with self.subTest(model=model.__name__):
                missing = expected - self._readonly(self.chu, self.objs[model])
                self.assertFalse(missing, f"{model.__name__} chưa khoá: {sorted(missing)}")

    def test_s9_ac2_form_sua_mo_duoc_va_khong_co_input_field_khoa(self):
        self.client.force_login(self.chu)
        for model, expected in EXPECTED_LOCKED.items():
            with self.subTest(model=model.__name__):
                resp = self.client.get(change_url(self.objs[model]))
                self.assertEqual(resp.status_code, 200)
                html = resp.content.decode()
                for name in expected:
                    self.assertNotIn(f'name="{name}"', html, f"{model.__name__}.{name}")

    def test_s9_ac2_phieu_giao_post_doi_nguoi_giao_trang_thai_db_khong_doi(self):
        before = DeliveryNote.objects.values().get(pk=self.note.pk)
        resp = self.post_as(
            self.chu, self.note, status=DeliveryNote.Status.COMPLETED,
            assigned_to=self.giao.pk, failed_attempts="2", note="gọi trước khi giao",
        )
        self.assertEqual(resp.status_code, 302, resp.content[:2000])
        after = DeliveryNote.objects.values().get(pk=self.note.pk)
        self.assertEqual(after["note"], "gọi trước khi giao")  # field không khoá vẫn lưu
        after["note"] = before["note"]
        self.assertEqual(after, before)

    def test_s9_ac2_superuser_khong_bi_khoa(self):
        for model, expected in EXPECTED_LOCKED.items():
            with self.subTest(model=model.__name__):
                self.assertFalse(expected & self._readonly(self.root, self.objs[model]))

    def test_s9_ac2_khong_superuser_khong_tao_tay_phieu_giao_phieu_hoan_giao_dich(self):
        self.client.force_login(self.chu)
        for model in (DeliveryNote, Refund, PaymentTransaction):
            with self.subTest(model=model.__name__):
                self.assertEqual(self.client.get(add_url(model)).status_code, 403)

    def test_s9_ac2_khong_superuser_tao_kiem_ke_nguoi_tao_la_minh(self):
        # created_by chỉ đọc với người thường → hệ thống ghi theo người đăng nhập (BR-PQ-16).
        self.client.force_login(self.ql)
        resp = self.client.post(add_url(StockReconciliation), {
            "count_date": "2026-09-24", "note": "kiểm tay",
            "status": StockReconciliation.Status.APPROVED, "created_by": self.chu.pk,
            "lines-TOTAL_FORMS": "0", "lines-INITIAL_FORMS": "0",
        })
        self.assertEqual(resp.status_code, 302, resp.content[:3000])
        rec = StockReconciliation.objects.get(note="kiểm tay")
        self.assertEqual(rec.created_by, self.ql)
        self.assertEqual(rec.status, StockReconciliation.Status.DRAFT)

    def test_s9_ac3_superuser_doi_nguoi_giao_ghi_audit(self):
        resp = self.post_as(self.root, self.note, assigned_to=self.giao.pk)
        self.assertEqual(resp.status_code, 302, resp.content[:2000])
        log = AuditLog.objects.get(action="admin_edit")
        self.assertEqual(log.model_name, "delivery.DeliveryNote")
        self.assertEqual(log.changes, {"assigned_to": {"from": None, "to": self.giao.pk}})


class S9MasterDataTests(S9Base):
    def test_s9_ac5_chu_van_sua_mat_hang_gia_ncc(self):
        price_list = PriceList.objects.create(name="Bán lẻ", is_default=True)
        price = ItemPrice.objects.create(
            price_list=price_list, item=self.item, rate=Decimal("120000"),
            valid_from=datetime.date(2026, 9, 1),
        )
        cases = (
            (self.item, {"name": "Cá thu phi lê"}, Item, "name", "Cá thu phi lê"),
            (price, {"rate": "125000"}, ItemPrice, "rate", Decimal("125000")),
            (self.sup, {"name": "Đầu mối A2"}, Supplier, "name", "Đầu mối A2"),
        )
        for obj, overrides, model, field, expected in cases:
            with self.subTest(model=model.__name__):
                resp = self.post_as(self.chu, obj, **overrides)
                self.assertEqual(resp.status_code, 302, resp.content[:2000])
                self.assertEqual(getattr(model.objects.get(pk=obj.pk), field), expected)
        self.assertFalse(AuditLog.objects.filter(action="admin_edit").exists())

    def test_s9_quyen_nguoi_khong_phai_staff_khong_vao_admin(self):
        kho = make_user("kho1", "nv_kho")  # không is_staff
        self.client.force_login(kho)
        resp = self.client.get(change_url(self.batch))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])
