"""
02b §3.3 — thứ tự kiểm lỗi tạo đơn Shop: SHOP_CLOSED, VALIDATION, đơn cũ (200), INVALID_QTY, POLICY_CHANGED, OUT_OF_STOCK.
BR-BH-17 (mã lỗi nay là SHOP_CLOSED / VALIDATION.fields.consent), BR-BH-22, BR-BH-24, BR-BH-27. Dữ liệu giả.
"""
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.content.entries.services import publish_entry
from apps.content.models.entries import Entry
from apps.sales.models import SalesOrder

from .test_shop_create import ShopCreateBase

User = get_user_model()
REQUEST_ID = "6f1c2a7e-3b4d-4c5e-9f00-1a2b3c4d5e6f"


class ErrorOrderBase(ShopCreateBase):
    def setUp(self):
        super().setUp()
        self.simple = self._item("MUC-ONG", price="278000")
        self._stocked_batch(self.simple, "50")
        self.user = User.objects.create_user(username="author", password="x")

    def publish_policy(self):
        entry = Entry.objects.create(
            kind="page", title="Chính sách quyền riêng tư", slug="quyen-rieng-tu", excerpt="x", page_role="privacy",
            body={"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "v1"}]}]}, created_by=self.user,
        )
        publish_entry(entry=entry, actor=self.user, row_version=entry.row_version,
                      checklist_confirmed=True, acknowledge_warnings=True)
        entry.refresh_from_db()
        self.entry = entry
        return entry.published_version


@override_settings(PRIVACY_CONSENT_REQUIRED=True)
class ShopClosedTests(ErrorOrderBase):
    def test_no_published_policy_is_503_shop_closed_before_validation(self):
        resp = self.client.post("/api/shop/orders/", {"customer": {}, "items": []}, format="json")
        self.assertEqual(resp.status_code, 503, resp.content)
        self.assertEqual(resp.json(), {"code": "SHOP_CLOSED", "detail": "Shop tạm chưa nhận đơn."})
        self.assertEqual(SalesOrder.objects.count(), 0)

    def test_shop_closed_comes_before_invalid_qty(self):
        resp = self.post([("MUC-ONG", "0.5")])
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["code"], "SHOP_CLOSED")

    def test_old_br_bh_17_code_is_gone(self):
        resp = self.post([("MUC-ONG", "1")])
        self.assertNotEqual(resp.json()["code"], "BR-BH-17")


@override_settings(PRIVACY_CONSENT_REQUIRED=True)
class ConsentOrderTests(ErrorOrderBase):
    def setUp(self):
        super().setUp()
        self.v1 = self.publish_policy()

    def consent(self, **kw):
        return {"privacy_consent": {"accepted": True, "policy_version_id": self.v1.pk, **kw}}

    def test_unticked_consent_is_validation_with_consent_field(self):
        for payload in (None, {"accepted": False, "policy_version_id": self.v1.pk}, {"accepted": "true"}, "x"):
            with self.subTest(payload=payload):
                resp = self.post([("MUC-ONG", "1")], privacy_consent=payload)
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "VALIDATION")
                self.assertEqual(resp.json()["fields"], {"consent": "Đánh dấu đồng ý ở trên để đặt hàng."})
        self.assertEqual(SalesOrder.objects.count(), 0)

    def test_validation_lists_consent_together_with_other_fields(self):
        body = {"customer": {"phone": "1", "name": "A"}, "delivery_address": "x", "items": [{"item_code": "MUC-ONG", "qty": "1"}]}
        resp = self.client.post("/api/shop/orders/", body, format="json")
        self.assertEqual(set(resp.json()["fields"]), {"phone", "consent"})

    def test_validation_comes_before_invalid_qty_and_stale_policy(self):
        resp = self.post([("MUC-ONG", "0.5")], delivery_address="", privacy_consent={"accepted": True, "policy_version_id": 999999})
        self.assertEqual(resp.json()["code"], "VALIDATION")

    def test_invalid_qty_comes_before_policy_changed(self):
        resp = self.post([("MUC-ONG", "0.5")], privacy_consent={"accepted": True, "policy_version_id": 999999})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "INVALID_QTY")

    def test_policy_changed_comes_before_out_of_stock(self):
        resp = self.post([("KHONG-CO", "1")], privacy_consent={"accepted": True, "policy_version_id": 999999})
        self.assertEqual(resp.status_code, 409)
        body = resp.json()
        self.assertEqual(body["code"], "POLICY_CHANGED")
        self.assertEqual(body["current"]["version_id"], self.v1.pk)
        self.assertEqual(body["current"]["slug"], "quyen-rieng-tu")

    def test_out_of_stock_after_policy_ok(self):
        resp = self.post([("KHONG-CO", "1")], **self.consent())
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "OUT_OF_STOCK")

    def test_replay_wins_over_stale_policy_and_stock(self):
        first = self.post([("MUC-ONG", "1")], client_request_id=REQUEST_ID, **self.consent())
        self.assertEqual(first.status_code, 201, first.content)
        again = self.post([("MUC-ONG", "1")], client_request_id=REQUEST_ID,
                          privacy_consent={"accepted": True, "policy_version_id": 999999})
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["order_code"], first.json()["order_code"])

    def test_valid_consent_creates_order(self):
        self.assertEqual(self.post([("MUC-ONG", "1")], **self.consent()).status_code, 201)


@override_settings(PRIVACY_CONSENT_REQUIRED=False)
class ConsentOptionalTests(ErrorOrderBase):
    def test_flag_off_without_policy_allows_order(self):
        self.assertEqual(self.post([("MUC-ONG", "1")]).status_code, 201)

    def test_flag_off_with_policy_and_no_consent_allows_order(self):
        self.user = User.objects.create_user(username="author2", password="x")
        self.publish_policy()
        self.assertEqual(self.post([("MUC-ONG", "1")]).status_code, 201)
