"""
site-info mở rộng cho Shop mới (SHOP-5-01 AC1–AC5; 02b §3.6; BR-ND-18; bất biến 9).

Dữ liệu trong test là giả (số 0900000000, tên "Khách Giả"), không dùng dữ liệu thật.
"""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.content.body.scan import get_phone_allowlist

NEW_SELLER_KEYS = {
    "zalo",
    "working_hours",
    "registration_issued_by",
    "registration_issued_on",
    "website_notice_url",
    "website_notice_image",
}
OLD_SELLER_VALUES = dict(
    SELLER_NAME="Vựa Thử Nghiệm",
    SELLER_BUSINESS_TYPE="Hộ kinh doanh",
    SELLER_REG_NO="0000000000",
    SELLER_TAX_CODE="0000000000",
    SELLER_ADDRESS="1 Đường Thử, Phường Thử, Tỉnh Thử",
    SELLER_PHONE="0900000000",
    SELLER_EMAIL="lienhe@example.com",
)
EMPTY_NEW_VALUES = dict(
    SELLER_ZALO="",
    SELLER_WORKING_HOURS="",
    SELLER_REG_ISSUED_BY="",
    SELLER_REG_ISSUED_ON="",
    SELLER_WEBSITE_NOTICE_URL="",
    SELLER_WEBSITE_NOTICE_IMAGE="",
    SHOP_RETURN_REPORT_HOURS="",
)


class SiteInfoShopTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("public-site-info")

    def get(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        return resp.json()

    @override_settings(
        **OLD_SELLER_VALUES,
        SELLER_ZALO="0900000001",
        SELLER_WORKING_HOURS="7:00–20:00 hằng ngày",
        SELLER_REG_ISSUED_BY="Phòng Tài chính – Kế hoạch (giả)",
        SELLER_REG_ISSUED_ON="01/01/2026",
        SELLER_WEBSITE_NOTICE_URL="https://example.com/thong-bao",
        SELLER_WEBSITE_NOTICE_IMAGE="https://example.com/da-thong-bao.png",
        SHOP_RETURN_REPORT_HOURS="24",
    )
    def test_shop_5_01_ac1_returns_new_seller_keys_and_policies(self):
        """AC1 (BR-ND-18): env có giá trị -> trả đúng các khoá mới + khối policies."""
        data = self.get()
        seller = data["seller"]
        self.assertEqual(seller["zalo"], "0900000001")
        self.assertEqual(seller["working_hours"], "7:00–20:00 hằng ngày")
        self.assertEqual(seller["registration_issued_by"], "Phòng Tài chính – Kế hoạch (giả)")
        self.assertEqual(seller["registration_issued_on"], "01/01/2026")
        self.assertEqual(seller["website_notice_url"], "https://example.com/thong-bao")
        self.assertEqual(seller["website_notice_image"], "https://example.com/da-thong-bao.png")
        self.assertTrue(data["seller_complete"])
        self.assertEqual(
            data["policies"],
            {"return_report_hours": 24, "min_qty_kg": "1", "qty_step_kg": "0.5", "hold_minutes": 30},
        )

    @override_settings(**OLD_SELLER_VALUES, **EMPTY_NEW_VALUES)
    def test_shop_5_01_ac2_empty_env_gives_null_not_empty_string(self):
        """AC2: env trống -> null (không "", không "Đang chờ"); seller_complete giữ nghĩa 7 trường cũ."""
        data = self.get()
        for key in NEW_SELLER_KEYS:
            self.assertIn(key, data["seller"])
            self.assertIsNone(data["seller"][key], key)
        self.assertIsNone(data["policies"]["return_report_hours"])
        self.assertTrue(data["seller_complete"])
        self.assertNotIn("Đang chờ", self.client.get(self.url).content.decode())

    @override_settings(**EMPTY_NEW_VALUES)
    def test_shop_5_01_ac2_whitespace_values_are_null(self):
        with override_settings(SELLER_ZALO="   ", SELLER_WORKING_HOURS="\t"):
            data = self.get()
        self.assertIsNone(data["seller"]["zalo"])
        self.assertIsNone(data["seller"]["working_hours"])

    def test_shop_5_01_return_report_hours_invalid_is_null(self):
        """Số giờ không phải số nguyên dương -> null (Shop ẩn câu có số, E3)."""
        for raw in ("abc", "0", "-5", "1.5"):
            with self.subTest(raw=raw), override_settings(SHOP_RETURN_REPORT_HOURS=raw):
                self.assertIsNone(self.get()["policies"]["return_report_hours"])

    def test_shop_5_01_website_notice_only_http_links(self):
        """Link/ảnh thông báo website chỉ nhận http(s); giá trị khác -> null (chặn javascript:)."""
        with override_settings(
            SELLER_WEBSITE_NOTICE_URL="javascript:alert(1)",
            SELLER_WEBSITE_NOTICE_IMAGE="data:image/png;base64,AAAA",
        ):
            seller = self.get()["seller"]
        self.assertIsNone(seller["website_notice_url"])
        self.assertIsNone(seller["website_notice_image"])

    @override_settings(SHOP_MIN_QTY_KG=Decimal("1.0"), SHOP_QTY_STEP_KG=Decimal("0.50"), SALES_ORDER_TTL_MINUTES=15)
    def test_shop_5_01_policies_follow_settings(self):
        """Ba số cho trang Cách mua đọc từ settings, số kg in gọn (không số 0 thừa)."""
        policies = self.get()["policies"]
        self.assertEqual(policies["min_qty_kg"], "1")
        self.assertEqual(policies["qty_step_kg"], "0.5")
        self.assertEqual(policies["hold_minutes"], 15)

    def test_shop_5_01_ac3_no_search_chips(self):
        """AC3 (D): không có khoá search_chips."""
        self.assertNotIn("search_chips", self.get())

    def test_shop_5_01_ac4_contract_keys_exact(self):
        """AC4 (G2): chỉ đúng tập khoá đã chốt — không thêm khoá nào khác."""
        data = self.get()
        self.assertEqual(
            set(data.keys()),
            {"seller", "seller_complete", "privacy_consent_required", "confirm_call_notice",
             "confirm_call_hours", "confirmation_policy", "policies"},
        )
        self.assertEqual(
            set(data["seller"].keys()),
            {"name", "business_type", "registration_no", "tax_code", "address", "phone", "email"} | NEW_SELLER_KEYS,
        )
        self.assertEqual(set(data["policies"].keys()), {"return_report_hours", "min_qty_kg", "qty_step_kg", "hold_minutes"})

    @override_settings(**OLD_SELLER_VALUES)
    def test_shop_5_01_ac4_no_customer_data(self):
        """AC4 (bất biến 9): có khách trong DB nhưng site-info không chứa tên, SĐT, địa chỉ khách."""
        from apps.sales.models import Customer

        Customer.objects.create(phone="0912345678", name="Khách Giả Một", default_address="99 Đường Giả, Phường Giả")
        text = self.client.get(self.url).content.decode()
        for forbidden in ("0912345678", "Khách Giả Một", "99 Đường Giả", "customer", "delivery_address"):
            self.assertNotIn(forbidden, text)


class PhoneAllowlistTests(TestCase):
    @override_settings(CONTENT_PHONE_ALLOWLIST=(), SHOP_HOTLINE="0900 000 002", SELLER_PHONE="+84900000003")
    def test_shop_5_01_ac5_hotline_and_seller_phone_in_allowlist(self):
        """AC5 (06-marketing F4): hotline và SĐT người bán tự nằm trong danh sách số được phép."""
        allowed = get_phone_allowlist()
        self.assertIn("0900000002", allowed)
        self.assertIn("0900000003", allowed)

    @override_settings(CONTENT_PHONE_ALLOWLIST=("0900000004",), SHOP_HOTLINE="1900 xxxx", SELLER_PHONE="")
    def test_shop_5_01_ac5_placeholder_hotline_is_ignored(self):
        """Hotline giữ chỗ (chưa phải số) không thêm gì; danh sách cấu hình vẫn giữ."""
        self.assertEqual(get_phone_allowlist(), {"0900000004"})
