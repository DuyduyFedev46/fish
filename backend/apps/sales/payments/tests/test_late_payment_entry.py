"""
#15 (02d) / BR-TT-18 — Chủ ghi tay khoản tiền về muộn ở Hàng chờ thanh toán (LP-AC1 … LP-AC16).

`POST /api/sales/payments/record-late/`: tạo PaymentTransaction source=MANUAL, ORPHAN (đơn Đã huỷ/Tự huỷ)
hoặc UNMATCHED (không đơn). Không đổi đơn, kho, hoá đơn. Dữ liệu giả (SĐT 09000003xx).
"""
import json
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.db import IntegrityError
from django.test import override_settings
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, StockLedgerEntry
from apps.sales.models import PaymentTransaction, Refund, SalesInvoice, SalesOrder
from apps.sales.orders.tests.test_s10_api import SENSITIVE_KEYS, OrderApiBase, find_keys
from apps.sales.payments import services as payment_services
from apps.sales.payments.auto_confirm import process_exact_payment_matches
from apps.sales.payments.timeline import build_payment_timeline

URL = "/api/sales/payments/record-late/"
WEBHOOK_URL = "/api/internal/payments/sepay-webhook/"
IPN_URL = "/api/internal/payments/sepay-ipn/"
MARK = "GHI-CHU-TU-DO-XYZ"
FAKE_PHONE = "0900000321"


