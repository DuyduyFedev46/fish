"""
P1 (BR-TT-01, 13, 14, 17): máy chủ lập tham số thanh toán cổng SePay cho đơn Giữ chỗ.

`POST /api/shop/orders/<order_code>/checkout/` — Shop công khai (guest), KHÔNG cần 4 số
cuối SĐT vì response không chứa thông tin khách (P1-AC6).
"""
import datetime
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments import checkout as checkout_services
from apps.sales.payments import services as payment_services

SEPAY_SETTINGS = dict(
    SEPAY_ENV="SANDBOX",
    SEPAY_MERCHANT_ID="MCH-TEST-01",
    SEPAY_SECRET_KEY="top-secret-do-not-leak",
    SHOP_BASE_URL="https://shop.example.vn",
    SEPAY_CHECKOUT_URL_SANDBOX="https://pay-sandbox.sepay.vn/v1/checkout/init",
    SEPAY_CHECKOUT_URL_PRODUCTION="https://pay.sepay.vn/v1/checkout/init",
)


@override_settings(**SEPAY_SETTINGS)
class CheckoutParamsBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        g = ItemGroup.objects.create(name="Cá")
        item = Item.objects.create(code="CA-P1", name="Cá", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(
            price_list=pl, item=item, rate=Decimal("180000"),
            valid_from=timezone.localdate() - datetime.timedelta(days=1),
        )
        b = batch_services.create_batch(
            item=item, supplier=Supplier.objects.create(name="A"),
            warehouse=Warehouse.objects.create(name="Kho"),
            received_date=timezone.localdate(), qty=Decimal("50"), purchase_rate=Decimal("100000"),
        )
        batch_services.publish_batch(batch=b, actor=None)
        self.order = order_services.create_order(
            customer_phone="0912345678", customer_name="Chị Hoa", delivery_address="12 Lê Lợi",
            phone="0912345678", lines=[{"item_code": "CA-P1", "qty": Decimal("3")}],
        )  # tổng 540.000đ

    def _checkout(self, code=None):
        return self.client.post(f"/api/shop/orders/{code or self.order.code}/checkout/")


class P1AC1HappyPathTests(CheckoutParamsBase):
    def test_p1_ac1_returns_signed_checkout_params(self):
        resp = self._checkout()
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data["order_invoice_number"], self.order.code)
        self.assertEqual(data["order_amount"], "540000")
        self.assertEqual(data["currency"], "VND")
        self.assertEqual(data["merchant"], "MCH-TEST-01")
        self.assertEqual(data["operation"], "PURCHASE")
        self.assertEqual(data["payment_method"], "BANK_TRANSFER")  # VietQR — V1 chỉ giá trị này
        self.assertEqual(data["order_description"], f"Thanh toan don {self.order.code}")
        self.assertEqual(data["checkout_url"], "https://pay-sandbox.sepay.vn/v1/checkout/init")
        self.assertTrue(data["success_url"])
        self.assertTrue(data["cancel_url"])
        self.assertTrue(data["error_url"])
        self.assertIn(self.order.code, data["success_url"])
        self.assertTrue(data["signature"])
        self.assertNotIn("merchant_id", data)  # tên field ĐÚNG là "merchant" (SDK chính thức)

        # Chữ ký phải khớp lại được (cô lập trong 1 hàm — BR-TT-13).
        expected = checkout_services._sign(checkout_services._signature_string({
            "merchant": "MCH-TEST-01", "operation": "PURCHASE",
            "payment_method": "BANK_TRANSFER", "order_amount": "540000", "currency": "VND",
            "order_invoice_number": self.order.code,
            "order_description": data["order_description"],
            "success_url": data["success_url"], "error_url": data["error_url"],
            "cancel_url": data["cancel_url"],
        }))
        self.assertEqual(data["signature"], expected)

    def test_p1_ac1_fields_is_ordered_array_ending_with_signature(self):
        """`fields` là NGUỒN CHÍNH cho FE dựng form POST — mảng có thứ tự đúng SDK SePay."""
        data = self._checkout().json()
        names = [f["name"] for f in data["fields"]]
        self.assertEqual(names, [
            "merchant", "operation", "payment_method", "order_amount", "currency",
            "order_invoice_number", "order_description", "success_url", "error_url",
            "cancel_url", "signature",
        ])
        by_name = {f["name"]: f["value"] for f in data["fields"]}
        self.assertEqual(by_name["merchant"], "MCH-TEST-01")
        self.assertEqual(by_name["order_amount"], "540000")
        self.assertEqual(by_name["signature"], data["signature"])

    def test_p1_ac1_no_secret_leak_via_fields_array(self):
        data = self._checkout().json()
        values = [f["value"] for f in data["fields"]]
        self.assertNotIn("top-secret-do-not-leak", values)


