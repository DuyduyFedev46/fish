"""
SHOP-3b-04 — áp mã khi tạo đơn: giữ lượt, đóng băng, phân bổ vào dòng, không cộng dồn, dùng khi IPN khớp, nhả khi tự huỷ
(BR-DM-18…21, BR-BH-15, 27). Dữ liệu giả (tên, SĐT, địa chỉ).
"""
import datetime
import json
import logging
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.catalog.models import PricingRule
from apps.catalog.vouchers.tests.base import make_voucher
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import make_user
from apps.inventory.models import Batch
from apps.sales.models import SalesInvoice, SalesOrder, SalesOrderLine, SalesOrderLineBatch, VoucherRedemption
from apps.sales.orders import services
from apps.sales.payments import services as payment_services

from .test_shop_create import FAKE_ADDRESS, FAKE_NAME, FAKE_PHONE, ShopCreateBase

D = Decimal
State = VoucherRedemption.State


class VoucherOrderBase(ShopCreateBase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.a = self._item("MUC-A", price="150000")   # 2 kg = 300.000
        self.b = self._item("MUC-B", price="128000")   # 2 kg = 256.000
        self.batch_a = self._stocked_batch(self.a, "40")
        self.batch_b = self._stocked_batch(self.b, "40")
        self.owner = make_user("chu_voucher", roles.OWNER)
        self.voucher = make_voucher(owner=self.owner)
        self.cart = [("MUC-A", "2"), ("MUC-B", "2")]  # 556.000

    def order_with(self, code="CAVE10", cart=None, **extra):
        extra = {"voucher_code": code, **extra} if code is not None else extra
        return self.post(cart or self.cart, **extra)

    def redemption(self, order_code):
        return VoucherRedemption.objects.get(order__code=order_code)

    def pay(self, order, txn="TXV1"):
        order.refresh_from_db()
        return payment_services.confirm_payment(
            order=order, bank_txn_id=txn, amount=order.total_amount, received_at=timezone.now(),
        )


class ApplyTests(VoucherOrderBase):
    def test_s3b_04_ac1_discount_is_frozen_and_allocated_to_lines(self):
        response = self.order_with()
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual((data["subtotal"], data["total_amount"]), ("556000", "506000"))
        self.assertEqual(data["discount"], {"source": "voucher", "code": "CAVE10", "amount": "50000"})
        self.assertEqual([l["amount"] for l in data["lines"]], ["300000", "256000"])  # gộp, chưa trừ
        order = SalesOrder.objects.get(code=data["order_code"])
        lines = list(order.lines.order_by("pk"))
        self.assertEqual([l.discount_amount for l in lines], [D("26978"), D("23022")])
        self.assertEqual([l.amount for l in lines], [D("273022"), D("232978")])
        self.assertTrue(all(l.pricing_rule_id is None for l in lines))
        self.assertEqual(sum(l.discount_amount for l in lines), D("50000"))
        self.assertEqual(order.total_amount, sum(l.amount for l in lines))  # tổng đơn = tổng dòng sau phân bổ
        r = self.redemption(order.code)
        self.assertEqual((r.state, r.code, r.discount_amount, r.voucher_id), (State.HELD, "CAVE10", D("50000"), self.voucher.pk))

    def test_code_is_normalized(self):
        self.assertEqual(self.order_with("cave 10").json()["discount"]["code"], "CAVE10")

    def test_empty_or_missing_code_means_no_voucher(self):
        for body in ({"voucher_code": ""}, {"voucher_code": None}, {}):
            with self.subTest(body=body):
                data = self.post(self.cart, **body).json()
                self.assertEqual(data["discount"], {"source": None, "code": None, "amount": "0"})
        self.assertEqual(VoucherRedemption.objects.count(), 0)

    def test_non_string_code_is_validation(self):
        response = self.order_with(12345)
        self.assertEqual((response.status_code, response.json()["code"]), (400, "VALIDATION"))
        self.assertIn("voucher_code", response.json()["fields"])

    def test_s3b_04_ac8_without_code_pricing_rule_works_as_before(self):
        PricingRule.objects.create(name="Giảm 20k", apply_on="ORDER", min_amount=D("100000"), discount_type="AMOUNT",
                                   discount_value=D("20000"))
        data = self.post(self.cart).json()
        self.assertEqual(data["discount"], {"source": "promo", "code": None, "amount": "20000"})
        order = SalesOrder.objects.get(code=data["order_code"])
        self.assertTrue(all(l.pricing_rule_id for l in order.lines.all()))
        self.assertFalse(VoucherRedemption.objects.exists())

    def test_whole_vnd_allocation_for_three_lines(self):
        c = self._item("MUC-C", price="33333")
        self._stocked_batch(c, "40")
        make_voucher(code="BAMON111", kind="AMOUNT", value=D("10001"), max_discount=None, min_order_amount=D("0"))
        data = self.order_with("BAMON111", cart=[("MUC-A", "1"), ("MUC-B", "1"), ("MUC-C", "1")]).json()
        order = SalesOrder.objects.get(code=data["order_code"])
        discounts = [l.discount_amount for l in order.lines.order_by("pk")]
        self.assertTrue(all(d == d.to_integral_value() for d in discounts))
        self.assertEqual(sum(discounts), D("10001"))
        self.assertEqual(order.total_amount, D("311333") - D("10001"))
        self.assertEqual(order.total_amount, sum(l.amount for l in order.lines.all()))

    def test_amount_voucher_cap_and_total_positive(self):
        make_voucher(code="TIEN400K", kind="AMOUNT", value=D("400000"), max_discount=None, min_order_amount=D("0"))
        data = self.order_with("TIEN400K", cart=[("MUC-A", "4")]).json()  # 600.000 -> giảm tối đa 300.000
        self.assertEqual((data["discount"]["amount"], data["total_amount"]), ("300000", "300000"))

    def test_stock_cost_snapshot_unchanged_by_voucher(self):
        with_code = self.order_with().json()["order_code"]
        without = self.post(self.cart).json()["order_code"]
        def costs(code):
            return list(SalesOrderLineBatch.objects.filter(order_line__order__code=code)
                        .order_by("order_line__pk", "pk").values_list("qty", "unit_cost"))
        self.assertEqual(costs(with_code), costs(without))
        self.assertTrue(all(unit_cost > 0 for _qty, unit_cost in costs(with_code)))


class NoStackingTests(VoucherOrderBase):
    def add_rule(self, amount):
        PricingRule.objects.create(name=f"Giảm {amount}", apply_on="ORDER", min_amount=D("100000"),
                                   discount_type="AMOUNT", discount_value=D(amount))

    def snapshot_counts(self):
        return {"orders": SalesOrder.objects.count(), "redemptions": VoucherRedemption.objects.count(),
                "reserved": [str(q) for q in Batch.objects.order_by("pk").values_list("qty_reserved", flat=True)]}

    def test_voucher_better_than_promo_replaces_it_not_adds(self):
        self.add_rule("20000")
        data = self.order_with().json()
        self.assertEqual((data["discount"]["source"], data["discount"]["amount"], data["total_amount"]),
                         ("voucher", "50000", "506000"))  # không phải 556000 − 70000
        order = SalesOrder.objects.get(code=data["order_code"])
        self.assertTrue(all(l.pricing_rule_id is None for l in order.lines.all()))

    def test_s3b_03_ac5_better_promo_rejects_voucher_without_consuming_a_use(self):
        self.add_rule("60000")
        before = self.snapshot_counts()
        response = self.order_with()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"code": "VOUCHER_INVALID", "detail": "Mã giảm giá không còn dùng được.",
                                           "reason_code": "BETTER_PROMO"})
        self.assertEqual(self.snapshot_counts(), before)
        retry = self.post(self.cart).json()  # đặt tiếp không dùng mã: ưu đãi tự động áp
        self.assertEqual((retry["discount"]["source"], retry["discount"]["amount"]), ("promo", "60000"))

    def test_tie_keeps_the_automatic_promo_and_counts_no_use(self):
        self.add_rule("50000")
        response = self.order_with()
        self.assertEqual((response.status_code, response.json()["reason_code"]), (400, "BETTER_PROMO"))
        self.assertEqual(VoucherRedemption.objects.count(), 0)
        self.assertEqual(SalesOrder.objects.count(), 0)