class LateBase(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.owner = self.chu  # naming: allow - tên thuộc tính của OrderApiBase dùng chung
        self.order = self._order(phone="0900000301")  # BOOKED 540.000đ
        self.dead = self._order(phone="0900000302")
        SalesOrder.objects.filter(pk=self.dead.pk).update(status=SalesOrder.Status.AUTO_CANCELLED)
        self.dead.refresh_from_db()

    def body(self, **kw):
        base = {
            "bank_txn_id": "FT26100300001", "amount": "350000",
            "received_at": (timezone.now() - timedelta(hours=2)).isoformat(),
            "order_code": self.dead.code,
        }
        base.update(kw)
        return {k: v for k, v in base.items() if v is not None}

    def post(self, user=None, **kw):
        return client_for(user or self.owner).post(URL, self.body(**kw), format="json")

    @override_settings(INTERNAL_SERVICE_TOKEN="tok")
    def webhook(self, txn, amount, order_code="", url=WEBHOOK_URL):
        resp = client_for(None).post(
            url,
            {"bank_txn_id": txn, "order_code": order_code, "amount": amount,
             "received_at": timezone.now().isoformat()},
            format="json", HTTP_X_INTERNAL_TOKEN="tok",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp


class LateHappyPathTests(LateBase):
    def test_lp_ac1_auto_cancelled_order_becomes_orphan_and_order_untouched(self):
        invoices = SalesInvoice.objects.count()
        ledger = StockLedgerEntry.objects.count()
        reserved = {b.pk: b.qty_reserved for b in Batch.objects.all()}
        resp = self.post(bank_txn_id=" ft 2610 0300001 ", order_code=self.dead.code.lower())
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertFalse(body["duplicate"])
        pay = PaymentTransaction.objects.get(bank_txn_id="FT26100300001")
        self.assertEqual(pay.source, PaymentTransaction.Source.MANUAL)
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.ORPHAN)
        self.assertEqual(pay.resolution_status, PaymentTransaction.ResolutionStatus.OPEN)
        self.assertEqual(pay.sales_order_id, self.dead.pk)
        self.assertEqual(pay.environment, "")
        self.assertEqual(pay.amount, Decimal("350000"))
        self.assertEqual(pay.raw_payload, {})
        self.assertEqual(body["payment"]["id"], pay.pk)
        self.assertEqual(body["payment"]["available_actions"], ["refund"])
        self.dead.refresh_from_db()
        self.assertEqual(self.dead.status, SalesOrder.Status.AUTO_CANCELLED)
        self.assertEqual(SalesInvoice.objects.count(), invoices)
        self.assertEqual(StockLedgerEntry.objects.count(), ledger)
        self.assertEqual({b.pk: b.qty_reserved for b in Batch.objects.all()}, reserved)
        self.assertFalse(AuditLog.objects.filter(model_name=SalesOrder._meta.label, object_id=str(self.dead.pk)).exists())
        audit = AuditLog.objects.get(action="record_late_payment")
        self.assertEqual(audit.actor, self.owner)
        self.assertEqual(audit.model_name, PaymentTransaction._meta.label)
        self.assertEqual(audit.object_id, str(pay.pk))
        self.assertEqual(audit.note, "")

    def test_lp_ac2_cancelled_order_becomes_orphan(self):
        SalesOrder.objects.filter(pk=self.dead.pk).update(status=SalesOrder.Status.CANCELLED)
        resp = self.post()
        self.assertEqual(resp.status_code, 201, resp.content)
        pay = PaymentTransaction.objects.get(bank_txn_id="FT26100300001")
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.ORPHAN)
        self.dead.refresh_from_db()
        self.assertEqual(self.dead.status, SalesOrder.Status.CANCELLED)

    def test_lp_ac3_no_order_becomes_unmatched_and_auto_confirm_skips_it(self):
        for blank in ("", None):
            PaymentTransaction.objects.all().delete()
            resp = client_for(self.owner).post(URL, {
                "bank_txn_id": "FT26100300009", "amount": "540000", "order_code": blank,
                "received_at": timezone.now().isoformat(),
            }, format="json")
            self.assertEqual(resp.status_code, 201, resp.content)
            pay = PaymentTransaction.objects.get()
            self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.UNMATCHED)
            self.assertIsNone(pay.sales_order_id)
            self.assertEqual(pay.source, PaymentTransaction.Source.MANUAL)
            self.assertEqual(resp.json()["payment"]["available_actions"], ["attach_to_order", "refund"])
        before = PaymentTransaction.objects.values_list("pk", "match_status", "resolution_status", "duplicate_warning")
        before = list(before)
        process_exact_payment_matches()
        self.assertEqual(
            list(PaymentTransaction.objects.values_list("pk", "match_status", "resolution_status", "duplicate_warning")),
            before,
        )

    def test_lp_ac3_auto_confirm_query_excludes_manual(self):
        import inspect
        from apps.sales.payments import auto_confirm
        self.assertIn("exclude(source=PaymentTransaction.Source.MANUAL)", inspect.getsource(auto_confirm))

    def test_lp_ac4_resend_same_returns_200_duplicate_one_row_one_audit(self):
        self.assertEqual(self.post().status_code, 201)
        resp = self.post(bank_txn_id="ft26100300001")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["duplicate"])
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="record_late_payment").count(), 1)

    def test_lp_ac4_resend_same_without_order(self):
        self.assertEqual(self.post(order_code=None).status_code, 201)
        resp = self.post(order_code="")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["duplicate"])
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_amount_is_rounded_to_dong_precision(self):
        resp = self.post(amount="350000.004")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(PaymentTransaction.objects.get().amount, Decimal("350000.00"))

    def test_paid_total_unchanged_after_orphan(self):
        self.post()
        self.assertEqual(payment_services.order_paid_total(self.dead), Decimal("0"))