class SignatureAlgorithmVectorTests(TestCase):
    """
    Vector cố định, tính độc lập với chính thuật toán trong `checkout.py` — đúng theo SDK
    chính thức SePay (`sepayvn/sepay-pg-node`, `src/checkout.ts`): nối "key=value" (bỏ key
    None) THEO THỨ TỰ FORM, phân cách ",", HMAC-SHA256, base64 (KHÔNG hex).
    """

    def test_signature_matches_independently_computed_vector(self):
        import base64
        import hashlib
        import hmac

        secret = "test-secret"
        values = {
            "merchant": "MCH1", "operation": "PURCHASE", "payment_method": "BANK_TRANSFER",
            "order_amount": "540000", "currency": "VND",
            "order_invoice_number": "SO260926-A1B2C3",
            "order_description": "Thanh toan don SO260926-A1B2C3",
            "success_url": "https://shop.example.vn/s", "error_url": "https://shop.example.vn/e",
            "cancel_url": "https://shop.example.vn/c",
        }
        message = checkout_services._signature_string(values)
        self.assertEqual(
            message,
            "merchant=MCH1,operation=PURCHASE,payment_method=BANK_TRANSFER,"
            "order_amount=540000,currency=VND,order_invoice_number=SO260926-A1B2C3,"
            "order_description=Thanh toan don SO260926-A1B2C3,"
            "success_url=https://shop.example.vn/s,error_url=https://shop.example.vn/e,"
            "cancel_url=https://shop.example.vn/c",
        )
        expected_digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        expected_signature = base64.b64encode(expected_digest).decode("ascii")

        with override_settings(SEPAY_SECRET_KEY=secret):
            actual_signature = checkout_services._sign(message)
        self.assertEqual(actual_signature, expected_signature)
        # base64, KHÔNG phải hex (hex chỉ gồm 0-9a-f, base64 có thể có chữ hoa/=/+ etc.)
        self.assertTrue(any(c not in "0123456789abcdef" for c in actual_signature))

    def test_different_field_order_gives_different_signature(self):
        """Thứ tự field đổi -> chữ ký đổi — chứng minh thứ tự có ý nghĩa (không phải HMAC vô hại)."""
        secret = "test-secret"
        values = {
            "merchant": "MCH1", "operation": "PURCHASE", "payment_method": "BANK_TRANSFER",
            "order_amount": "540000", "currency": "VND",
            "order_invoice_number": "SO260926-A1B2C3",
        }
        ordered_message = checkout_services._signature_string(values)
        # Cùng cặp key=value nhưng nối theo thứ tự KHÁC FIELD_ORDER (đảo tay).
        reordered_message = ",".join([
            f"currency={values['currency']}", f"merchant={values['merchant']}",
            f"operation={values['operation']}", f"payment_method={values['payment_method']}",
            f"order_amount={values['order_amount']}",
            f"order_invoice_number={values['order_invoice_number']}",
        ])
        self.assertNotEqual(ordered_message, reordered_message)
        with override_settings(SEPAY_SECRET_KEY=secret):
            sig_ordered = checkout_services._sign(ordered_message)
            sig_reordered = checkout_services._sign(reordered_message)
        self.assertNotEqual(sig_ordered, sig_reordered)

    def test_none_values_are_skipped_not_stringified(self):
        message = checkout_services._signature_string({
            "merchant": "MCH1", "env": None, "operation": "PURCHASE", "customer_id": None,
        })
        self.assertEqual(message, "merchant=MCH1,operation=PURCHASE")


