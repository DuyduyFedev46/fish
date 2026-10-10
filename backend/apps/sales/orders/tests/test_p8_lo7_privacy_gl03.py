"""
P8 Lô 7 — SR-24 / F5: củng cố test khung go-live GL-03. Dữ liệu giả.

- F5(a) hàm đọc cờ `privacy_consent_required(testing, debug, env)` ở config/settings.py:
  mặc định TẮT khi test/debug, BẬT ngoài dev/test, biến môi trường ghi đè.
- F5(b) GL-03-AC10: POST Django Admin thật (force_login superuser) đổi 2 field consent -> không đổi.
- F5(c) GL-03-AC9: response tra đơn của đơn CÓ đồng ý bằng đúng tập khoá công khai.
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.content.models.entries import Entry
from apps.sales.models import SalesOrder
from apps.sales.orders.tests import test_privacy_consent as base
from config.settings import privacy_consent_required

User = get_user_model()

PUBLIC_LOOKUP_KEYS = {
    "order_code", "status", "state", "status_label", "placed_at", "paid_at", "delivered_at", "booked_expires_at",
    "server_now", "hold_minutes", "payment_pending_minutes", "delivery", "lines", "subtotal", "discount",
    "total_amount", "cancel_notice", "late_payment", "lookup_token",
}


def _lookup(code, phone="0912345678"):
    return APIClient().post("/api/shop/orders/lookup/", {"order_code": code, "phone": phone}, format="json")


class PrivacyConsentFlagFunctionTests(TestCase):
    def test_f5a_ngoai_dev_va_test_mac_dinh_bat(self):
        self.assertTrue(privacy_consent_required(False, False, {}))

    def test_f5a_test_hoac_debug_mac_dinh_tat(self):
        self.assertFalse(privacy_consent_required(True, False, {}))
        self.assertFalse(privacy_consent_required(False, True, {}))
        self.assertFalse(privacy_consent_required(True, True, {}))

    def test_f5a_bien_moi_truong_ghi_de_ca_hai_chieu(self):
        for val in ("1", "true", "TRUE", " yes ", "on"):
            with self.subTest(val=val):
                self.assertTrue(privacy_consent_required(True, True, {"PRIVACY_CONSENT_REQUIRED": val}))
        for val in ("0", "false", "no", "off", ""):
            with self.subTest(val=val):
                self.assertFalse(privacy_consent_required(False, False, {"PRIVACY_CONSENT_REQUIRED": val}))

    def test_f5a_settings_dang_chay_dung_gia_tri_ham(self):
        """Hằng cấu hình đang dùng phải bằng đúng kết quả của hàm với môi trường thật lúc nạp."""
        import os
        from django.conf import settings as dj
        from config import settings as cfg
        self.assertEqual(
            cfg.PRIVACY_CONSENT_REQUIRED,
            privacy_consent_required(cfg.TESTING, cfg.DEBUG, os.environ),
        )
        self.assertIsInstance(dj.PRIVACY_CONSENT_REQUIRED, bool)


class ConsentEvidenceTests(TestCase):
    """Dùng lại fixture (trang chính sách đã đăng, lô, giá) của PrivacyConsentTests mà không chạy lại test của nó."""

    def setUp(self):
        base.PrivacyConsentTests.setUp(self)

    _payload = base.PrivacyConsentTests._payload

    def _create_order_with_consent(self):
        res = self.client.post("/api/shop/orders/", self._payload(), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        return SalesOrder.objects.get(code=res.json()["order_code"]), res.json()["order_code"]

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_f5c_gl03_ac9_tra_don_co_dong_y_dung_tap_khoa_cong_khai(self):
        order, code = self._create_order_with_consent()
        self.assertIsNotNone(order.privacy_consent_at)  # chắc chắn là đơn CÓ đồng ý
        res = _lookup(code)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(set(res.json().keys()), PUBLIC_LOOKUP_KEYS)

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_f5c_gl03_ac9_tra_don_khong_chua_gia_tri_ca_nhan_hay_consent(self):
        _, code = self._create_order_with_consent()
        body = _lookup(code).content.decode()
        for forbidden in ("Anh A", "0912345678", "123 Bến Cảng", "privacy", "consent", "policy_version"):
            self.assertNotIn(forbidden, body)

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_f5b_gl03_ac10_admin_post_khong_doi_2_field_consent(self):
        order, _ = self._create_order_with_consent()
        orig_at, orig_ver = order.privacy_consent_at, order.privacy_policy_version
        self.assertIsNotNone(orig_at)
        self.assertIsNotNone(orig_ver)

        su = User.objects.create_superuser(username="su_gl03", password="x", email="su@example.invalid")
        c = self.client_class()
        c.force_login(su)
        url = reverse("admin:sales_salesorder_change", args=[order.pk])
        page = c.get(url)
        self.assertEqual(page.status_code, 200)

        # Dựng dữ liệu form từ chính form của Admin, rồi cố tình gửi giá trị khác cho 2 field consent.
        form = page.context["adminform"].form
        data = {}
        for name, field in form.fields.items():
            val = form.initial.get(name)
            if val is None:
                continue
            data[name] = val.pk if hasattr(val, "pk") else val
        for fs in page.context["inline_admin_formsets"]:
            mgmt = fs.formset.management_form
            for k, v in mgmt.initial.items():
                data[f"{fs.formset.prefix}-{k}"] = v
            for i, f in enumerate(fs.formset.forms):
                for name in f.fields:
                    v = f.initial.get(name)
                    if v is not None:
                        data[f"{f.prefix}-{name}"] = v.pk if hasattr(v, "pk") else v
        other_entry = Entry.objects.create(
            kind="page", title="Trang khác", slug="trang-khac-gl03", excerpt="x", created_by=su,
        )
        data["privacy_consent_at"] = "2020-01-01 00:00:00"
        data["privacy_policy_version"] = str(other_entry.pk)
        res = c.post(url, data)
        self.assertIn(res.status_code, (200, 302), getattr(res, "content", b"")[:300])

        order.refresh_from_db()
        self.assertEqual(order.privacy_consent_at, orig_at)
        self.assertEqual(order.privacy_policy_version, orig_ver)

    def test_f5b_admin_khong_hien_2_field_consent_o_dang_sua_duoc(self):
        """Hai field là readonly_fields: không nằm trong form.fields (không có ô nhập)."""
        from django.contrib import admin
        from apps.sales.models import SalesOrder as SO
        ma = admin.site._registry[SO]
        self.assertIn("privacy_consent_at", ma.readonly_fields)
        self.assertIn("privacy_policy_version", ma.readonly_fields)
