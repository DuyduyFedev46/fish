"""
FISH-66 S1 (doc/features/2026-11-14-hang-ban-excel-dong-lanh): khách đặt từ 0,5 kg một món.
BR-BH-22 (mức tối thiểu/bước đọc từ settings, mặc định 0,5 kg), BR-BH-23, BR-BH-05/06/15, bất biến 1, 7, 9.
Các ca dưới đây kiểm GIÁ TRỊ MẶC ĐỊNH nên không override settings, trừ AC10 và AC13. Dữ liệu giả.
"""
import json
from decimal import Decimal

from django.test import override_settings

from apps.inventory.models import Batch
from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderLineBatch

from .test_shop_create import FAKE_ADDRESS, FAKE_NAME, FAKE_PHONE, ShopCreateBase


class HalfKgOrderTests(ShopCreateBase):
    def setUp(self):
        super().setUp()
        self.fish = self._item("CA-THU", price="200000")
        self.batch = self._stocked_batch(self.fish, "5")

    def test_s1_ac1_half_kg_creates_order_and_reserves_half_kg(self):
        resp = self.post([("CA-THU", "0.5")])
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["total_amount"], "100000")
        line = SalesOrderLine.objects.get()
        self.assertEqual(line.qty, Decimal("0.5"))
        alloc = SalesOrderLineBatch.objects.get()
        self.assertEqual(alloc.qty, Decimal("0.5"))
        self.assertEqual(alloc.batch_id, self.batch.pk)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_reserved, Decimal("0.5"))

    def test_s1_ac2_one_and_half_kg_is_valid(self):
        resp = self.post([("CA-THU", "1.5")])
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_s1_ac3_bad_quantities_rejected_with_vietnamese_message_and_no_side_effects(self):
        before = self.snapshot()
        for qty in ("0.25", "0", "0.7", "-0.5"):
            with self.subTest(qty=qty):
                resp = self.post([("CA-THU", qty)])
                self.assertEqual(resp.status_code, 400, resp.content)
                body = resp.json()
                self.assertEqual(body["code"], "INVALID_QTY")
                self.assertIn("từ 0,5 kg, mỗi lần thêm 0,5 kg", body["detail"])
                self.assertNotIn("BR-BH-22", body["detail"])  # mã luật nằm ở code/docstring, không lộ cho khách
                self.assertEqual(body["lines"], [{"item_code": "CA-THU", "min_qty": "0.5", "qty_step": "0.5"}])
                self.assertEqual(self.snapshot(), before)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_reserved, Decimal("0"))

    def test_s1_ac4_one_bad_line_rejects_whole_order(self):
        other = self._item("TOM-THU", price="100000")
        self._stocked_batch(other, "5")
        before = self.snapshot()
        resp = self.post([("CA-THU", "0.5"), ("TOM-THU", "0.25")])
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual([line["item_code"] for line in resp.json()["lines"]], ["TOM-THU"])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(SalesOrder.objects.count(), 0)

    def test_s1_ac5_half_combo_still_rejected(self):
        self.combo("COMBO-THU", [(self.fish, "0.5")])
        before = self.snapshot()
        resp = self.post([("COMBO-THU", "0.5")])
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "INVALID_QTY")
        self.assertEqual(body["lines"], [{"item_code": "COMBO-THU", "min_qty": "1", "qty_step": "1"}])
        self.assertEqual(self.snapshot(), before)

    def test_s1_ac7_tail_half_kg_orderable_but_one_kg_is_short(self):
        tail = self._item("DUOI", price="100000")
        self._stocked_batch(tail, "0.5")
        resp = self.post([("DUOI", "1")])
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "OUT_OF_STOCK")
        self.assertEqual(self.post([("DUOI", "0.5")]).status_code, 201)

    def test_s1_ac9_odd_price_total_rounds_to_whole_dong(self):
        odd = self._item("GIA-LE", price="99999")
        self._stocked_batch(odd, "5")
        resp = self.post([("GIA-LE", "0.5")])
        self.assertEqual(resp.status_code, 201, resp.content)
        # 0,5 x 99.999 = 49.999,50 -> half-up nguyên đồng 50.000 (BR-BH-15)
        self.assertEqual(resp.json()["total_amount"], "50000")
        self.assertEqual(SalesOrder.objects.get().total_amount, Decimal("50000"))

    def test_s1_ac10_env_minimum_one_kg_rejects_half_kg(self):
        with override_settings(SHOP_MIN_QTY_KG=Decimal("1")):
            resp = self.post([("CA-THU", "0.5")])
            self.assertEqual(resp.status_code, 400, resp.content)
            body = resp.json()
            self.assertEqual(body["code"], "INVALID_QTY")
            self.assertEqual(body["lines"][0]["min_qty"], "1")
            self.assertIn("từ 1 kg, mỗi lần thêm 0,5 kg", body["detail"])

    def test_s1_ac12_responses_have_no_cost_batch_or_customer_data(self):
        for resp in (self.post([("CA-THU", "0.5")]), self.post([("CA-THU", "0.25")])):
            raw = json.dumps(resp.json(), ensure_ascii=False)
            for forbidden in ("purchase_rate", "landed_unit_cost", "unit_cost", "batch", self.batch.batch_id,
                              "qty_reserved", FAKE_PHONE, FAKE_NAME, FAKE_ADDRESS):
                self.assertNotIn(forbidden, raw)

    def test_s1_ac13_old_one_kg_order_is_unchanged_after_new_half_kg_order(self):
        with override_settings(SHOP_MIN_QTY_KG=Decimal("1")):
            old_code = self.post([("CA-THU", "1")]).json()["order_code"]
        old_order = SalesOrder.objects.get(code=old_code)
        old_total = old_order.total_amount
        self.assertEqual(self.post([("CA-THU", "0.5")]).status_code, 201)
        old_order.refresh_from_db()
        self.assertEqual(old_order.total_amount, old_total)
        self.assertEqual([line.qty for line in old_order.lines.all()], [Decimal("1")])
        self.assertEqual(Batch.objects.get().qty_reserved, Decimal("1.5"))