class LateRejectTests(LateBase):
    def test_lp_ac5_txn_exists_from_webhook_400_br_tt_03(self):
        self.webhook("FT26100300001", "350000")  # webhook không đơn: UNMATCHED
        existing = PaymentTransaction.objects.get()
        resp = self.post()
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "BR-TT-03")
        self.assertEqual(body["existing_payment_id"], existing.pk)
        self.assertIn("bank_txn_id", body)
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_lp_ac5_same_txn_other_order_or_other_amount_400(self):
        self.assertEqual(self.post().status_code, 201)
        other = self._order(phone="0900000303")
        SalesOrder.objects.filter(pk=other.pk).update(status=SalesOrder.Status.CANCELLED)
        for kw in ({"order_code": other.code}, {"amount": "360000"}, {"order_code": ""}):
            with self.subTest(kw=kw):
                resp = self.post(**kw)
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "BR-TT-03")
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_lp_ac5_concurrent_integrity_error_returns_400(self):
        with mock.patch.object(PaymentTransaction.objects, "create", side_effect=IntegrityError("unique")):
            resp = self.post()
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-TT-03")
        self.assertFalse(AuditLog.objects.filter(action="record_late_payment").exists())

    def test_lp_ac5_concurrent_integrity_error_no_order(self):
        with mock.patch.object(PaymentTransaction.objects, "get_or_create", side_effect=IntegrityError("unique")):
            resp = self.post(order_code="")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-TT-03")

    def test_lp_ac6_bad_amount_400_with_field_key(self):
        for bad in ("0", "-1", "abc", "", "0.004", "1000000000000"):
            with self.subTest(amount=bad):
                resp = self.post(amount=bad)
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "BR-TT-18")
                self.assertIn("amount", resp.json())
        resp = client_for(self.owner).post(URL, {k: v for k, v in self.body().items() if k != "amount"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-TT-18")
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_lp_ac7_bad_txn_id_400(self):
        for bad in ("", "   ", "F" * 101, "FT 123 ghi chú", "FT123é", "FT123;DROP", "Nguyễn Văn Giả"):
            with self.subTest(txn=bad):
                resp = self.post(bank_txn_id=bad)
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "BR-TT-18")
                self.assertIn("bank_txn_id", resp.json())
        for good in ("FT.26_10-03/1",):
            PaymentTransaction.objects.all().delete()
            self.assertEqual(self.post(bank_txn_id=good, order_code="").status_code, 201)
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_lp_ac8_bad_received_at_400(self):
        future = (timezone.now() + timedelta(minutes=30)).isoformat()
        for bad in ("", "hôm qua", "2026-13-45T00:00:00", future):
            with self.subTest(received_at=bad):
                resp = self.post(received_at=bad)
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "BR-TT-18")
                self.assertIn("received_at", resp.json())
        resp = client_for(self.owner).post(URL, {k: v for k, v in self.body().items() if k != "received_at"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_tl15_l2_date_only_received_at_is_400_with_time_hint(self):
        """TL15-L2: chỉ có ngày (thành 00:00 ngầm) bị từ chối, bắt buộc có phần giờ."""
        for bad in ("2026-10-06", " 2026-10-06 ", timezone.localdate().isoformat()):
            with self.subTest(received_at=bad):
                resp = self.post(received_at=bad)
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "BR-TT-18")
                self.assertIn("received_at", resp.json())
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_tl15_l2_older_than_max_age_is_400_but_yesterday_is_ok(self):
        """TL15-L2: cũ hơn LATE_PAYMENT_MAX_AGE_DAYS (mặc định 400) thì 400; hôm qua thì 201; đúng ngưỡng vẫn nhận."""
        resp = self.post(received_at=(timezone.now() - timedelta(days=401)).isoformat())
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-TT-18")
        self.assertIn("received_at", resp.json())
        self.assertFalse(PaymentTransaction.objects.exists())
        resp = self.post(received_at=(timezone.now() - timedelta(days=399)).isoformat())
        self.assertEqual(resp.status_code, 201, resp.content)
        PaymentTransaction.objects.all().delete()
        resp = self.post(received_at=(timezone.now() - timedelta(days=1)).isoformat(), bank_txn_id="FT26100300002")
        self.assertEqual(resp.status_code, 201, resp.content)

    @override_settings(LATE_PAYMENT_MAX_AGE_DAYS=10)
    def test_tl15_l2_max_age_is_a_setting(self):
        self.assertEqual(self.post(received_at=(timezone.now() - timedelta(days=11)).isoformat()).status_code, 400)
        self.assertEqual(self.post(received_at=(timezone.now() - timedelta(days=9)).isoformat()).status_code, 201)

    def test_tl15_l2_naive_datetime_with_time_still_accepted(self):
        naive = timezone.localtime(timezone.now() - timedelta(hours=3)).replace(tzinfo=None).isoformat(timespec="seconds")
        self.assertEqual(self.post(received_at=naive).status_code, 201)

    def test_lp_ac8_within_five_minutes_future_accepted(self):
        resp = self.post(received_at=(timezone.now() + timedelta(minutes=3)).isoformat())
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_lp_ac9_unknown_order_400_not_silently_unmatched(self):
        resp = self.post(order_code="SO-KHONG-CO")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "LATE_PAYMENT_ORDER_NOT_FOUND")
        self.assertIn("order_code", resp.json())
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_lp_ac10_booked_order_400_with_order_id(self):
        resp = self.post(order_code=self.order.code)
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "LATE_PAYMENT_ORDER_BOOKED")
        self.assertEqual(body["order_id"], self.order.pk)
        self.assertIn("order_code", body)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.BOOKED)
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_lp_ac10_paid_orders_400(self):
        for status in (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING, SalesOrder.Status.COMPLETED):
            SalesOrder.objects.filter(pk=self.order.pk).update(status=status)
            with self.subTest(status=status):
                resp = self.post(order_code=self.order.code)
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "LATE_PAYMENT_ORDER_PAID")
                self.assertIn("để trống mã đơn", resp.json()["detail"])
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_orphan_cannot_confirm_order(self):
        self.post()
        pay = PaymentTransaction.objects.get()
        resp = client_for(self.owner).post(
            f"/api/sales/payments/{pay.pk}/resolve", {"action": "CONFIRM_ORDER", "order_id": self.dead.pk}, format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.dead.refresh_from_db()
        self.assertEqual(self.dead.status, SalesOrder.Status.AUTO_CANCELLED)


class LateDuplicateTests(LateBase):
    def test_lp_ac11_same_amount_on_order_409_then_ack_sets_warning(self):
        self.webhook("FT-OTHER-1", "350000", order_code=self.dead.code)  # ORPHAN từ webhook, cùng tiền
        resp = self.post()
        self.assertEqual(resp.status_code, 409, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "LATE_PAYMENT_POSSIBLE_DUPLICATE")
        similar = PaymentTransaction.objects.get(bank_txn_id="FT-OTHER-1")
        self.assertEqual(body["similar_payment_id"], similar.pk)
        self.assertEqual(body["similar_bank_txn_id"], "FT-OTHER-1")
        self.assertIn("similar_received_at", body)
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        resp = self.post(acknowledge_possible_duplicate=True)
        self.assertEqual(resp.status_code, 201, resp.content)
        pay = PaymentTransaction.objects.get(bank_txn_id="FT26100300001")
        self.assertEqual(pay.duplicate_warning, payment_services.DUPLICATE_LATE_MANUAL_WARNING)
        self.assertEqual(resp.json()["payment"]["duplicate_warning"], payment_services.DUPLICATE_LATE_MANUAL_WARNING)
        audit = AuditLog.objects.get(action="record_late_payment")
        self.assertTrue(audit.changes["acknowledged_duplicate"])

    def test_lp_ac11_different_amount_on_order_no_conflict(self):
        self.webhook("FT-OTHER-2", "100000", order_code=self.dead.code)
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(PaymentTransaction.objects.get(bank_txn_id="FT26100300001").duplicate_warning, "")

    def test_lp_ac11_split_overpaid_row_is_ignored(self):
        PaymentTransaction.objects.create(
            bank_txn_id="FTX-THUA", sales_order=self.dead, amount=Decimal("350000"),
            match_status=PaymentTransaction.MatchStatus.OVERPAID, resolution_status="OPEN",
            source=PaymentTransaction.Source.WEBHOOK, raw_payload={"split_from": "FTX"},
            received_at=timezone.now(),
        )
        self.assertEqual(self.post().status_code, 201)

    def test_lp_ac11_unmatched_window(self):
        now = timezone.now()
        self.webhook("FT-NEAR", "350000")  # UNMATCHED, giờ nhận ~ now
        resp = self.post(order_code="", received_at=(now - timedelta(hours=1)).isoformat())
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["code"], "LATE_PAYMENT_POSSIBLE_DUPLICATE")
        with override_settings(LATE_PAYMENT_DUPLICATE_WINDOW_HOURS=1):
            resp = self.post(order_code="", received_at=(now - timedelta(hours=3)).isoformat())
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["payment"]["duplicate_warning"], "")

    def test_lp_ac11_unmatched_other_amount_no_conflict(self):
        self.webhook("FT-NEAR2", "111000")
        self.assertEqual(self.post(order_code="").status_code, 201)

    def test_lp_ac12_webhook_same_txn_after_manual_no_new_row(self):
        self.assertEqual(self.post().status_code, 201)
        resp = self.webhook("FT26100300001", "350000", order_code=self.dead.code)
        self.assertFalse(resp.json()["matched"])
        self.assertEqual(resp.json()["match_status"], "ORPHAN")
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_lp_ac12_ipn_same_txn_after_manual_no_new_row(self):
        self.assertEqual(self.post(order_code="").status_code, 201)
        resp = self.webhook("ft26100300001", "350000", order_code="", url=IPN_URL)
        self.assertFalse(resp.json()["matched"])
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_lp_ac12_webhook_different_txn_flags_orphan(self):
        self.assertEqual(self.post().status_code, 201)
        self.webhook("FT-DIFF", "350000", order_code=self.dead.code)
        late = PaymentTransaction.objects.get(bank_txn_id="FT-DIFF")
        self.assertEqual(late.match_status, PaymentTransaction.MatchStatus.ORPHAN)
        self.assertEqual(late.duplicate_warning, payment_services.DUPLICATE_LATE_MANUAL_WARNING)
        self.assertEqual(PaymentTransaction.objects.get(bank_txn_id="FT26100300001").duplicate_warning, "")

    def test_lp_ac12_webhook_other_amount_not_flagged(self):
        self.assertEqual(self.post().status_code, 201)
        self.webhook("FT-DIFF2", "360000", order_code=self.dead.code)
        self.assertEqual(PaymentTransaction.objects.get(bank_txn_id="FT-DIFF2").duplicate_warning, "")

    def test_lp_ac12_webhook_unmatched_flag_inside_and_outside_window(self):
        self.assertEqual(self.post(order_code="", received_at=timezone.now().isoformat()).status_code, 201)
        self.webhook("FT-IN", "350000")
        self.assertEqual(
            PaymentTransaction.objects.get(bank_txn_id="FT-IN").duplicate_warning,
            payment_services.DUPLICATE_LATE_MANUAL_WARNING,
        )
        with override_settings(LATE_PAYMENT_DUPLICATE_WINDOW_HOURS=0):
            PaymentTransaction.objects.filter(bank_txn_id="FT26100300001").update(
                received_at=timezone.now() - timedelta(hours=5))
            self.webhook("FT-OUT", "350000")
        self.assertEqual(PaymentTransaction.objects.get(bank_txn_id="FT-OUT").duplicate_warning, "")

    def test_lp_ac12_flagged_unmatched_escalates_not_auto_confirmed(self):
        """Nhãn nghi trùng của dòng webhook được job tự khớp đẩy lên Chủ (nhánh BR-TT-15 có sẵn)."""
        self.assertEqual(self.post(order_code="", received_at=timezone.now().isoformat()).status_code, 201)
        self.webhook("FT-IN2", "350000")
        flagged = PaymentTransaction.objects.get(bank_txn_id="FT-IN2")
        self.assertTrue(flagged.duplicate_warning)


