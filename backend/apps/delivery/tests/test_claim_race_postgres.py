"""
B1 (QA 08/10): hai người nhận cùng một việc gọi xác nhận cùng lúc -> đúng một người giữ, người còn lại 409 CLAIMED
(CS-05-AC3, CS-05-AC4), không bao giờ 500 AttributeError.
Gốc lỗi: `select_for_update(of=("self",)).select_related("claimed_by")`; sau khi chờ khoá, Postgres (READ COMMITTED)
không nạp lại phía nối ngoài nên `task.claimed_by` thành None dù `claimed_by_id` đã có.
Chỉ chạy trên PostgreSQL. Dữ liệu giả.
"""
import threading
import time
from datetime import timedelta
from unittest import skipUnless

from django.db import connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts import roles
from apps.common.exceptions import ConflictError
from apps.common.tests.fixtures import make_confirming_note, make_user
from apps.delivery.confirmation import services
from apps.delivery.models import ConfirmationTask

JOIN_TIMEOUT_SECONDS = 10
ROUNDS = 15


@skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL: select_for_update không có tác dụng trên SQLite.")
class ClaimRaceTests(TransactionTestCase):
    serialized_rollback = True

    def _fixture_setup(self):
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.all().delete()
        super()._fixture_setup()
        ContentType.objects.clear_cache()

    def setUp(self):
        self.cs1 = make_user("race_cs1", roles.CUSTOMER_SERVICE)
        self.cs2 = make_user("race_cs2", roles.CUSTOMER_SERVICE)

    def _task(self, index):
        _order, _customer, note = make_confirming_note(f"RC{index:04d}", f"09100{index:05d}")
        return ConfirmationTask.objects.get(note=note)

    def test_b1_waiter_sees_holder_after_lock_wait_is_409_not_500(self):
        """Người đến sau chờ khoá; khi người trước commit thì nhận 409 CLAIMED có tên người giữ."""
        for i in range(ROUNDS):
            with self.subTest(i=i):
                task = self._task(i)
                result = {}

                def waiter():
                    try:
                        services.claim_task(task.pk, self.cs2)
                        result["outcome"] = "ok"
                    except ConflictError as exc:
                        result["outcome"] = exc.code
                    except Exception as exc:  # noqa: BLE001
                        result["outcome"] = f"ERROR {type(exc).__name__}"
                    finally:
                        connection.close()

                thread = threading.Thread(target=waiter)
                with transaction.atomic():
                    locked = ConfirmationTask.objects.select_for_update().get(pk=task.pk)
                    locked.claimed_by = self.cs1
                    locked.claimed_until = timezone.now() + timedelta(minutes=5)
                    locked.save(update_fields=["claimed_by", "claimed_until"])
                    thread.start()
                    time.sleep(0.4)  # để luồng kia chắc chắn đang chờ khoá
                thread.join(JOIN_TIMEOUT_SECONDS)
                self.assertFalse(thread.is_alive(), "treo quá thời hạn (nghi deadlock)")
                self.assertEqual(result["outcome"], "CLAIMED")
                self.assertEqual(ConfirmationTask.objects.get(pk=task.pk).claimed_by_id, self.cs1.pk)

    def test_b1_two_claims_at_once_exactly_one_wins(self):
        for i in range(ROUNDS):
            with self.subTest(i=i):
                task = self._task(100 + i)
                barrier = threading.Barrier(2)
                outcomes = []

                def claim(user):
                    try:
                        barrier.wait(JOIN_TIMEOUT_SECONDS)
                        services.claim_task(task.pk, user)
                        outcomes.append("ok")
                    except ConflictError as exc:
                        outcomes.append(exc.code)
                    except Exception as exc:  # noqa: BLE001
                        outcomes.append(f"ERROR {type(exc).__name__}")
                    finally:
                        connection.close()

                threads = [threading.Thread(target=claim, args=(u,)) for u in (self.cs1, self.cs2)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(JOIN_TIMEOUT_SECONDS)
                    self.assertFalse(t.is_alive(), "treo quá thời hạn (nghi deadlock)")
                self.assertEqual(sorted(outcomes), ["CLAIMED", "ok"])
