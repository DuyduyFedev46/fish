"""
P3 (BR-TT-02, 03, 10, 14, 15): lõi ghi nhận giao dịch CỔNG SePay và chống ghi đôi.

Endpoint mới cho adapter — contract khớp `DJANGO_IPN_ENDPOINT_PATH` ở `adapter/app/main.py`
(P2, xem 03-dev-notes.md mục "P2 (adapter)"):
`POST /api/internal/payments/sepay-ipn/` — CÙNG shape body với webhook cũ
{bank_txn_id, order_code, amount, received_at, raw}, chỉ khác nguồn ghi = Source.GATEWAY
và có gắn môi trường (BR-TT-14). Adapter tự lọc IPN ORDER_PAID/CAPTURED/VND TRƯỚC khi gọi
endpoint này (Q9) — Django ở đây không cần biết notification_type.
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
from apps.sales.models import PaymentTransaction, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services

IPN_URL = "/api/internal/payments/sepay-ipn/"  # phải khớp DJANGO_IPN_ENDPOINT_PATH ở adapter (P2)


@override_settings(INTERNAL_SERVICE_TOKEN="secret-token", SEPAY_ENV="SANDBOX")
class SepayGatewayIpnBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        g = ItemGroup.objects.create(name="Cá")
        item = Item.objects.create(code="CA-GW", name="Cá", item_group=g)
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
            customer_phone="0912345678", customer_name="A", delivery_address="x",
            phone="0912345678", lines=[{"item_code": "CA-GW", "qty": Decimal("3")}],
        )  # tổng 540.000đ

    def _post(self, token, body):
        return self.client.post(IPN_URL, body, format="json", HTTP_X_INTERNAL_TOKEN=token)

    def _ipn(self, txn, amount, order_code=None, received_at=None):
        return self._post("secret-token", {
            "bank_txn_id": txn,
            "order_code": self.order.code if order_code is None else order_code,
            "amount": amount,
            "received_at": (received_at or timezone.now()).isoformat(),
        })


class P3AC1MatchedTests(SepayGatewayIpnBase):
    def test_p3_ac1_matched_source_gateway_invoice_processing_delivery(self):
        resp = self._ipn("SPG-1", "540000")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["matched"])

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.PROCESSING)

        payment = PaymentTransaction.objects.get(bank_txn_id="SPG-1")
        self.assertEqual(payment.source, PaymentTransaction.Source.GATEWAY)
        self.assertEqual(payment.match_status, PaymentTransaction.MatchStatus.MATCHED)

        invoice = SalesInvoice.objects.get(sales_order=self.order)
        self.assertEqual(invoice.payment_method, "VIETQR")
        self.assertEqual(invoice.delivery_notes.count(), 1)  # signal tạo phiếu giao PREPARING
        self.assertEqual(invoice.delivery_notes.first().status, "PREPARING")

    def test_p3_ac2_wrong_token_401(self):
        resp = self._post("wrong", {"bank_txn_id": "X", "order_code": self.order.code,
                                     "amount": "1000", "received_at": timezone.now().isoformat()})
        self.assertEqual(resp.status_code, 401)


class P3AC2OrphanTests(SepayGatewayIpnBase):
    def test_p3_ac2_ipn_after_auto_cancelled_is_orphan_no_restore(self):
        order_services.cancel_unpaid_expired(now=timezone.now())  # chưa hết hạn -> không huỷ gì
        self.order.booked_expires_at = timezone.now() - datetime.timedelta(minutes=1)
        self.order.save(update_fields=["booked_expires_at"])
        order_services.cancel_unpaid_expired()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.AUTO_CANCELLED)

        resp = self._ipn("SPG-ORPHAN", "540000")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["matched"])
        payment = PaymentTransaction.objects.get(bank_txn_id="SPG-ORPHAN")
        self.assertEqual(payment.match_status, PaymentTransaction.MatchStatus.ORPHAN)
        self.assertEqual(payment.resolution_status, PaymentTransaction.ResolutionStatus.OPEN)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.AUTO_CANCELLED)  # không khôi phục


class P3AC3UnderpaidTests(SepayGatewayIpnBase):
    def test_p3_ac3_underpaid_goes_to_queue(self):
        resp = self._ipn("SPG-UNDER", "500000")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["matched"])
        payment = PaymentTransaction.objects.get(bank_txn_id="SPG-UNDER")
        self.assertEqual(payment.match_status, PaymentTransaction.MatchStatus.UNDERPAID)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.BOOKED)


class P3AC4OverpaidSplitTests(SepayGatewayIpnBase):
    def test_p3_ac4_overpaid_split_into_separate_queue_row(self):
        resp = self._ipn("SPG-OVER", "600000")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["matched"])
        matched = PaymentTransaction.objects.get(bank_txn_id="SPG-OVER")
        self.assertEqual(matched.amount, Decimal("540000.00"))
        extra = PaymentTransaction.objects.get(bank_txn_id="SPG-OVER-THUA")
        self.assertEqual(extra.amount, Decimal("60000.00"))
        self.assertEqual(extra.match_status, PaymentTransaction.MatchStatus.OVERPAID)
        self.assertEqual(extra.resolution_status, PaymentTransaction.ResolutionStatus.OPEN)


class P3AC5SecondPaymentOverpaidTests(SepayGatewayIpnBase):
    def test_p3_ac5_second_gateway_payment_for_paid_order_is_overpaid(self):
        self._ipn("SPG-1ST", "540000")
        resp = self._ipn("SPG-2ND", "540000")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["matched"])
        second = PaymentTransaction.objects.get(bank_txn_id="SPG-2ND")
        self.assertEqual(second.match_status, PaymentTransaction.MatchStatus.OVERPAID)
        self.assertEqual(second.duplicate_warning, "")  # khoản đầu KHÔNG phải xác nhận tay
        self.assertEqual(SalesInvoice.objects.filter(sales_order=self.order).count(), 1)


class P3AC6ManualThenSameTxnTests(SepayGatewayIpnBase):
    def test_p3_ac6_ipn_same_ft_code_as_manual_confirm_is_idempotent(self):
        payment_services.confirm_payment_manual(
            order=self.order, bank_txn_id="FT999", actor=None,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.PROCESSING)
        self.assertEqual(PaymentTransaction.objects.filter(sales_order=self.order).count(), 1)

        resp = self._ipn("ft999", "540000")  # Q4: cùng mã FT (chuẩn hoá hoa/thường khác)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["matched"])
        # Không ghi dòng mới — vẫn đúng 1 giao dịch cho đơn này.
        self.assertEqual(PaymentTransaction.objects.filter(sales_order=self.order).count(), 1)
        txn = PaymentTransaction.objects.get(sales_order=self.order)
        self.assertEqual(txn.source, PaymentTransaction.Source.MANUAL)  # bản ghi CŨ, không đổi


class P3AC7ManualThenDifferentTxnDuplicateWarningTests(SepayGatewayIpnBase):
    def test_p3_ac7_ipn_without_ft_code_same_amount_flagged_duplicate(self):
        payment_services.confirm_payment_manual(
            order=self.order, bank_txn_id="FT888", actor=None,
        )
        resp = self._ipn("SPG-NOFT", "540000")  # mã cổng khác hẳn FT888, cùng số tiền
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["matched"])
        overpaid = PaymentTransaction.objects.get(bank_txn_id="SPG-NOFT")
        self.assertEqual(overpaid.match_status, PaymentTransaction.MatchStatus.OVERPAID)
        self.assertEqual(
            overpaid.duplicate_warning,
            "Nghi trùng xác nhận tay, đối chiếu sao kê trước khi hoàn",
        )
        # Đối chứng: hiện được qua API hàng chờ (Chủ xem) — không chỉ nằm trong DB.
        from apps.common.tests.fixtures import client_for, make_user

        chu = make_user("chu-p3ac7", "chu")
        resp2 = client_for(chu).get(f"/api/sales/payments/{overpaid.pk}/")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(
            resp2.json()["duplicate_warning"],
            "Nghi trùng xác nhận tay, đối chiếu sao kê trước khi hoàn",
        )

    def test_p3_ac7_khong_gan_nhan_neu_khoan_dau_khong_phai_manual(self):
        """Đối chứng P3-AC5: khoản đầu qua CỔNG (không phải MANUAL) -> không gắn nhãn nghi trùng."""
        self._ipn("SPG-A", "540000")
        resp = self._ipn("SPG-B", "540000")
        self.assertFalse(resp.json()["matched"])
        second = PaymentTransaction.objects.get(bank_txn_id="SPG-B")
        self.assertEqual(second.duplicate_warning, "")


class P3AC8EnvironmentTests(SepayGatewayIpnBase):
    def test_p3_ac8_environment_recorded_sandbox_and_filterable(self):
        self._ipn("SPG-ENV1", "540000")
        payment = PaymentTransaction.objects.get(bank_txn_id="SPG-ENV1")
        self.assertEqual(payment.environment, "SANDBOX")

    @override_settings(SEPAY_ENV="PRODUCTION")
    def test_p3_ac8_environment_recorded_production(self):
        self._ipn("SPG-ENV2", "540000")
        payment = PaymentTransaction.objects.get(bank_txn_id="SPG-ENV2")
        self.assertEqual(payment.environment, "PRODUCTION")

    def test_p3_ac8_manual_confirm_has_no_environment(self):
        payment, _ = payment_services.confirm_payment_manual(
            order=self.order, bank_txn_id="FT-ENV", actor=None,
        )
        self.assertEqual(payment.environment, "")


class P3AC9MigrationBackfillTests(TestCase):
    def test_p3_ac9_old_source_choices_unaffected(self):
        """Migration chỉ THÊM field/choice — dữ liệu cũ (WEBHOOK/MANUAL) giữ nguyên nguồn."""
        order = order_services.create_order(
            customer_phone="0900000099", customer_name="Z", delivery_address="x",
            phone="0900000099",
            lines=[{"item_code": self._make_item().code, "qty": Decimal("1")}],
        )
        payment_services.confirm_payment(
            order=order, bank_txn_id="OLD-1", amount=order.total_amount,
            received_at=timezone.now(), source=PaymentTransaction.Source.WEBHOOK,
        )
        p = PaymentTransaction.objects.get(bank_txn_id="OLD-1")
        self.assertEqual(p.source, PaymentTransaction.Source.WEBHOOK)
        self.assertEqual(p.environment, "")
        self.assertEqual(p.duplicate_warning, "")

    def _make_item(self):
        g = ItemGroup.objects.create(name="Cá cũ")
        item = Item.objects.create(code="CA-OLD", name="Cá", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ cũ", is_default=True)
        ItemPrice.objects.create(
            price_list=pl, item=item, rate=Decimal("100000"),
            valid_from=timezone.localdate() - datetime.timedelta(days=1),
        )
        b = batch_services.create_batch(
            item=item, supplier=Supplier.objects.create(name="B"),
            warehouse=Warehouse.objects.create(name="Kho cũ"),
            received_date=timezone.localdate(), qty=Decimal("10"), purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=b, actor=None)
        return item
