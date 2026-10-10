"""
SHOP-2-02 — tạo đơn Shop kiểm số lượng (BR-BH-22) và trả lỗi hết hàng có cấu trúc (BR-BH-24).
G1 (không số kg tồn) và G3 (không mã lô) kiểm trên toàn chuỗi JSON. Bất biến 9: không log dữ liệu khách.
Dữ liệu giả (tên, SĐT, địa chỉ).
"""
import datetime
import json
import logging
from decimal import Decimal
from unittest import mock

from django.test import override_settings
from rest_framework.test import APIClient

from apps.catalog.models import BundleLine, Item
from apps.common.exceptions import BusinessError
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, StockLedgerEntry
from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderLineBatch
from apps.sales.orders import services
from apps.sales.orders.shop_errors import InvalidQtyError, OutOfStockError

from .base import SalesServiceBase

FAKE_PHONE = "0900000001"
FAKE_NAME = "Nguyễn Văn A"
FAKE_ADDRESS = "1 Đường Thử, Phường Mẫu"


class ShopCreateBase(SalesServiceBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def combo(self, code, parts, price="450000"):
        combo = self._item(code, price=price, item_type=Item.ItemType.BUNDLE)
        for component, qty in parts:
            BundleLine.objects.create(bundle=combo, component=component, qty_per_bundle=Decimal(str(qty)))
        return combo

    def post(self, items, **extra):
        body = {
            "customer": {"phone": FAKE_PHONE, "name": FAKE_NAME},
            "delivery_address": FAKE_ADDRESS,
            "phone": FAKE_PHONE,
            "items": [{"item_code": code, "qty": str(qty)} for code, qty in items],
        }
        body.update(extra)
        return self.client.post("/api/shop/orders/", body, format="json")

    def snapshot(self):
        return {
            "orders": SalesOrder.objects.count(),
            "lines": SalesOrderLine.objects.count(),
            "allocations": SalesOrderLineBatch.objects.count(),
            "ledger": StockLedgerEntry.objects.count(),
            "reserved": [str(q) for q in Batch.objects.order_by("pk").values_list("qty_reserved", flat=True)],
        }


class ValidQtyTests(ShopCreateBase):
    def test_s2_02_ac1_valid_kg_quantities_create_order(self):
        self._stocked_batch(self._item("MUC-ONG", price="278000"), "50")
        for qty in ("1", "1.5", "2", "10.5"):
            resp = self.post([("MUC-ONG", qty)])
            self.assertEqual(resp.status_code, 201, f"{qty}: {resp.content}")

    def test_s2_02_ac1_combo_whole_numbers_create_order(self):
        part = self._item("MUC-ONG", price="278000")
        self._stocked_batch(part, "50")
        self.combo("COMBO-LAU", [(part, "0.5")])
        for qty in ("1", "3"):
            self.assertEqual(self.post([("COMBO-LAU", qty)]).status_code, 201, qty)

    def test_success_response_total_is_whole_vnd_string(self):
        self._stocked_batch(self._item("MUC-ONG", price="100000"), "50")
        data = self.post([("MUC-ONG", "3")]).json()
        self.assertEqual(data["total_amount"], "300000")  # SHOP-3-01: money_str, không còn ".00"


class InvalidQtyTests(ShopCreateBase):
    def setUp(self):
        super().setUp()
        self.simple = self._item("MUC-ONG", price="278000")
        self._stocked_batch(self.simple, "50")
        self.combo("COMBO-LAU", [(self.simple, "0.5")])
        self.combo("COMBO-NUONG", [(self.simple, "0.5")])

    def assert_invalid_qty(self, resp, expected_codes):
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "INVALID_QTY")
        self.assertEqual(body["detail"], "Số lượng không hợp lệ.")
        self.assertEqual([line["item_code"] for line in body["lines"]], expected_codes)
        return body

    def test_s2_02_ac2_bad_kg_quantities_rejected_without_side_effects(self):
        before = self.snapshot()
        for qty in ("0.5", "0.3", "1.25", "0", "-1", "0.999"):
            with self.subTest(qty=qty):
                body = self.assert_invalid_qty(self.post([("MUC-ONG", qty)]), ["MUC-ONG"])
                self.assertEqual(body["lines"][0], {"item_code": "MUC-ONG", "min_qty": "1", "qty_step": "0.5"})
                self.assertEqual(self.snapshot(), before)

    def test_s2_02_ac2_bad_combo_quantities_rejected_without_side_effects(self):
        before = self.snapshot()
        for qty in ("1.5", "0", "-1", "0.5"):
            with self.subTest(qty=qty):
                body = self.assert_invalid_qty(self.post([("COMBO-LAU", qty)]), ["COMBO-LAU"])
                self.assertEqual(body["lines"][0], {"item_code": "COMBO-LAU", "min_qty": "1", "qty_step": "1"})
                self.assertEqual(self.snapshot(), before)

    def test_s2_02_ac2_lists_every_bad_line_and_only_bad_lines(self):
        before = self.snapshot()
        resp = self.post([("MUC-ONG", "0.5"), ("COMBO-LAU", "2"), ("COMBO-NUONG", "1.5")])
        # dòng hợp lệ (combo 2) không bị liệt kê; hai dòng sai theo đúng thứ tự gửi
        self.assertEqual(resp.status_code, 400)
        self.assertEqual([l["item_code"] for l in resp.json()["lines"]], ["MUC-ONG", "COMBO-NUONG"])
        self.assertEqual(self.snapshot(), before)

    def test_s2_02_ac5_step_comes_from_settings(self):
        with override_settings(SHOP_QTY_STEP_KG=Decimal("1")):
            body = self.assert_invalid_qty(self.post([("MUC-ONG", "1.5")]), ["MUC-ONG"])
            self.assertEqual(body["lines"][0]["qty_step"], "1")
            self.assertEqual(self.post([("MUC-ONG", "2")]).status_code, 201)

    def test_min_comes_from_settings(self):
        with override_settings(SHOP_MIN_QTY_KG=Decimal("2")):
            self.assert_invalid_qty(self.post([("MUC-ONG", "1.5")]), ["MUC-ONG"])
            self.assertEqual(self.post([("MUC-ONG", "2")]).status_code, 201)

    def test_unparseable_quantity_is_validation_error_not_500(self):
        before = self.snapshot()
        for qty in ("abc", "NaN", "Infinity", "", None):
            with self.subTest(qty=qty):
                resp = self.client.post(
                    "/api/shop/orders/",
                    {"customer": {"phone": FAKE_PHONE, "name": FAKE_NAME}, "delivery_address": FAKE_ADDRESS,
                     "items": [{"item_code": "MUC-ONG", "qty": qty}]},
                    format="json",
                )
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "VALIDATION")
                self.assertIn("items", resp.json()["fields"])
                self.assertEqual(self.snapshot(), before)

    def test_review_m1_huge_or_odd_numbers_never_500(self):
        """Review lô 1 M1: "1e30", "-0", rất nhiều chữ số thập phân… -> 400 có code, không 500, không ghi DB."""
        before = self.snapshot()
        odd = ["1e30", "1E30", "-0", "0e0", "1e-30", "1." + "0" * 60 + "1", "9" * 80, "1e999999999", "-1e30"]
        for qty in odd:
            for code in ("MUC-ONG", "COMBO-LAU"):
                with self.subTest(qty=qty, code=code):
                    resp = self.post([(code, qty)])
                    self.assertIn(resp.status_code, (400,), resp.content)
                    self.assertIn(resp.json()["code"], {"INVALID_QTY", "VALIDATION", "OUT_OF_STOCK"})
                    self.assertEqual(self.snapshot(), before)

    def test_service_raises_invalid_qty_before_any_write(self):
        before = self.snapshot()
        with self.assertRaises(InvalidQtyError) as caught:
            services.create_order(
                customer_phone=FAKE_PHONE, customer_name=FAKE_NAME, delivery_address=FAKE_ADDRESS,
                phone=FAKE_PHONE, lines=[{"item_code": "MUC-ONG", "qty": Decimal("0.5")}],
            )
        self.assertEqual(caught.exception.code, "INVALID_QTY")
        self.assertEqual(self.snapshot(), before)


