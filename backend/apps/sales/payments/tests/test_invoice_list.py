"""
R13 (ERP theo design Lô 12, 02b §3.8): `GET /api/sales/invoices/` danh sách hoá đơn bán cho Kế toán (W5j).

- Quyền Tầng 1 `sales.view_salesinvoice` (owner, manager, warehouse_staff). CSKH / NV giao / không nhóm → 403, chưa đăng nhập → 401.
- `cogs`, `gross_profit` (và `totals.gross_profit`) chỉ khi có `view_costprice` (chỉ Chủ); người khác KHÔNG có key.
- Dữ liệu khách (`customer_name`) theo phạm vi dòng + response `Cache-Control: no-store`.
- Lọc `status`, `date_from/date_to`, `q` (mã hoá đơn/mã đơn); sai tham số → 400 `INVALID_FILTER`.
- Chi tiết giữ serializer cũ; ghi bị chặn (read-only).
Mọi dữ liệu là giả.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts import roles
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_batch, make_master, make_user
from apps.sales.models import (
    Customer, SalesInvoice, SalesInvoiceLine, SalesInvoiceLineBatch, SalesOrder,
)

URL = "/api/sales/invoices/"
ROW_KEYS = {
    "id", "code", "sales_order", "order_code", "customer_name", "issued_at", "amount", "status",
    "status_label",
    "customer_hidden_reason",  # PV-07 (02b §2.7)
}
COST_ROW_KEYS = {"cogs", "gross_profit"}
COGS_SENTINEL = "4242"  # tổng giá vốn của hoá đơn mẫu: 10 kg × 424,2 → 4242 (số lạ để quét rò)
PROFIT_SENTINEL = "95758"
FAKE_NAME = "Khách Giả Một"
FAKE_PHONE = "0900000777"


def utc(day, hour=3):
    return datetime.datetime(2026, 9, day, hour, 0, tzinfo=datetime.timezone.utc)


class InvoiceListBase(TestCase):
    def setUp(self):
        self.owner = make_user("u_owner", roles.OWNER)
        self.manager = make_user("u_manager", roles.MANAGER)
        self.warehouse_staff = make_user("u_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("u_courier", roles.DELIVERY_STAFF)
        self.customer_service = make_user("u_cs", roles.CUSTOMER_SERVICE)
        self.no_group = User.objects.create_user("u_no_group", password="x")
        self.item, self.supplier, self.warehouse = make_master()
        self.batch = make_batch(self.item, self.supplier, self.warehouse, qty="100")
        self.seq = 0

    def make_invoice(self, *, amount="100000", cogs_unit="424.2", qty="10", issued_at=None,
                     status=SalesInvoice.Status.ISSUED, name=FAKE_NAME, with_lines=True):
        self.seq += 1
        n = self.seq
        customer = Customer.objects.create(phone=f"09000008{n:02d}", name=name, default_address="1 Cảng")
        order = SalesOrder.objects.create(
            code=f"SO-T{n:03d}", customer=customer, status=SalesOrder.Status.PROCESSING,
            delivery_address="1 Cảng", phone=customer.phone, total_amount=Decimal(amount),
        )
        invoice = SalesInvoice.objects.create(
            code=f"HD-T{n:03d}", sales_order=order, customer=customer, amount=Decimal(amount),
            issued_at=issued_at or utc(10), status=status,
        )
        if with_lines:
            line = SalesInvoiceLine.objects.create(
                invoice=invoice, item=self.item, qty=Decimal(qty), rate=Decimal("10000"), amount=Decimal(amount),
            )
            SalesInvoiceLineBatch.objects.create(
                invoice_line=line, batch=self.batch, component_item=self.item, qty=Decimal(qty),
                unit_cost=Decimal(cogs_unit),
            )
        return invoice

    def get(self, user, query=""):
        return client_for(user).get(URL + query)


class InvoiceListPermissionTests(InvoiceListBase):
    def setUp(self):
        super().setUp()
        self.make_invoice(amount="100000")

    def test_r13_ac1_owner_manager_warehouse_staff_200(self):
        for user in (self.owner, self.manager, self.warehouse_staff):
            with self.subTest(user=user.username):
                response = self.get(user)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["count"], 1)

    def test_r13_ac1_other_groups_403_without_body_data(self):
        for user in (self.courier, self.customer_service, self.no_group):
            with self.subTest(user=user.username):
                response = self.get(user)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn(FAKE_NAME, response.content.decode())
                self.assertNotIn("HD-T001", response.content.decode())

    def test_r13_ac1_anonymous_401(self):
        self.assertEqual(self.get(None).status_code, 401)

    def test_r13_ac1_detail_is_403_for_courier_and_works_for_owner(self):
        invoice = SalesInvoice.objects.get()
        self.assertEqual(client_for(self.courier).get(f"{URL}{invoice.pk}/").status_code, 403)
        self.assertEqual(client_for(self.owner).get(f"{URL}{invoice.pk}/").status_code, 200)

    def test_r13_ac1_writes_not_allowed(self):
        invoice = SalesInvoice.objects.get()
        client = client_for(self.owner)
        self.assertEqual(client.post(URL, {}, format="json").status_code, 405)
        self.assertEqual(client.patch(f"{URL}{invoice.pk}/", {"amount": "1"}, format="json").status_code, 405)
        self.assertEqual(client.delete(f"{URL}{invoice.pk}/").status_code, 405)


class InvoiceListContractTests(InvoiceListBase):
    def test_r13_ac2_owner_row_has_cogs_and_gross_profit(self):
        self.make_invoice(amount="100000", cogs_unit="424.2", qty="10")
        row = self.get(self.owner).json()["results"][0]
        self.assertEqual(set(row), ROW_KEYS | COST_ROW_KEYS)
        self.assertEqual(row["code"], "HD-T001")
        self.assertEqual(row["order_code"], "SO-T001")
        self.assertEqual(row["customer_name"], FAKE_NAME)
        self.assertEqual(row["amount"], "100000")
        self.assertEqual(row["status"], "ISSUED")
        self.assertEqual(row["status_label"], "Đã xuất")
        self.assertEqual(row["cogs"], COGS_SENTINEL)
        self.assertEqual(row["gross_profit"], PROFIT_SENTINEL)

    def test_r13_ac2_totals_skip_cancelled_and_match_rows(self):
        self.make_invoice(amount="100000", cogs_unit="424.2", qty="10")
        self.make_invoice(amount="50000", cogs_unit="1000", qty="10")  # cogs 10000
        self.make_invoice(amount="999999", cogs_unit="1", qty="1", status=SalesInvoice.Status.CANCELLED)
        body = self.get(self.owner).json()
        self.assertEqual(body["count"], 3)  # danh sách vẫn hiện hoá đơn đã huỷ
        self.assertEqual(body["totals"], {"amount": "150000", "gross_profit": str(150000 - 4242 - 10000)})

    def test_r13_ac2_invoice_without_batch_lines_has_zero_cogs(self):
        self.make_invoice(amount="70000", with_lines=False)
        row = self.get(self.owner).json()["results"][0]
        self.assertEqual(row["cogs"], "0")
        self.assertEqual(row["gross_profit"], "70000")

    def test_r13_ac2_sorted_newest_first_and_paginated_20(self):
        for day in range(1, 23):
            self.make_invoice(issued_at=utc(day))
        body = self.get(self.owner).json()
        self.assertEqual(body["count"], 22)
        self.assertEqual(len(body["results"]), 20)
        self.assertEqual(body["results"][0]["code"], "HD-T022")
        self.assertEqual(len(self.get(self.owner, "?page=2").json()["results"]), 2)

    def test_r13_ac2_totals_cover_all_pages_not_only_current(self):
        for day in range(1, 23):
            self.make_invoice(amount="1000", cogs_unit="0", issued_at=utc(day))
        self.assertEqual(self.get(self.owner, "?page=2").json()["totals"]["amount"], "22000")

    def test_r13_ac2_detail_keeps_old_serializer(self):
        invoice = self.make_invoice()
        body = client_for(self.owner).get(f"{URL}{invoice.pk}/").json()
        self.assertIn("lines", body)
        self.assertNotIn("cogs", body)
        self.assertIn("payment_method", body)


class InvoiceListFilterTests(InvoiceListBase):
    def setUp(self):
        super().setUp()
        self.a = self.make_invoice(issued_at=utc(5))
        self.b = self.make_invoice(issued_at=utc(15), status=SalesInvoice.Status.CANCELLED)
        self.c = self.make_invoice(issued_at=utc(25))

    def codes(self, query):
        response = self.get(self.owner, query)
        self.assertEqual(response.status_code, 200, response.content)
        return [r["code"] for r in response.json()["results"]]

    def test_r13_ac3_status_filter(self):
        self.assertEqual(self.codes("?status=CANCELLED"), [self.b.code])
        self.assertEqual(sorted(self.codes("?status=ISSUED")), sorted([self.a.code, self.c.code]))
        self.assertEqual(len(self.codes("?status=ISSUED,CANCELLED")), 3)

    def test_r13_ac3_date_range_uses_local_day(self):
        self.assertEqual(self.codes("?date_from=2026-09-10&date_to=2026-09-20"), [self.b.code])
        self.assertEqual(self.codes("?date_from=2026-09-15"), [self.c.code, self.b.code])
        self.assertEqual(self.codes("?date_to=2026-09-05"), [self.a.code])

    def test_r13_ac3_q_matches_invoice_or_order_code_case_insensitive(self):
        self.assertEqual(self.codes("?q=hd-t002"), [self.b.code])
        self.assertEqual(self.codes("?q=SO-T003"), [self.c.code])
        self.assertEqual(self.codes("?q=khong-co"), [])

    def test_r13_ac3_q_does_not_search_customer_name(self):
        self.assertEqual(self.codes("?q=Giả"), [])

    def test_r13_ac3_filters_combine(self):
        self.assertEqual(self.codes("?status=ISSUED&date_from=2026-09-20"), [self.c.code])

    def test_r13_ac3_invalid_filters_400_without_echo(self):
        for query in (
            "?status=BOGUS", "?date_from=2026-13-40", "?date_from=abc", "?date_to=2026-9-1",
            "?date_from=2026-09-20&date_to=2026-09-01",
        ):
            with self.subTest(query=query):
                response = self.get(self.owner, query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "INVALID_FILTER")
                for value in ("BOGUS", "2026-13-40", "abc"):
                    self.assertNotIn(value, response.json()["detail"])


class InvoiceListCostLeakTests(InvoiceListBase):
    def setUp(self):
        super().setUp()
        self.make_invoice(amount="100000", cogs_unit="424.2", qty="10")

    def test_r13_ac4_non_owner_has_no_cost_keys_in_rows_or_totals(self):
        for user in (self.manager, self.warehouse_staff):
            with self.subTest(user=user.username):
                response = self.get(user)
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(set(body["results"][0]), ROW_KEYS)
                self.assertEqual(set(body["totals"]), {"amount"})
                self.assertEqual(body["totals"]["amount"], "100000")
                text = response.content.decode()
                for key in COST_KEYS:
                    self.assertNotIn(f'"{key}"', text, key)
                for sentinel in (COGS_SENTINEL, PROFIT_SENTINEL, "424.2"):
                    self.assertNotIn(sentinel, text)

    def test_r13_ac4_non_owner_detail_has_no_unit_cost(self):
        invoice = SalesInvoice.objects.get()
        for user in (self.manager, self.warehouse_staff):
            text = client_for(user).get(f"{URL}{invoice.pk}/").content.decode()
            self.assertNotIn("unit_cost", text)
            self.assertNotIn("424.2", text)

    def test_r13_ac4_user_with_only_view_salesinvoice_gets_no_cost(self):
        user = make_user("u_direct", perms=("sales.view_salesinvoice",))
        note = SalesInvoice.objects.get().delivery_notes.get()
        note.assigned_to = user
        note.save(update_fields=["assigned_to"])
        body = self.get(user).json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(set(body["results"][0]) & COST_ROW_KEYS, set())
        self.assertNotIn("gross_profit", body["totals"])

    def test_r13_ac4_owner_sees_cost(self):
        body = self.get(self.owner).json()
        self.assertEqual(body["results"][0]["cogs"], COGS_SENTINEL)
        self.assertEqual(body["totals"]["gross_profit"], PROFIT_SENTINEL)

    def test_r13_ac4_filtered_totals_do_not_leak_via_error_or_empty(self):
        text = self.get(self.manager, "?status=CANCELLED").content.decode()
        self.assertNotIn("gross_profit", text)


class InvoiceListCustomerDataTests(InvoiceListBase):
    def test_r13_pii_response_is_no_store_for_every_allowed_role(self):
        self.make_invoice()
        for user in (self.owner, self.manager, self.warehouse_staff):
            with self.subTest(user=user.username):
                self.assertEqual(self.get(user)["Cache-Control"], "no-store")

    def test_r13_pii_customer_name_only_for_order_customer_info_permission(self):
        """PV-07 (thay M1): `customer_name` chỉ khi có V2 `sales.view_order_customer_info`. Mặc định cả owner, manager và
        NV kho đều có (ngoại lệ đã duyệt Q-4: trước đây NV kho thấy tên = null). Gỡ V2 khỏi nhóm NV kho thì tên = null."""
        from django.contrib.auth.models import Group, Permission

        self.make_invoice()
        for user in (self.owner, self.manager, self.warehouse_staff):
            with self.subTest(user=user.username):
                row = self.get(user).json()["results"][0]
                self.assertEqual(row["customer_name"], FAKE_NAME)
        Group.objects.get(name=roles.WAREHOUSE_STAFF).permissions.remove(
            Permission.objects.get(content_type__app_label="sales", codename="view_order_customer_info"))
        response = self.get(User.objects.get(pk=self.warehouse_staff.pk))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertIn("customer_name", body["results"][0])
        self.assertIsNone(body["results"][0]["customer_name"])
        self.assertEqual(body["results"][0]["customer_hidden_reason"], "not_permitted")
        self.assertEqual(body["results"][0]["code"], "HD-T001")  # các cột còn lại vẫn có
        self.assertNotIn(FAKE_NAME, response.content.decode())

    def test_r13_pii_customer_view_list_permission_alone_does_not_show_name(self):
        """Quyền "Xem khách hàng" (danh bạ) không còn mở tên trên hoá đơn: chỉ V2 mới mở (BR-PQ-38)."""
        self.make_invoice()
        user = make_user("u_wh_names", roles.WAREHOUSE_STAFF, perms=("sales.view_customer_list",))
        from django.contrib.auth.models import Group, Permission

        Group.objects.get(name=roles.WAREHOUSE_STAFF).permissions.remove(
            Permission.objects.get(content_type__app_label="sales", codename="view_order_customer_info"))
        self.assertIsNone(self.get(User.objects.get(pk=user.pk)).json()["results"][0]["customer_name"])

    def test_r13_pii_detail_no_store(self):
        invoice = self.make_invoice()
        self.assertEqual(client_for(self.owner).get(f"{URL}{invoice.pk}/")["Cache-Control"], "no-store")

    def test_r13_pii_list_has_no_phone_or_address(self):
        self.make_invoice()
        text = self.get(self.owner).content.decode()
        self.assertNotIn(FAKE_PHONE[:6], text)
        self.assertNotIn("1 Cảng", text)
        self.assertNotIn("phone", text)
        self.assertNotIn("address", text)

    def test_r13_pii_direct_perm_user_only_sees_invoices_in_scope(self):
        mine = self.make_invoice()
        self.make_invoice()
        note = mine.delivery_notes.get()
        courier = make_user(
            "u_direct_courier", roles.DELIVERY_STAFF,
            perms=("sales.view_salesinvoice", "sales.view_customer_list"),
        )
        note.assigned_to = courier
        note.save(update_fields=["assigned_to"])
        body = self.get(courier).json()
        self.assertEqual([r["code"] for r in body["results"]], [mine.code])
        self.assertEqual(body["results"][0]["customer_name"], FAKE_NAME)  # phiếu còn trong cửa sổ xem
        self.assertEqual(body["totals"]["amount"], "100000")  # tổng chỉ gồm hoá đơn trong phạm vi

    def test_r13_pii_name_hidden_when_note_window_expired(self):
        mine = self.make_invoice()
        courier = make_user(
            "u_direct_courier", roles.DELIVERY_STAFF,
            perms=("sales.view_salesinvoice", "sales.view_customer_list"),
        )
        note = mine.delivery_notes.get()
        note.assigned_to = courier
        note.status = note.Status.COMPLETED
        note.completed_at = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
        note.save(update_fields=["assigned_to", "status", "completed_at"])
        row = self.get(courier).json()["results"][0]
        self.assertIsNone(row["customer_name"])
        self.assertNotIn(FAKE_NAME, str(row))


class InvoiceListBuildOnceTests(InvoiceListBase):
    def test_r13_l4_list_builds_filtered_queryset_once(self):
        from unittest import mock

        from apps.sales.payments.api import SalesInvoiceViewSet

        self.make_invoice()
        with mock.patch.object(SalesInvoiceViewSet, "filter_queryset", autospec=True,
                               side_effect=SalesInvoiceViewSet.filter_queryset) as spy:
            self.assertEqual(self.get(self.owner).status_code, 200)
        self.assertEqual(spy.call_count, 1)


class InvoiceListQueryCountTests(InvoiceListBase):
    def run_list(self, user):
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self.get(user).status_code, 200)
        return len(ctx)

    def test_r13_no_n_plus_one_for_owner_and_manager(self):
        self.make_invoice()
        for user in (self.owner, self.manager):
            self.run_list(user)  # làm nóng (cache quyền/content type)
        base = {u.username: self.run_list(u) for u in (self.owner, self.manager)}
        for _ in range(6):
            self.make_invoice()
        for user in (self.owner, self.manager):
            self.assertEqual(self.run_list(user), base[user.username], user.username)
