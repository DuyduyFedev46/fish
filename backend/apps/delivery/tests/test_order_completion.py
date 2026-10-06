"""
W37 L1 (S1, S2): giao xong phiếu cuối thì đơn Hoàn tất; huỷ và giao xong không ra hai kết cục.
BR-BH-18, BR-GH-05, BR-GH-24, BR-PQ-04/05/11. Dữ liệu giả (SĐT 0900000xxx).
Đua thật (hai luồng) nằm ở test_completion_race_postgres.py; ở đây là 5 ca tất định chạy trên mọi engine.
"""
import json
from unittest import mock

from django.db.models.query import QuerySet

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import client_for, confirm_note_for_test, make_user
from apps.delivery import services
from apps.delivery.models import DeliveryNote
from apps.inventory.models import StockLedgerEntry
from apps.reports.tests.financial_snapshot import financial_snapshot
from apps.sales.models import SalesCreditNote, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase

S = DeliveryNote.Status
PHONE = "0900000123"
NAME = "Khách Thử Hoàn Tất"
ADDRESS = "12 Lê Lợi, Vũng Tàu"
BR_GH_24_MESSAGE = "Đơn đã huỷ — mang hàng về kho."


def status_url(note):
    return f"/api/delivery/notes/{note.pk}/status/"


