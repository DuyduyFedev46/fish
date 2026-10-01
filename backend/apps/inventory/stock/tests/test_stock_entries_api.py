"""
R7b (02b §3.8, ED-24): GET /api/inventory/stock-entries/ — danh sách phiếu điều chỉnh kho, chỉ đọc.

- ED-24-AC1: cột mã `SE-n`, mục đích, lô, mặt hàng, biến động, người làm, ngày.
- ED-24-AC2: lọc theo mục đích và theo ngày.
- D-1: đợt này không có form điều chỉnh tồn; phiếu (nếu có tạo qua API cũ) không đổi tồn, không ghi sổ.
- ED-24-AC4: nhóm không có `view_stockentry` → 403; chưa đăng nhập → 401; không rò giá vốn.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.inventory.models import StockEntry, StockLedgerEntry

from .base import NON_READERS, READERS, StockApiBase

URL = "/api/inventory/stock-entries/"
EXPECTED_KEYS = {
    "id", "code", "purpose", "purpose_label", "batch", "batch_code", "item_name",
    "qty_change", "reason", "created_by", "created_by_name", "created_at",
}
MATERIAL, ADJUSTMENT = StockEntry.Purpose.MATERIAL_RECEIPT, StockEntry.Purpose.ADJUSTMENT


def vn(year, month, day, hour, minute):
    return datetime.datetime(year, month, day, hour, minute, tzinfo=timezone.get_current_timezone())


class StockEntryBase(StockApiBase):
    def make_entry(self, *, batch=None, purpose=ADJUSTMENT, qty="-1", actor=None, when=None):
        entry = StockEntry.objects.create(
            purpose=purpose, batch=batch or self.batch, qty_change=Decimal(qty), reason="kiểm đếm",
            created_by=actor or self.warehouse_staff,
        )
        if when:
            StockEntry.objects.filter(pk=entry.pk).update(created_at=when)
        return entry

    def setUp(self):
        super().setUp()
        self.batch = self.make_batch(qty="40")


class StockEntryListTests(StockEntryBase):
    def test_ed24_ac4_readers_get_200_others_403_401(self):
        for name in READERS:
            self.assertEqual(self.api(self.users[name]).get(URL).status_code, 200, name)
        for name in NON_READERS:
            self.assertEqual(self.api(self.users[name]).get(URL).status_code, 403, name)
        self.assertEqual(self.api(self.no_group).get(URL).status_code, 403)
        self.assertEqual(self.api(None).get(URL).status_code, 401)

    def test_ed24_ac1_exact_keys_and_display_fields(self):
        entry = self.make_entry(purpose=MATERIAL, qty="2.5")
        row = self.api(self.owner).get(URL).json()["results"][0]
        self.assertEqual(set(row), EXPECTED_KEYS)
        self.assertEqual(row["code"], f"SE-{entry.pk}")
        self.assertEqual(row["purpose_label"], "Nhập vật tư")
        self.assertEqual(row["batch_code"], self.batch.batch_id)
        self.assertEqual(row["item_name"], "Cá thu")
        self.assertEqual(row["created_by_name"], "Kho Thử")
        self.assertEqual(row["qty_change"], "2.500")

    def test_ed24_created_by_name_never_a_phone_number(self):
        self.make_entry()
        body = self.api(self.owner).get(URL).content.decode()
        self.assertNotIn("0900000999", body)

    def test_ed24_created_by_name_falls_back_to_username(self):
        self.make_entry(actor=self.manager)
        row = self.api(self.owner).get(URL).json()["results"][0]
        self.assertEqual(row["created_by_name"], "u_manager")

    def test_ed24_ac4_no_cost_for_every_reader(self):
        self.make_entry()
        for name in READERS:
            self.assert_no_cost(self.api(self.users[name]).get(URL), who=name)
        entry_id = StockEntry.objects.get().pk
        self.assert_no_cost(self.api(self.manager).get(f"{URL}{entry_id}/"), who="retrieve")

    def test_ed24_newest_first_and_paginated(self):
        for i in range(25):
            self.make_entry(qty=str(-i - 1))
        body = self.api(self.owner).get(URL).json()
        self.assertEqual(body["count"], 25)
        self.assertEqual(len(body["results"]), 20)
        ids = [r["id"] for r in body["results"]]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_ed24_ac2_filter_by_purpose(self):
        a = self.make_entry(purpose=MATERIAL)
        b = self.make_entry(purpose=ADJUSTMENT)
        ids = lambda q: {r["id"] for r in self.api(self.owner).get(URL + q).json()["results"]}  # noqa: E731
        self.assertEqual(ids(f"?purpose={MATERIAL}"), {a.pk})
        self.assertEqual(ids(f"?purpose={ADJUSTMENT}"), {b.pk})
        self.assertEqual(ids(f"?purpose={MATERIAL},{ADJUSTMENT}"), {a.pk, b.pk})
        self.assertEqual(ids("?purpose="), {a.pk, b.pk})

    def test_ed24_ac2_filter_by_date_uses_vietnam_time(self):
        old = self.make_entry(when=vn(2026, 10, 1, 0, 30))
        late = self.make_entry(when=vn(2026, 10, 1, 23, 59))
        nxt = self.make_entry(when=vn(2026, 10, 2, 0, 5))
        ids = lambda q: {r["id"] for r in self.api(self.owner).get(URL + q).json()["results"]}  # noqa: E731
        self.assertEqual(ids("?date_from=2026-10-01&date_to=2026-10-01"), {old.pk, late.pk})
        self.assertEqual(ids("?date_from=2026-10-02&date_to=2026-10-02"), {nxt.pk})
        self.assertEqual(ids("?date_to=2026-10-01"), {old.pk, late.pk})

    def test_ed24_invalid_filters_get_400_without_echo(self):
        for query, secret in (
            ("purpose=HACKME_SECRET", "HACKME_SECRET"),
            ("date_from=ngay-sai-SECRET", "ngay-sai-SECRET"),
            ("date_to=2026-13-45", "2026-13-45"),
        ):
            response = self.api(self.owner).get(f"{URL}?{query}")
            self.assertEqual(response.status_code, 400, query)
            self.assertEqual(response.json()["code"], "INVALID_FILTER", query)
            self.assertNotIn(secret, response.content.decode(), query)

    def test_ed24_no_n_plus_one(self):
        def count():
            user = User.objects.get(pk=self.manager.pk)
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.api(user).get(URL).status_code, 200)
            return len(ctx)

        self.make_entry()
        small = count()
        for i in range(6):
            other = self.make_batch(item=self.item2, qty="5")
            self.make_entry(batch=other, actor=self.manager if i % 2 else self.warehouse_staff)
        self.assertEqual(count(), small)


class StockEntryNoStockChangeTests(StockEntryBase):
    def test_d1_creating_an_entry_does_not_change_stock_or_ledger(self):
        before_qty = self.batch.qty_available
        before_ledger = StockLedgerEntry.objects.count()
        response = self.api(self.warehouse_staff).post(
            URL, {"purpose": ADJUSTMENT, "batch": self.batch.pk, "qty_change": "-5", "reason": "hỏng"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, before_qty)
        self.assertEqual(StockLedgerEntry.objects.count(), before_ledger)

    def test_d1_delivery_and_customer_service_cannot_create(self):
        for name in NON_READERS:
            response = self.api(self.users[name]).post(
                URL, {"purpose": ADJUSTMENT, "batch": self.batch.pk, "qty_change": "-1"}, format="json",
            )
            self.assertEqual(response.status_code, 403, name)
        self.assertEqual(StockEntry.objects.count(), 0)

    def test_d1_delete_is_not_available(self):
        entry = self.make_entry()
        self.assertEqual(self.api(self.owner).delete(f"{URL}{entry.pk}/").status_code, 405)
        self.assertTrue(StockEntry.objects.filter(pk=entry.pk).exists())

    def test_d1_entries_cannot_be_edited_after_creation(self):
        """QA Lô 7 L7-B1: PATCH/PUT từng sửa được qty_change/reason mà không để dấu vết."""
        entry = self.make_entry()
        before = (entry.qty_change, entry.reason)
        for user in (self.owner, self.warehouse_staff):
            client = self.api(user)
            self.assertEqual(client.patch(f"{URL}{entry.pk}/", {"reason": "sửa"}, format="json").status_code, 405)
            self.assertEqual(client.put(f"{URL}{entry.pk}/", {"reason": "sửa"}, format="json").status_code, 405)
        entry.refresh_from_db()
        self.assertEqual((entry.qty_change, entry.reason), before)