class OutOfStockTests(ShopCreateBase):
    def setUp(self):
        super().setUp()
        self.short_item = self._item("MUC-ONG", price="278000")
        self.batch = self._stocked_batch(self.short_item, "1.5")
        self.empty_item = self._item("TOM-SU", price="300000")

    def assert_out_of_stock(self, resp, expected):
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "OUT_OF_STOCK")
        self.assertEqual(body["detail"], "Một số món vừa hết hàng.")
        self.assertEqual(body["lines"], expected)
        return body

    def test_s2_02_ac3_short_and_out_lines_without_kg_or_batch_code(self):
        before = self.snapshot()
        resp = self.post([("MUC-ONG", "2"), ("TOM-SU", "1")])
        self.assert_out_of_stock(
            resp,
            [
                {"item_code": "MUC-ONG", "stock_level": "short"},
                {"item_code": "TOM-SU", "stock_level": "out"},
            ],
        )
        raw = resp.content.decode()
        for forbidden in ("1.5", "0.5", "kg", "Kg", self.batch.batch_id, "batch"):
            self.assertNotIn(forbidden, raw)
        self.assertEqual(self.snapshot(), before)

    def test_only_failing_lines_are_listed(self):
        self._stocked_batch(self._item("CUA", price="100000"), "20")
        resp = self.post([("CUA", "2"), ("TOM-SU", "1")])
        self.assert_out_of_stock(resp, [{"item_code": "TOM-SU", "stock_level": "out"}])

    def test_line_level_out_when_item_below_minimum_sellable(self):
        """Còn 0,9 kg: dưới mức tối thiểu 1 kg nên là "out" chứ không phải "short" (BR-BH-23)."""
        self._stocked_batch(self._item("TAIL", price="100000"), "0.9")
        self.assert_out_of_stock(self.post([("TAIL", "1")]), [{"item_code": "TAIL", "stock_level": "out"}])

    def test_inactive_unpriced_and_unknown_items_are_out(self):
        off = self._item("OFF", price="100000")
        self._stocked_batch(off, "20")
        off.is_active = False
        off.save()
        nopr = self._item("NOPRICE")
        self._stocked_batch(nopr, "20")
        before = self.snapshot()
        resp = self.post([("OFF", "1"), ("NOPRICE", "1"), ("KHONG-CO", "1")])
        self.assert_out_of_stock(
            resp,
            [
                {"item_code": "OFF", "stock_level": "out"},
                {"item_code": "NOPRICE", "stock_level": "out"},
                {"item_code": "KHONG-CO", "stock_level": "out"},
            ],
        )
        self.assertEqual(self.snapshot(), before)

    def test_combo_with_one_component_short_is_short(self):
        rich = self._item("RICH", price="100000")
        self._stocked_batch(rich, "100")
        combo = self.combo("COMBO-LAU", [(rich, "1"), (self.short_item, "1")])   # MUC-ONG chỉ 1,5 kg
        self.assertEqual(combo.item_type, Item.ItemType.BUNDLE)
        # còn 1,5 kg mực: 2 combo cần 2 kg (thiếu, nhưng ráp được 1 bộ nên là "short"), 1 combo cần 1 kg (đủ)
        self.assert_out_of_stock(self.post([("COMBO-LAU", "2")]), [{"item_code": "COMBO-LAU", "stock_level": "short"}])
        self.assertEqual(self.post([("COMBO-LAU", "1")]).status_code, 201)

    def test_combo_with_empty_component_is_out(self):
        rich = self._item("RICH", price="100000")
        self._stocked_batch(rich, "100")
        self.combo("COMBO-LAU", [(rich, "1"), (self.empty_item, "1")])
        self.assert_out_of_stock(self.post([("COMBO-LAU", "1")]), [{"item_code": "COMBO-LAU", "stock_level": "out"}])

    def test_demand_is_summed_across_lines_sharing_a_component(self):
        part = self._item("SHARED", price="100000")
        self._stocked_batch(part, "3")
        self.combo("COMBO-A", [(part, "0.5")], price="200000")
        before = self.snapshot()
        # 2 kg lẻ + 4 combo × 0,5 kg = 4 kg > 3 kg: từng dòng đủ riêng lẻ nhưng cộng lại thiếu
        resp = self.post([("SHARED", "2"), ("COMBO-A", "4")])
        self.assert_out_of_stock(
            resp,
            [
                {"item_code": "SHARED", "stock_level": "short"},
                {"item_code": "COMBO-A", "stock_level": "short"},
            ],
        )
        self.assertEqual(self.snapshot(), before)

    def test_exact_remaining_stock_is_accepted(self):
        self.assertEqual(self.post([("MUC-ONG", "1.5")]).status_code, 201)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_reserved, Decimal("1.5"))

    def test_expired_only_stock_is_out(self):
        gone = self._item("GONE", price="100000")
        self._stocked_batch(gone, "10", received=self.today - datetime.timedelta(days=400))
        self.assert_out_of_stock(self.post([("GONE", "1")]), [{"item_code": "GONE", "stock_level": "out"}])

    def test_service_raises_out_of_stock_error(self):
        with self.assertRaises(OutOfStockError) as caught:
            services.create_order(
                customer_phone=FAKE_PHONE, customer_name=FAKE_NAME, delivery_address=FAKE_ADDRESS,
                phone=FAKE_PHONE, lines=[{"item_code": "TOM-SU", "qty": Decimal("1")}],
            )
        self.assertEqual(caught.exception.code, "OUT_OF_STOCK")
        self.assertEqual(caught.exception.http_status, 400)

    def test_reservation_race_loser_gets_out_of_stock_and_rolls_back(self):
        """Tồn đủ lúc kiểm trước nhưng `reserve` thua (người khác giữ trước): vẫn ra OUT_OF_STOCK, rollback cả đơn."""
        self._stocked_batch(self._item("CUA", price="100000"), "20")
        real_reserve = batch_services.reserve
        calls = {"n": 0}

        def losing_reserve(*, batch, qty):
            calls["n"] += 1
            if calls["n"] == 2:   # dòng thứ hai thua đua
                raise BusinessError(
                    "Không đủ tồn khả dụng để giữ chỗ (BR-BH-02).", code="BR-BH-02"
                )
            return real_reserve(batch=batch, qty=qty)

        before = self.snapshot()
        with mock.patch.object(batch_services, "reserve", side_effect=losing_reserve):
            resp = self.post([("CUA", "2"), ("MUC-ONG", "1")])
        self.assertEqual(calls["n"], 2)
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "OUT_OF_STOCK")
        self.assertEqual([l["item_code"] for l in body["lines"]], ["MUC-ONG"])
        self.assertIn(body["lines"][0]["stock_level"], {"out", "short"})
        self.assertEqual(self.snapshot(), before)   # dòng CUA đã giữ chỗ được hoàn tác
        raw = resp.content.decode()
        for forbidden in ("kg", self.batch.batch_id, "BR-BH-02"):
            self.assertNotIn(forbidden, raw)


