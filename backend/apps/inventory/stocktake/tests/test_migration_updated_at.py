"""
Migration inventory/0005 — thêm `StockReconciliation.updated_at` (B1, 02b §3.9).

Chỉ thêm, không mất dữ liệu cũ; phiếu cũ được điền `updated_at = created_at`; lùi về 0004 rồi tiến lại được.
Chỉ lùi/tiến app `inventory` (không đụng app khác).
"""
import datetime

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [("inventory", "0004_batchsupplierreturn")]
AFTER = [("inventory", "0005_stockreconciliation_updated_at")]


class UpdatedAtMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        self.migrate(AFTER)  # trả DB test về trạng thái mới nhất
        super().tearDown()

    def test_backfill_keeps_old_rows_and_reverse_forward_roundtrip(self):
        old_apps = self.migrate(BEFORE)
        User = old_apps.get_model("auth", "User")
        Reconciliation = old_apps.get_model("inventory", "StockReconciliation")
        user = User.objects.create(username="cu_kiemke")
        old = Reconciliation.objects.create(count_date=datetime.date(2026, 9, 1), created_by=user, note="phiếu cũ")
        self.assertFalse(hasattr(old, "updated_at"))

        new_apps = self.migrate(AFTER)
        Reconciliation = new_apps.get_model("inventory", "StockReconciliation")
        row = Reconciliation.objects.get(pk=old.pk)
        self.assertEqual(row.note, "phiếu cũ")
        self.assertEqual(row.updated_at, row.created_at)

        # Lùi lần nữa rồi tiến lại: dữ liệu vẫn còn.
        self.migrate(BEFORE)
        new_apps = self.migrate(AFTER)
        self.assertEqual(new_apps.get_model("inventory", "StockReconciliation").objects.filter(pk=old.pk).count(), 1)
