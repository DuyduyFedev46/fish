"""
STA-02 (T-B1…T-B14): tạo đơn Shop với địa chỉ có cấu trúc (BR-BH-29, BR-BH-34, BR-BH-35).
Mã tỉnh/xã là dữ liệu công cộng; tên khách, SĐT, số nhà đều là dữ liệu giả.
"""
import logging

from django.core.cache import cache

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch
from apps.sales.models import Customer, SalesOrder, SalesInvoice
from apps.sales.models import VoucherRedemption
from apps.sales.orders import services

from .test_shop_create import FAKE_ADDRESS, FAKE_NAME, FAKE_PHONE, ShopCreateBase

STREET = "12 Đường Giả, hẻm 3"
NEW_ADDRESS = {"scheme": "current", "province_code": "68", "district_code": None, "ward_code": "22945", "street": STREET}
OLD_ADDRESS = {"scheme": "legacy", "province_code": "60", "district_code": "593", "ward_code": "22915", "street": STREET}
STRUCTURE_FIELDS = ("address_scheme", "province_code", "district_code", "ward_code", "street_address")
LEAK_KEYS = ("delivery_address", "address_scheme", "province_code", "district_code", "ward_code", "street")


def all_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from all_keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from all_keys(value)


class StructuredAddressBase(ShopCreateBase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.item = self._item("CA-THU", price="100000")
        self.batch = self._stocked_batch(self.item, "50")

    def post_parts(self, parts, **extra):
        return self.post([("CA-THU", "1")], delivery_address_parts=parts, **extra)

    def no_text_body(self, parts, **extra):
        body = {
            "customer": {"phone": FAKE_PHONE, "name": FAKE_NAME},
            "delivery_address_parts": parts,
            "items": [{"item_code": "CA-THU", "qty": "1"}],
        }
        body.update(extra)
        return self.client.post("/api/shop/orders/", body, format="json")

    def counts(self):
        return (
            SalesOrder.objects.count(),
            [str(q) for q in Batch.objects.order_by("pk").values_list("qty_reserved", flat=True)],
            VoucherRedemption.objects.count(),
        )


class CreateWithPartsTests(StructuredAddressBase):
    def test_b1_current_saved_and_composed(self):
        resp = self.no_text_body(NEW_ADDRESS)
        self.assertEqual(resp.status_code, 201, resp.content)
        order = SalesOrder.objects.get()
        self.assertEqual(order.address_scheme, "current")
        self.assertEqual(order.province_code, "68")
        self.assertEqual(order.district_code, "")
        self.assertEqual(order.ward_code, "22945")
        self.assertEqual(order.street_address, STREET)
        self.assertEqual(order.delivery_address, f"{STREET}, Phường Phan Thiết, Tỉnh Lâm Đồng")
        self.assertEqual(Customer.objects.get().default_address, order.delivery_address)

    def test_b2_legacy_saved_with_district(self):
        resp = self.no_text_body(OLD_ADDRESS)
        self.assertEqual(resp.status_code, 201, resp.content)
        order = SalesOrder.objects.get()
        self.assertEqual((order.address_scheme, order.province_code, order.district_code, order.ward_code), ("legacy", "60", "593", "22915"))
        self.assertEqual(order.delivery_address.count(", "), 4)  # số nhà có 1 dấu phẩy + xã, huyện, tỉnh

    def test_b7_street_boundary_and_whitespace(self):
        self.assertEqual(self.no_text_body({**NEW_ADDRESS, "street": "a" * 200}).status_code, 201)
        resp = self.no_text_body({**NEW_ADDRESS, "street": "12\n  Đường\tGiả"}, client_request_id=None)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(SalesOrder.objects.latest("pk").street_address, "12 Đường Giả")

    def test_b8_server_composes_ignoring_text(self):
        resp = self.post_parts(NEW_ADDRESS, delivery_address="Chuỗi tự gửi lên")
        self.assertEqual(resp.status_code, 201, resp.content)
        order = SalesOrder.objects.get()
        self.assertNotEqual(order.delivery_address, "Chuỗi tự gửi lên")
        self.assertTrue(order.delivery_address.startswith(STREET))

    def test_b10_legacy_text_only_is_free_text(self):
        with self.assertLogs("apps.sales.orders.shop_api", level="INFO") as logs:
            resp = self.post([("CA-THU", "1")])
        self.assertEqual(resp.status_code, 201)
        order = SalesOrder.objects.get()
        self.assertEqual(order.delivery_address, FAKE_ADDRESS)
        self.assertTrue(all(getattr(order, f) == "" for f in STRUCTURE_FIELDS))
        self.assertTrue(any("address=free_text" in line for line in logs.output))

    def test_b14_resend_same_request_id_keeps_first_address(self):
        rid = "1b4e28ba-2fa1-11d2-883f-0016d3cca427"
        self.assertEqual(self.no_text_body(NEW_ADDRESS, client_request_id=rid).status_code, 201)
        resp = self.no_text_body(OLD_ADDRESS, client_request_id=rid)
        self.assertEqual(resp.status_code, 200)
        order = SalesOrder.objects.get()
        self.assertEqual(order.address_scheme, "current")
        self.assertEqual(order.delivery_address, f"{STREET}, Phường Phan Thiết, Tỉnh Lâm Đồng")


class InvalidPartsTests(StructuredAddressBase):
    def assert_rejected(self, parts, expected_fields, **extra):
        before = self.counts()
        resp = self.no_text_body(parts, **extra)
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "VALIDATION")
        for field in expected_fields:
            self.assertIn(field, body["fields"])
        self.assertEqual(self.counts(), before)  # T-B9: không đơn, không giữ chỗ, không lượt mã
        return body

    def test_b3_current_ward_of_other_province(self):
        self.assert_rejected({**NEW_ADDRESS, "ward_code": "00004"}, ["ward_code"])

    def test_b4_legacy_missing_or_wrong_district(self):
        body = self.assert_rejected({**OLD_ADDRESS, "district_code": None}, ["district_code", "ward_code"])
        self.assertNotIn("street", body["fields"])
        self.assert_rejected({**OLD_ADDRESS, "district_code": "001"}, ["district_code", "ward_code"])
        self.assert_rejected({**OLD_ADDRESS, "ward_code": "00001"}, ["ward_code"])

    def test_b5_current_with_district(self):
        self.assert_rejected({**NEW_ADDRESS, "district_code": "593"}, ["district_code"])

    def test_b6_unknown_codes_and_bad_types(self):
        self.assert_rejected({**NEW_ADDRESS, "province_code": "99", "ward_code": "00000"}, ["province_code", "ward_code"])
        self.assert_rejected({**NEW_ADDRESS, "province_code": 68, "ward_code": 22945}, ["province_code", "ward_code"])
        self.assert_rejected({**NEW_ADDRESS, "scheme": "new"}, ["scheme"])
        self.assert_rejected("12 Đường Giả", ["delivery_address"])

    def test_b7_bad_street(self):
        for street in ("", "   \n ", "a" * 201, None, 12):
            self.assert_rejected({**NEW_ADDRESS, "street": street}, ["street"])

    def test_b9_nothing_held_with_valid_voucher_attached(self):
        # Mã hợp lệ thật (Tech Lead review): lỗi địa chỉ phải chặn trước bước giữ lượt mã.
        import datetime
        from decimal import Decimal
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from apps.catalog.models import Voucher
        now = timezone.now()
        Voucher.objects.create(
            code="CAVE10", name="x", kind="AMOUNT", value=Decimal("10000"),
            starts_at=now - datetime.timedelta(hours=1), ends_at=now + datetime.timedelta(days=1),
            total_uses=5, created_by=get_user_model().objects.create_user("owner_sta", password="x"),
        )
        cases = (
            ({**NEW_ADDRESS, "ward_code": "00004"}, ["ward_code"]),
            ({**OLD_ADDRESS, "district_code": "001"}, ["district_code", "ward_code"]),
            ({**NEW_ADDRESS, "street": ""}, ["street"]),
        )
        for bad, expected in cases:
            self.assert_rejected(bad, expected, voucher_code="CAVE10")
        ok = self.no_text_body(NEW_ADDRESS, voucher_code="CAVE10")
        self.assertEqual(ok.status_code, 201, ok.content)  # đối chứng: mã dùng được thật
        self.assertEqual(VoucherRedemption.objects.count(), 1)

    def test_errors_merge_with_other_fields(self):
        resp = self.client.post("/api/shop/orders/", {
            "customer": {"phone": "123", "name": ""},
            "delivery_address_parts": {**NEW_ADDRESS, "ward_code": "x"},
            "items": [{"item_code": "CA-THU", "qty": "1"}],
        }, format="json")
        self.assertEqual({"name", "phone", "ward_code"} <= set(resp.json()["fields"]), True)


