"""
P8 Lô 7 — SR-22 / F08: `escalate_expired_windows` khoá phiếu giao (DeliveryNote) TRƯỚC việc gọi khách
(ConfirmationTask), đúng thứ tự khoá đơn -> phiếu -> task (02b CSKH §1.5). Dữ liệu giả.
"""
from datetime import timedelta
from unittest import mock

from django.db.models.query import QuerySet
from django.utils import timezone

from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.models import ConfirmationTask, DeliveryNote
from apps.delivery.tests import test_confirmation_escalation


class F08LockOrderTests(test_confirmation_escalation.ConfirmationL3BaseTestCase):
    def test_f08_escalate_expired_windows_khoa_phieu_truoc_task(self):
        t0 = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0)

        locked = []
        real = QuerySet.select_for_update

        def spy(qs, *args, **kwargs):
            locked.append(qs.model)
            return real(qs, *args, **kwargs)

        with mock.patch.object(QuerySet, "select_for_update", spy):
            n = confirmation_services.escalate_expired_windows(now=t0 + timedelta(minutes=31))

        self.assertEqual(n, 1)
        self.assertIn(DeliveryNote, locked)
        self.assertIn(ConfirmationTask, locked)
        self.assertLess(locked.index(DeliveryNote), locked.index(ConfirmationTask))
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)
