"""
R6 (02b §3.8, ED-29): GET /api/inventory/ledger/ — Sổ nhập xuất, chỉ đọc, append-only (bất biến 4).

- ED-29-AC1: cột đủ, `type_label`, `balance_after`, `created_by_name` ("Hệ thống" khi không có người làm).
- ED-29-AC2: lọc theo khoảng ngày, lô, loại, kho, mặt hàng; `count` đúng với bộ lọc.
- ED-29-AC3: không có thao tác ghi (POST/PUT/PATCH/DELETE → 405).
- ED-29-AC4: nhóm không có `view_stockledgerentry` → 403, chưa đăng nhập → 401.
- Bất biến 1: Sổ chỉ có kg, không có khoá tiền / giá vốn với mọi nhóm.
"""
import datetime
import zoneinfo
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts import roles
from apps.common.tests.fixtures import make_order_with_note
from apps.inventory.models import StockLedgerEntry, StockReconciliation, StockReconciliationLine
from apps.inventory.stock import services as stock_services
from apps.inventory.stocktake import services as stocktake_services

from .base import NON_READERS, READERS, StockApiBase

URL = "/api/inventory/ledger/"
VN = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")
MT = StockLedgerEntry.MovementType

EXPECTED_KEYS = {
    "id", "batch", "batch_code", "item", "item_name", "warehouse", "warehouse_name",
    "movement_type", "type_label", "qty_change", "balance_after",
    "reference", "reference_display", "reference_link", "created_at", "created_by", "created_by_name",
}


class LedgerApiBase(StockApiBase):
    def rows(self, user=None, **params):
        response = self.api(user or self.owner).get(URL, params)
        self.assertEqual(response.status_code, 200, response.content[:300])
        return response.json()["results"]

    def move(self, batch, qty, movement_type, reference="", actor=None):
        return stock_services.record_movement(
            batch=batch, qty_change=Decimal(qty), movement_type=movement_type, reference=reference, actor=actor,
        )


class LedgerPermissionTests(LedgerApiBase):
    def setUp(self):
        super().setUp()
        self.make_batch(actor=self.warehouse_staff)

    def test_ed29_ac4_readers_get_200(self):
        for name in READERS:
            response = self.api(self.users[name]).get(URL)
            self.assertEqual(response.status_code, 200, name)
            self.assertEqual(response.json()["count"], 1, name)

    def test_ed29_ac4_non_readers_get_403(self):
        for name in NON_READERS:
            self.assertEqual(self.api(self.users[name]).get(URL).status_code, 403, name)
        self.assertEqual(self.api(self.no_group).get(URL).status_code, 403)

    def test_ed29_ac4_anonymous_gets_401(self):
        self.assertEqual(self.api(None).get(URL).status_code, 401)

    def test_ed29_ac3_ledger_is_read_only(self):
        entry = StockLedgerEntry.objects.get()
        for method in ("post", "put", "patch", "delete"):
            for url in (URL, f"{URL}{entry.pk}/"):
                response = getattr(self.api(self.owner), method)(url, {}, format="json")
                self.assertIn(response.status_code, (404, 405), (method, url, response.status_code))
        self.assertEqual(StockLedgerEntry.objects.count(), 1)

    def test_ed29_retrieve_one_entry_has_same_fields(self):
        entry = StockLedgerEntry.objects.get()
        response = self.api(self.owner).get(f"{URL}{entry.pk}/")
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertEqual(set(response.json()), EXPECTED_KEYS)


