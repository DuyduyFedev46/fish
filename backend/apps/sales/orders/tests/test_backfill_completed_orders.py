"""
W37 L4 (S3): lệnh `backfill_completed_orders` chuyển bù đơn cũ đã giao xong sang Hoàn tất.
BR-BH-18, BR-BH-21, BR-BC-06, BR-PQ-04/05/11, bất biến 9. Dữ liệu giả (SĐT 0900000xxx).
"""
import datetime
import json
from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.urls import get_resolver
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.delivery import services as delivery_services
from apps.delivery.models import DeliveryNote
from apps.delivery.tests.test_order_completion import ADDRESS, NAME, PHONE, CompletionBase
from apps.reports.tests.financial_snapshot import financial_snapshot
from apps.sales.models import SalesCreditNote, SalesOrder
from apps.sales.orders import completion
from apps.sales.orders import services as order_services

S = DeliveryNote.Status
COMMAND = "backfill_completed_orders"


class BackfillBase(CompletionBase):
    def _legacy(self, note_status=S.COMPLETED, order_status=SalesOrder.Status.PROCESSING):
        """Đơn kiểu dữ liệu cũ: phiếu đã ở `note_status` nhưng đơn chưa được chuyển (trước W37)."""
        order, note = self._processing()
        DeliveryNote.objects.filter(pk=note.pk).update(
            status=note_status,
            completed_at=timezone.now() if note_status == S.COMPLETED else None,
        )
        SalesOrder.objects.filter(pk=order.pk).update(status=order_status)
        order.refresh_from_db()
        note.refresh_from_db()
        return order, note

    def _run(self, *args):
        out, err = StringIO(), StringIO()
        call_command(COMMAND, *args, stdout=out, stderr=err)
        return out.getvalue()

    def _audits(self, order=None):
        qs = AuditLog.objects.filter(action=completion.COMPLETE_ORDER_ACTION)
        return qs.filter(object_id=str(order.pk)) if order is not None else qs

    def _status(self, order):
        return SalesOrder.objects.values_list("status", flat=True).get(pk=order.pk)


class BackfillRuleTests(BackfillBase):
    def _four_orders(self):
        x, _ = self._legacy()
        y, _ = self._legacy(note_status=S.FAILED)
        z, _ = self._legacy(note_status=S.CANCELLED, order_status=SalesOrder.Status.CANCELLED)
        w, _ = self._legacy(order_status=SalesOrder.Status.PAID)
        return x, y, z, w

    def test_s3_ac1_only_processing_with_completed_note_moves(self):
        x, y, z, w = self._four_orders()
        self._run()
        self.assertEqual(self._status(x), "COMPLETED")
        self.assertEqual(self._status(y), "PROCESSING")
        self.assertEqual(self._status(z), "CANCELLED")
        self.assertEqual(self._status(w), "PAID")

    def test_s3_ac2_one_system_audit_with_backfill_marker_and_no_personal_data(self):
        x, y, z, w = self._four_orders()
        note = DeliveryNote.objects.get(sales_invoice=x.invoice)
        self._run()
        self.assertEqual(self._audits().count(), 1)
        row = self._audits(x).get()
        self.assertIsNone(row.actor)
        self.assertEqual(row.actor_kind, "system")
        self.assertEqual(
            row.changes,
            {"status": {"from": "PROCESSING", "to": "COMPLETED"}, "delivery_note": note.code,
             "delivery_note_id": note.pk, "backfill": "W37"},
        )
        blob = json.dumps(row.changes, ensure_ascii=False) + row.note
        for secret in (PHONE, NAME, ADDRESS, "Lê Lợi"):
            self.assertNotIn(secret, blob)

    def test_s3_ac3_rerun_is_noop(self):
        x, *_ = self._four_orders()
        self._run()
        audits = AuditLog.objects.count()
        out = self._run()
        self.assertIn("Đã chuyển 0 đơn", out)
        self.assertEqual(AuditLog.objects.count(), audits)
        self.assertEqual(self._status(x), "COMPLETED")

    def test_s3_ac4_dry_run_lists_codes_and_writes_nothing(self):
        x, y, z, w = self._four_orders()
        audits = AuditLog.objects.count()
        out = self._run("--dry-run")
        self.assertIn("Sẽ chuyển 1 đơn", out)
        self.assertIn(x.code, out)
        for other in (y, z, w):
            self.assertNotIn(other.code, out)
        self.assertEqual(self._status(x), "PROCESSING")
        self.assertEqual(AuditLog.objects.count(), audits)

    def test_r4_output_has_no_personal_data(self):
        self._four_orders()
        for args in (("--dry-run",), ()):
            out = self._run(*args)
            for secret in (PHONE, NAME, ADDRESS, "Lê Lợi", "Vũng Tàu"):
                self.assertNotIn(secret, out)

    def test_s3_ac6_other_open_note_keeps_order_processing(self):
        order, _ = self._legacy()
        second = delivery_services.create_delivery_note(invoice=order.invoice)
        DeliveryNote.objects.filter(pk=second.pk).update(status=S.DELIVERING)
        self._run()
        self.assertEqual(self._status(order), "PROCESSING")
        self.assertFalse(self._audits(order).exists())

    def test_cancelled_extra_note_does_not_block(self):
        order, _ = self._legacy()
        extra = delivery_services.create_delivery_note(invoice=order.invoice)
        DeliveryNote.objects.filter(pk=extra.pk).update(status=S.CANCELLED)
        self._run()
        self.assertEqual(self._status(order), "COMPLETED")

    def test_trigger_note_is_latest_completed_note(self):
        order, first = self._legacy()
        later = delivery_services.create_delivery_note(invoice=order.invoice)
        DeliveryNote.objects.filter(pk=later.pk).update(
            status=S.COMPLETED, completed_at=timezone.now() + datetime.timedelta(hours=1),
        )
        self._run()
        self.assertEqual(self._audits(order).get().changes["delivery_note_id"], later.pk)