class CompletionBase(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.courier, self.manager, self.owner = self.giao, self.ql, self.chu  # naming: allow - thuộc tính fixture cũ của OrderApiBase
        self.other_courier = make_user("giao2", roles.DELIVERY_STAFF)

    def _order(self, phone=PHONE, qty="2", name=NAME):
        return super()._order(phone=phone, qty=qty, name=name)

    def _processing(self, courier=None, to=S.DELIVERING):
        """Đơn PROCESSING + phiếu gán cho `courier`, đã đẩy tới trạng thái `to`. Trả (order, note)."""
        self._txn_seq = getattr(self, "_txn_seq", 0) + 1
        order = self._paid_order(phone=PHONE, txn=f"FT26267{self._txn_seq:06d}")
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        confirm_note_for_test(note)
        note.assigned_to = courier or self.courier
        note.save(update_fields=["assigned_to"])
        for step in (S.READY, S.DELIVERING):
            services.advance_status(note=note, to_status=step, actor=self.courier)
            if step == to:
                break
        note.refresh_from_db()
        return order, note

    def _complete(self, user, note, **extra):
        body = {"to_status": S.COMPLETED, "from_status": S.DELIVERING}
        body.update(extra)
        return client_for(user).post(status_url(note), body, format="json")

    def _order_audits(self, order):
        return AuditLog.objects.filter(model_name="sales.SalesOrder", object_id=str(order.pk), action="complete_order")


class OrderCompletesOnDeliveryTests(CompletionBase):
    def test_s1_ac1_last_note_completed_completes_order(self):
        order, note = self._processing()
        resp = self._complete(self.courier, note)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], "COMPLETED")
        self.assertFalse(body["already"])
        self.assertEqual(body["order_status"], "COMPLETED")
        note.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(note.status, S.COMPLETED)
        self.assertIsNotNone(note.completed_at)
        self.assertEqual(order.status, SalesOrder.Status.COMPLETED)

    def test_s1_ac2_exactly_one_system_audit_without_personal_data(self):
        order, note = self._processing()
        note_audits_before = AuditLog.objects.filter(action="delivery_advance_status", object_id=str(note.pk)).count()
        self._complete(self.courier, note)
        audits = self._order_audits(order)
        self.assertEqual(audits.count(), 1)
        row = audits.get()
        self.assertIsNone(row.actor)
        self.assertEqual(row.actor_kind, "system")
        self.assertEqual(
            row.changes,
            {"status": {"from": "PROCESSING", "to": "COMPLETED"}, "delivery_note": note.code, "delivery_note_id": note.pk},
        )
        blob = json.dumps(row.changes, ensure_ascii=False) + row.note
        for secret in (PHONE, NAME, ADDRESS, "Lê Lợi"):
            self.assertNotIn(secret, blob)
        note_audits = AuditLog.objects.filter(action="delivery_advance_status", object_id=str(note.pk))
        self.assertEqual(note_audits.count(), note_audits_before + 1)
        self.assertEqual(note_audits.latest("id").actor, self.courier)

    def test_s1_ac3_no_documents_or_financial_numbers_change(self):
        order, note = self._processing()
        # Dựng hai kỳ: hoá đơn lùi về tháng trước.
        import datetime
        from django.utils import timezone
        order.invoice.issued_at = timezone.now() - datetime.timedelta(days=40)
        order.invoice.save(update_fields=["issued_at"])
        other = self._paid_order(phone="0900000124", txn="FT2626712399")
        order_services.cancel_paid_order(order=other, actor=self.manager, reason_code="CUSTOMER_CHANGED_MIND")
        self.assertTrue(SalesCreditNote.objects.exists())
        before = financial_snapshot(self.owner)
        self._complete(self.courier, note)
        after = financial_snapshot(self.owner)
        self.assertEqual(before, after)

    def test_s1_ac4_resend_is_idempotent(self):
        order, note = self._processing()
        self._complete(self.courier, note)
        note_audits = AuditLog.objects.filter(object_id=str(note.pk)).count()
        order_audits = self._order_audits(order).count()
        resp = self._complete(self.courier, note)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["already"])
        self.assertEqual(resp.json()["order_status"], "COMPLETED")
        self.assertEqual(AuditLog.objects.filter(object_id=str(note.pk)).count(), note_audits)
        self.assertEqual(self._order_audits(order).count(), order_audits)

    def test_s1_ac5_failure_keeps_order_processing(self):
        order, note = self._processing()
        resp = client_for(self.courier).post(
            status_url(note), {"to_status": "FAILED", "failure_reason": "NOT_MET"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "FAILED")
        self.assertEqual(resp.json()["order_status"], "PROCESSING")
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        self.assertFalse(self._order_audits(order).exists())

    def test_s1_ac6_redelivery_after_failure_completes_order(self):
        order, note = self._processing()
        services.mark_failed(note=note, actor=self.courier, reason="NOT_MET")
        services.advance_status(note=note, to_status=S.DELIVERING, actor=self.courier)
        resp = self._complete(self.courier, note)
        self.assertEqual(resp.status_code, 200, resp.content)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.COMPLETED)

    def test_s1_ac7_other_failed_note_keeps_order_processing(self):
        order, note = self._processing()
        second = services.create_delivery_note(invoice=order.invoice)
        DeliveryNote.objects.filter(pk=second.pk).update(status=S.FAILED)
        resp = self._complete(self.courier, note)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["order_status"], "PROCESSING")
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        self.assertFalse(self._order_audits(order).exists())

    def test_s1_ac8_cancelled_note_does_not_count(self):
        order, note = self._processing()
        done = services.create_delivery_note(invoice=order.invoice)
        cancelled = services.create_delivery_note(invoice=order.invoice)
        DeliveryNote.objects.filter(pk=done.pk).update(status=S.COMPLETED)
        DeliveryNote.objects.filter(pk=cancelled.pk).update(status=S.CANCELLED)
        self._complete(self.courier, note)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.COMPLETED)

    def test_s1_ac9_rollback_when_order_audit_fails(self):
        order, note = self._processing()
        audits_before = AuditLog.objects.count()
        real = __import__("apps.common.audit", fromlist=["record_audit"]).record_audit

        def boom(action, **kwargs):
            if action == "complete_order":
                raise RuntimeError("simulated failure")
            return real(action, **kwargs)

        client = client_for(self.courier)
        client.raise_request_exception = False
        with mock.patch("apps.sales.orders.completion.record_audit", side_effect=boom):
            resp = client.post(status_url(note), {"to_status": "COMPLETED", "from_status": "DELIVERING"}, format="json")
        self.assertGreaterEqual(resp.status_code, 400)
        note.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(note.status, S.DELIVERING)
        self.assertIsNone(note.completed_at)
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        self.assertEqual(AuditLog.objects.count(), audits_before)

    def test_s1_ac10_only_processing_order_moves(self):
        for status in (SalesOrder.Status.PAID, SalesOrder.Status.COMPLETED):
            with self.subTest(status=status):
                order, note = self._processing()
                SalesOrder.objects.filter(pk=order.pk).update(status=status)
                resp = self._complete(self.courier, note)
                self.assertEqual(resp.status_code, 200, resp.content)
                order.refresh_from_db()
                self.assertEqual(order.status, status)
                self.assertFalse(self._order_audits(order).exists())

    def test_s1_ac11_unassigned_courier_gets_404(self):
        order, note = self._processing()
        resp = self._complete(self.other_courier, note)
        self.assertEqual(resp.status_code, 404)
        note.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(note.status, S.DELIVERING)
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)

    def test_s1_ac12_no_direct_status_write_on_order(self):
        order, _ = self._processing()
        for user in (self.owner, self.manager, self.courier):
            for method in ("patch", "put"):
                with self.subTest(user=user.username, method=method):
                    resp = getattr(client_for(user), method)(
                        f"/api/sales/orders/{order.pk}/", {"status": "COMPLETED"}, format="json",
                    )
                    self.assertIn(resp.status_code, (403, 404, 405))
                    order.refresh_from_db()
                    self.assertEqual(order.status, SalesOrder.Status.PROCESSING)

    def test_s1_ac13_user_without_change_deliverynote_gets_403(self):
        # NV kho của repo này có change_deliverynote (đóng gói), nên dùng người chỉ có quyền xem phiếu.
        viewer = make_user("viewer1", perms=("delivery.view_deliverynote",))
        order, note = self._processing(courier=viewer)
        resp = self._complete(viewer, note)
        self.assertEqual(resp.status_code, 403, resp.content)
        note.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(note.status, S.DELIVERING)
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)

    def test_unauthenticated_gets_401(self):
        _, note = self._processing()
        resp = client_for(None).post(status_url(note), {"to_status": "COMPLETED"}, format="json")
        self.assertIn(resp.status_code, (401, 403))

    def test_order_status_present_on_every_branch(self):
        order, note = self._processing(to=S.READY)
        # READY -> DELIVERING
        resp = client_for(self.courier).post(status_url(note), {"to_status": "DELIVERING", "from_status": "READY"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["order_status"], "PROCESSING")
        # already (lặp)
        resp = client_for(self.courier).post(status_url(note), {"to_status": "DELIVERING", "from_status": "DELIVERING"}, format="json")
        self.assertTrue(resp.json()["already"])
        self.assertEqual(resp.json()["order_status"], "PROCESSING")
        # FAILED
        resp = client_for(self.courier).post(status_url(note), {"to_status": "FAILED", "failure_reason": "NOT_MET"}, format="json")
        self.assertEqual(resp.json()["order_status"], "PROCESSING")
        # READY ở bước đóng gói (chủ có quyền pack)
        order2, note2 = self._processing_to_ready_by_owner()
        self.assertIn("order_status", self._pack_response.json())
        self.assertEqual(self._pack_response.json()["order_status"], "PROCESSING")

    def _processing_to_ready_by_owner(self):
        order = self._paid_order(phone="0900000125", txn="FT2626712500")
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        confirm_note_for_test(note)
        self._pack_response = client_for(self.owner).post(
            status_url(note), {"to_status": "READY", "from_status": "PREPARING"}, format="json",
        )
        self.assertEqual(self._pack_response.status_code, 200, self._pack_response.content)
        return order, note

    def test_order_status_is_read_fresh_from_database(self):
        order, note = self._processing()
        resp = self._complete(self.courier, note)
        self.assertEqual(resp.json()["order_status"], SalesOrder.objects.get(pk=order.pk).status)

    def test_response_keys_have_no_personal_data(self):
        order, note = self._processing()
        body = self._complete(self.courier, note).json()
        self.assertEqual(body["order_status"], "COMPLETED")
        blob = json.dumps(body, ensure_ascii=False)
        self.assertNotIn(PHONE, blob)


class CancelRaceDeterministicTests(CompletionBase):
    """S2: năm ca tất định thay cho đua thật trên SQLite. Đối tượng cũ trong bộ nhớ = bên đến sau thấy dữ liệu cũ."""

    def _count_audits(self):
        return AuditLog.objects.count()

    def test_s2_ac1_case1_cancel_wins_then_redelivery_gets_br_gh_24(self):
        order, note = self._processing()
        services.mark_failed(note=note, actor=self.courier, reason="NOT_MET")
        stale = DeliveryNote.objects.get(pk=note.pk)
        self.assertEqual(stale.status, S.FAILED)
        order_services.cancel_paid_order(order=order, actor=self.manager, reason_code="CUSTOMER_CHANGED_MIND")
        audits = self._count_audits()
        with self.assertRaises(BusinessError) as ctx:
            services.advance_status(note=stale, to_status=S.DELIVERING, actor=self.courier, from_status=S.FAILED)
        self.assertEqual(ctx.exception.code, "BR-GH-24")
        self.assertEqual(DeliveryNote.objects.get(pk=note.pk).status, S.CANCELLED)
        self.assertEqual(self._count_audits(), audits)

    def test_s2_ac1_case2_cancel_wins_then_complete_gets_br_gh_24(self):
        order, note = self._processing()
        stale = DeliveryNote.objects.get(pk=note.pk)
        self.assertEqual(stale.status, S.DELIVERING)
        services.mark_failed(note=note, actor=self.courier, reason="NOT_MET")
        order_services.cancel_paid_order(order=order, actor=self.manager, reason_code="CUSTOMER_CHANGED_MIND")
        audits = self._count_audits()
        with self.assertRaises(BusinessError) as ctx:
            services.advance_status(note=stale, to_status=S.COMPLETED, actor=self.courier, from_status=S.DELIVERING)
        self.assertEqual(ctx.exception.code, "BR-GH-24")
        self.assertEqual(str(ctx.exception), BR_GH_24_MESSAGE)
        self.assertEqual(DeliveryNote.objects.get(pk=note.pk).status, S.CANCELLED)
        self.assertEqual(SalesOrder.objects.get(pk=order.pk).status, SalesOrder.Status.CANCELLED)
        self.assertEqual(self._count_audits(), audits)

    def test_s2_ac4_case3_cancel_wins_then_failure_report_gets_br_gh_24(self):
        order, note = self._processing()
        stale = DeliveryNote.objects.get(pk=note.pk)
        services.mark_failed(note=note, actor=self.courier, reason="NOT_MET")
        order_services.cancel_paid_order(order=order, actor=self.manager, reason_code="CUSTOMER_CHANGED_MIND")
        audits = self._count_audits()
        with self.assertRaises(BusinessError) as ctx:
            services.mark_failed(note=stale, actor=self.courier, reason="NOT_MET")
        self.assertEqual(ctx.exception.code, "BR-GH-24")
        self.assertEqual(DeliveryNote.objects.get(pk=note.pk).status, S.CANCELLED)
        self.assertEqual(self._count_audits(), audits)

    def test_s2_ac3_case4_complete_wins_then_cancel_gets_br_gh_05(self):
        order, note = self._processing()
        stale_order = SalesOrder.objects.get(pk=order.pk)
        self.assertEqual(stale_order.status, SalesOrder.Status.PROCESSING)
        self._complete(self.courier, note)
        movements = StockLedgerEntry.objects.count()
        with self.assertRaises(BusinessError) as ctx:
            order_services.cancel_paid_order(order=stale_order, actor=self.manager, reason_code="CUSTOMER_CHANGED_MIND")
        self.assertEqual(ctx.exception.code, "BR-GH-05")
        self.assertEqual(SalesCreditNote.objects.count(), 0)
        self.assertEqual(StockLedgerEntry.objects.count(), movements)
        self.assertFalse(StockLedgerEntry.objects.filter(movement_type=StockLedgerEntry.MovementType.CANCEL_RESTORE).exists())
        self.assertEqual(SalesOrder.objects.get(pk=order.pk).status, SalesOrder.Status.COMPLETED)

    def test_s2_ac1_case5_cancelled_order_with_uncancelled_old_note(self):
        order, note = self._processing()
        services.mark_failed(note=note, actor=self.courier, reason="NOT_MET")
        SalesOrder.objects.filter(pk=order.pk).update(status=SalesOrder.Status.CANCELLED)
        stale = DeliveryNote.objects.get(pk=note.pk)
        self.assertEqual(stale.status, S.FAILED)
        with self.assertRaises(BusinessError) as ctx:
            services.advance_status(note=stale, to_status=S.DELIVERING, actor=self.courier, from_status=S.FAILED)
        self.assertEqual(ctx.exception.code, "BR-GH-24")
        self.assertEqual(DeliveryNote.objects.get(pk=note.pk).status, S.FAILED)

    def test_s2_ac2_api_returns_400_br_gh_24_for_cancelled_order(self):
        order, note = self._processing()
        services.mark_failed(note=note, actor=self.courier, reason="NOT_MET")
        order_services.cancel_paid_order(order=order, actor=self.manager, reason_code="CUSTOMER_CHANGED_MIND")
        audits = self._count_audits()
        resp = self._complete(self.courier, note)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-GH-24")
        self.assertEqual(resp.json()["detail"], BR_GH_24_MESSAGE)
        self.assertEqual(resp.json()["current_status"], "CANCELLED")
        self.assertEqual(DeliveryNote.objects.get(pk=note.pk).status, S.CANCELLED)
        self.assertEqual(self._count_audits(), audits)
        # S2-AC4 qua API: báo thất bại cũng 400 BR-GH-24
        resp = client_for(self.courier).post(status_url(note), {"to_status": "FAILED", "failure_reason": "NOT_MET"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-GH-24")
        self.assertEqual(DeliveryNote.objects.get(pk=note.pk).status, S.CANCELLED)

    def test_s2_ac3_api_cancel_after_completion_returns_br_gh_05(self):
        order, note = self._processing()
        self._complete(self.courier, note)
        resp = client_for(self.manager).post(
            f"/api/sales/orders/{order.pk}/cancel/", {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-GH-05")
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.COMPLETED)
        self.assertEqual(SalesCreditNote.objects.count(), 0)

    def test_s2_ac6_courier_cannot_cancel_order(self):
        order, note = self._processing()
        services.mark_failed(note=note, actor=self.courier, reason="NOT_MET")
        resp = client_for(self.courier).post(
            f"/api/sales/orders/{order.pk}/cancel/", {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        self.assertEqual(DeliveryNote.objects.get(pk=note.pk).status, S.FAILED)


class LockOrderTests(CompletionBase):
    """R10: mọi đường đổi phiếu khoá SalesOrder rồi mới DeliveryNote."""

    def _lock_sequence(self, call):
        locked = []
        real = QuerySet.select_for_update

        def spy(qs, *args, **kwargs):
            locked.append(qs.model)
            return real(qs, *args, **kwargs)

        with mock.patch.object(QuerySet, "select_for_update", spy):
            call()
        return locked

    def _assert_order_before_note(self, locked):
        self.assertIn(SalesOrder, locked)
        self.assertIn(DeliveryNote, locked)
        self.assertLess(locked.index(SalesOrder), locked.index(DeliveryNote))

    def test_s2_ac5_advance_status_locks_order_before_note(self):
        _, note = self._processing()
        locked = self._lock_sequence(
            lambda: services.advance_status(note=note, to_status=S.COMPLETED, actor=self.courier, from_status=S.DELIVERING)
        )
        self._assert_order_before_note(locked)

    def test_s2_ac5_mark_failed_locks_order_before_note(self):
        _, note = self._processing()
        locked = self._lock_sequence(lambda: services.mark_failed(note=note, actor=self.courier, reason="NOT_MET"))
        self._assert_order_before_note(locked)

    def test_s2_ac5_cancel_paid_order_keeps_order_before_note(self):
        order, note = self._processing()
        services.mark_failed(note=note, actor=self.courier, reason="NOT_MET")
        locked = self._lock_sequence(
            lambda: order_services.cancel_paid_order(order=order, actor=self.manager, reason_code="CUSTOMER_CHANGED_MIND")
        )
        self._assert_order_before_note(locked)
