"""
SHOP-3-01 — tạo đơn Shop trả dòng món, mã tra đơn, chống trùng `client_request_id`; thứ tự lỗi theo 02b §3.3.
BR-BH-25, 27, 17; V-02, V-06; bất biến 9 (response không có tên, SĐT, địa chỉ). Dữ liệu giả.
"""
import base64
import datetime
import json
import logging
import uuid

from django.test import override_settings
from django.utils import timezone

from apps.inventory.models import Batch
from apps.sales.models import SalesOrder

from .test_shop_create import FAKE_ADDRESS, FAKE_NAME, FAKE_PHONE, ShopCreateBase

REQUEST_ID = "6f1c2a7e-3b4d-4c5e-9f00-1a2b3c4d5e6f"


class CreateContractTests(ShopCreateBase):
    def setUp(self):
        super().setUp()
        self.simple = self._item("MUC-ONG", price="278000")
        self._stocked_batch(self.simple, "50")
        self.combo("COMBO-LAU", [(self.simple, "0.5")], price="450000")

    def test_s3_01_ac1_created_response_has_lines_token_and_utc_times(self):
        resp = self.post([("MUC-ONG", "1.5"), ("COMBO-LAU", "1")], client_request_id=REQUEST_ID)
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual(
            set(data),
            {"order_code", "status", "subtotal", "discount", "total_amount", "booked_expires_at", "server_now",
             "hold_minutes", "lines", "lookup_token"},
        )
        self.assertEqual(data["status"], "BOOKED")
        self.assertEqual(data["subtotal"], "867000")
        self.assertEqual(data["total_amount"], "867000")
        self.assertEqual(data["discount"], {"source": None, "code": None, "amount": "0"})
        self.assertEqual(data["hold_minutes"], 30)
        self.assertEqual(
            data["lines"],
            [
                {"item_code": "MUC-ONG", "name": "MUC-ONG", "unit": "kg", "qty": "1.5", "amount": "417000"},
                {"item_code": "COMBO-LAU", "name": "COMBO-LAU", "unit": "combo", "qty": "1", "amount": "450000"},
            ],
        )
        order = SalesOrder.objects.get(code=data["order_code"])
        self.assertEqual(order.client_request_id, uuid.UUID(REQUEST_ID))
        self.assertEqual(
            data["booked_expires_at"], order.booked_expires_at.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        created = order.created_at
        expires = datetime.datetime.strptime(data["booked_expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        self.assertAlmostEqual((expires - created).total_seconds(), 30 * 60, delta=5)
        self.assertTrue(data["server_now"].endswith("Z"))
        self.assertEqual(resp["Cache-Control"], "no-store")

    @override_settings(SALES_ORDER_TTL_MINUTES=45)
    def test_s3_01_ac1_hold_minutes_comes_from_settings(self):
        data = self.post([("MUC-ONG", "1")]).json()
        self.assertEqual(data["hold_minutes"], 45)

    def test_s3_01_ac1_promo_discount_reported_with_source(self):
        from apps.catalog.models import PricingRule

        PricingRule.objects.create(
            name="Giảm 10%", apply_on=PricingRule.ApplyOn.ITEM, item=self.simple,
            discount_type=PricingRule.DiscountType.PERCENT, discount_value=10,
        )
        data = self.post([("MUC-ONG", "2")]).json()
        self.assertEqual(data["subtotal"], "556000")
        self.assertEqual(data["discount"], {"source": "promo", "code": None, "amount": "55600"})
        self.assertEqual(data["total_amount"], "500400")
        self.assertEqual(data["lines"][0]["amount"], "556000")  # thành tiền gộp, trước giảm

    def test_s3_01_ac2_same_client_request_id_returns_same_order_once(self):
        first = self.post([("MUC-ONG", "2")], client_request_id=REQUEST_ID)
        before = self.snapshot()
        second = self.post([("MUC-ONG", "2")], client_request_id=REQUEST_ID)
        third = self.post([("MUC-ONG", "2")], client_request_id=REQUEST_ID.upper())
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(third.status_code, 200)
        self.assertEqual(second.json()["order_code"], first.json()["order_code"])
        self.assertEqual(second.json()["lines"], first.json()["lines"])
        self.assertEqual(SalesOrder.objects.count(), 1)
        self.assertEqual(self.snapshot(), before)  # không giữ chỗ gấp đôi

    def test_s3_01_ac2_replay_skips_stock_and_quantity_checks(self):
        """Gửi lại sau khi hết hàng vẫn trả đơn cũ (đơn đã có thật), không 400."""
        first = self.post([("MUC-ONG", "2")], client_request_id=REQUEST_ID)
        Batch.objects.update(qty_reserved=Batch.objects.first().qty_available)
        again = self.post([("MUC-ONG", "2")], client_request_id=REQUEST_ID)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["order_code"], first.json()["order_code"])

    def test_s3_01_ac2_failed_first_attempt_does_not_burn_the_request_id(self):
        bad = self.post([("MUC-ONG", "0.5")], client_request_id=REQUEST_ID)
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(SalesOrder.objects.count(), 0)
        ok = self.post([("MUC-ONG", "1")], client_request_id=REQUEST_ID)
        self.assertEqual(ok.status_code, 201)

    def test_s3_01_ac2_different_request_ids_make_different_orders(self):
        a = self.post([("MUC-ONG", "1")], client_request_id=str(uuid.uuid4()))
        b = self.post([("MUC-ONG", "1")], client_request_id=str(uuid.uuid4()))
        self.assertNotEqual(a.json()["order_code"], b.json()["order_code"])

    def test_s3_01_ac2_client_request_id_is_optional(self):
        self.assertEqual(self.post([("MUC-ONG", "1")]).status_code, 201)
        self.assertEqual(self.post([("MUC-ONG", "1")]).status_code, 201)
        self.assertEqual(SalesOrder.objects.filter(client_request_id__isnull=True).count(), 2)

    def test_s3_01_ac3_phone_normalized_and_lookup_accepts_both_forms(self):
        body = {
            "customer": {"phone": "+84 900 000 001", "name": FAKE_NAME},
            "delivery_address": FAKE_ADDRESS,
            "items": [{"item_code": "MUC-ONG", "qty": "1"}],
        }
        resp = self.client.post("/api/shop/orders/", body, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        order = SalesOrder.objects.get(code=resp.json()["order_code"])
        self.assertEqual(order.phone, "0900000001")
        self.assertEqual(order.customer.phone, "0900000001")
        for typed in ("0900000001", "+84900000001", "0900 000 001"):
            found = self.client.post(
                "/api/shop/orders/lookup/", {"order_code": order.code, "phone": typed}, format="json"
            )
            self.assertEqual(found.status_code, 200, typed)

    def test_s3_01_ac4_validation_lists_each_bad_field_and_creates_nothing(self):
        body = {
            "client_request_id": "khong-phai-uuid",
            "customer": {"phone": "12345", "name": ""},
            "delivery_address": "",
            "items": [],
        }
        resp = self.client.post("/api/shop/orders/", body, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        data = resp.json()
        self.assertEqual(data["code"], "VALIDATION")
        self.assertEqual(data["detail"], "Thông tin đặt hàng chưa hợp lệ.")
        self.assertEqual(
            set(data["fields"]), {"client_request_id", "name", "phone", "delivery_address", "items"}
        )
        self.assertEqual(data["fields"]["phone"], "Số điện thoại cần 10 chữ số, bắt đầu bằng 0")
        self.assertEqual(SalesOrder.objects.count(), 0)

    def test_s3_01_ac4_validation_edges(self):
        cases = {
            "phone": [{"customer": {"phone": "090000000", "name": "A"}}, {"customer": {"phone": "09000000012", "name": "A"}},
                      {"customer": {"phone": "1900000001", "name": "A"}}, {"customer": {"phone": None, "name": "A"}}],
            "name": [{"customer": {"phone": FAKE_PHONE, "name": "x" * 101}}, {"customer": {"phone": FAKE_PHONE}}],
            "delivery_address": [{"delivery_address": "y" * 501}, {"delivery_address": "   "}],
            "items": [{"items": [{"item_code": "MUC-ONG", "qty": "1"}] * 2},
                      {"items": [{"item_code": f"X{i}", "qty": "1"} for i in range(31)]}],
        }
        base = {"customer": {"phone": FAKE_PHONE, "name": FAKE_NAME}, "delivery_address": FAKE_ADDRESS,
                "items": [{"item_code": "MUC-ONG", "qty": "1"}]}
        for field, variants in cases.items():
            for patch in variants:
                with self.subTest(field=field, patch=str(patch)[:40]):
                    resp = self.client.post("/api/shop/orders/", {**base, **patch}, format="json")
                    self.assertEqual(resp.status_code, 400)
                    self.assertEqual(resp.json()["code"], "VALIDATION")
                    self.assertIn(field, resp.json()["fields"])
        self.assertEqual(SalesOrder.objects.count(), 0)

    def test_s3_01_top_level_phone_key_is_ignored(self):
        body = {"customer": {"name": FAKE_NAME}, "phone": FAKE_PHONE, "delivery_address": FAKE_ADDRESS,
                "items": [{"item_code": "MUC-ONG", "qty": "1"}]}
        resp = self.client.post("/api/shop/orders/", body, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("phone", resp.json()["fields"])

    def test_s3_01_ac5_token_has_only_order_code_and_expiry_and_tamper_is_rejected(self):
        data = self.post([("MUC-ONG", "1")]).json()
        token = data["lookup_token"]
        payload_part = token.split(":")[0]
        decoded = base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4)).decode()
        self.assertEqual(json.loads(decoded), {"o": data["order_code"]})
        for pii in (FAKE_PHONE, FAKE_NAME, "Đường Thử"):
            self.assertNotIn(pii, base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4)).decode())
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        resp = self.client.post(
            "/api/shop/orders/lookup/", {"order_code": data["order_code"], "token": tampered}, format="json"
        )
        self.assertEqual(resp.status_code, 404)

    def test_s3_01_ac6_response_has_no_customer_data(self):
        resp = self.post([("MUC-ONG", "1")], client_request_id=REQUEST_ID)
        raw = resp.content.decode()
        for pii in (FAKE_PHONE, FAKE_PHONE[1:], FAKE_NAME, "Đường Thử", "Phường Mẫu", "+84"):
            self.assertNotIn(pii, raw)
        for key in ("customer", "phone", "delivery_address", "recipient", "batch", "unit_cost"):
            self.assertNotIn(f'"{key}"', raw)

    def test_s3_01_ac6_logs_have_no_pii_on_create_and_replay(self):
        class Capture(logging.Handler):
            def __init__(self):
                super().__init__(level=logging.DEBUG)
                self.lines = []

            def emit(self, record):
                self.lines.append(record.getMessage())
                self.lines.append(json.dumps(record.__dict__, default=str, ensure_ascii=False))

        capture = Capture()
        root = logging.getLogger()
        previous = root.level
        root.addHandler(capture)
        root.setLevel(logging.DEBUG)
        try:
            self.post([("MUC-ONG", "1")], client_request_id=REQUEST_ID)
            self.post([("MUC-ONG", "1")], client_request_id=REQUEST_ID)
        finally:
            root.removeHandler(capture)
            root.setLevel(previous)
        joined = "\n".join(capture.lines)
        for pii in (FAKE_PHONE, FAKE_PHONE[1:], FAKE_NAME, "Đường Thử", "Phường Mẫu"):
            self.assertNotIn(pii, joined)
        self.assertIn("SO", joined)  # chỉ có mã đơn

    def test_s3_01_replay_by_unique_constraint_returns_existing_order(self):
        """Request thua đua: IntegrityError ngoài atomic -> đọc đơn đã commit (BR-BH-27)."""
        from unittest import mock

        from apps.sales.orders import services

        first = self.post([("MUC-ONG", "1")], client_request_id=REQUEST_ID).json()["order_code"]
        with mock.patch.object(services, "find_by_client_request_id", side_effect=[None, SalesOrder.objects.get(code=first)]):
            resp = self.post([("MUC-ONG", "1")], client_request_id=REQUEST_ID)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["order_code"], first)
        self.assertEqual(SalesOrder.objects.count(), 1)

    def test_s3_01_unique_index_exists(self):
        field = SalesOrder._meta.get_field("client_request_id")
        self.assertTrue(field.unique)
        self.assertTrue(field.null)
