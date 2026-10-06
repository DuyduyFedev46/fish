"""
W37 S2-AC1 / S2-AC5: đua thật Huỷ đơn ∥ Giao xong, hai luồng, hai kết nối.
Chỉ chạy trên PostgreSQL (trên SQLite `select_for_update` không có tác dụng). Máy dev không có Postgres nên test này
bị `skip`; điều phối viên chốt T1 (b) ngày 07/10: chứng minh bằng test tất định + test thứ tự khoá, test này viết sẵn.
Chạy: DATABASE_URL=postgres://… manage.py test apps.delivery.tests.test_completion_race_postgres
(Django tạo DB `test_*` trên server, vì vậy KHÔNG trỏ vào staging hay production.)
"""
import threading
import time
from unittest import skipUnless

from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import confirm_note_for_test
from apps.delivery import services
from apps.delivery.models import DeliveryNote
from apps.sales.models import SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase

S = DeliveryNote.Status
ITERATIONS_PER_ORDER = 20
JOIN_TIMEOUT_SECONDS = 5


@skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL: select_for_update không có tác dụng trên SQLite.")
class CancelVersusCompleteRaceTests(TransactionTestCase):
    serialized_rollback = True  # giữ Group seed bởi migration sau mỗi test

    def setUp(self):
        OrderApiBase.setUp(self)
        self.courier, self.manager = self.giao, self.ql  # naming: allow - thuộc tính fixture cũ của OrderApiBase

    _order = OrderApiBase._order
    _paid_order = OrderApiBase._paid_order

    def _failed_note(self, index):
        order = self._paid_order(phone=f"09000{index:05d}", txn=f"FT26267{index:06d}")
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        confirm_note_for_test(note)
        note.assigned_to = self.courier
        note.save(update_fields=["assigned_to"])
        for step in (S.READY, S.DELIVERING):
            services.advance_status(note=note, to_status=step, actor=self.courier)
        services.mark_failed(note=note, actor=self.courier, reason="NOT_MET")
        return order, DeliveryNote.objects.get(pk=note.pk)

    def _run_once(self, index, cancel_first):
        order, note = self._failed_note(index)
        barrier = threading.Barrier(2)
        errors = []

        def cancel():
            try:
                barrier.wait(JOIN_TIMEOUT_SECONDS)
                if not cancel_first:
                    time.sleep(0.02)
                order_services.cancel_paid_order(order=order, actor=self.manager, reason_code="CUSTOMER_CHANGED_MIND")
            except BusinessError:
                pass
            except Exception as exc:  # noqa: BLE001 - deadlock hay lỗi bất ngờ đều là thất bại
                errors.append(exc)
            finally:
                close_old_connections()

        def deliver():
            try:
                barrier.wait(JOIN_TIMEOUT_SECONDS)
                if cancel_first:
                    time.sleep(0.02)
                stale = DeliveryNote.objects.get(pk=note.pk)
                services.advance_status(note=stale, to_status=S.DELIVERING, actor=self.courier, from_status=S.FAILED)
                stale = DeliveryNote.objects.get(pk=note.pk)
                services.advance_status(note=stale, to_status=S.COMPLETED, actor=self.courier, from_status=S.DELIVERING)
            except BusinessError:
                pass
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=cancel), threading.Thread(target=deliver)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(JOIN_TIMEOUT_SECONDS * 2)
            self.assertFalse(thread.is_alive(), "treo quá thời hạn (nghi deadlock)")
        self.assertEqual(errors, [])
        order.refresh_from_db()
        note.refresh_from_db()
        self.assertIn(
            (order.status, note.status),
            {
                (SalesOrder.Status.CANCELLED, S.CANCELLED),
                (SalesOrder.Status.COMPLETED, S.COMPLETED),
            },
        )

    def test_s2_ac1_cancel_holds_lock_first(self):
        for i in range(ITERATIONS_PER_ORDER):
            with self.subTest(i=i):
                self._run_once(i, cancel_first=True)

    def test_s2_ac1_delivery_holds_lock_first(self):
        for i in range(ITERATIONS_PER_ORDER):
            with self.subTest(i=i):
                self._run_once(1000 + i, cancel_first=False)