class P1AC2NoSecretLeakTests(CheckoutParamsBase):
    def test_p1_ac2_no_secret_in_response(self):
        resp = self._checkout()
        body_text = resp.content.decode("utf-8")
        self.assertNotIn("top-secret-do-not-leak", body_text)
        data = resp.json()
        self.assertNotIn("secret_key", data)
        self.assertNotIn("SEPAY_SECRET_KEY", data)


class P1AC3EnvironmentConfigTests(CheckoutParamsBase):
    def test_p1_ac3_sandbox_env_uses_sandbox_url(self):
        data = self._checkout().json()
        self.assertEqual(data["environment"], "SANDBOX")
        self.assertEqual(data["checkout_url"], "https://pay-sandbox.sepay.vn/v1/checkout/init")

    @override_settings(SEPAY_ENV="PRODUCTION")
    def test_p1_ac3_production_env_uses_production_url_by_config_only(self):
        data = self._checkout().json()
        self.assertEqual(data["environment"], "PRODUCTION")
        self.assertEqual(data["checkout_url"], "https://pay.sepay.vn/v1/checkout/init")


class P1AC4RejectInvalidOrderTests(CheckoutParamsBase):
    def test_p1_ac4_expired_ttl_rejected_even_if_still_booked_status(self):
        self.order.booked_expires_at = timezone.now() - datetime.timedelta(minutes=1)
        self.order.save(update_fields=["booked_expires_at"])
        resp = self._checkout()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("hết hạn", resp.json()["detail"])

    def test_p1_ac4_auto_cancelled_rejected(self):
        self.order.booked_expires_at = timezone.now() - datetime.timedelta(minutes=1)
        self.order.save(update_fields=["booked_expires_at"])
        order_services.cancel_unpaid_expired()
        resp = self._checkout()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("hết hạn", resp.json()["detail"])

    def test_p1_ac4_already_paid_rejected(self):
        payment_services.confirm_payment(
            order=self.order, bank_txn_id="FT-P1", amount=self.order.total_amount,
            received_at=timezone.now(),
        )
        resp = self._checkout()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("đã thanh toán", resp.json()["detail"])

    def test_p1_ac4_order_not_found_404(self):
        resp = self._checkout(code="SO-KHONGCO")
        self.assertEqual(resp.status_code, 404)


class P1AC5RetryPaymentTests(CheckoutParamsBase):
    def test_p1_ac5_repeat_checkout_same_order_same_amount(self):
        first = self._checkout().json()
        second = self._checkout().json()
        self.assertEqual(first["order_amount"], second["order_amount"])
        # Q5: từ lần 2 thêm hậu tố lần thử, adapter bóc lại đúng mã gốc.
        self.assertEqual(first["order_invoice_number"], self.order.code)
        self.assertEqual(second["order_invoice_number"], f"{self.order.code}-2")
        self.order.refresh_from_db()
        self.assertEqual(self.order.checkout_attempts, 2)


class P1AC6NoCustomerPiiTests(CheckoutParamsBase):
    def test_p1_ac6_response_has_no_customer_pii(self):
        data = self._checkout().json()
        blob = str(data)
        for leaked in ("Chị Hoa", "0912345678", "12 Lê Lợi"):
            self.assertNotIn(leaked, blob)


class P1AC7NoVietqrStubTests(CheckoutParamsBase):
    def test_p1_ac7_order_create_response_has_no_vietqr_field(self):
        resp = self.client.post(
            "/api/shop/orders/",
            {
                "customer": {"phone": "0987000000", "name": "Anh B"},
                "delivery_address": "1 Bến Cảng", "phone": "0987000000",
                "items": [{"item_code": "CA-P1", "qty": "1"}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertNotIn("vietqr", resp.json())
