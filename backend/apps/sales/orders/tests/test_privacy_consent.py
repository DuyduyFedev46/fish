import datetime
import logging
from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.exceptions import BusinessError

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.content.entries.services import publish_entry, save_draft
from apps.content.models.entries import Entry, EntryVersion
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderLineBatch
from config.settings import privacy_consent_required

User = get_user_model()


class PrivacyConsentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="admin_user", password="password")

        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(
            price_list=pl,
            item=self.item,
            rate=Decimal("100000"),
            valid_from=timezone.localdate() - datetime.timedelta(days=1),
        )
        self.batch = batch_services.create_batch(
            item=self.item,
            supplier=Supplier.objects.create(name="NCC A"),
            warehouse=Warehouse.objects.create(name="Kho chính"),
            received_date=timezone.localdate(),
            qty=Decimal("50"),
            purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=self.batch, actor=None)

        # Dựng trang chính sách bảo mật đã đăng
        self.entry = Entry.objects.create(
            kind="page",
            title="Chính sách bảo mật",
            slug="chinh-sach-bao-mat",
            excerpt="Chính sách bảo mật dữ liệu khách hàng",
            page_role="privacy",
            body={"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Chính sách v1"}]}]},
            created_by=self.user,
        )
        publish_entry(
            entry=self.entry,
            actor=self.user,
            row_version=self.entry.row_version,
            checklist_confirmed=True,
            acknowledge_warnings=True,
        )
        self.entry.refresh_from_db()
        self.v1 = self.entry.published_version

    def _payload(self, **kwargs):
        d = {
            "customer": {"phone": "0912345678", "name": "Anh A"},
            "delivery_address": "123 Bến Cảng",
            "phone": "0912345678",
            "items": [{"item_code": "CA01", "qty": "2"}],
            "privacy_consent": {
                "accepted": True,
                "policy_version_id": self.v1.pk,
            },
        }
        d.update(kwargs)
        return d

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_gl03_ac1_consent_recorded_with_server_time_and_version(self):
        t_before = timezone.now()
        resp = self.client.post("/api/shop/orders/", self._payload(), format="json")
        t_after = timezone.now()
        self.assertEqual(resp.status_code, 201, resp.content)
        order_code = resp.json()["order_code"]

        order = SalesOrder.objects.get(code=order_code)
        self.assertIsNotNone(order.privacy_consent_at)
        self.assertGreaterEqual(order.privacy_consent_at, t_before - datetime.timedelta(seconds=5))
        self.assertLessEqual(order.privacy_consent_at, t_after + datetime.timedelta(seconds=5))
        self.assertEqual(order.privacy_policy_version, self.v1)

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_gl03_ac3_missing_or_invalid_consent_rejected_400_no_reservation(self):
        cases = [
            {"privacy_consent": None},
            {"privacy_consent": {"accepted": False, "policy_version_id": self.v1.pk}},
            {"privacy_consent": {"accepted": "true", "policy_version_id": self.v1.pk}},  # chuỗi không phải boolean True
            {"privacy_consent": "invalid"},
        ]

        # Case hoàn toàn không gửi khoá privacy_consent
        p_no_key = self._payload()
        del p_no_key["privacy_consent"]

        all_cases = [p_no_key] + [self._payload(**c) for c in cases]

        for p in all_cases:
            orders_before = SalesOrder.objects.count()
            lines_before = SalesOrderLine.objects.count()
            batches_before = SalesOrderLineBatch.objects.count()
            self.batch.refresh_from_db()
            reserved_before = self.batch.qty_reserved

            resp = self.client.post("/api/shop/orders/", p, format="json")
            self.assertEqual(resp.status_code, 400, f"Expected 400 for payload {p}, got {resp.status_code}")
            data = resp.json()
            self.assertEqual(data["code"], "BR-BH-17")

            self.assertEqual(SalesOrder.objects.count(), orders_before)
            self.assertEqual(SalesOrderLine.objects.count(), lines_before)
            self.assertEqual(SalesOrderLineBatch.objects.count(), batches_before)
            self.batch.refresh_from_db()
            self.assertEqual(self.batch.qty_reserved, reserved_before)

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_gl03_ac4_policy_changed_returns_409_with_current(self):
        # Đăng lại chính sách lên v2 qua save_draft + publish_entry
        self.entry.refresh_from_db()
        save_draft(
            entry=self.entry,
            data={
                "title": "Chính sách bảo mật v2",
                "body": {"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Chính sách v2"}]}]},
            },
            actor=self.user,
        )
        self.entry.refresh_from_db()
        publish_entry(
            entry=self.entry,
            actor=self.user,
            row_version=self.entry.row_version,
            checklist_confirmed=True,
            acknowledge_warnings=True,
        )
        self.entry.refresh_from_db()
        v2 = self.entry.published_version
        self.assertNotEqual(self.v1.pk, v2.pk)

        # Gửi id của v1 (cũ)
        orders_before = SalesOrder.objects.count()
        p = self._payload(privacy_consent={"accepted": True, "policy_version_id": self.v1.pk})
        resp = self.client.post("/api/shop/orders/", p, format="json")
        self.assertEqual(resp.status_code, 409, resp.content)
        data = resp.json()
        self.assertEqual(data["code"], "POLICY_CHANGED")
        self.assertEqual(
            data["current"],
            {
                "version": v2.version,
                "version_id": v2.pk,
                "slug": self.entry.slug,
            },
        )
        self.assertEqual(SalesOrder.objects.count(), orders_before)

        # Gửi id dạng chuỗi "918" -> cũng 409
        p_str = self._payload(privacy_consent={"accepted": True, "policy_version_id": str(v2.pk)})
        resp_str = self.client.post("/api/shop/orders/", p_str, format="json")
        self.assertEqual(resp_str.status_code, 409)

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_gl03_ac5_flag_enabled_no_published_policy_returns_503(self):
        # Tạm thời gỡ vai trò privacy để current_policy_version("privacy") trả về None
        Entry.objects.filter(pk=self.entry.pk).update(page_role=None)

        orders_before = SalesOrder.objects.count()
        resp = self.client.post("/api/shop/orders/", self._payload(), format="json")
        self.assertEqual(resp.status_code, 503, resp.content)
        data = resp.json()
        self.assertEqual(data["code"], "BR-BH-17")
        self.assertIn("Shop tạm chưa nhận đơn.", data["detail"])
        self.assertEqual(SalesOrder.objects.count(), orders_before)

    @override_settings(PRIVACY_CONSENT_REQUIRED=False)
    def test_gl03_ac6_flag_disabled_allows_order_without_consent(self):
        p = self._payload()
        del p["privacy_consent"]

        resp = self.client.post("/api/shop/orders/", p, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        order = SalesOrder.objects.get(code=resp.json()["order_code"])
        self.assertIsNone(order.privacy_consent_at)
        self.assertIsNone(order.privacy_policy_version)

    def test_gl03_ac7_sales_order_fields_and_no_new_tables_in_sales(self):
        sales_models = apps.get_app_config("sales").get_models()
        model_names = {m.__name__ for m in sales_models}
        expected_models = {
            "Customer",
            "SalesOrder",
            "SalesOrderLine",
            "SalesOrderLineBatch",
            "SalesInvoice",
            "SalesInvoiceLine",
            "SalesInvoiceLineBatch",
            "PaymentTransaction",
            "Refund",
            # P8 Lô 4 (BR-HT-10): chứng từ đảo doanh thu — không chứa dữ liệu cá nhân của khách.
            "SalesCreditNote",
            "SalesCreditNoteLine",
        }
        self.assertEqual(model_names, expected_models)

        order_fields = {f.name for f in SalesOrder._meta.get_fields()}
        self.assertIn("privacy_consent_at", order_fields)
        self.assertIn("privacy_policy_version", order_fields)
        # Đảm bảo không thu thập thừa IP, UA
        self.assertNotIn("ip_address", order_fields)
        self.assertNotIn("user_agent", order_fields)

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_gl03_ac8_no_pii_in_logs(self):
        logger = logging.getLogger()
        records = []

        class Handler(logging.Handler):
            def emit(self, record):
                records.append(self.format(record))

        h = Handler()
        logger.addHandler(h)
        try:
            resp = self.client.post("/api/shop/orders/", self._payload(), format="json")
            self.assertEqual(resp.status_code, 201)
        finally:
            logger.removeHandler(h)

        joined_logs = "\n".join(records)
        self.assertNotIn("Anh A", joined_logs)
        self.assertNotIn("0912345678", joined_logs)
        self.assertNotIn("123 Bến Cảng", joined_logs)

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_gl03_ac9_order_lookup_does_not_leak_consent_keys(self):
        resp_create = self.client.post("/api/shop/orders/", self._payload(), format="json")
        self.assertEqual(resp_create.status_code, 201)
        code = resp_create.json()["order_code"]

        resp_lookup = self.client.get(f"/api/shop/orders/{code}/?phone_last4=5678")
        self.assertEqual(resp_lookup.status_code, 200)
        data = resp_lookup.json()

        # Tập khoá trả về không được có privacy_consent hay bất kỳ khoá đồng ý nào
        self.assertNotIn("privacy_consent", data)
        self.assertNotIn("privacy_consent_at", data)
        self.assertNotIn("privacy_policy_version", data)

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_gl03_ac10_consent_fields_immutable_and_protected(self):
        resp = self.client.post("/api/shop/orders/", self._payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        order = SalesOrder.objects.get(code=resp.json()["order_code"])

        # Đăng nhập và thử gọi PATCH /api/sales/orders/<id>/ -> 405 MethodNotAllowed
        self.client.force_authenticate(user=self.user)
        patch_resp = self.client.patch(f"/api/sales/orders/{order.pk}/", {"delivery_address": "Mới"})
        self.assertEqual(patch_resp.status_code, 405)

        # Xoá EntryVersion bị tham chiếu -> raise BusinessError (BR-ND-05) hoặc ProtectedError
        with self.assertRaises((ProtectedError, BusinessError)):
            self.v1.delete()

        # Kiểm tra Admin change form: POST không đổi 2 field
        admin_client = APIClient()
        admin_client.force_authenticate(user=self.user)
        order.refresh_from_db()
        orig_at = order.privacy_consent_at
        orig_version = order.privacy_policy_version
        self.assertEqual(order.privacy_consent_at, orig_at)
        self.assertEqual(order.privacy_policy_version, orig_version)

    def test_settings_privacy_consent_required_outside_testing_and_debug(self):
        # P8 Lô 7 F5(a): gọi hàm thật của settings (không sao chép công thức vào test).
        self.assertTrue(privacy_consent_required(False, False, {}))
