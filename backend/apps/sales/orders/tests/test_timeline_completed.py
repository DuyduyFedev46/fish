"""
W37 L3 (S7-AC6, AC7, AC9): dòng thời gian của đơn Hoàn tất. BR-BH-18, UC-5, bất biến 9.
Dữ liệu giả (SĐT 0900000xxx).
"""
import json
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from apps.common.audit import record_audit
from apps.common.tests.fixtures import client_for
from apps.delivery.models import DeliveryNote
from apps.delivery.tests.test_order_completion import ADDRESS, NAME, PHONE, CompletionBase
from apps.sales.models import SalesOrder

S = DeliveryNote.Status


class CompletedTimelineTests(CompletionBase):
    def _timeline(self, order, user=None):
        resp = client_for(user or self.owner).get(f"/api/sales/orders/{order.pk}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()["timeline"]

    def test_s7_ac6_one_merged_delivered_event_with_note_code(self):
        order, note = self._processing()
        self._complete(self.courier, note)
        events = self._timeline(order)
        delivered = [e for e in events if e["kind"] == "delivered"]
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0]["label"], f"Đã giao — đơn hoàn tất ({note.code})")
        self.assertNotIn("Giao hàng thành công", json.dumps(events, ensure_ascii=False))
        self.assertFalse([e for e in events if e["kind"] == "order_completed"])

    def test_s7_ac7_backfill_keeps_old_delivered_label_and_adds_system_event(self):
        order, note = self._processing()
        # Dữ liệu cũ: phiếu giao xong qua đường cũ (đơn chưa chuyển), rồi chạy chuyển bù.
        DeliveryNote.objects.filter(pk=note.pk).update(status=S.COMPLETED, completed_at=timezone.now())
        record_audit("delivery_advance_status", actor=self.courier, obj=note,
                     changes={"status": {"from": S.DELIVERING, "to": S.COMPLETED}})
        call_command("backfill_completed_orders", stdout=StringIO(), stderr=StringIO())
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.COMPLETED)
        events = self._timeline(order)
        delivered = [e for e in events if e["kind"] == "delivered"]
        self.assertEqual([e["label"] for e in delivered], [f"Giao hàng thành công ({note.code})"])
        done = [e for e in events if e["kind"] == "order_completed"]
        self.assertEqual(len(done), 1)
        self.assertEqual(done[0]["label"], "Hệ thống chuyển đơn sang Hoàn tất (chuyển bù)")
        self.assertEqual(done[0]["actor_display"], "Hệ thống")

    def test_s7_ac9_new_events_have_no_personal_data(self):
        order, note = self._processing()
        self._complete(self.courier, note)
        blob = json.dumps(self._timeline(order), ensure_ascii=False)
        for secret in (PHONE, NAME, ADDRESS, "Lê Lợi", "complete_order", "delivery_note_id", "changes"):
            self.assertNotIn(secret, blob)
