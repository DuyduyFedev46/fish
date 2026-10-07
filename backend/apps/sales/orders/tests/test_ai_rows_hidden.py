"""
Lô dọn chữ AI (A3–A8, 02b 2.3, BR-AI-17, BR-PQ-04/05) — khi AI tắt, mọi dòng thời gian không còn dòng AI và dòng
Hệ thống thuộc đề xuất AI; lọc TRƯỚC khi cắt `limit`; bật cờ thì hiện đủ (AuditLog không bị xoá). Dữ liệu giả.
"""
from decimal import Decimal

from django.test import override_settings

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.catalog.models import Item
from apps.common.audit import record_audit
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches.timeline import build_batch_timeline
from apps.sales.orders.timeline import build_timeline
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.sales.payments.timeline import build_payment_timeline
from apps.sales.refunds import services as refund_services
from apps.sales.refunds.timeline import build_refund_timeline

PROPOSAL = "P-FAKE-1"


def seed(obj, human, action="odd_action"):
    """1 dòng người, 1 dòng AI, 1 dòng Hệ thống có `proposal_ref`, cùng một chứng từ."""
    record_audit(action, actor=human, obj=obj)
    record_audit(action, actor_kind="ai", ai_actor=human, obj=obj)
    record_audit(action, actor_kind="system", proposal_ref=PROPOSAL, obj=obj)


def actor_kinds(rows):
    out = set()
    for r in rows:
        if isinstance(r, dict):
            out.add(r["actor"]["kind"] if isinstance(r.get("actor"), dict) else r.get("actor_kind") or r["actor"])
        else:
            out.add(r.actor_kind)
    return out


def labels(rows):
    return [r["label"] if isinstance(r, dict) else r.label for r in rows]


class AiRowsHiddenTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.owner = self.chu  # naming: allow - thuộc tính của OrderApiBase dùng chung
        self.manager = self.ql  # naming: allow - thuộc tính của OrderApiBase dùng chung
        self.order = self._paid_order()
        self.pay = self.order.payments.first()
        self.refund, _ = refund_services.create_invoice_refund(
            invoice=self.order.invoice, amount=Decimal("100000"), is_partial=True, reason="x", actor=self.manager,
        )
        seed(self.item, self.owner)
        # Mỗi builder chỉ dựng dòng cho action nó biết, nên seed theo action thật.
        seed(self.order, self.owner, action="cancel_unpaid_expired")
        seed(self.pay, self.owner, action="resolve_payment")
        seed(self.refund, self.owner, action="mark_refund_failed")
        seed(self.batch, self.owner, action="publish_batch")

    # --- từng builder --------------------------------------------------------------
    def _timelines(self):
        return {
            "order": build_timeline(self.order),
            "order_guidance": client_for(self.owner).get(f"/api/guidance/order/{self.order.pk}/").json()["timeline"],
            "payment": build_payment_timeline(self.pay),
            "refund": build_refund_timeline(self.refund),
            "batch": build_batch_timeline(self.batch, viewer=self.owner),
            "item": client_for(self.owner).get(f"/api/guidance/item/{self.item.pk}/").json()["timeline"],
        }

    @override_settings(AI_ENABLED=False)
    def test_off_no_ai_rows_in_any_timeline(self):
        for name, rows in self._timelines().items():
            kind_set = actor_kinds(rows)
            self.assertNotIn("ai", kind_set, name)
            self.assertNotIn("AI của", str(labels(rows)), name)
            self.assertTrue(rows, name)  # dòng người vẫn còn

    @override_settings(AI_ENABLED=True)
    def test_on_all_rows_shown(self):
        for name, rows in self._timelines().items():
            self.assertIn("ai", actor_kinds(rows), name)
        self.assertEqual(AuditLog.objects.filter(actor_kind="ai").count(), 5)  # dòng AI vẫn còn trong DB

    @override_settings(AI_ENABLED=False)
    def test_off_system_rows_with_proposal_hidden_but_plain_system_kept(self):
        record_audit("odd_plain_system", actor_kind="system", obj=self.item)
        rows = client_for(self.owner).get(f"/api/guidance/item/{self.item.pk}/").json()["timeline"]
        self.assertIn("system", actor_kinds(rows))
        self.assertNotIn("ai", actor_kinds(rows))
        raw = AuditLog.objects.filter(model_name=Item._meta.label, object_id=str(self.item.pk))
        self.assertEqual(raw.count(), 4)  # chỉ ẩn khi đọc

    @override_settings(AI_ENABLED=False, GUIDANCE_TIMELINE_MAX_ROWS=2)
    def test_off_limit_applies_after_filter(self):
        """Dòng AI mới nhất không được chiếm chỗ của dòng người."""
        record_audit("odd_ai_newest", actor_kind="ai", ai_actor=self.owner, obj=self.item)
        record_audit("odd_ai_newest2", actor_kind="ai", ai_actor=self.owner, obj=self.item)
        body = client_for(self.owner).get(f"/api/guidance/item/{self.item.pk}/").json()
        self.assertEqual(len(body["timeline"]), 1)  # chỉ dòng người
        self.assertFalse(body["timeline_truncated"])
        with override_settings(AI_ENABLED=True):
            body = client_for(self.owner).get(f"/api/guidance/item/{self.item.pk}/").json()
            self.assertEqual(len(body["timeline"]), 2)
            self.assertTrue(body["timeline_truncated"])

    # --- Nhật ký -------------------------------------------------------------------
    @override_settings(AI_ENABLED=False)
    def test_off_audit_log_hides_ai_rows(self):
        rows = client_for(self.owner).get("/api/audit-logs/", {"page_size": 200}).json()
        rows = rows["results"] if isinstance(rows, dict) else rows
        self.assertNotIn("ai", {r["actor_kind"] for r in rows})
        self.assertFalse([r for r in rows if r.get("note") == "" and r["action"] == "odd_system_action"])

    @override_settings(AI_ENABLED=True)
    def test_on_audit_log_shows_ai_rows(self):
        rows = client_for(self.owner).get("/api/audit-logs/", {"page_size": 200}).json()
        rows = rows["results"] if isinstance(rows, dict) else rows
        self.assertIn("ai", {r["actor_kind"] for r in rows})


class GuidanceStepAiNullTests(OrderApiBase):
    """02b mục 0: AI tắt thì `next_steps[].ai` luôn null (khoá hành vi `steps.py:resolve_step_ai`)."""

    @override_settings(AI_ENABLED=False)
    def test_off_every_next_step_ai_is_null(self):
        self.owner = self.chu  # naming: allow - thuộc tính của OrderApiBase dùng chung
        for order in (self._order(), self._paid_order(phone="0900000777", txn="FT-FAKE-2")):
            body = client_for(self.owner).get(f"/api/guidance/order/{order.pk}/").json()
            self.assertTrue(body["next_steps"])
            for step in body["next_steps"]:
                self.assertIsNone(step["ai"], step["key"])
            self.assertNotIn("AI soạn", str(body))