class LateRefundGuardTests(LateBase):
    def _refund(self, pay, **kw):
        return client_for(self.owner).post("/api/sales/refunds/create/", {
            "payment_transaction": pay.pk, "amount": "350000",
            "request_id": "11111111-1111-4111-8111-111111111111", **kw,
        }, format="json")

    def test_lp_ac13_refund_blocked_without_ack_then_ok_with_ack(self):
        self.webhook("FT-OTHER-1", "350000", order_code=self.dead.code)
        self.assertEqual(self.post(acknowledge_possible_duplicate=True).status_code, 201)
        pay = PaymentTransaction.objects.get(bank_txn_id="FT26100300001")
        resp = self._refund(pay)
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["code"], "PAYMENT_DUPLICATE_WARNING")
        self.assertEqual(resp.json()["detail"], pay.duplicate_warning)
        self.assertFalse(Refund.objects.exists())
        resp = self._refund(pay, acknowledge_duplicate_warning=True)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Refund.objects.count(), 1)
        audit = AuditLog.objects.get(action="create_refund")  # TL15-M1
        self.assertIs(audit.changes["acknowledged_duplicate_warning"], True)
        self.assertNotIn(payment_services.DUPLICATE_LATE_MANUAL_WARNING, json.dumps(audit.changes, ensure_ascii=False))

    def test_lp_ac13_legacy_overpaid_label_also_blocked(self):
        pay = PaymentTransaction.objects.create(
            bank_txn_id="FT-OVP", sales_order=self.dead, amount=Decimal("350000"),
            match_status=PaymentTransaction.MatchStatus.OVERPAID, resolution_status="OPEN",
            source=PaymentTransaction.Source.WEBHOOK, received_at=timezone.now(),
            duplicate_warning=payment_services.DUPLICATE_MANUAL_WARNING,
        )
        resp = self._refund(pay)
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["code"], "PAYMENT_DUPLICATE_WARNING")

    def test_lp_ac13_no_warning_no_ack_needed(self):
        self.assertEqual(self.post().status_code, 201)
        pay = PaymentTransaction.objects.get()
        self.assertEqual(self._refund(pay).status_code, 201)
        self.assertNotIn("acknowledged_duplicate_warning", AuditLog.objects.get(action="create_refund").changes)

    def test_lp_ac14_guidance_gw03_reads_duplicate_warning(self):
        self.webhook("FT-OTHER-1", "350000", order_code=self.dead.code)
        self.post(acknowledge_possible_duplicate=True)
        pay = PaymentTransaction.objects.get(bank_txn_id="FT26100300001")
        resp = client_for(self.owner).get(f"/api/guidance/payment/{pay.pk}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        codes = [w["code"] for w in resp.json()["warnings"]]
        self.assertIn("GW-03", codes)


class LatePermissionTests(LateBase):
    def test_lp_ac15_401_and_403_by_group_no_write(self):
        self.assertEqual(client_for(None).post(URL, self.body(), format="json").status_code, 401)
        for group in (roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE):
            user = make_user(f"u_{group}", group)
            with self.subTest(group=group):
                self.assertEqual(client_for(user).post(URL, self.body(), format="json").status_code, 403)
        self.assertFalse(PaymentTransaction.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action="record_late_payment").exists())

    def test_lp_ac15_user_with_confirm_payment_manual_perm_allowed(self):
        user = make_user("tien_ve_muon_user", perms=("sales.confirm_payment_manual", "sales.view_paymenttransaction"))
        self.assertEqual(client_for(user).post(URL, self.body(), format="json").status_code, 201)

    def test_lp_ac15_get_not_allowed(self):
        self.assertEqual(client_for(self.owner).get(URL).status_code, 405)