class ReserveMessagesTests(ShopCreateBase):
    """Câu lỗi tầng kho không lộ mã lô và số kg (G1, G3) — phòng thủ thêm, 02b §3.3."""

    def test_allocate_fefo_message_has_no_batch_code_or_kg(self):
        item = self._item("CA01", price="100000")
        batch = self._stocked_batch(item, "2")
        with self.assertRaises(BusinessError) as caught:
            batch_services.allocate_fefo(item=item, qty=Decimal("5"))
        message = str(caught.exception)
        self.assertEqual(caught.exception.code, "BR-BH-02")
        self.assertIn("Không đủ tồn khả dụng", message)
        for forbidden in (batch.batch_id, "kg", "Kg", "3", "5", "2"):
            self.assertNotIn(forbidden, message.replace("BR-BH-02", ""))

    def test_reserve_message_has_no_batch_code_or_kg(self):
        item = self._item("CA01", price="100000")
        batch = self._stocked_batch(item, "2")
        with self.assertRaises(BusinessError) as caught:
            batch_services.reserve(batch=batch, qty=Decimal("5"))
        message = str(caught.exception)
        self.assertEqual(caught.exception.code, "BR-BH-02")
        self.assertNotIn(batch.batch_id, message)
        self.assertNotIn("kg", message.lower())


