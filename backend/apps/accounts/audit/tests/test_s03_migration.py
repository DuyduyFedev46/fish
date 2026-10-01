"""
S03 — migration 0007 (accounts): thêm actor_kind/ai_actor/proposal_ref + backfill.

S03-AC1 (bất biến 8): dòng AuditLog cũ giữ nguyên giá trị, actor_kind backfill đúng
(actor null → system, còn lại → user). Chạy bằng MigrationExecutor để chứng minh
dữ liệu cũ không mất sau khi migrate thật.
"""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class AuditLogMigrationTests(TransactionTestCase):
    migrate_from = [("accounts", "0006_grant_change_item_image")]
    migrate_to = [("accounts", "0007_auditlog_ai_actor")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        # Các app khác giữ bản mới nhất; riêng accounts lùi về trạng thái TRƯỚC khi có 3 field mới
        # để tạo dữ liệu "kiểu cũ". Loại cả `ai` (P8b Lô 4: `ai/0003` phụ thuộc `accounts/0013`, nếu để
        # nó ở đích thì accounts bị kéo tới 0013 chứ không lùi về 0006). Loại cả `delivery` (Lô 4:
        # `delivery/0006` cấp quyền cho Group tên tiếng Anh nên phụ thuộc `accounts/0013`, cùng lý do). Loại cả
        # `sales` (Lô 6: `sales/0013` cấp quyền Xem khách hàng cho Group tên tiếng Anh, cùng lý do).
        targets = [
            t for t in executor.loader.graph.leaf_nodes() if t[0] not in ("accounts", "ai", "delivery", "sales")
        ] + self.migrate_from
        executor.migrate(targets)
        self.old_apps = executor.loader.project_state(targets).apps

        User = self.old_apps.get_model("auth", "User")
        AuditLog = self.old_apps.get_model("accounts", "AuditLog")
        self.user = User.objects.create(username="cu1")
        AuditLog.objects.create(actor=self.user, action="close_batch", note="dòng người")
        AuditLog.objects.create(actor=None, action="cancel_expired_orders", note="dòng hệ thống")

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.migrate_to)
        self.new_apps = executor.loader.project_state(self.migrate_to).apps

    def test_s03_ac1_backfill_actor_kind_khong_mat_du_lieu_cu(self):
        AuditLog = self.new_apps.get_model("accounts", "AuditLog")
        rows = {r.action: r for r in AuditLog.objects.all()}
        self.assertEqual(len(rows), 2, "dữ liệu cũ bị mất sau migration")
        user_row = rows["close_batch"]
        self.assertEqual(user_row.actor_kind, "user")
        self.assertEqual(user_row.actor_id, self.user.id)
        self.assertEqual(user_row.note, "dòng người")
        self.assertEqual(rows["cancel_expired_orders"].actor_kind, "system")
