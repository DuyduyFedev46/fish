"""FISH-66 S6-AC8: kiểm tranh chấp song song và thứ tự khoá khi commit_import (02b §5.3, §9). Dữ liệu giả."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import time
from unittest import skipUnless

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections, transaction
from django.test import TestCase, TransactionTestCase

from apps.accounts.models import AuditLog
from apps.catalog.item_files import services
from apps.catalog.item_files.columns import IMPORT_PERMS, columns_for
from apps.catalog.item_files.token import verify_preview_token_signature
from apps.catalog.item_files.workbook import build_items_workbook
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.audit import record_audit
from apps.common.exceptions import ConflictError
from apps.common.tests.postgres_race import PostgresRaceFixtureMixin
from apps.common.tests.fixtures import make_user


class CommitSequentialTests(TestCase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("u_owner", perms=IMPORT_PERMS)
        self.price_list = PriceList.objects.create(name="Bán lẻ", is_default=True)
        self.group = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=self.group)

    def test_sequential_two_different_previews_second_gets_import_data_changed(self):
        b1 = build_items_workbook(
            columns_for(with_prices=True),
            [{"code": "CA01", "name": "Cá thu A", "item_group": "Cá", "is_active": True, "new_price": 200000}],
        )
        b2 = build_items_workbook(
            columns_for(with_prices=True),
            [{"code": "CA01", "name": "Cá thu B", "item_group": "Cá", "is_active": True, "new_price": 210000}],
        )
        p1 = services.preview_import(user=self.owner, uploaded_file=SimpleUploadedFile("a.xlsx", b1))
        p2 = services.preview_import(user=self.owner, uploaded_file=SimpleUploadedFile("b.xlsx", b2))

        services.commit_import(
            user=self.owner,
            uploaded_file=SimpleUploadedFile("a.xlsx", b1),
            preview_token=p1["preview_token"],
        )
        with self.assertRaises(ConflictError) as ctx:
            services.commit_import(
                user=self.owner,
                uploaded_file=SimpleUploadedFile("b.xlsx", b2),
                preview_token=p2["preview_token"],
            )
        self.assertEqual(ctx.exception.code, "IMPORT_DATA_CHANGED")
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, "Cá thu A")


@skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL cho select_for_update song song thật")
class CommitConcurrentPgTests(PostgresRaceFixtureMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("u_owner", perms=IMPORT_PERMS)
        self.price_list = PriceList.objects.create(name="Bán lẻ", is_default=True)
        self.group = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=self.group)

    def test_concurrent_commits_of_same_preview_only_apply_once(self):
        content = build_items_workbook(
            columns_for(with_prices=True),
            [{"code": "MUC01", "name": "Mực mới", "item_group": "Cá", "is_active": True, "new_price": 150000}],
        )
        plan = services.preview_import(
            user=self.owner,
            uploaded_file=SimpleUploadedFile("race.xlsx", content),
        )
        token = plan["preview_token"]

        def _worker():
            try:
                return (
                    "ok",
                    services.commit_import(
                        user=self.owner,
                        uploaded_file=SimpleUploadedFile("race.xlsx", content),
                        preview_token=token,
                    ),
                )
            except ConflictError as exc:
                return ("conflict", exc.code)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_worker)
            f2 = pool.submit(_worker)
            results = [f1.result(), f2.result()]

        statuses = sorted(r[0] for r in results)
        self.assertEqual(statuses, ["conflict", "ok"])
        self.assertEqual(Item.objects.filter(code="MUC01").count(), 1)
        self.assertEqual(ItemPrice.objects.filter(item__code="MUC01").count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="import_items").count(), 1)

    def _wait_until_a_session_waits_for_lock(self, timeout=10.0):
        deadline = time.monotonic() + timeout
        with connection.cursor() as cur:
            while time.monotonic() < deadline:
                cur.execute(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()"
                )
                if cur.fetchone()[0] >= 1:
                    return True
                time.sleep(0.05)
        return False

    def test_td01_second_commit_waits_for_default_price_list_lock_then_gets_already_applied(self):
        """TD-01 (02b §13.3 L3): luồng chính giữ khoá bảng giá mặc định, luồng phụ phải CHỜ rồi nhận 409."""
        content = build_items_workbook(
            columns_for(with_prices=True),
            [{"code": "MUC01", "name": "Mực mới", "item_group": "Cá", "is_active": True, "new_price": 150000}],
        )
        plan = services.preview_import(user=self.owner, uploaded_file=SimpleUploadedFile("lock.xlsx", content))
        token = plan["preview_token"]
        import_ref = verify_preview_token_signature(token, user_id=self.owner.pk)["n"]

        def _second_commit():
            try:
                services.commit_import(
                    user=self.owner,
                    uploaded_file=SimpleUploadedFile("lock.xlsx", content),
                    preview_token=token,
                )
                return ("ok", None)
            except ConflictError as exc:
                return ("conflict", exc.code)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                PriceList.objects.select_for_update().filter(is_default=True).order_by("pk").first()
                future = pool.submit(_second_commit)
                self.assertTrue(self._wait_until_a_session_waits_for_lock(), "Luồng phụ không chờ khoá")
                with self.assertRaises(FutureTimeoutError):
                    future.result(timeout=0.5)  # luồng phụ chưa xong khi luồng chính còn giữ khoá
                self.assertFalse(future.done())
                record_audit(
                    "import_items",
                    actor=self.owner,
                    changes={
                        "import_ref": import_ref,
                        "rows": 1,
                        "created": 1,
                        "updated": 0,
                        "price_changed": 1,
                        "visibility_changed": 0,
                    },
                )
            result = future.result(timeout=30)

        self.assertEqual(result, ("conflict", "IMPORT_ALREADY_APPLIED"))
        self.assertEqual(AuditLog.objects.filter(action="import_items").count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="create_item").count(), 0)
        self.assertEqual(ItemPrice.objects.count(), 0)
        self.assertFalse(Item.objects.filter(code="MUC01").exists())