class LogsHavePiiFreeTests(ShopCreateBase):
    """SHOP-2-02 AC6, bất biến 9: lỗi tạo đơn không ghi tên, SĐT, địa chỉ hay request.data vào log."""

    class _Capture(logging.Handler):
        def __init__(self):
            super().__init__(level=logging.DEBUG)
            self.lines = []

        def emit(self, record):
            self.lines.append(record.getMessage())
            self.lines.append(json.dumps(record.__dict__, default=str, ensure_ascii=False))

    def test_s2_02_ac6_logs_have_no_pii_on_validation_and_stock_errors(self):
        self._stocked_batch(self._item("MUC-ONG", price="278000"), "50")
        capture = self._Capture()
        root = logging.getLogger()
        previous_level = root.level
        root.addHandler(capture)
        root.setLevel(logging.DEBUG)
        try:
            self.post([("MUC-ONG", "0.5")])       # INVALID_QTY
            self.post([("KHONG-CO", "1")])        # OUT_OF_STOCK
            self.post([("MUC-ONG", "abc")])       # VALIDATION
        finally:
            root.removeHandler(capture)
            root.setLevel(previous_level)
        joined = "\n".join(capture.lines)
        for pii in (FAKE_PHONE, FAKE_PHONE[1:], FAKE_NAME, "Đường Thử", "Phường Mẫu", "request.data"):
            self.assertNotIn(pii, joined)

    def test_error_bodies_never_echo_customer_data(self):
        self._stocked_batch(self._item("MUC-ONG", price="278000"), "50")
        for resp in (self.post([("MUC-ONG", "0.5")]), self.post([("KHONG-CO", "1")]), self.post([("MUC-ONG", "abc")])):
            raw = resp.content.decode()
            for pii in (FAKE_PHONE, FAKE_NAME, "Đường Thử"):
                self.assertNotIn(pii, raw)