class LatePrivacyAndCostTests(LateBase):
    def test_lp_ac16_timeline_labels_and_actor(self):
        self.assertEqual(self.post().status_code, 201)
        pay = PaymentTransaction.objects.get()
        events = build_payment_timeline(pay)
        late = [e for e in events if e.kind == "payment_recorded_late"]
        self.assertEqual(len(late), 1)
        self.assertIn("Ghi tay tiền về muộn 350.000 đ", late[0].label)
        self.assertIn("FT26100300001", late[0].label)
        self.assertNotEqual(late[0].actor_display, "Hệ thống")
        self.assertEqual(late[0].actor_kind, "user")
        order_events = client_for(self.owner).get(f"/api/sales/orders/{self.dead.pk}/").json()["timeline"]
        received = [e for e in order_events if e["kind"] == "payment_received"]
        self.assertEqual(len(received), 1)
        self.assertIn("Xác nhận tay", received[0]["label"])
        self.assertIn("Về sau khi đơn đã huỷ", received[0]["label"])
        self.assertNotEqual(received[0]["actor_display"], "Hệ thống")

    def test_free_text_note_not_stored_anywhere(self):
        resp = self.post(note=f"{MARK} gọi {FAKE_PHONE}")
        self.assertEqual(resp.status_code, 201, resp.content)
        pay = PaymentTransaction.objects.get()
        stored = json.dumps(
            [
                {f.name: str(getattr(pay, f.name, "")) for f in PaymentTransaction._meta.get_fields() if hasattr(f, "attname")},
                list(AuditLog.objects.values("note", "changes", "object_repr")),
                [e.label for e in build_payment_timeline(pay)],
                client_for(self.owner).get(f"/api/sales/orders/{self.dead.pk}/").json()["timeline"],
                resp.json(),
            ],
            ensure_ascii=False, default=str,
        )
        self.assertNotIn(MARK, stored)
        self.assertNotIn(FAKE_PHONE, stored)

    def test_ignored_keys_cannot_set_source_or_status(self):
        resp = self.post(source="WEBHOOK", match_status="MATCHED", sales_order=self.order.pk, environment="PRODUCTION")
        self.assertEqual(resp.status_code, 201, resp.content)
        pay = PaymentTransaction.objects.get()
        self.assertEqual(pay.source, PaymentTransaction.Source.MANUAL)
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.ORPHAN)
        self.assertEqual(pay.sales_order_id, self.dead.pk)
        self.assertEqual(pay.environment, "")

    def test_response_has_no_raw_payload_cost_or_personal_data(self):
        resp = self.post()
        text = json.dumps(resp.json(), ensure_ascii=False)
        self.assertEqual(find_keys(resp.json(), SENSITIVE_KEYS | {"cogs", "raw_payload"}), set())
        for needle in ("0900000302", "Chị Hoa", "Lê Lợi", "customer", "phone", "address"):
            self.assertNotIn(needle, text)

    def test_audit_has_no_personal_data_or_note_key(self):
        self.post()
        audit = AuditLog.objects.get(action="record_late_payment")
        self.assertEqual(set(audit.changes), {
            "bank_txn_id", "amount", "match_status", "source", "order", "received_at", "acknowledged_duplicate",
        })
        self.assertEqual(audit.changes["order"], self.dead.code)
        blob = json.dumps(audit.changes, ensure_ascii=False)
        for needle in ("0900000302", "Chị Hoa", "Lê Lợi"):
            self.assertNotIn(needle, blob)

    def test_service_does_not_log_payload(self):
        with self.assertNoLogs(level="DEBUG"):
            self.post()

    def test_no_order_audit_changes_order_is_none(self):
        self.post(order_code="")
        self.assertIsNone(AuditLog.objects.get(action="record_late_payment").changes["order"])