class ConfirmationEditTests(StructuredAddressBase):
    def test_b10_cs12_text_edit_clears_structure(self):
        self.assertEqual(self.no_text_body(NEW_ADDRESS).status_code, 201)
        order = SalesOrder.objects.get()
        services.update_delivery_address(order, "Số 2 Đường Thử, P. Thử")
        order.refresh_from_db()
        self.assertEqual(order.delivery_address, "Số 2 Đường Thử, P. Thử")
        self.assertTrue(all(getattr(order, f) == "" for f in STRUCTURE_FIELDS))

    def test_b10_cs12_endpoint_recipient_only_keeps_structure(self):
        order, _customer, note = self._confirming_order()
        cs = make_user("cs_addr", roles.CUSTOMER_SERVICE)
        client = client_for(cs)
        resp = client.post(f"/api/confirmation/queue/{note.pk}/recipient/", {"recipient_name": "Người Nhận Hộ"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        order.refresh_from_db()
        self.assertEqual(order.address_scheme, "current")
        resp = client.post(
            f"/api/confirmation/queue/{note.pk}/recipient/", {"delivery_address": "Số 2 Đường Thử, P. Thử"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        order.refresh_from_db()
        self.assertTrue(all(getattr(order, f) == "" for f in STRUCTURE_FIELDS))

    def _confirming_order(self):
        """Tạo đơn có địa chỉ cấu trúc rồi chuyển sang CONFIRMING bằng hoá đơn (signal tạo phiếu giao)."""
        import datetime
        from decimal import Decimal
        self.assertEqual(self.no_text_body(NEW_ADDRESS).status_code, 201)
        order = SalesOrder.objects.get()
        SalesOrder.objects.filter(pk=order.pk).update(status=SalesOrder.Status.PROCESSING)
        order.refresh_from_db()
        invoice = SalesInvoice.objects.create(
            code=f"INV-{order.code}", sales_order=order, customer=order.customer,
            issued_at=datetime.datetime(2026, 9, 1, 8, 0, tzinfo=datetime.timezone.utc),
            amount=Decimal("100000"), status=SalesInvoice.Status.ISSUED,
        )
        return order, order.customer, invoice.delivery_notes.get()


class NoLeakTests(StructuredAddressBase):
    def assert_clean(self, resp):
        raw = resp.content.decode()
        for key in set(all_keys(resp.json())):
            self.assertNotIn(key, LEAK_KEYS, key)
        for text in (STREET, "Phan Thiết", "Lâm Đồng", "22945"):
            self.assertNotIn(text, raw)

    def test_b11_public_responses_do_not_leak(self):
        create = self.no_text_body(NEW_ADDRESS)
        self.assertEqual(create.status_code, 201)
        self.assert_clean(create)
        order = SalesOrder.objects.get()
        by_phone = self.client.post("/api/shop/orders/lookup/", {"order_code": order.code, "phone": FAKE_PHONE}, format="json")
        self.assertEqual(by_phone.status_code, 200)
        self.assert_clean(by_phone)
        by_token = self.client.post(
            "/api/shop/orders/lookup/", {"order_code": order.code, "token": by_phone.json()["lookup_token"]}, format="json"
        )
        self.assertEqual(by_token.status_code, 200)
        self.assert_clean(by_token)
        checkout = self.client.post(f"/api/shop/orders/{order.code}/checkout/")
        self.assertIn(checkout.status_code, (200, 400, 409, 503))
        self.assert_clean(checkout)

    def test_b12_erp_detail_has_no_new_structure_keys(self):
        self.assertEqual(self.no_text_body(NEW_ADDRESS).status_code, 201)
        order = SalesOrder.objects.get()
        for group in (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE):
            client = client_for(make_user(f"u_{group}", group))
            resp = client.get(f"/api/sales/orders/{order.pk}/")
            self.assertIn(resp.status_code, (200, 403, 404), group)
            if group == roles.OWNER:
                self.assertEqual(resp.status_code, 200, resp.content)  # không để test qua rỗng
            if resp.status_code == 200:
                for key in set(all_keys(resp.json())):
                    self.assertNotIn(key, ("address_scheme", "province_code", "district_code", "ward_code", "street_address", "street"), group)

    def test_b13_no_personal_data_in_logs(self):
        sensitive = (STREET, "Phan Thiết", "22945", FAKE_NAME, FAKE_PHONE, "Lâm Đồng")
        bad = {**NEW_ADDRESS, "ward_code": "00004"}
        root = logging.getLogger()
        old_level = root.level
        root.setLevel(logging.DEBUG)
        try:
            with self.assertLogs(level=logging.DEBUG) as logs:
                logging.getLogger("probe").debug("probe")
                self.assertEqual(self.no_text_body(NEW_ADDRESS).status_code, 201)
                self.assertEqual(self.no_text_body(bad).status_code, 400)
        finally:
            root.setLevel(old_level)
        for line in logs.output:
            if line.startswith("DEBUG:probe"):
                continue
            if "django.db.backends" in line:
                continue  # câu SQL của test DB, không phải log ứng dụng
            for text in sensitive:
                self.assertNotIn(text, line)