class InvalidAtOrderTests(VoucherOrderBase):
    def assert_nothing_held(self, response, reason, **extra):
        self.assertEqual(response.status_code, 400, response.content)
        body = response.json()
        self.assertEqual((body["code"], body["reason_code"]), ("VOUCHER_INVALID", reason))
        for key, value in extra.items():
            self.assertEqual(body[key], value)
        self.assertEqual(SalesOrder.objects.count(), 0)
        self.assertEqual(SalesOrderLine.objects.count(), 0)
        self.assertEqual(SalesOrderLineBatch.objects.count(), 0)
        self.assertEqual(VoucherRedemption.objects.count(), 0)
        self.assertTrue(all(q == 0 for q in Batch.objects.values_list("qty_reserved", flat=True)))

    def test_unknown_code(self):
        self.assert_nothing_held(self.order_with("KHONGCO1"), "INVALID")

    def test_s3b_04_ac3_disabled_between_check_and_order(self):
        self.assertTrue(self.order_with().status_code == 201)
        self.voucher.is_active = False
        self.voucher.save()
        VoucherRedemption.objects.all().delete()
        SalesOrder.objects.all().update(status="CANCELLED")
        before_reserved = [str(q) for q in Batch.objects.order_by("pk").values_list("qty_reserved", flat=True)]
        response = self.order_with()
        self.assertEqual((response.status_code, response.json()["reason_code"]), (400, "INVALID"))
        self.assertEqual([str(q) for q in Batch.objects.order_by("pk").values_list("qty_reserved", flat=True)], before_reserved)
        self.assertEqual(VoucherRedemption.objects.count(), 0)

    def test_expired_and_not_started(self):
        make_voucher(code="HETHAN01", starts_at=timezone.now() - datetime.timedelta(days=9),
                     ends_at=timezone.now() - datetime.timedelta(minutes=1))
        make_voucher(code="SAUNAY01", starts_at=timezone.now() + datetime.timedelta(hours=1))
        self.assert_nothing_held(self.order_with("HETHAN01"), "EXPIRED")
        self.assert_nothing_held(self.order_with("SAUNAY01"), "INVALID")

    def test_min_order_has_missing_amount_only_here(self):
        response = self.order_with(cart=[("MUC-B", "2")])
        self.assert_nothing_held(response, "MIN_ORDER", missing_amount="44000")
        used_up = make_voucher(code="HETLUOT1", total_uses=1)
        VoucherRedemption.objects.create(order=self._existing_order(), voucher=used_up, code="HETLUOT1",
                                         discount_amount=D("1000"), state=State.USED)
        body = self.order_with("HETLUOT1").json()
        self.assertEqual(body["reason_code"], "USED_UP")
        self.assertNotIn("missing_amount", body)

    def _existing_order(self):
        from apps.catalog.vouchers.tests.test_api import make_order

        return make_order("0900000999")

    def test_voucher_invalid_comes_before_out_of_stock(self):
        response = self.order_with("KHONGCO1", cart=[("MUC-A", "500")])  # vừa mã sai vừa hết hàng
        self.assertEqual(response.json()["code"], "VOUCHER_INVALID")

    def test_out_of_stock_with_valid_voucher_holds_nothing(self):
        response = self.order_with(cart=[("MUC-A", "500"), ("MUC-B", "2")])
        self.assertEqual(response.json()["code"], "OUT_OF_STOCK")
        self.assertEqual(VoucherRedemption.objects.count(), 0)
        self.assertEqual(SalesOrder.objects.count(), 0)

    def test_losing_the_stock_race_after_the_hold_rolls_the_hold_back(self):
        def lost(*args, **kwargs):
            raise BusinessError("Không đủ hàng.", code="BR-BH-02")

        with mock.patch("apps.sales.orders.services.batches.allocate_fefo", side_effect=lost):
            response = self.order_with()
        self.assertEqual(response.json()["code"], "OUT_OF_STOCK")
        self.assertEqual(VoucherRedemption.objects.count(), 0)
        self.assertEqual(SalesOrder.objects.count(), 0)

    def test_used_up_after_last_use_is_held_and_released_use_is_reusable(self):
        make_voucher(code="MOTLUOT1", total_uses=1, min_order_amount=D("0"))
        first = self.order_with("MOTLUOT1")
        self.assertEqual(first.status_code, 201)
        self.assert_used_up_for_second()
        SalesOrder.objects.filter(code=first.json()["order_code"]).update(
            booked_expires_at=timezone.now() - datetime.timedelta(minutes=1))
        services.cancel_unpaid_expired()
        self.assertEqual(self.order_with("MOTLUOT1", client_request_id="6f1c2a7e-3b4d-4c5e-9f00-1a2b3c4d5e6f").status_code, 201)

    def assert_used_up_for_second(self):
        second = self.order_with("MOTLUOT1")
        self.assertEqual((second.status_code, second.json()["reason_code"]), (400, "USED_UP"))
        self.assertEqual(SalesOrder.objects.count(), 1)

    def test_resend_same_request_id_returns_old_order_and_holds_no_more(self):
        make_voucher(code="MOTLUOT1", total_uses=1, min_order_amount=D("0"))
        rid = "6f1c2a7e-3b4d-4c5e-9f00-1a2b3c4d5e6f"
        first = self.order_with("MOTLUOT1", client_request_id=rid)
        reserved = [str(q) for q in Batch.objects.order_by("pk").values_list("qty_reserved", flat=True)]
        again = self.order_with("MOTLUOT1", client_request_id=rid)
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(first.json()["order_code"], again.json()["order_code"])
        self.assertEqual(VoucherRedemption.objects.count(), 1)
        self.assertEqual([str(q) for q in Batch.objects.order_by("pk").values_list("qty_reserved", flat=True)], reserved)

    def test_error_body_has_no_counts_or_personal_data(self):
        make_voucher(code="HETLUOT1", total_uses=1)
        VoucherRedemption.objects.create(order=self._existing_order(), voucher=Voucher_get("HETLUOT1"), code="HETLUOT1",
                                         discount_amount=D("1000"), state=State.HELD)
        raw = self.order_with("HETLUOT1").content.decode()
        for hidden in (FAKE_PHONE, FAKE_NAME, "Đường Thử", "total_uses", "used", "remaining", "0900000999"):
            self.assertNotIn(hidden, raw)