class LedgerContractTests(LedgerApiBase):
    def test_ed29_ac1_exact_key_set_and_no_cost_for_every_group(self):
        batch = self.make_batch(actor=self.warehouse_staff)
        self.move(batch, "-10", MT.SALE, "INV-X")
        for name in READERS:
            response = self.api(self.users[name]).get(URL)
            self.assert_no_cost(response, who=name)
            for row in response.json()["results"]:
                self.assertEqual(set(row), EXPECTED_KEYS, name)

    def test_ed29_ac1_display_values(self):
        batch = self.make_batch(actor=self.warehouse_staff)
        (row,) = self.rows()
        self.assertEqual(row["batch"], batch.pk)
        self.assertEqual(row["batch_code"], batch.batch_id)
        self.assertEqual(row["item"], self.item.pk)
        self.assertEqual(row["item_name"], "Cá thu")
        self.assertEqual(row["warehouse"], self.wh.pk)
        self.assertEqual(row["warehouse_name"], "Kho chính")
        self.assertEqual(row["movement_type"], "RECEIPT")
        self.assertEqual(row["type_label"], "Nhập lô")
        self.assertEqual(row["qty_change"], "100.000")
        self.assertEqual(row["balance_after"], "100.000")

    def test_ed29_ac1_write_off_label_is_overridden(self):
        batch = self.make_batch()
        self.move(batch, "0", MT.WRITE_OFF, "return 3 (huỷ bỏ, lỗ 0kg)")
        labels = {row["movement_type"]: row["type_label"] for row in self.rows()}
        self.assertEqual(labels["WRITE_OFF"], "Ghi lỗ, huỷ hàng")
        # Nhãn khác giữ đúng nhãn của model (enum-map).
        self.assertEqual(labels["RECEIPT"], "Nhập lô")

    def test_ed29_ac1_type_label_covers_every_movement_type(self):
        batch = self.make_batch()
        for movement_type, _label in MT.choices:
            self.move(batch, "0", movement_type)
        for row in self.rows():
            self.assertTrue(row["type_label"], row["movement_type"])

    def test_ed29_ac1_created_by_name_user_profile_username_and_system(self):
        batch = self.make_batch(actor=self.warehouse_staff)           # có hồ sơ: "Kho Thử"
        self.move(batch, "-1", MT.SALE, "INV-A", actor=self.manager)  # không hồ sơ: tên đăng nhập
        self.move(batch, "-1", MT.SALE, "INV-B", actor=None)          # Hệ thống
        names = [row["created_by_name"] for row in self.rows()]       # mới nhất trước
        self.assertEqual(names, ["Hệ thống", "u_manager", "Kho Thử"])
        for row in self.rows():
            self.assertNotIn("0900000999", str(row))  # không lộ SĐT nhân viên

    def test_ed29_orders_newest_first(self):
        batch = self.make_batch()
        self.move(batch, "-1", MT.SALE, "INV-A")
        self.move(batch, "-1", MT.SALE, "INV-B")
        self.assertEqual([r["reference"] for r in self.rows()], ["INV-B", "INV-A", f"create_batch {batch.batch_id}"])


class LedgerBalanceTests(LedgerApiBase):
    """`balance_after` = tổng lũy kế `qty_change` của lô đến dòng đó, KHÔNG phụ thuộc bộ lọc."""

    def _chain(self):
        """Nhập 100 → bán 30 → kiểm kê (sổ 70, đếm 65, chênh -5)."""
        batch = self.make_batch(qty="100", actor=self.warehouse_staff)
        order, _customer, _note = make_order_with_note("SO-T1", "0900000123")
        self.move(batch, "-30", MT.SALE, order.invoice.code)
        recon = StockReconciliation.objects.create(count_date=self.today, created_by=self.warehouse_staff)
        StockReconciliationLine.objects.create(
            reconciliation=recon, batch=batch, system_qty=Decimal("70"), counted_qty=Decimal("65"),
        )
        stocktake_services.apply_reconciliation(reconciliation=recon, approver=self.manager)
        batch.refresh_from_db()
        self.assertEqual(batch.qty_available, Decimal("65"))
        return batch

    def test_ed29_balance_after_chain_receipt_sale_stocktake(self):
        self._chain()
        rows = list(reversed(self.rows()))  # cũ → mới
        self.assertEqual([r["movement_type"] for r in rows], ["RECEIPT", "SALE", "RECONCILE"])
        self.assertEqual([r["qty_change"] for r in rows], ["100.000", "-30.000", "-5.000"])
        self.assertEqual([r["balance_after"] for r in rows], ["100.000", "70.000", "65.000"])

    def test_ed29_balance_after_last_row_equals_batch_stock(self):
        batch = self._chain()
        newest = self.rows(batch=batch.pk)[0]
        self.assertEqual(Decimal(newest["balance_after"]), batch.qty_available)

    def test_ed29_balance_after_stays_correct_when_filtered(self):
        batch = self._chain()
        by_type = self.rows(movement_type="SALE")
        self.assertEqual([r["balance_after"] for r in by_type], ["70.000"])  # không phải -30
        by_type = self.rows(movement_type="RECONCILE")
        self.assertEqual([r["balance_after"] for r in by_type], ["65.000"])
        entries = list(StockLedgerEntry.objects.filter(batch=batch).order_by("id"))
        yesterday = self.today - datetime.timedelta(days=1)
        entries[0].created_at = datetime.datetime.combine(yesterday, datetime.time(9, 0), VN)
        StockLedgerEntry.objects.filter(pk=entries[0].pk).update(created_at=entries[0].created_at)
        today_rows = self.rows(date_from=self.today.isoformat())
        self.assertEqual([r["balance_after"] for r in reversed(today_rows)], ["70.000", "65.000"])

    def test_ed29_balance_after_is_per_batch(self):
        batch_a = self.make_batch(qty="100")
        batch_b = self.make_batch(item=self.item2, qty="40")
        self.move(batch_a, "-10", MT.SALE, "INV-A")
        self.move(batch_b, "-5", MT.SALE, "INV-B")
        self.move(batch_a, "-10", MT.SALE, "INV-C")
        by_ref = {r["reference"]: r["balance_after"] for r in self.rows()}
        self.assertEqual(by_ref["INV-A"], "90.000")
        self.assertEqual(by_ref["INV-B"], "35.000")
        self.assertEqual(by_ref["INV-C"], "80.000")

    def test_ed29_balance_after_with_equal_timestamps_uses_id_order(self):
        batch = self.make_batch(qty="100")
        first = self.move(batch, "-10", MT.SALE, "INV-A")
        self.move(batch, "-10", MT.SALE, "INV-B")
        StockLedgerEntry.objects.filter(batch=batch).update(created_at=first.created_at)
        by_ref = {r["reference"]: r["balance_after"] for r in self.rows()}
        self.assertEqual(by_ref["INV-A"], "90.000")
        self.assertEqual(by_ref["INV-B"], "80.000")


