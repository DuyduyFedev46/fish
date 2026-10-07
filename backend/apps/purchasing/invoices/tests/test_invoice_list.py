"""
R11 (ERP theo design Lô 12, 02b §3.8): `GET /api/purchasing/invoices/` đọc danh sách hoá đơn mua.

- Quyền Tầng 1 `purchasing.view_purchaseinvoice` (owner, manager). Các vai khác 403, chưa đăng nhập 401.
- D-3 (Duy chốt): Quản lý THẤY `amount`, không thêm khoá. `amount` không thuộc COST_KEYS (ngoại lệ D-3).
- Lọc `is_paid`, `supplier`, `month`; sai tham số → 400 `INVALID_FILTER`, thông điệp không lặp giá trị gửi lên.
- Ghi (POST/PATCH) giữ như cũ: chỉ owner; DELETE 405 (BR-PQ-10).
Mọi dữ liệu là giả.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts import roles
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Warehouse
from apps.purchasing.models import PurchaseInvoice, PurchaseReceipt, PurchaseReceiptLine, Supplier

URL = "/api/purchasing/invoices/"
EXPECTED_KEYS = {
    "id", "code", "supplier", "supplier_name", "receipt", "receipt_code", "amount",
    "is_paid", "is_paid_label", "invoice_date", "paid_at", "created_by",
}
AMOUNT_SENTINEL = "7654321.00"
SUPPLIER_PHONE = "0900000555"  # giả, không được lộ ở danh sách hoá đơn


class InvoiceListBase(TestCase):
    def setUp(self):
        self.owner = make_user("u_owner", roles.OWNER)
        self.manager = make_user("u_manager", roles.MANAGER)
        self.warehouse_staff = make_user("u_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("u_courier", roles.DELIVERY_STAFF)
        self.customer_service = make_user("u_cs", roles.CUSTOMER_SERVICE)
        self.no_group = User.objects.create_user("u_no_group", password="x")
        self.supplier = Supplier.objects.create(name="Đầu mối A", phone=SUPPLIER_PHONE)
        self.other_supplier = Supplier.objects.create(name="Vựa B")
        group = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=group)
        self.warehouse = Warehouse.objects.create(name="Kho chính")

    def make_receipt(self, supplier=None):
        receipt = PurchaseReceipt.objects.create(
            supplier=supplier or self.supplier, warehouse=self.warehouse,
            received_date=datetime.date(2026, 9, 28), created_by=self.owner,
        )
        PurchaseReceiptLine.objects.create(receipt=receipt, item=self.item, qty=Decimal("3"), rate=Decimal("100"))
        return receipt

    def make_invoice(self, *, supplier=None, receipt=None, amount="1000000", is_paid=True,
                     invoice_date=datetime.date(2026, 9, 28)):
        paid_at = datetime.datetime(2026, 9, 29, 3, 0, tzinfo=datetime.timezone.utc) if is_paid else None
        return PurchaseInvoice.objects.create(
            supplier=supplier or self.supplier, receipt=receipt, amount=Decimal(amount), is_paid=is_paid,
            invoice_date=invoice_date, paid_at=paid_at, created_by=self.owner,
        )

    def get(self, user, query=""):
        return client_for(user).get(f"{URL}{query}")

    def ids(self, user, query=""):
        resp = self.get(user, query)
        self.assertEqual(resp.status_code, 200, (query, resp.content))
        return [row["id"] for row in resp.json()["results"]]


class InvoiceListPermissionTests(InvoiceListBase):
    def test_r11_owner_and_manager_get_200(self):
        self.make_invoice()
        for user in (self.owner, self.manager):
            self.assertEqual(self.get(user).status_code, 200, user.username)

    def test_r11_other_roles_403_and_anonymous_401(self):
        self.make_invoice(amount="7654321")
        for user in (self.warehouse_staff, self.courier, self.customer_service, self.no_group):
            resp = self.get(user)
            self.assertEqual(resp.status_code, 403, user.username)
            self.assertNotIn("7654321", resp.content.decode(), user.username)
        self.assertEqual(self.get(None).status_code, 401)

    def test_r11_detail_follows_the_same_permissions(self):
        invoice = self.make_invoice()
        url = f"{URL}{invoice.pk}/"
        self.assertEqual(client_for(self.manager).get(url).status_code, 200)
        self.assertEqual(client_for(self.warehouse_staff).get(url).status_code, 403)
        self.assertEqual(client_for(None).get(url).status_code, 401)


class InvoiceListContractTests(InvoiceListBase):
    def test_r11_row_contract_and_labels(self):
        receipt = self.make_receipt()
        paid = self.make_invoice(receipt=receipt, amount="1234567.50")
        unpaid = self.make_invoice(is_paid=False, supplier=self.other_supplier)
        resp = self.get(self.owner)
        body = resp.json()
        self.assertEqual(body["count"], 2)
        rows = {row["id"]: row for row in body["results"]}
        row = rows[paid.pk]
        self.assertEqual(set(row), EXPECTED_KEYS)
        self.assertEqual(row["code"], f"#{paid.pk}")
        self.assertEqual(row["supplier"], self.supplier.pk)
        self.assertEqual(row["supplier_name"], "Đầu mối A")
        self.assertEqual(row["receipt"], receipt.pk)
        self.assertEqual(row["receipt_code"], f"PR-{receipt.pk}")
        self.assertEqual(row["amount"], "1234567.50")
        self.assertIs(row["is_paid"], True)
        self.assertEqual(row["is_paid_label"], "Đã trả tiền")
        self.assertEqual(row["invoice_date"], "2026-09-28")
        self.assertIsNotNone(row["paid_at"])
        other = rows[unpaid.pk]
        self.assertIsNone(other["receipt"])
        self.assertIsNone(other["receipt_code"])
        self.assertEqual(other["is_paid_label"], "Chưa trả tiền")
        self.assertIsNone(other["paid_at"])

    def test_r11_d3_manager_sees_amount(self):
        """D-3: Quản lý thấy `amount` hoá đơn mua, cùng body với owner."""
        self.make_invoice(amount=AMOUNT_SENTINEL)
        owner_rows = self.get(self.owner).json()["results"]
        manager_rows = self.get(self.manager).json()["results"]
        self.assertEqual(manager_rows[0]["amount"], AMOUNT_SENTINEL)
        self.assertEqual(manager_rows, owner_rows)
        self.assertEqual(set(manager_rows[0]), EXPECTED_KEYS)

    def test_r11_detail_has_same_keys(self):
        invoice = self.make_invoice(amount=AMOUNT_SENTINEL)
        body = client_for(self.manager).get(f"{URL}{invoice.pk}/").json()
        self.assertEqual(set(body), EXPECTED_KEYS)
        self.assertEqual(body["amount"], AMOUNT_SENTINEL)

    def test_r11_no_supplier_personal_data_in_response(self):
        self.make_invoice(receipt=self.make_receipt())
        for user in (self.owner, self.manager):
            self.assertNotIn(SUPPLIER_PHONE, self.get(user).content.decode(), user.username)

    def test_r11_sorted_by_invoice_date_then_id_desc_and_paginated_20(self):
        older = self.make_invoice(invoice_date=datetime.date(2026, 9, 1))
        newer = self.make_invoice(invoice_date=datetime.date(2026, 9, 20))
        same_day_later = self.make_invoice(invoice_date=datetime.date(2026, 9, 20))
        self.assertEqual(self.ids(self.owner), [same_day_later.pk, newer.pk, older.pk])
        for _ in range(22):
            self.make_invoice()
        body = self.get(self.owner).json()
        self.assertEqual(body["count"], 25)
        self.assertEqual(len(body["results"]), 20)
        self.assertIsNotNone(body["next"])


class InvoiceListFilterTests(InvoiceListBase):
    def setUp(self):
        super().setUp()
        self.paid_sep = self.make_invoice(invoice_date=datetime.date(2026, 9, 30))
        self.unpaid_sep = self.make_invoice(is_paid=False, invoice_date=datetime.date(2026, 9, 5))
        self.paid_oct = self.make_invoice(supplier=self.other_supplier, invoice_date=datetime.date(2026, 10, 1))

    def test_r11_filter_is_paid(self):
        self.assertEqual(set(self.ids(self.owner, "?is_paid=1")), {self.paid_sep.pk, self.paid_oct.pk})
        self.assertEqual(set(self.ids(self.owner, "?is_paid=true")), {self.paid_sep.pk, self.paid_oct.pk})
        self.assertEqual(self.ids(self.owner, "?is_paid=0"), [self.unpaid_sep.pk])
        self.assertEqual(self.ids(self.owner, "?is_paid=false"), [self.unpaid_sep.pk])
        self.assertEqual(len(self.ids(self.owner, "?is_paid=")), 3)

    def test_r11_filter_supplier(self):
        self.assertEqual(self.ids(self.owner, f"?supplier={self.other_supplier.pk}"), [self.paid_oct.pk])

    def test_r11_filter_month_uses_invoice_date_with_boundaries(self):
        self.assertEqual(set(self.ids(self.owner, "?month=2026-09")), {self.paid_sep.pk, self.unpaid_sep.pk})
        self.assertEqual(self.ids(self.owner, "?month=2026-10"), [self.paid_oct.pk])
        self.assertEqual(self.ids(self.owner, "?month=2026-11"), [])

    def test_r11_filters_combine(self):
        self.assertEqual(self.ids(self.manager, f"?month=2026-09&is_paid=0&supplier={self.supplier.pk}"),
                         [self.unpaid_sep.pk])

    def test_r11_invalid_filters_get_400_without_echoing_value(self):
        bad = [
            "is_paid=maybe", "is_paid=2", "supplier=abc", "supplier=-1", "supplier=0", "supplier=%2B3",
            "supplier=99999999999999999999", f"supplier={'9' * 5000}", "supplier=%EF%BC%91",
            "month=2026-13", "month=2026-1", "month=26-10", "month=1999-12", "month=2101-01",
            "month=%0A2026-10", "month=abc",
        ]
        for query in bad:
            resp = self.get(self.owner, f"?{query}")
            self.assertEqual(resp.status_code, 400, query)
            body = resp.json()
            self.assertEqual(body["code"], "INVALID_FILTER", query)
            value = query.split("=", 1)[1]
            if len(value) > 3 and "%" not in value:
                self.assertNotIn(value, body["detail"], query)

    def test_r11_invalid_filter_does_not_leak_to_non_permitted_role(self):
        self.assertEqual(self.get(self.warehouse_staff, "?is_paid=maybe").status_code, 403)


class InvoiceListQueryCountTests(InvoiceListBase):
    def test_r11_no_n_plus_one(self):
        def run():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.get(self.owner).status_code, 200)
            return len(ctx)

        self.make_invoice(receipt=self.make_receipt())
        run()  # lần đầu nạp cache quyền / content type, không tính
        base = run()
        for _ in range(8):
            self.make_invoice(receipt=self.make_receipt(), supplier=self.other_supplier)
        self.assertEqual(run(), base)


class InvoiceWriteUnchangedTests(InvoiceListBase):
    def payload(self):
        return {"supplier": self.supplier.pk, "amount": "500000.00", "is_paid": False, "invoice_date": "2026-10-01"}

    def test_r11_owner_creates_and_response_has_labels(self):
        resp = client_for(self.owner).post(URL, self.payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(set(body), EXPECTED_KEYS)
        self.assertEqual(body["code"], f"#{body['id']}")
        self.assertEqual(body["is_paid_label"], "Chưa trả tiền")
        self.assertEqual(body["created_by"], self.owner.pk)

    def test_r11_manager_cannot_create_or_patch(self):
        invoice = self.make_invoice()
        self.assertEqual(client_for(self.manager).post(URL, self.payload(), format="json").status_code, 403)
        resp = client_for(self.manager).patch(f"{URL}{invoice.pk}/", {"is_paid": False}, format="json")
        self.assertEqual(resp.status_code, 403)
        invoice.refresh_from_db()
        self.assertTrue(invoice.is_paid)

    def test_r11_owner_patch_and_delete_405(self):
        invoice = self.make_invoice(is_paid=False)
        # Lô 17a (TL12-paid): đánh dấu đã trả thì phải kèm thời điểm trả.
        paid_at = (timezone.now() - datetime.timedelta(hours=1)).isoformat()
        resp = client_for(self.owner).patch(f"{URL}{invoice.pk}/", {"is_paid": True, "paid_at": paid_at}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["is_paid_label"], "Đã trả tiền")
        self.assertEqual(client_for(self.owner).delete(f"{URL}{invoice.pk}/").status_code, 405)
        self.assertTrue(PurchaseInvoice.objects.filter(pk=invoice.pk).exists())
