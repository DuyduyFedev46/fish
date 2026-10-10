"""
Lô 5: ngân sách truy vấn của hai danh sách đọc phạm vi ở Lô 4 (L1, review Lô 4, R8) và đua thật PV-10-AC5.

R8: phân giải phạm vi thêm tối đa 3 truy vấn cho một request danh sách, dù gọi nhiều lần (nhớ trên đối tượng user).
PV-10-AC5 chỉ chạy được trên PostgreSQL (trên SQLite `select_for_update` không có tác dụng); máy dev bỏ qua, như
`apps/delivery/tests/test_completion_race_postgres.py`. Chạy: DATABASE_URL=postgres://… manage.py test <module này>
(Django tạo DB `test_*`, KHÔNG trỏ vào staging hay production).
"""
import threading
from unittest import mock, skipUnless

from django.contrib.auth.models import Group, User
from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from apps.common.tests.postgres_race import PostgresRaceFixtureMixin
from apps.accounts import roles
from apps.accounts.capabilities.tests.base import detail_url, put_url
from apps.accounts.data_scopes import resolver

from .test_orders_invoices_scope import ScopeSceneBase


class ListQueryBudgetTests(ScopeSceneBase):
    def _count(self, label, url, patched=None):
        from django.db import connection as conn
        from django.test.utils import CaptureQueriesContext

        client = APIClient()
        client.force_authenticate(self.user(label))
        with CaptureQueriesContext(conn) as queries:
            self.assertEqual(client.get(url).status_code, 200)
        return len(queries)

    def _budget(self, label, url, extra_targets=()):
        real = resolver.resolve_data_scopes(self.user(label))  # giá trị thật, tính ngoài phép đo
        constant = dict(real)
        with_resolver = self._count(label, url)
        patches = [mock.patch("apps.accounts.data_scopes.resolver.resolve_data_scopes", return_value=constant)]
        patches += [mock.patch(target, return_value=constant) for target in extra_targets]
        for patch in patches:
            patch.start()
        try:
            baseline = self._count(label, url)
        finally:
            for patch in patches:
                patch.stop()
        self.assertLessEqual(with_resolver - baseline, 3, (label, url, with_resolver, baseline))

    def test_l1_delivery_note_list_adds_at_most_three_queries(self):
        for label in ("courier", "warehouse_staff"):
            self._budget(label, "/api/delivery/notes/")
            self._budget(label, "/api/delivery/notes/?assigned_to=me" if label == "courier" else "/api/delivery/notes/")

    def test_l1_confirmation_queue_adds_at_most_three_queries(self):
        for label in ("customer_service", "manager"):
            self._budget(
                label, "/api/confirmation/queue/", extra_targets=("apps.delivery.confirmation.scope.resolve_data_scopes",))
            self._budget(
                label, "/api/confirmation/queue/?state=DONE",
                extra_targets=("apps.delivery.confirmation.scope.resolve_data_scopes",))

    def test_l1_receipts_returns_customers_lists_add_at_most_three_queries(self):
        self._budget("warehouse_staff", "/api/purchasing/receipts/")
        self._budget("courier", "/api/inventory/returns/")
        self._budget("manager", "/api/sales/customer-directory/")


@skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL: select_for_update không có tác dụng trên SQLite.")
class ConcurrentSaveRaceTests(PostgresRaceFixtureMixin, TransactionTestCase):
    """PV-10-AC5: hai PUT cùng `version` chạy song song, đúng một 200 và một 409."""

    def setUp(self):
        self.owner = User.objects.create_user("race_owner", password="x")
        self.owner.groups.add(Group.objects.get(name=roles.OWNER))

    def _put(self, version, value, results, index):
        try:
            client = APIClient()
            client.force_authenticate(User.objects.get(pk=self.owner.pk))
            response = client.put(
                put_url(roles.WAREHOUSE_STAFF), {"version": version, "scopes": {"receipts": value}}, format="json")
            results[index] = response.status_code
        finally:
            connection.close()

    def test_pv10_ac5_two_parallel_saves_one_wins(self):
        client = APIClient()
        client.force_authenticate(self.owner)
        version = client.get(detail_url(roles.WAREHOUSE_STAFF)).json()["version"]
        results = [None, None]
        threads = [
            threading.Thread(target=self._put, args=(version, "created_by_me", results, 0)),
            threading.Thread(target=self._put, args=(version, "created_by_me_today", results, 1)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertEqual(sorted(results), [200, 409])