class LedgerReferenceTests(LedgerApiBase):
    def _by_ref(self):
        return {r["reference"]: r for r in self.rows()}

    def test_ed29_reference_display_and_link_per_kind(self):
        receipt, receipt_batch = self.make_receipt_batch(actor=self.warehouse_staff)
        batch = self.make_batch(qty="200")
        order, _customer, _note = make_order_with_note("SO-T2", "0900000124")
        self.move(batch, "-1", MT.SALE, order.invoice.code)
        self.move(batch, "1", MT.CANCEL_RESTORE, f"cancel {order.code}")
        self.move(batch, "1", MT.RECONCILE, "reconciliation 12")
        self.move(batch, "1", MT.RETURN_RESTOCK, "return 7 (hàng hoàn)")
        self.move(batch, "0", MT.WRITE_OFF, "return 8 (huỷ bỏ, lỗ 3kg)")
        self.move(batch, "-1", MT.SUPPLIER_RETURN, "supplier_return SR-5")
        self.move(batch, "-1", MT.WRITE_OFF, f"cancel_expired_batch {batch.batch_id}")
        self.move(batch, "-1", MT.WRITE_OFF, f"cancel_purchase_receipt PR-{receipt.pk}")
        self.move(batch, "1", MT.RECEIPT, "Nhập lô DEMO-01")
        self.move(batch, "1", MT.RECEIPT, "")
        refs = self._by_ref()

        def check(ref, display, link):
            self.assertEqual(refs[ref]["reference_display"], display, ref)
            self.assertEqual(refs[ref]["reference_link"], link, ref)

        check(f"create_batch {receipt_batch.batch_id}", f"PR-{receipt.pk}", {"kind": "receipt", "id": receipt.pk})
        check(f"create_batch {batch.batch_id}", batch.batch_id, {"kind": "batch", "id": batch.pk})
        check(order.invoice.code, order.invoice.code, {"kind": "invoice", "id": order.invoice.pk})
        check(f"cancel {order.code}", order.code, {"kind": "order", "id": order.pk})
        check("reconciliation 12", "KK-12", {"kind": "stocktake", "id": 12})
        check("return 7 (hàng hoàn)", "RT-7", {"kind": "return", "id": 7})
        check("return 8 (huỷ bỏ, lỗ 3kg)", "RT-8", {"kind": "return", "id": 8})
        check("supplier_return SR-5", "SR-5", {"kind": "supplier_return", "id": 5})
        check(f"cancel_expired_batch {batch.batch_id}", batch.batch_id, {"kind": "batch", "id": batch.pk})
        check(f"cancel_purchase_receipt PR-{receipt.pk}", f"PR-{receipt.pk}", {"kind": "receipt", "id": receipt.pk})
        check("Nhập lô DEMO-01", "Nhập lô DEMO-01", None)
        check("", "", None)

    def test_ed29_reference_to_unknown_document_has_no_link(self):
        batch = self.make_batch()
        self.move(batch, "-1", MT.SALE, "INV-NOT-EXIST")
        self.move(batch, "1", MT.CANCEL_RESTORE, "cancel SO-NOT-EXIST")
        refs = self._by_ref()
        self.assertIsNone(refs["INV-NOT-EXIST"]["reference_link"])
        self.assertEqual(refs["INV-NOT-EXIST"]["reference_display"], "INV-NOT-EXIST")
        self.assertIsNone(refs["cancel SO-NOT-EXIST"]["reference_link"])

    def test_ed29_malformed_reference_does_not_break(self):
        batch = self.make_batch()
        for reference in ("reconciliation abc", "return ", "supplier_return SR-", "reconciliation " + "9" * 40,
                          "cancel_purchase_receipt PR-" + "9" * 40):
            self.move(batch, "1", MT.RECONCILE, reference)
        refs = self._by_ref()
        for reference in ("reconciliation abc", "return ", "supplier_return SR-"):
            self.assertIsNone(refs[reference]["reference_link"], reference)
        for reference in ("reconciliation " + "9" * 40, "cancel_purchase_receipt PR-" + "9" * 40):
            self.assertIsNone(refs[reference]["reference_link"], reference)