def Voucher_get(code):
    from apps.catalog.models import Voucher

    return Voucher.objects.get(code=code)


class LifecycleTests(VoucherOrderBase):
    def create(self):
        return SalesOrder.objects.get(code=self.order_with().json()["order_code"])

    def test_s3b_04_ac5_matched_payment_marks_used_in_the_invoice_transaction(self):
        order = self.create()
        self.pay(order)
        r = self.redemption(order.code)
        self.assertEqual(r.state, State.USED)
        self.assertIsNotNone(r.used_at)
        invoice = SalesInvoice.objects.get(sales_order=order)
        self.assertEqual(invoice.amount, D("506000"))
        self.assertEqual(sum(l.amount for l in invoice.lines.all()), D("506000"))  # doanh thu ghi theo tiền thực thu

    def test_underpaid_payment_does_not_mark_used(self):
        order = self.create()
        payment_services.confirm_payment(order=order, bank_txn_id="TXLOW", amount=D("100"), received_at=timezone.now())
        self.assertEqual(self.redemption(order.code).state, State.HELD)

    def test_manual_confirmation_via_underpaid_totals_also_marks_used(self):
        order = self.create()
        first = payment_services.confirm_payment(order=order, bank_txn_id="TXP1", amount=D("300000"), received_at=timezone.now())
        payment_services.confirm_payment(order=order, bank_txn_id="TXP2", amount=D("206000"), received_at=timezone.now())
        payment_services.resolve_payment(payment=first, action="CONFIRM_ORDER", actor=self.owner)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        self.assertEqual(self.redemption(order.code).state, State.USED)

    def test_payment_is_idempotent_for_the_redemption(self):
        order = self.create()
        self.pay(order)
        used_at = self.redemption(order.code).used_at
        self.pay(order)  # cùng mã giao dịch
        self.assertEqual(self.redemption(order.code).used_at, used_at)

    def test_s3b_04_ac6_expiry_job_releases_once_and_is_idempotent(self):
        order = self.create()
        SalesOrder.objects.filter(pk=order.pk).update(booked_expires_at=timezone.now() - datetime.timedelta(minutes=1))
        self.assertEqual(services.cancel_unpaid_expired(), 1)
        r = self.redemption(order.code)
        self.assertEqual(r.state, State.RELEASED)
        released_at = r.released_at
        self.assertIsNotNone(released_at)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.AUTO_CANCELLED)
        self.assertEqual(services.cancel_unpaid_expired(), 0)
        r.refresh_from_db()
        self.assertEqual((r.state, r.released_at), (State.RELEASED, released_at))
        self.assertTrue(all(q == 0 for q in Batch.objects.values_list("qty_reserved", flat=True)))

    def test_expiry_job_does_not_touch_other_orders_redemptions(self):
        keep = self.create()
        gone = SalesOrder.objects.get(code=self.order_with().json()["order_code"])
        SalesOrder.objects.filter(pk=gone.pk).update(booked_expires_at=timezone.now() - datetime.timedelta(minutes=1))
        services.cancel_unpaid_expired()
        self.assertEqual(self.redemption(keep.code).state, State.HELD)
        self.assertEqual(self.redemption(gone.code).state, State.RELEASED)

    def test_late_payment_after_auto_cancel_keeps_the_use_released(self):
        order = self.create()
        SalesOrder.objects.filter(pk=order.pk).update(booked_expires_at=timezone.now() - datetime.timedelta(minutes=1))
        services.cancel_unpaid_expired()
        self.pay(order, txn="TXLATE")
        self.assertEqual(self.redemption(order.code).state, State.RELEASED)

    def test_s3b_04_ac7_cancelling_a_paid_order_does_not_give_the_use_back(self):
        order = self.create()
        self.pay(order)
        order.refresh_from_db()
        services.cancel_paid_order(order=order, actor=self.owner, reason_code="CUSTOMER_CHANGED_MIND")
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(self.redemption(order.code).state, State.USED)
        make_voucher(code="DUNGLAI1", total_uses=1, min_order_amount=D("0"))
        used = self.order_with("DUNGLAI1")
        self.pay(SalesOrder.objects.get(code=used.json()["order_code"]), txn="TXV2")
        services.cancel_paid_order(order=SalesOrder.objects.get(code=used.json()["order_code"]), actor=self.owner,
                                   reason_code="CUSTOMER_CHANGED_MIND")
        self.assertEqual(self.order_with("DUNGLAI1").json()["reason_code"], "USED_UP")

    def test_lookup_shows_the_voucher_discount_in_every_state(self):
        order = self.create()
        client = APIClient()
        body = {"order_code": order.code, "phone": FAKE_PHONE}
        expected = {"source": "voucher", "code": "CAVE10", "amount": "50000"}
        self.assertEqual(client.post("/api/shop/orders/lookup/", body, format="json").json()["discount"], expected)
        SalesOrder.objects.filter(pk=order.pk).update(booked_expires_at=timezone.now() - datetime.timedelta(minutes=1))
        services.cancel_unpaid_expired()  # lượt đã nhả nhưng giá đóng băng của đơn vẫn là giá mã
        self.assertEqual(client.post("/api/shop/orders/lookup/", body, format="json").json()["discount"], expected)

    def test_redemption_exposes_no_personal_fields(self):
        names = {f.name for f in VoucherRedemption._meta.get_fields()}
        self.assertEqual(names, {"id", "order", "voucher", "code", "discount_amount", "state", "held_at", "used_at",
                                 "released_at"})


class PrivacyTests(VoucherOrderBase):
    def test_create_with_voucher_does_not_leak_or_log_personal_data(self):
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
            response = self.order_with()
            self.order_with("KHONGCO1")
        finally:
            root.removeHandler(capture)
            root.setLevel(previous)
        for text in ("\n".join(capture.lines), response.content.decode()):
            for pii in (FAKE_PHONE, FAKE_PHONE[1:], FAKE_NAME, "Đường Thử", "Phường Mẫu", "request.data"):
                self.assertNotIn(pii, text)
        for hidden in ("unit_cost", "purchase_rate", "landed", "batch"):
            self.assertNotIn(hidden, response.content.decode())

    def test_no_audit_is_written_for_shop_orders_with_personal_data(self):
        self.order_with()
        self.assertFalse(AuditLog.objects.filter(action__in=["create_voucher"]).exists())
