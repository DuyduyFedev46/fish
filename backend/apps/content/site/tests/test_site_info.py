from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.content.site.checks import check_seller_info


class SiteInfoApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("public-site-info")

    @override_settings(
        SELLER_NAME="Vựa Thử Nghiệm",
        SELLER_BUSINESS_TYPE="Hộ kinh doanh",
        SELLER_REG_NO="0000000000",
        SELLER_TAX_CODE="0000000000",
        SELLER_ADDRESS="1 Đường Thử, Phường Thử, Tỉnh Thử",
        SELLER_PHONE="0900000000",
        SELLER_EMAIL="lienhe@example.com",
        PRIVACY_CONSENT_REQUIRED=True,
        SHOP_CONFIRM_CALL_NOTICE=False,
        SHOP_CONFIRM_CALL_HOURS="7:00–20:00",
    )
    def test_gl01_ac1_seller_complete_when_all_fields_provided(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["seller_complete"])
        self.assertEqual(
            data["seller"],
            {
                "name": "Vựa Thử Nghiệm",
                "business_type": "Hộ kinh doanh",
                "registration_no": "0000000000",
                "tax_code": "0000000000",
                "address": "1 Đường Thử, Phường Thử, Tỉnh Thử",
                "phone": "0900000000",
                "email": "lienhe@example.com",
            },
        )
        self.assertIs(data["privacy_consent_required"], True)
        self.assertIs(data["confirm_call_notice"], False)
        self.assertEqual(data["confirm_call_hours"], "7:00–20:00")

    @override_settings(
        SELLER_NAME="Vựa Thử Nghiệm",
        SELLER_PHONE="0900000000",
    )
    def test_gl01_ac3_seller_phone_dynamic_without_cache(self):
        resp1 = self.client.get(self.url)
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()["seller"]["phone"], "0900000000")

        with override_settings(SELLER_PHONE="0911223344"):
            resp2 = self.client.get(self.url)
            self.assertEqual(resp2.status_code, 200)
            self.assertEqual(resp2.json()["seller"]["phone"], "0911223344")

    @override_settings(
        SELLER_NAME="Vựa Thử Nghiệm",
        SELLER_BUSINESS_TYPE="Hộ kinh doanh",
        SELLER_REG_NO="0000000000",
        SELLER_TAX_CODE="",
        SELLER_ADDRESS="1 Đường Thử, Phường Thử, Tỉnh Thử",
        SELLER_PHONE="0900000000",
        SELLER_EMAIL="lienhe@example.com",
    )
    def test_gl01_ac4_missing_seller_tax_code_warning_w001(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["seller"]["tax_code"])
        self.assertFalse(data["seller_complete"])

        warnings = check_seller_info()
        self.assertEqual(len(warnings), 1)
        w = warnings[0]
        self.assertEqual(w.id, "content.W001")
        self.assertIn("SELLER_TAX_CODE", w.msg)
        # Không in giá trị biến khác (như tên người bán, địa chỉ, sđt) vào cảnh báo
        self.assertNotIn("Vựa Thử Nghiệm", w.msg)
        self.assertNotIn("0900000000", w.msg)
        self.assertNotIn("1 Đường Thử", w.msg)

    @override_settings(
        SELLER_NAME="Vựa Thử Nghiệm",
        SELLER_BUSINESS_TYPE="Hộ kinh doanh",
        SELLER_REG_NO="0000000000",
        SELLER_TAX_CODE="0000000000",
        SELLER_ADDRESS="1 Đường Thử",
        SELLER_PHONE="0900000000",
        SELLER_EMAIL="lienhe@example.com",
        SEPAY_SECRET_KEY="sepay-secret-gia-12345",
    )
    def test_gl01_ac7_contract_keys_and_no_secrets_leaked(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Tập khoá gốc: cho phép 5 khoá của khung go-live + cskh_notice của CSKH Lô 3
        expected_root_keys = {
            "seller",
            "seller_complete",
            "privacy_consent_required",
            "confirm_call_notice",
            "confirm_call_hours",
            "cskh_notice",
            "confirmation_policy",
        }
        self.assertEqual(set(data.keys()), expected_root_keys)

        expected_seller_keys = {
            "name",
            "business_type",
            "registration_no",
            "tax_code",
            "address",
            "phone",
            "email",
        }
        self.assertEqual(set(data["seller"].keys()), expected_seller_keys)

        raw_content = resp.content.decode("utf-8")
        self.assertNotIn("sepay-secret-gia-12345", raw_content)
        self.assertNotIn("SEPAY_SECRET_KEY", raw_content)

    def test_gl01_ac8_disallowed_methods_405(self):
        for method in [self.client.post, self.client.put, self.client.patch, self.client.delete]:
            resp = method(self.url, data={})
            self.assertEqual(resp.status_code, 405)

        # Kiểm tra Cache-Control
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("Cache-Control"), "public, max-age=300")