class LedgerFilterTests(LedgerApiBase):
    def setUp(self):
        super().setUp()
        self.batch_a = self.make_batch(qty="100")                                    # CA01, kho chính
        self.batch_b = self.make_batch(item=self.item2, warehouse=self.wh2, qty="40")  # CA02, kho lạnh
        self.move(self.batch_a, "-10", MT.SALE, "INV-A")
        self.move(self.batch_b, "-5", MT.WRITE_OFF, "cancel_expired_batch X")
        self.move(self.batch_b, "1", MT.RECONCILE, "reconciliation 1")

    def refs(self, **params):
        return {r["reference"] for r in self.rows(**params)}

    def test_ed29_ac2_filter_by_batch(self):
        refs = self.refs(batch=self.batch_a.pk)
        self.assertEqual(refs, {f"create_batch {self.batch_a.batch_id}", "INV-A"})

    def test_ed29_ac2_filter_by_movement_type_multiple(self):
        self.assertEqual(self.refs(movement_type="SALE"), {"INV-A"})
        self.assertEqual(self.refs(movement_type="SALE,WRITE_OFF"), {"INV-A", "cancel_expired_batch X"})
        self.assertEqual(self.refs(movement_type=" SALE , RECONCILE "), {"INV-A", "reconciliation 1"})

    def test_ed29_ac2_filter_by_warehouse_and_item(self):
        self.assertEqual(len(self.rows(warehouse=self.wh2.pk)), 3)   # lô B: nhập, ghi lỗ, kiểm kê
        self.assertEqual({r["batch"] for r in self.rows(warehouse=self.wh.pk)}, {self.batch_a.pk})
        self.assertEqual({r["batch"] for r in self.rows(item=self.item2.pk)}, {self.batch_b.pk})
        self.assertEqual(self.rows(warehouse=self.wh.pk, item=self.item2.pk), [])

    def test_ed29_ac2_filter_by_date_uses_vietnam_time(self):
        day = datetime.date(2026, 10, 1)
        StockLedgerEntry.objects.update(created_at=datetime.datetime(2026, 10, 5, 12, 0, tzinfo=VN))
        # 00:30 ngày 01/10 giờ VN = 17:30 ngày 30/09 UTC → thuộc ngày 01/10.
        StockLedgerEntry.objects.filter(reference="INV-A").update(
            created_at=datetime.datetime(2026, 10, 1, 0, 30, tzinfo=VN))
        StockLedgerEntry.objects.filter(reference="reconciliation 1").update(
            created_at=datetime.datetime(2026, 10, 1, 23, 59, tzinfo=VN))
        in_day = self.refs(date_from=day.isoformat(), date_to=day.isoformat())
        self.assertEqual(in_day, {"INV-A", "reconciliation 1"})
        self.assertEqual(self.refs(date_to="2026-09-30"), set())
        after = self.refs(date_from="2026-10-02")
        self.assertNotIn("INV-A", after)
        self.assertNotIn("reconciliation 1", after)
        self.assertEqual(len(after), 3)  # ba dòng còn lại ở ngày 05/10
        self.assertEqual(self.refs(date_from="2026-10-05", date_to="2026-10-05"), after)

    def test_ed29_ac2_count_matches_filter(self):
        response = self.api(self.owner).get(URL, {"movement_type": "SALE,RECONCILE"})
        self.assertEqual(response.json()["count"], 2)

    def test_ed29_pagination_page_size_20(self):
        batch = self.make_batch(qty="500")
        for i in range(24):
            self.move(batch, "-1", MT.SALE, f"INV-P{i}")
        first = self.api(self.owner).get(URL, {"batch": batch.pk}).json()
        self.assertEqual(first["count"], 25)
        self.assertEqual(len(first["results"]), 20)
        second = self.api(self.owner).get(URL, {"batch": batch.pk, "page": 2}).json()
        self.assertEqual(len(second["results"]), 5)
        # balance_after đúng trên trang 2 (dòng cũ nhất = nhập 500).
        self.assertEqual(second["results"][-1]["balance_after"], "500.000")

    def test_ed29_empty_filter_values_mean_no_filter(self):
        total = self.api(self.owner).get(URL).json()["count"]
        params = {"batch": "", "movement_type": "", "warehouse": "", "item": "", "date_from": "", "date_to": ""}
        self.assertEqual(self.api(self.owner).get(URL, params).json()["count"], total)

    def test_ed29_unknown_ids_give_empty_list(self):
        self.assertEqual(self.rows(batch=999999), [])
        self.assertEqual(self.rows(warehouse=999999), [])
        self.assertEqual(self.rows(item=999999), [])

    def test_ed29_invalid_filters_get_400_without_echo(self):
        bad = {
            "batch": ["abc", "0", "-1", "1.5", "+5", "١٢٣", "9" * 25, str(2**63)],
            "warehouse": ["x", "0"],
            "item": ["x", "0"],
            "movement_type": ["NOT_A_TYPE", "SALE,NOT_A_TYPE"],
            "date_from": ["2026-13-01", "20261001", "2026-10-1", "abc", "2026-02-30"],
            "date_to": ["2026-13-01", "abc"],
        }
        for name, values in bad.items():
            for value in values:
                response = self.api(self.owner).get(URL, {name: value})
                self.assertEqual(response.status_code, 400, (name, value, response.content[:200]))
                body = response.json()
                self.assertEqual(body["code"], "INVALID_FILTER", (name, value))
                self.assertIn(name, body["detail"])
                if len(value.strip()) > 3:
                    self.assertNotIn(value, response.content.decode(), (name, value))

    def test_ed29_invalid_filter_checked_after_permission(self):
        response = self.api(self.users[roles.DELIVERY_STAFF]).get(URL, {"batch": "abc"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.api(None).get(URL, {"batch": "abc"}).status_code, 401)


class LedgerQueryCountTests(LedgerApiBase):
    def _count(self):
        user = User.objects.get(pk=self.warehouse_staff.pk)  # bỏ cache quyền để mỗi lần đếm như nhau
        with CaptureQueriesContext(connection) as ctx:
            response = self.api(user).get(URL)
        self.assertEqual(response.status_code, 200)
        return len(ctx), response.json()["count"]

    def _seed(self, n):
        for i in range(n):
            batch = self.make_batch(qty="50", actor=self.warehouse_staff)
            order, _c, _n = make_order_with_note(f"SO-Q{n}-{i}", f"09{n:02d}{i:06d}")
            self.move(batch, "-1", MT.SALE, order.invoice.code, actor=None)
            self.move(batch, "1", MT.CANCEL_RESTORE, f"cancel {order.code}", actor=self.manager)
            self.move(batch, "1", MT.RECONCILE, f"reconciliation {i + 1}", actor=self.warehouse_staff)

    def test_ed29_no_n_plus_one(self):
        self._seed(1)
        small_queries, small_count = self._count()
        self._seed(5)
        big_queries, big_count = self._count()
        self.assertGreater(big_count, small_count)
        self.assertEqual(big_queries, small_queries, "số truy vấn không được tăng theo số dòng")
        self.assertLessEqual(big_queries, 12)
