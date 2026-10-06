"""
TL-D3-L4 / TL15-L5 — `AuditLog.note`/`changes` không chép chữ người dùng tự gõ (bất biến 9).

Ghi chú tự do có thể chứa tên hoặc SĐT của khách / người chuyển khoản. Nhật ký chỉ ghi mã lý do,
nhãn cố định hoặc "có ghi chú"; chữ gốc nằm trên chứng từ (có phân quyền riêng). Dữ liệu giả.
"""
import ast
import re
import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.audit import NOTE_PRESENT_LABEL, NOTE_PRESENT_NEUTRAL_LABEL, note_marker, record_audit
from apps.common.tests.fixtures import client_for
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.models import ConfirmationTask
from apps.delivery.tests.test_confirmation_operations import ConfirmationL4BaseTestCase
from apps.sales.models import PaymentTransaction, Refund
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
        self.assertEqual(note_marker(FREE_PHONE, on_document=False), NOTE_PRESENT_NEUTRAL_LABEL)
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

    @override_settings(INTERNAL_SERVICE_TOKEN="tok")
    def test_attach_underpaid_stores_note_on_payment_not_audit(self):
        resp = client_for(None).post(
            "/api/internal/payments/sepay-webhook/",
            {"bank_txn_id": "FTSHORT", "order_code": "", "amount": "300000",
             "received_at": "2026-09-25T10:00:00+07:00"},
            format="json", HTTP_X_INTERNAL_TOKEN="tok",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        pay = PaymentTransaction.objects.get(bank_txn_id="FTSHORT")
        resp = client_for(self.owner).post(
            f"/api/sales/payments/{pay.pk}/resolve",
            {"action": "ATTACH_TO_ORDER", "order_id": self.order.pk, "note": FREE}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        pay.refresh_from_db()
        self.assertEqual(pay.resolution_note, FREE)  # chữ gốc nằm trên giao dịch
        self.assertEqual(AuditLog.objects.get(action="attach_payment").note, NOTE_PRESENT_LABEL)
        assert_no_leak(self, SECRET_NAME)

    def test_admin_edit_locked_free_text_fields_not_copied_to_audit(self):
        """TL-AN-M2: superuser sửa raw_payload / resolution_note / failure_reason / bank_txn_ref -> chỉ ghi changed."""
        root = User.objects.create_superuser("root_fake", password="x")
        req = RequestFactory().post("/")
        req.user = root
        order = self._paid_order(phone="0905555555", txn="FTADM")
        pay = order.payments.first()
        pay.raw_payload = {"content": f"{SECRET_NAME} {FAKE_PHONE}"}
        pay.resolution_note = FREE
        admin.site._registry[PaymentTransaction].save_model(req, pay, None, True)
        refund, _ = refund_services.create_invoice_refund(
            invoice=order.invoice, amount=Decimal("100000"), is_partial=True, reason="x", actor=self.owner,
        )
        refund.failure_reason = FREE
        refund.bank_txn_ref = f"{SECRET_NAME}-REF"
        admin.site._registry[Refund].save_model(req, refund, None, True)
        logs = list(AuditLog.objects.filter(action="admin_edit"))
        self.assertEqual(len(logs), 2)
        for log in logs:
            for value in log.changes.values():
                self.assertEqual(value, {"changed": True})
        self.assertEqual(set(logs[0].changes) | set(logs[1].changes),
                         {"raw_payload", "resolution_note", "failure_reason", "bank_txn_ref"})
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
        # Chỉ chặn TÊN giả ở note/changes. Mã GD hoàn do Chủ nhập vẫn vào `changes.bank_txn_ref` (giữ để
        # đối soát, chờ Duy quyết), nên KHÔNG assert SĐT giả ở đây: test này không chứng minh chặn SĐT.
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

    def test_cancel_note_rejects_long_digit_run_and_too_long(self):
        order = self._paid_order()
        for bad in ("gọi 0900000321 giúp", "x" * 201):
            resp = client_for(self.manager).post(
                f"/api/sales/orders/{order.pk}/cancel/", {"reason_code": "OTHER", "note": bad}, format="json",
            )
            self.assertEqual(resp.status_code, 400, resp.content)
            self.assertEqual(resp.json()["code"], "BR-GH-19")
        order.refresh_from_db()
        self.assertEqual(order.cancel_note, "")

    def test_cancel_paid_order_note_is_reason_label_only(self):
        order = self._paid_order()
        resp = client_for(self.manager).post(
            f"/api/sales/orders/{order.pk}/cancel/",
            {"reason_code": "OTHER", "note": FREE}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        log = AuditLog.objects.get(action="cancel_paid_order")
        self.assertEqual(log.note, f"Lý do: Khác · {NOTE_PRESENT_LABEL}")
        order.refresh_from_db()
        self.assertEqual(order.cancel_note, FREE)  # chữ gốc ở đơn
        detail = client_for(self.owner).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertEqual(detail["cancel_note"], FREE)
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
        task.refresh_from_db()
        self.assertEqual(task.decision_note, FREE)  # chữ gốc nằm trên chứng từ
        log = AuditLog.objects.get(action="delivery_extended")
        self.assertEqual(log.note, NOTE_PRESENT_LABEL)
        assert_no_leak(self, SECRET_NAME)

    def test_decide_deliver_without_confirm_reason_not_in_audit(self):
        _, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WANT_CANCEL")
        confirmation_services.decide(task.pk, self.manager, "DELIVER_WITHOUT_CONFIRM", reason=FREE)
        task.refresh_from_db()
        self.assertEqual(task.decision_note, FREE)
        self.assertEqual(AuditLog.objects.get(action="delivery_confirm_skipped").note, NOTE_PRESENT_LABEL)
        assert_no_leak(self, SECRET_NAME)

    def test_decision_note_in_detail_only_for_in_scope_users(self):
        _, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WANT_CANCEL")
        confirmation_services.decide(task.pk, self.manager, "EXTEND", reason=FREE,
                                     until=timezone.now() + timedelta(hours=2))
        body = client_for(self.manager).get(f"/api/confirmation/queue/{note.pk}/").json()
        self.assertEqual(body["decision_note"], FREE)
        shop = client_for(None).get(f"/api/confirmation/queue/{note.pk}/")
        self.assertIn(shop.status_code, (401, 403))
        listing = client_for(self.manager).get("/api/confirmation/queue/").content.decode()
        self.assertNotIn("decision_note", listing)  # danh sách không mang field này

    def test_unconfirm_reason_not_in_audit(self):
        _, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        task.refresh_from_db()
        confirmation_services.unconfirm(task.pk, self.cs1, reason=FREE)
        self.assertEqual(ConfirmationTask.objects.get(pk=task.pk).decision_note, FREE)
        self.assertEqual(AuditLog.objects.get(action="delivery_unconfirmed").note, NOTE_PRESENT_LABEL)
        assert_no_leak(self, SECRET_NAME)
        self.assertEqual(ConfirmationTask.objects.get(pk=task.pk).state, ConfirmationTask.State.PENDING)


class RecordAuditCallSitesSweepTests(TestCase):
    """
    Quét tĩnh: chốt chặn dò lỗi, không phải bảo đảm. Lớp chặn chính là test chạy thật theo từng điểm.

    Duyệt đệ quy cây con của `note=` và `changes=` (trừ lời gọi `note_marker(...)`), báo khi gặp
    biến/thuộc tính tên chữ tự do, `data["note"]`, `request.data.get("note")`, kể cả trong f-string,
    `str(x)`, `.strip()`. Miễn theo từng cặp (file, action), không miễn cả file.
    """

    RAW_NAMES = {"note", "reason", "memo", "description", "clean_reason", "clean_note", "free_note",
                 "reason_note", "failure_note", "failure_reason", "text", "message", "resolution_note",
                 "note_text", "display_name", "phone", "address", "delivery_address", "raw_payload"}
    # (file, action) có chủ ý: lý do là mã chọn từ danh sách cố định (BR-ND-15) hoặc câu do hệ thống sinh.
    ALLOWED = {
        ("content/entries/services.py", "content_return"),
        ("content/entries/services.py", "content_unpublish"),
        ("sales/payments/auto_confirm.py", "escalate_unmatched_payment"),
        # Dữ liệu cá nhân của NHÂN VIÊN (không phải khách); chờ Duy quyết thu tối thiểu (review câu hỏi 2).
        ("accounts/staff/services.py", "staff_create"),
    }

    def _root(self):
        return Path(__file__).resolve().parents[2]

    def _calls(self):
        root = self._root()
        for path in root.rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            if "/tests/" in rel or "/migrations/" in rel or rel.endswith("common/audit.py"):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == "record_audit":
                    yield rel, node

    @staticmethod
    def _action(call):
        node = call.args[0] if call.args else next((k.value for k in call.keywords if k.arg == "action"), None)
        return node.value if isinstance(node, ast.Constant) else "<dynamic>"

    def _raw_hits(self, node):
        """Các dấu hiệu chữ tự do trong cây con của `node`, bỏ qua mọi lời gọi `note_marker(...)`."""
        if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == "note_marker":
            return []
        hits = []
        if isinstance(node, ast.Name) and node.id in self.RAW_NAMES:
            hits.append(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in self.RAW_NAMES:
            hits.append(node.attr)
        elif isinstance(node, ast.Subscript):
            key = node.slice
            if isinstance(key, ast.Constant) and key.value in self.RAW_NAMES:
                hits.append(key.value)
        elif isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "get":
            if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value in self.RAW_NAMES:
                hits.append(node.args[0].value)
        for child in ast.iter_child_nodes(node):
            hits += self._raw_hits(child)
        return hits

    def test_no_raw_user_text_in_note_or_changes(self):
        calls = list(self._calls())
        self.assertGreater(len(calls), 50)
        bad = []
        for rel, call in calls:
            action = self._action(call)
            if (rel, action) in self.ALLOWED:
                continue
            for kw in call.keywords:
                if kw.arg in ("note", "changes"):
                    for hit in self._raw_hits(kw.value):
                        bad.append(f"{rel}:{call.lineno} {kw.arg} <- {hit}")
        self.assertEqual(bad, [])

    def test_allowlist_pairs_still_exist(self):
        found = {(rel, self._action(call)) for rel, call in self._calls()}
        self.assertEqual(self.ALLOWED - found, set(), "allowlist chứa cặp không còn tồn tại")

    def test_sweep_detects_evasions(self):
        evasions = [
            "record_audit('x', note=reason)",
            "record_audit('x', note=str(reason))",
            "record_audit('x', note=reason.strip())",
            "record_audit('x', note=data['note'])",
            "record_audit('x', note=request.data.get('note'))",
            "record_audit('x', note=f'ghi {x.note[:50]}')",
            "record_audit('x', changes={'a': {'to': refund.failure_reason}})",
            "record_audit('x', changes={'t': clean_note})",
        ]
        for src in evasions:
            call = ast.parse(src).body[0].value
            hits = [h for kw in call.keywords for h in self._raw_hits(kw.value)]
            self.assertTrue(hits, src)
        ok = ast.parse("record_audit('x', note=note_marker(note), changes={'n': 1})").body[0].value
        self.assertEqual([h for kw in ok.keywords for h in self._raw_hits(kw.value)], [])

    def test_audit_log_rows_only_created_by_record_audit(self):
        root = self._root()
        offenders = []
        for path in root.rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            if "/migrations/" in rel or "/tests/" in rel or rel.endswith("common/audit.py"):
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(r"AuditLog\.objects\.(bulk_)?create|(?<!class )\bAuditLog\(", text):
                offenders.append(rel)
        self.assertEqual(offenders, [])
