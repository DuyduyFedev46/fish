"""Test webhook nội bộ SePay (adapter FastAPI gọi vào, service token)."""
import datetime
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesInvoice
from apps.sales.orders import services as order_services


@override_settings(INTERNAL_SERVICE_TOKEN="secret-token")
class WebhookInternalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        g = ItemGroup.objects.create(name="Cá")
        item = Item.objects.create(code="CA01", name="Cá", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(
            price_list=pl, item=item, rate=Decimal("100000"),
            valid_from=timezone.localdate() - datetime.timedelta(days=1),
        )
        b = batch_services.create_batch(
            item=item, supplier=Supplier.objects.create(name="A"),
            warehouse=Warehouse.objects.create(name="Kho"),
            received_date=timezone.localdate(), qty=Decimal("50"), purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=b, actor=None)
        self.order = order_services.create_order(
            customer_phone="0912345678", customer_name="A", delivery_address="x",
            phone="0912345678", lines=[{"item_code": "CA01", "qty": Decimal("2")}],
        )

    def _post(self, token, body):
        return self.client.post(
            "/api/internal/payments/sepay-webhook/", body, format="json",
            HTTP_X_INTERNAL_TOKEN=token,
        )

    def test_wrong_token_401(self):
        resp = self._post("wrong", {"bank_txn_id": "T1", "order_code": self.order.code,
                                    "amount": "200000", "received_at": timezone.now().isoformat()})
        self.assertEqual(resp.status_code, 401)

    def test_matched_payment_issues_invoice(self):
        resp = self._post("secret-token", {
            "bank_txn_id": "T2", "order_code": self.order.code,
            "amount": str(self.order.total_amount), "received_at": timezone.now().isoformat(),
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["matched"])
        self.assertEqual(SalesInvoice.objects.filter(sales_order=self.order).count(), 1)
        # signal tự tạo phiếu giao
        inv = SalesInvoice.objects.get(sales_order=self.order)
        self.assertEqual(inv.delivery_notes.count(), 1)

    def test_orphan_when_order_code_unknown(self):
        resp = self._post("secret-token", {
            "bank_txn_id": "T3", "order_code": "SO-KHONGCO",
            "amount": "50000", "received_at": timezone.now().isoformat(),
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["matched"])

    # --- QA lần 2 · N3: thiếu/sai received_at → 400 có code (trước đây 500 IntegrityError) ---
    def test_n3_thieu_received_at_400_khong_ghi_gi(self):
        from apps.sales.models import PaymentTransaction
        for order_code in (self.order.code, "SO-KHONGCO"):
            for bad in (None, "", "khong-phai-ngay", "2026-13-45T10:00:00"):
                with self.subTest(order_code=order_code, received_at=bad):
                    body = {"bank_txn_id": "T-N3", "order_code": order_code, "amount": "200000"}
                    if bad is not None:
                        body["received_at"] = bad
                    resp = self._post("secret-token", body)
                    self.assertEqual(resp.status_code, 400, resp.content)
                    self.assertEqual(resp.json()["code"], "WEBHOOK_INVALID_INPUT")
                    self.assertIn("received_at", resp.json()["detail"])
        self.assertFalse(PaymentTransaction.objects.filter(bank_txn_id="T-N3").exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "BOOKED")


# --- Sửa theo code review trước deploy 1 (BR-TT-03/05, bảo mật webhook) ---------------------
@override_settings(INTERNAL_SERVICE_TOKEN="secret-token")
class ReviewWebhookFixTests(TestCase):
    """R1: amount phải hữu hạn và > 0 · R3: so token bằng hmac.compare_digest ·
    R5: idempotent theo bank_txn_id khi thiếu/sai order_code; bank_txn_id ≤ 100 ký tự."""

    setUp = WebhookInternalTests.setUp
    _post = WebhookInternalTests._post

    def body(self, **kw):
        base = {"bank_txn_id": "T-R", "order_code": self.order.code,
                "amount": str(self.order.total_amount), "received_at": timezone.now().isoformat()}
        base.update(kw)
        return {k: v for k, v in base.items() if v is not None}

    def test_r1_amount_khong_huu_han_hoac_khong_duong_400_khong_ghi_gi(self):
        from apps.sales.models import PaymentTransaction
        for order_code in (self.order.code, "SO-KHONGCO", ""):
            for bad in ("NaN", "nan", "sNaN", "Infinity", "-Infinity", "inf", "-5", "0",
                        "0.00", "abc", "", None, [1], {"x": 1}):
                with self.subTest(order_code=order_code, amount=bad):
                    body = self.body(order_code=order_code)
                    body.pop("amount")
                    if bad is not None:
                        body["amount"] = bad
                    resp = self._post("secret-token", body)
                    self.assertEqual(resp.status_code, 400, resp.content)
                    self.assertEqual(resp.json()["code"], "WEBHOOK_INVALID_INPUT")
                    self.assertIn("amount", resp.json()["detail"])
        self.assertFalse(PaymentTransaction.objects.exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "BOOKED")

    def test_r1_amount_so_duong_van_nhan(self):
        resp = self._post("secret-token", self.body(amount=float(self.order.total_amount)))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["matched"])

    def test_r3_so_token_bang_compare_digest(self):
        import hmac
        from unittest import mock
        with mock.patch("apps.sales.payments.internal_api.hmac.compare_digest",
                        wraps=hmac.compare_digest) as spy:
            self.assertEqual(self._post("sai", self.body()).status_code, 401)
            self.assertEqual(self._post("", self.body()).status_code, 401)
            self.assertEqual(self._post("secret-token", self.body()).status_code, 200)
        self.assertGreaterEqual(spy.call_count, 2)

    def test_r3_token_khong_ascii_401_khong_500(self):
        self.assertEqual(self._post("tôken", self.body()).status_code, 401)

    @override_settings(INTERNAL_SERVICE_TOKEN="")
    def test_r3_chua_cau_hinh_token_luon_401(self):
        self.assertEqual(self._post("", self.body()).status_code, 401)

    def test_r5_gui_lai_khong_order_code_ma_giao_dich_da_khop_tra_matched(self):
        first = self._post("secret-token", self.body(bank_txn_id="T-R5"))
        self.assertTrue(first.json()["matched"])
        for order_code in (None, "", "SO-KHONGCO"):
            with self.subTest(order_code=order_code):
                resp = self._post("secret-token", self.body(bank_txn_id="T-R5",
                                                            order_code=order_code))
                self.assertEqual(resp.status_code, 200, resp.content)
                self.assertTrue(resp.json()["matched"])
                self.assertEqual(resp.json()["order_status"], "PROCESSING")
                self.assertEqual(resp.json()["match_status"], "MATCHED")
        from apps.sales.models import PaymentTransaction
        self.assertEqual(PaymentTransaction.objects.filter(bank_txn_id="T-R5").count(), 1)
        self.assertEqual(SalesInvoice.objects.filter(sales_order=self.order).count(), 1)

    def test_r5_gui_lai_giao_dich_chua_khop_van_matched_false(self):
        body = self.body(bank_txn_id="T-R5b", order_code="SO-KHONGCO")
        self.assertFalse(self._post("secret-token", body).json()["matched"])
        resp = self._post("secret-token", body)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["matched"])

    def test_r5_bank_txn_id_qua_100_ky_tu_400(self):
        from apps.sales.models import PaymentTransaction
        for order_code in (self.order.code, "SO-KHONGCO"):
            with self.subTest(order_code=order_code):
                resp = self._post("secret-token", self.body(bank_txn_id="T" * 101,
                                                            order_code=order_code))
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "WEBHOOK_INVALID_INPUT")
                self.assertIn("bank_txn_id", resp.json()["detail"])
        self.assertFalse(PaymentTransaction.objects.exists())
        ok = self._post("secret-token", self.body(bank_txn_id="T" * 100))
        self.assertEqual(ok.status_code, 200, ok.content)