class LateCrossTypeDuplicateTests(LateBase):
    """TL15-H1: nghi trùng không phụ thuộc bên kia có gắn đơn hay không (cả hai chiều, trong cửa sổ giờ)."""

    def _flag(self, txn):
        return PaymentTransaction.objects.get(bank_txn_id=txn).duplicate_warning

    def test_manual_unmatched_then_ipn_orphan_is_flagged(self):
        self.assertEqual(self.post(order_code="", received_at=timezone.now().isoformat()).status_code, 201)
        self.webhook("SEPAY-ID-1", "350000", order_code=self.dead.code, url=IPN_URL)
        late = PaymentTransaction.objects.get(bank_txn_id="SEPAY-ID-1")
        self.assertEqual(late.match_status, PaymentTransaction.MatchStatus.ORPHAN)
        self.assertEqual(late.duplicate_warning, payment_services.DUPLICATE_LATE_MANUAL_WARNING)

    def test_manual_unmatched_then_ipn_orphan_other_amount_or_outside_window_not_flagged(self):
        self.assertEqual(self.post(order_code="", received_at=timezone.now().isoformat()).status_code, 201)
        self.webhook("SEPAY-ID-2", "360000", order_code=self.dead.code, url=IPN_URL)
        self.assertEqual(self._flag("SEPAY-ID-2"), "")
        PaymentTransaction.objects.filter(bank_txn_id="FT26100300001").update(
            received_at=timezone.now() - timedelta(hours=200))
        self.webhook("SEPAY-ID-3", "350000", order_code=self.dead.code, url=IPN_URL)
        self.assertEqual(self._flag("SEPAY-ID-3"), "")

    def test_ipn_orphan_then_manual_unmatched_returns_409(self):
        self.webhook("SEPAY-ID-4", "350000", order_code=self.dead.code, url=IPN_URL)
        resp = self.post(order_code="")
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["code"], "LATE_PAYMENT_POSSIBLE_DUPLICATE")
        self.assertEqual(resp.json()["similar_bank_txn_id"], "SEPAY-ID-4")
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_ipn_orphan_then_manual_unmatched_other_amount_or_outside_window_ok(self):
        self.webhook("SEPAY-ID-5", "350000", order_code=self.dead.code, url=IPN_URL)
        self.assertEqual(self.post(order_code="", amount="360000").status_code, 201)
        with override_settings(LATE_PAYMENT_DUPLICATE_WINDOW_HOURS=1):
            resp = self.post(order_code="", bank_txn_id="FT-FAR",
                             received_at=(timezone.now() - timedelta(hours=10)).isoformat())
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_webhook_unmatched_then_manual_with_cancelled_order_returns_409(self):
        self.webhook("FT-WH-U", "350000")
        resp = self.post()  # gắn đơn Tự huỷ
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["similar_bank_txn_id"], "FT-WH-U")
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_webhook_unmatched_then_manual_with_order_other_amount_ok(self):
        self.webhook("FT-WH-U2", "111000")
        self.assertEqual(self.post().status_code, 201)

    def test_manual_orphan_then_webhook_unmatched_is_flagged(self):
        self.assertEqual(self.post(received_at=timezone.now().isoformat()).status_code, 201)
        self.webhook("FT-WH-U3", "350000")  # webhook không mã đơn: UNMATCHED
        late = PaymentTransaction.objects.get(bank_txn_id="FT-WH-U3")
        self.assertEqual(late.match_status, PaymentTransaction.MatchStatus.UNMATCHED)
        self.assertEqual(late.duplicate_warning, payment_services.DUPLICATE_LATE_MANUAL_WARNING)

    def test_manual_orphan_then_webhook_unmatched_other_amount_or_outside_window_not_flagged(self):
        self.assertEqual(self.post(received_at=timezone.now().isoformat()).status_code, 201)
        self.webhook("FT-WH-U4", "360000")
        self.assertEqual(self._flag("FT-WH-U4"), "")
        PaymentTransaction.objects.filter(bank_txn_id="FT26100300001").update(
            received_at=timezone.now() - timedelta(hours=200))
        self.webhook("FT-WH-U5", "350000")
        self.assertEqual(self._flag("FT-WH-U5"), "")
