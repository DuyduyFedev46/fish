"""
TL-D3-L4 / TL15-L5 — `AuditLog.note`/`changes` không chép chữ người dùng tự gõ (bất biến 9).

Ghi chú tự do có thể chứa tên hoặc SĐT của khách / người chuyển khoản. Nhật ký chỉ ghi mã lý do,
nhãn cố định hoặc "có ghi chú"; chữ gốc nằm trên chứng từ (có phân quyền riêng). Dữ liệu giả.
"""
import ast
import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.audit import NOTE_PRESENT_LABEL, note_marker, record_audit
from apps.common.tests.fixtures import client_for
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.models import ConfirmationTask
from apps.delivery.tests.test_confirmation_operations import ConfirmationL4BaseTestCase
from apps.sales.models import PaymentTransaction
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.sales.payments import services as payment_services
from apps.sales.refunds import services as refund_services

SECRET_NAME = "Nguyễn Văn Giả"
FAKE_PHONE = "0900000321"
FREE = f"{SECRET_NAME} chuyển hộ"  # chữ tự do có tên giả (SĐT dài bị chặn riêng ở vài API)
FREE_PHONE = f"{SECRET_NAME} {FAKE_PHONE}"


def assert_no_leak(test, *needles):
    blob = json.dumps(
        list(AuditLog.objects.values("note", "changes", "object_repr")), ensure_ascii=False, default=str,
    )
    for needle in needles:
        test.assertNotIn(needle, blob)


class NoteMarkerTests(TestCase):
    def test_marker_fixed_label_or_empty(self):
        self.assertEqual(note_marker(FREE_PHONE), NOTE_PRESENT_LABEL)
        self.assertNotIn(SECRET_NAME, note_marker(FREE_PHONE))
        self.assertEqual(note_marker("   "), "")
        self.assertEqual(note_marker(None), "")


class PaymentsOrdersRefundsNoFreeTextTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.owner = self.chu  # naming: allow - tên thuộc tính của OrderApiBase dùng chung
        self.manager = self.ql  # naming: allow - tên thuộc tính của OrderApiBase dùng chung
        self.order = self._order()

    def _pay(self, order, txn, amount):
        return payment_services.confirm_payment(
            order=order, bank_txn_id=txn, amount=Decimal(amount), received_at=timezone.now(),
        )

    @override_settings(INTERNAL_SERVICE_TOKEN="tok")
    def test_attach_to_order_note_not_in_audit(self):
        resp = client_for(None).post(
            "/api/internal/payments/sepay-webhook/",
            {"bank_txn_id": "FTNOCODE", "order_code": "", "amount": "540000",
             "received_at": "2026-09-25T10:00:00+07:00"},
            format="json", HTTP_X_INTERNAL_TOKEN="tok",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        pay = PaymentTransaction.objects.get(bank_txn_id="FTNOCODE")
        resp = client_for(self.owner).post(
            f"/api/sales/payments/{pay.pk}/resolve",
            {"action": "ATTACH_TO_ORDER", "order_id": self.order.pk, "note": FREE_PHONE}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        for log in AuditLog.objects.filter(action__in=("attach_payment", "resolve_payment")):
            self.assertIn(log.note, ("", NOTE_PRESENT_LABEL))
        self.assertTrue(AuditLog.objects.filter(action="resolve_payment", note=NOTE_PRESENT_LABEL).exists())
        assert_no_leak(self, SECRET_NAME, FAKE_PHONE)

    def test_confirm_order_note_not_in_audit(self):
        self._pay(self.order, "FTA", "300000")
        pay_b = self._pay(self.order, "FTB", "240000")
        resp = client_for(self.owner).post(
            f"/api/sales/payments/{pay_b.pk}/resolve",
            {"action": "CONFIRM_ORDER", "note": FREE_PHONE}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(AuditLog.objects.filter(action="resolve_payment").exists())
        assert_no_leak(self, SECRET_NAME, FAKE_PHONE)

    def test_refunded_payment_note_is_fixed_label(self):
        order = self._paid_order(phone="0905555555", txn="FTPAID")
        pay = order.payments.first()
        refund, _ = refund_services.create_invoice_refund(
            invoice=order.invoice, amount=Decimal("100000"), is_partial=True, reason=FREE, actor=self.owner,
        )
        refund_services.confirm_refund(refund=refund, bank_txn_ref=f"REF{FAKE_PHONE}", actor=self.owner)
        self.assertTrue(AuditLog.objects.filter(action="confirm_refund").exists())
        for log in AuditLog.objects.all():
            self.assertNotIn(SECRET_NAME, log.note)
        assert_no_leak(self, SECRET_NAME)
        self.assertIsNotNone(pay)

    def test_refund_failed_reason_not_in_audit(self):
        order = self._paid_order(phone="0905555555", txn="FTPAID")
        refund, _ = refund_services.create_invoice_refund(
            invoice=order.invoice, amount=Decimal("100000"), is_partial=True, reason=FREE, actor=self.owner,
        )
        refund_services.mark_refund_failed(refund=refund, reason=FREE_PHONE, actor=self.owner)
        log = AuditLog.objects.get(action="mark_refund_failed")
        self.assertEqual(log.note, NOTE_PRESENT_LABEL)
        refund.refresh_from_db()
        self.assertEqual(refund.failure_reason, FREE_PHONE)  # chữ gốc vẫn ở chứng từ
        assert_no_leak(self, SECRET_NAME, FAKE_PHONE)

    def test_cancel_paid_order_note_is_reason_label_only(self):
        order = self._paid_order()
        resp = client_for(self.manager).post(
            f"/api/sales/orders/{order.pk}/cancel/",
            {"reason_code": "OTHER", "note": FREE_PHONE}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        log = AuditLog.objects.get(action="cancel_paid_order")
        self.assertEqual(log.note, "Lý do: Khác")
        assert_no_leak(self, SECRET_NAME, FAKE_PHONE)


class DeliveryConfirmationNoFreeTextTests(ConfirmationL4BaseTestCase):
    def setUp(self):
        super().setUp()
        self.manager = self.ql  # naming: allow - tên thuộc tính của ConfirmationL4BaseTestCase dùng chung

    def test_decide_extend_reason_not_in_audit(self):
        _, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WANT_CANCEL")
        confirmation_services.decide(
            task.pk, self.manager, "EXTEND", reason=FREE, until=timezone.now() + timedelta(hours=2),
        )
        log = AuditLog.objects.get(action="delivery_extended")
        self.assertEqual(log.note, NOTE_PRESENT_LABEL)
        assert_no_leak(self, SECRET_NAME)

    def test_decide_deliver_without_confirm_reason_not_in_audit(self):
        _, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WANT_CANCEL")
        confirmation_services.decide(task.pk, self.manager, "DELIVER_WITHOUT_CONFIRM", reason=FREE)
        self.assertEqual(AuditLog.objects.get(action="delivery_confirm_skipped").note, NOTE_PRESENT_LABEL)
        assert_no_leak(self, SECRET_NAME)

    def test_unconfirm_reason_not_in_audit(self):
        _, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        task.refresh_from_db()
        confirmation_services.unconfirm(task.pk, self.cs1, reason=FREE)
        self.assertEqual(AuditLog.objects.get(action="delivery_unconfirmed").note, NOTE_PRESENT_LABEL)
        assert_no_leak(self, SECRET_NAME)
        self.assertEqual(ConfirmationTask.objects.get(pk=task.pk).state, ConfirmationTask.State.PENDING)


class RecordAuditCallSitesSweepTests(TestCase):
    """Quét tĩnh: `record_audit(note=<biến chữ tự do>)` hay `changes` chứa `reason`/`note` thô đều bị chặn."""

    RAW_NAMES = {"note", "reason", "memo", "description", "clean_reason", "clean_note", "free_note",
                 "reason_note", "failure_note", "text", "message", "resolution_note"}

    # Có chủ ý: lý do là mã chọn từ danh sách cố định (BR-ND-15) hoặc do hệ thống sinh, không phải chữ người gõ.
    ALLOWED = {"content/entries/services.py", "sales/payments/auto_confirm.py"}

    def _calls(self):
        root = Path(__file__).resolve().parents[2]
        for path in root.rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            if rel in self.ALLOWED or "/tests/" in rel or "/migrations/" in rel or rel.endswith("common/audit.py"):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == "record_audit":
                    yield rel, node

    def _is_raw(self, node):
        if isinstance(node, ast.Name):
            return node.id in self.RAW_NAMES
        if isinstance(node, ast.Attribute):
            return node.attr in self.RAW_NAMES
        if isinstance(node, ast.JoinedStr):
            return any(self._is_raw(v.value) for v in node.values if isinstance(v, ast.FormattedValue))
        if isinstance(node, ast.BoolOp):
            return any(self._is_raw(v) for v in node.values)
        return False

    def test_no_raw_user_text_in_note_or_changes(self):
        calls = list(self._calls())
        self.assertGreater(len(calls), 50)
        bad = []
        for rel, call in calls:
            for kw in call.keywords:
                if kw.arg == "note" and self._is_raw(kw.value):
                    bad.append(f"{rel}:{call.lineno} note=")
                if kw.arg == "changes" and isinstance(kw.value, ast.Dict):
                    for key, val in zip(kw.value.keys, kw.value.values):
                        if isinstance(key, ast.Constant) and key.value in ("reason", "note") and self._is_raw(val):
                            bad.append(f"{rel}:{call.lineno} changes[{key.value}]")
        self.assertEqual(bad, [])

    def test_sweep_detects_raw_note(self):
        call = ast.parse("record_audit('x', note=reason)").body[0].value
        self.assertTrue(self._is_raw(call.keywords[0].value))