class BackfillFailureTests(BackfillBase):
    def test_s3_ac7_error_in_second_order_stops_with_nonzero_exit_and_rerun_finishes(self):
        orders = [self._legacy()[0] for _ in range(3)]
        real = completion.complete_order_if_delivered
        calls = {"n": 0}

        def flaky(**kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("simulated failure")
            return real(**kwargs)

        with mock.patch(
            "apps.sales.management.commands.backfill_completed_orders.complete_order_if_delivered", side_effect=flaky,
        ):
            out = StringIO()
            with self.assertRaises(CommandError) as ctx:
                call_command(COMMAND, stdout=out, stderr=StringIO())
        self.assertIn(orders[1].code, str(ctx.exception))
        self.assertEqual([self._status(o) for o in orders], ["COMPLETED", "PROCESSING", "PROCESSING"])
        self.assertEqual(self._audits().count(), 1)
        for secret in (PHONE, NAME, ADDRESS):
            self.assertNotIn(secret, str(ctx.exception) + out.getvalue())

        out = self._run()
        self.assertIn("Đã chuyển 2 đơn", out)
        self.assertEqual([self._status(o) for o in orders], ["COMPLETED"] * 3)
        self.assertEqual(self._audits().count(), 3)

    def test_audit_failure_rolls_back_that_order_only(self):
        order, _ = self._legacy()
        with mock.patch("apps.sales.orders.completion.record_audit", side_effect=RuntimeError("boom")):
            with self.assertRaises(CommandError):
                call_command(COMMAND, stdout=StringIO(), stderr=StringIO())
        self.assertEqual(self._status(order), "PROCESSING")


class BackfillFinancialAndAccessTests(BackfillBase):
    def test_s3_ac5_r1_financial_snapshot_unchanged_across_two_periods(self):
        order, _ = self._legacy()
        order.invoice.issued_at = timezone.now() - datetime.timedelta(days=40)  # tháng trước
        order.invoice.save(update_fields=["issued_at"])
        other = self._paid_order(phone="0900000124", txn="FT2626799999")
        order_services.cancel_paid_order(order=other, actor=self.manager, reason_code="CUSTOMER_CHANGED_MIND")
        self.assertTrue(SalesCreditNote.objects.exists())
        before = financial_snapshot(self.owner)
        self._run()
        after = financial_snapshot(self.owner)
        self.assertEqual(self._status(order), "COMPLETED")
        self.assertEqual(before, after)

    def test_s3_ac8_no_http_route_for_backfill(self):
        def walk(patterns, prefix=""):
            for p in patterns:
                text = prefix + str(p.pattern)
                if hasattr(p, "url_patterns"):
                    yield from walk(p.url_patterns, text)
                else:
                    yield text

        routes = list(walk(get_resolver().url_patterns))
        self.assertTrue(routes)
        for route in routes:
            self.assertNotIn("backfill", route)
        self.assertNotIn("backfill", " ".join(routes))

    def test_s3_ac8_roles_get_404_or_405_on_guessed_urls(self):
        for user in (self.owner, self.manager, self.courier):
            for path in ("/api/sales/orders/backfill/", "/api/sales/orders/backfill_completed_orders/"):
                resp = client_for(user).post(path)
                self.assertIn(resp.status_code, (404, 405))
