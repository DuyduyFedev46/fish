"""
R15 (ERP theo design Lô 12, 02b §3.8): báo cáo lãi lỗ cho Chủ (W3a).

- `GET /api/reports/batches/?month=YYYY-MM&state=closed|provisional&page=`: danh sách `batch_pnl` của lô có phát sinh
  trong kỳ (nhập trong tháng, có hoá đơn bán xuất trong tháng, hoặc chốt trong tháng) + `item_name`, `status`,
  `status_label`. Số liệu LÀ kết quả `batch_pnl`, không tính lại công thức.
- `GET /api/reports/period/` thêm `invoice_count`, `refund_count`; các số cũ giữ nguyên.
- Quyền `reports.view_profitreport` (chỉ Chủ): mọi vai khác 403, chưa đăng nhập 401. Toàn bộ là lãi lỗ nên người
  không có quyền không nhận được số nào. Mọi dữ liệu là giả.
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
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier
from apps.reports import services
from apps.sales.models import (
    Customer, Refund, SalesCreditNote, SalesInvoice, SalesInvoiceLine, SalesInvoiceLineBatch, SalesOrder,
)

URL = "/api/reports/batches/"
PERIOD_URL = "/api/reports/period/"
EXPECTED_KEYS = {
    "batch_id", "provisional", "qty_received", "qty_sold", "landed_unit_cost", "revenue", "reversed_qty",
    "reversed_revenue", "purchase_cost", "allocated_cost", "shrinkage_qty", "shrinkage_cost", "damage_qty",
    "damage_cost", "expired_qty", "expired_cost", "supplier_return_qty", "supplier_refund_amount", "total_cost",
    "profit", "item_name", "status", "status_label",
}
PURCHASE_RATE = Decimal("76543")  # số lạ để quét rò


def vn(year, month, day, hour=10):
    return datetime.datetime(year, month, day, hour, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=7)))


class ReportBase(TestCase):
    def setUp(self):
        self.owner = make_user("u_owner", roles.OWNER)
        self.manager = make_user("u_manager", roles.MANAGER)
        self.warehouse_staff = make_user("u_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("u_courier", roles.DELIVERY_STAFF)
        self.customer_service = make_user("u_cs", roles.CUSTOMER_SERVICE)
        self.no_group = User.objects.create_user("u_no_group", password="x")
        group = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=group)
        self.supplier = Supplier.objects.create(name="Đầu mối A")
        self.warehouse = Warehouse.objects.create(name="Kho chính")
        self.seq = 0

    def make_batch(self, received=datetime.date(2026, 9, 10), qty="100", status=None, closed_at=None):
        batch = batch_services.create_batch(
            item=self.item, supplier=self.supplier, warehouse=self.warehouse, received_date=received,
            qty=Decimal(qty), purchase_rate=PURCHASE_RATE,
        )
        if status:
            Batch.objects.filter(pk=batch.pk).update(status=status, closed_at=closed_at)
            batch.refresh_from_db()
        return batch

    def sell(self, batch, *, issued_at, qty="2", rate="150000", status=SalesInvoice.Status.ISSUED, amount=None):
        self.seq += 1
        customer = Customer.objects.create(phone=f"09000009{self.seq:02d}", name=f"Khách Giả {self.seq}")
        total = amount if amount is not None else Decimal(qty) * Decimal(rate)
        order = SalesOrder.objects.create(
            code=f"SO-R{self.seq:03d}", customer=customer, status=SalesOrder.Status.PROCESSING,
            delivery_address="1 Cảng", phone=customer.phone, total_amount=total,
        )
        invoice = SalesInvoice.objects.create(
            code=f"HD-R{self.seq:03d}", sales_order=order, customer=customer, amount=total,
            issued_at=issued_at, status=status,
        )
        line = SalesInvoiceLine.objects.create(
            invoice=invoice, item=self.item, qty=Decimal(qty), rate=Decimal(rate), amount=total,
        )
        SalesInvoiceLineBatch.objects.create(
            invoice_line=line, batch=batch, component_item=self.item, qty=Decimal(qty), unit_cost=PURCHASE_RATE,
        )
        return invoice

    def get(self, user, query=""):
        return client_for(user).get(URL + query)


class BatchesPermissionTests(ReportBase):
    def setUp(self):
        super().setUp()
        self.make_batch()

    def test_r15_ac1_owner_200(self):
        self.assertEqual(self.get(self.owner).status_code, 200)

    def test_r15_ac1_other_groups_403_without_numbers(self):
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service, self.no_group):
            with self.subTest(user=user.username):
                response = self.get(user)
                self.assertEqual(response.status_code, 403)
                text = response.content.decode()
                self.assertNotIn(str(PURCHASE_RATE), text)
                for key in COST_KEYS:
                    self.assertNotIn(f'"{key}"', text)

    def test_r15_ac1_forbidden_even_with_invalid_filter(self):
        self.assertEqual(self.get(self.manager, "?month=bad").status_code, 403)

    def test_r15_ac1_anonymous_401(self):
        self.assertEqual(self.get(None).status_code, 401)

    def test_r15_ac1_user_with_only_view_costprice_is_403(self):
        user = make_user("u_cost", perms=("inventory.view_costprice",))
        self.assertEqual(self.get(user).status_code, 403)

    def test_r15_ac1_user_with_only_view_profitreport_200(self):
        user = make_user("u_profit", perms=("reports.view_profitreport",))
        self.assertEqual(self.get(user).status_code, 200)

    def test_r15_ac1_writes_not_allowed(self):
        self.assertEqual(client_for(self.owner).post(URL, {}, format="json").status_code, 405)


class BatchesContractTests(ReportBase):
    def test_r15_ac2_row_is_batch_pnl_plus_labels(self):
        batch = self.make_batch()
        self.sell(batch, issued_at=vn(2026, 9, 12))
        body = self.get(self.owner, "?month=2026-09").json()
        self.assertEqual(set(body), {"count", "next", "previous", "results"})
        row = body["results"][0]
        self.assertEqual(set(row), EXPECTED_KEYS)
        self.assertEqual(row["batch_id"], batch.batch_id)
        self.assertEqual(row["item_name"], "Cá thu")
        self.assertEqual(row["status"], batch.status)
        self.assertEqual(row["status_label"], batch.get_status_display())
        self.assertTrue(row["provisional"])

    def test_r15_ac2_numbers_equal_batch_pnl(self):
        batch = self.make_batch()
        self.sell(batch, issued_at=vn(2026, 9, 12), qty="2", rate="150000")
        self.sell(batch, issued_at=vn(2026, 9, 14), qty="3", rate="140000")
        expected = services.batch_pnl(batch=batch)
        row = self.get(self.owner, "?month=2026-09").json()["results"][0]
        for key, value in expected.items():
            if isinstance(value, Decimal):
                self.assertEqual(Decimal(row[key]), value, key)
            else:
                self.assertEqual(row[key], value, key)
        self.assertEqual(Decimal(row["revenue"]), Decimal("720000"))

    def test_r15_ac2_cancelled_invoice_not_counted_like_batch_pnl(self):
        batch = self.make_batch()
        self.sell(batch, issued_at=vn(2026, 9, 12), qty="2", rate="150000")
        self.sell(batch, issued_at=vn(2026, 9, 13), qty="5", rate="150000", status=SalesInvoice.Status.CANCELLED)
        row = self.get(self.owner, "?month=2026-09").json()["results"][0]
        self.assertEqual(Decimal(row["revenue"]), Decimal("300000"))
        self.assertEqual(Decimal(row["revenue"]), services.batch_pnl(batch=batch)["revenue"])

    def test_r15_ac2_closed_batch_is_not_provisional(self):
        closed_at = vn(2026, 9, 20)
        self.make_batch(status=Batch.Status.CLOSED, closed_at=closed_at)
        row = self.get(self.owner, "?month=2026-09").json()["results"][0]
        self.assertFalse(row["provisional"])
        self.assertEqual(row["status"], "CLOSED")
        self.assertEqual(row["status_label"], "Đã chốt")

    def test_r15_ac2_empty_period_returns_empty_results(self):
        self.make_batch()
        body = self.get(self.owner, "?month=2025-01").json()
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["results"], [])

    def test_r15_ac2_paginated_20_newest_first(self):
        for day in range(1, 23):
            self.make_batch(received=datetime.date(2026, 9, min(day, 28)))
        body = self.get(self.owner, "?month=2026-09").json()
        self.assertEqual(body["count"], 22)
        self.assertEqual(len(body["results"]), 20)
        self.assertEqual(len(self.get(self.owner, "?month=2026-09&page=2").json()["results"]), 2)
        ids = [r["batch_id"] for r in body["results"]]
        self.assertEqual(ids, sorted(ids, key=lambda b: Batch.objects.get(batch_id=b).received_date, reverse=True))


class BatchesPeriodTests(ReportBase):
    """Lô có phát sinh trong kỳ: nhập trong tháng, có hoá đơn (chưa huỷ) xuất trong tháng, hoặc chốt trong tháng."""

    def ids(self, query):
        response = self.get(self.owner, query)
        self.assertEqual(response.status_code, 200, response.content)
        return {r["batch_id"] for r in response.json()["results"]}

    def test_r15_ac3_received_in_month(self):
        sep = self.make_batch(received=datetime.date(2026, 9, 10))
        oct_ = self.make_batch(received=datetime.date(2026, 10, 2))
        self.assertEqual(self.ids("?month=2026-09"), {sep.batch_id})
        self.assertEqual(self.ids("?month=2026-10"), {oct_.batch_id})

    def test_r15_ac3_sold_in_month_even_if_received_earlier(self):
        batch = self.make_batch(received=datetime.date(2026, 8, 20))
        self.sell(batch, issued_at=vn(2026, 9, 12))
        self.assertEqual(self.ids("?month=2026-09"), {batch.batch_id})
        self.assertEqual(self.ids("?month=2026-08"), {batch.batch_id})
        self.assertEqual(self.ids("?month=2026-10"), set())

    def test_r15_ac3_sold_and_received_same_month_listed_once(self):
        batch = self.make_batch(received=datetime.date(2026, 9, 1))
        self.sell(batch, issued_at=vn(2026, 9, 12))
        self.sell(batch, issued_at=vn(2026, 9, 13))
        self.assertEqual(self.get(self.owner, "?month=2026-09").json()["count"], 1)

    def test_r15_ac3_cancelled_invoice_alone_does_not_bring_batch_in(self):
        batch = self.make_batch(received=datetime.date(2026, 8, 20))
        self.sell(batch, issued_at=vn(2026, 9, 12), status=SalesInvoice.Status.CANCELLED)
        self.assertEqual(self.ids("?month=2026-09"), set())

    def test_r15_ac3_closed_in_month(self):
        batch = self.make_batch(received=datetime.date(2026, 7, 1), status=Batch.Status.CLOSED, closed_at=vn(2026, 9, 28))
        self.assertEqual(self.ids("?month=2026-09"), {batch.batch_id})

    def test_r15_ac3_month_boundary_uses_vietnam_time(self):
        batch = self.make_batch(received=datetime.date(2026, 8, 20))
        # 2026-09-30 18:00 UTC = 2026-10-01 01:00 giờ VN → thuộc tháng 10
        self.sell(batch, issued_at=datetime.datetime(2026, 9, 30, 18, 0, tzinfo=datetime.timezone.utc))
        self.assertIn(batch.batch_id, self.ids("?month=2026-10"))
        self.assertNotIn(batch.batch_id, self.ids("?month=2026-09"))

    def test_r15_ac3_no_month_lists_all_batches(self):
        self.make_batch(received=datetime.date(2026, 9, 10))
        self.make_batch(received=datetime.date(2026, 10, 2))
        self.assertEqual(self.get(self.owner).json()["count"], 2)

    def test_r15_ac4_state_filter(self):
        provisional = self.make_batch(received=datetime.date(2026, 9, 10))
        closed = self.make_batch(received=datetime.date(2026, 9, 11), status=Batch.Status.CLOSED, closed_at=vn(2026, 9, 29))
        self.assertEqual(self.ids("?month=2026-09&state=closed"), {closed.batch_id})
        self.assertEqual(self.ids("?month=2026-09&state=provisional"), {provisional.batch_id})
        self.assertEqual(self.ids("?month=2026-09"), {closed.batch_id, provisional.batch_id})

    def test_r15_ac4_state_only_filter_without_month(self):
        provisional = self.make_batch(received=datetime.date(2026, 9, 10))
        self.make_batch(received=datetime.date(2026, 9, 11), status=Batch.Status.CLOSED, closed_at=vn(2026, 9, 29))
        self.assertEqual(self.ids("?state=provisional"), {provisional.batch_id})

    def test_r15_ac5_invalid_filters_400_without_echo(self):
        self.make_batch()
        for query in ("?month=2026-13", "?month=26-09", "?month=abc", "?month=2026-9", "?state=BOGUS", "?state=Closed"):
            with self.subTest(query=query):
                response = self.get(self.owner, query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "INVALID_FILTER")
                for value in ("2026-13", "abc", "BOGUS", "Closed"):
                    self.assertNotIn(value, response.json()["detail"])


class BatchesQueryCountTests(ReportBase):
    def test_r15_query_count_is_bounded_by_batch_pnl_cost_per_row(self):
        first = self.make_batch(received=datetime.date(2026, 9, 1))
        self.sell(first, issued_at=vn(2026, 9, 12))
        with CaptureQueriesContext(connection) as ctx:
            services.batch_pnl(batch=first)
        per_batch = len(ctx)
        self.get(self.owner, "?month=2026-09")  # làm nóng
        with CaptureQueriesContext(connection) as ctx:
            self.get(self.owner, "?month=2026-09")
        base = len(ctx)
        for day in range(2, 8):
            batch = self.make_batch(received=datetime.date(2026, 9, day))
            self.sell(batch, issued_at=vn(2026, 9, 12))
        with CaptureQueriesContext(connection) as ctx:
            self.get(self.owner, "?month=2026-09")
        # mỗi lô thêm đúng chi phí của một lần `batch_pnl`: không phát sinh thêm truy vấn riêng cho tên mặt hàng, nhãn…
        self.assertEqual(len(ctx) - base, 6 * per_batch)


class PeriodCountsTests(ReportBase):
    def period(self, year=2026, month=9):
        response = client_for(self.owner).get(f"{PERIOD_URL}?year={year}&month={month}")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_r15_ac6_old_keys_unchanged_and_counts_added(self):
        batch = self.make_batch()
        body = self.period()
        self.assertEqual(
            set(body),
            {"year", "month", "revenue", "cogs", "credit_notes", "cogs_reversed", "refunds", "profit",
             "invoice_count", "refund_count"},
        )
        self.assertEqual(body["invoice_count"], 0)
        self.assertEqual(body["refund_count"], 0)
        self.sell(batch, issued_at=vn(2026, 9, 12))
        expected = services.period_pnl(year=2026, month=9)
        body = self.period()
        for key, value in expected.items():
            if isinstance(value, Decimal):
                self.assertEqual(Decimal(body[key]), value, key)

    def test_r15_ac6_invoice_count_counts_issued_in_month_only(self):
        batch = self.make_batch()
        self.sell(batch, issued_at=vn(2026, 9, 12))
        self.sell(batch, issued_at=vn(2026, 9, 30))
        self.sell(batch, issued_at=vn(2026, 9, 13), status=SalesInvoice.Status.CANCELLED)
        self.sell(batch, issued_at=vn(2026, 10, 2))
        self.assertEqual(self.period(2026, 9)["invoice_count"], 2)
        self.assertEqual(self.period(2026, 10)["invoice_count"], 1)

    def test_r15_ac6_invoice_count_matches_period_revenue_basis(self):
        batch = self.make_batch()
        self.sell(batch, issued_at=datetime.datetime(2026, 9, 30, 18, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(self.period(2026, 10)["invoice_count"], 1)
        self.assertEqual(self.period(2026, 9)["invoice_count"], 0)

    def _refund(self, invoice, confirmed_at, amount="50000", status=Refund.Status.REFUNDED):
        return Refund.objects.create(
            sales_invoice=invoice, amount=Decimal(amount), status=status, confirmed_at=confirmed_at,
            bank_txn_ref="FAKE-TXN-1", created_by=self.owner,
        )

    def test_r15_ac6_refund_count_follows_period_pnl_refund_rule(self):
        batch = self.make_batch()
        invoice = self.sell(batch, issued_at=vn(2026, 9, 5))
        other = self.sell(batch, issued_at=vn(2026, 9, 6))
        self._refund(invoice, vn(2026, 9, 20))
        self._refund(other, vn(2026, 9, 21), amount="30000")
        self._refund(other, vn(2026, 9, 22), status=Refund.Status.PENDING, amount="10000")  # chưa hoàn: không tính
        self._refund(other, vn(2026, 10, 3), amount="20000")  # tháng khác
        body = self.period(2026, 9)
        self.assertEqual(body["refund_count"], 2)
        self.assertEqual(Decimal(body["refunds"]), Decimal("80000"))
        self.assertEqual(self.period(2026, 10)["refund_count"], 1)

    def test_r15_ac6_refund_confirmed_after_credit_note_is_not_counted(self):
        batch = self.make_batch()
        invoice = self.sell(batch, issued_at=vn(2026, 9, 5))
        SalesCreditNote.objects.create(
            code="DC-HD-R001", source_key="cancel:fake-1", sales_invoice=invoice, issued_at=vn(2026, 9, 18),
            amount=invoice.amount, stock_restored=True,
        )
        self._refund(invoice, vn(2026, 9, 20))   # sau chứng từ đảo → đã đảo, không trừ lần hai
        self._refund(invoice, vn(2026, 9, 10), amount="10000")  # trước chứng từ đảo → vẫn trừ
        body = self.period(2026, 9)
        self.assertEqual(body["refund_count"], 1)
        self.assertEqual(Decimal(body["refunds"]), Decimal("10000"))

    def test_r15_ac6_refund_without_invoice_is_not_counted(self):
        # phiếu hoàn gắn giao dịch không hoá đơn (S13-AC5) không vào lãi kỳ nên cũng không đếm
        self.assertEqual(self.period()["refund_count"], 0)

    def test_r15_ac6_period_still_403_for_non_owner(self):
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service):
            response = client_for(user).get(f"{PERIOD_URL}?year=2026&month=9")
            self.assertEqual(response.status_code, 403)
            self.assertNotIn("invoice_count", response.content.decode())
