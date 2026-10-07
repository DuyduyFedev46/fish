"""
`manage.py seed_qa` — bộ dữ liệu giả cố định cho e2e (lô dọn e2e, Duy duyệt 08/10).

Kiểm: idempotent (chạy hai lần không nhân đôi, cùng bảng mã → id); cổng chặn (DEBUG tắt, DB giống production
không cờ nào mở được); không dữ liệu thật (SĐT 09000000nn, tên/địa chỉ giả, không in ra màn hình, không đụng
dữ liệu khác khi --reset); bộ dữ liệu phủ đủ trạng thái các e2e cần.
"""
import json
import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.accounts.models import AuditLog
from apps.accounts.qa_fixture import guard
from apps.accounts.qa_fixture.build import USERS
from apps.catalog.models import Item, ItemGroup
from apps.delivery.models import CallScript, ConfirmationTask, DeliveryNote
from apps.common.audit import record_audit
from apps.inventory.models import Batch, ReturnToStock, StockLedgerEntry, StockReconciliation, Warehouse
from apps.purchasing.models import PurchaseReceipt
from django.db.models import Sum

from apps.sales.models import Customer, PaymentTransaction, Refund, SalesInvoice, SalesOrder

PASSWORD = "Qa-Test-Pass-1"
User = get_user_model()


class SeedQaBase(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.manifest_path = Path(tmp.name) / "ids.json"
        env = mock.patch.dict(os.environ, {"QA_PASSWORD": PASSWORD})
        env.start()
        self.addCleanup(env.stop)

    def run_seed(self, *args):
        out = StringIO()
        with override_settings(DEBUG=True):
            call_command("seed_qa", "--manifest", str(self.manifest_path), *args, stdout=out)
        return out.getvalue()

    def manifest(self):
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))


def counts():
    return {
        "orders": SalesOrder.objects.count(), "notes": DeliveryNote.objects.count(),
        "payments": PaymentTransaction.objects.count(), "refunds": Refund.objects.count(),
        "batches": Batch.objects.count(), "users": User.objects.count(),
        "customers": Customer.objects.count(), "items": Item.objects.count(),
        "audit": AuditLog.objects.count(), "returns": ReturnToStock.all_objects.count(),
        "receipts": PurchaseReceipt.objects.count(), "scripts": CallScript.objects.count(),
    }


class SeedQaIdempotentTests(SeedQaBase):
    def test_running_twice_does_not_duplicate_and_ids_are_stable(self):
        self.run_seed()
        first_counts, first_manifest = counts(), self.manifest()
        self.run_seed()
        self.assertEqual(counts(), first_counts)
        self.assertEqual(self.manifest(), first_manifest)

    def test_manifest_maps_codes_to_real_ids(self):
        self.run_seed()
        manifest = self.manifest()
        for code, info in manifest["orders"].items():
            self.assertTrue(code.startswith("QA-"))
            self.assertEqual(SalesOrder.objects.get(code=code).pk, info["id"])
        for code, info in manifest["delivery_notes"].items():
            self.assertEqual(DeliveryNote.objects.get(code=code).pk, info["id"])
        for username, pk in manifest["users"].items():
            self.assertEqual(User.objects.get(username=username).pk, pk)
        self.assertEqual(manifest["password_env"], "QA_PASSWORD")


class SeedQaGuardTests(SeedQaBase):
    def test_refuses_when_debug_is_off_and_creates_nothing(self):
        before = counts()
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError) as ctx:
                call_command("seed_qa", "--manifest", str(self.manifest_path), stdout=StringIO())
        self.assertIn("DEBUG", str(ctx.exception))
        self.assertEqual(counts(), before)
        self.assertFalse(self.manifest_path.exists())

    def test_reset_is_also_guarded(self):
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command("seed_qa", "--reset", stdout=StringIO())

    def test_explicit_flag_allows_debug_off_on_sqlite(self):
        with override_settings(DEBUG=False):
            call_command("seed_qa", "--allow-non-local", "--manifest", str(self.manifest_path),
                         stdout=StringIO())
        self.assertTrue(SalesOrder.objects.filter(code="QA-SO-01").exists())

    def _facts(self, name, host="", sqlite=False):
        return mock.patch.object(guard, "database_facts",
                                 return_value={"is_sqlite": sqlite, "name": name, "host": host})

    def test_production_like_database_is_always_refused_even_with_flag(self):
        for name, host in (("postgres", "db.supabase.co"), ("cangca_prod", ""), ("app", "prod-db.internal")):
            with self._facts(name, host), override_settings(DEBUG=True):
                for flags in ((), ("--allow-non-local",)):
                    with self.assertRaises(CommandError, msg=f"{name}/{host}/{flags}") as ctx:
                        call_command("seed_qa", *flags, "--manifest", str(self.manifest_path),
                                     stdout=StringIO())
                    self.assertIn("production", str(ctx.exception))
        self.assertEqual(SalesOrder.objects.count(), 0)

    def test_sepay_production_is_always_refused_even_with_flag(self):
        for flags in ((), ("--allow-non-local",)):
            with override_settings(DEBUG=True, SEPAY_ENV="PRODUCTION"):
                with self.assertRaises(CommandError) as ctx:
                    call_command("seed_qa", *flags, "--manifest", str(self.manifest_path), stdout=StringIO())
            self.assertIn("SEPAY_ENV", str(ctx.exception))
        self.assertEqual(SalesOrder.objects.count(), 0)

    def test_staging_database_is_allowed_with_debug_on(self):
        with self._facts("cangca_staging", "db.supabase.co"):
            self.run_seed()
        self.assertTrue(SalesOrder.objects.filter(code="QA-SO-01").exists())

    def test_non_staging_postgres_needs_flag(self):
        with self._facts("cangca_dev", "localhost"), override_settings(DEBUG=True):
            with self.assertRaises(CommandError):
                call_command("seed_qa", "--manifest", str(self.manifest_path), stdout=StringIO())
            call_command("seed_qa", "--allow-non-local", "--manifest", str(self.manifest_path),
                         stdout=StringIO())
        self.assertTrue(SalesOrder.objects.filter(code="QA-SO-01").exists())

    def test_password_env_is_required(self):
        with mock.patch.dict(os.environ, {"QA_PASSWORD": ""}):
            with self.assertRaises(CommandError) as ctx:
                self.run_seed()
        self.assertIn("QA_PASSWORD", str(ctx.exception))
        self.assertEqual(User.objects.filter(username__startswith="qa_").count(), 0)


class SeedQaNoRealDataTests(SeedQaBase):
    def test_all_personal_data_is_fake_and_not_printed(self):
        output = self.run_seed()
        for customer in Customer.objects.all():
            self.assertTrue(customer.phone.startswith("09000000"), customer.phone)
            self.assertIn("QA", customer.name)
            self.assertIn("QA-", customer.default_address)
        for order in SalesOrder.objects.all():
            self.assertTrue(order.code.startswith("QA-"))
            self.assertTrue(order.phone.startswith("09000000"))
            self.assertIn("QA-", order.delivery_address)
        for username in User.objects.values_list("username", flat=True):
            self.assertTrue(username.startswith("qa_"))
        phones = list(Customer.objects.values_list("phone", flat=True))
        self.assertTrue(phones)
        for phone in phones:
            self.assertNotIn(phone, output)
        self.assertNotIn(PASSWORD, output)
        self.assertNotIn(PASSWORD, self.manifest_path.read_text(encoding="utf-8"))
        self.assertNotIn("Địa chỉ", output)

    def test_no_personal_data_in_audit_log(self):
        self.run_seed()
        phones = list(Customer.objects.values_list("phone", flat=True))
        for log in AuditLog.objects.all():
            text = f"{log.note} {log.changes} {log.object_repr}"
            for phone in phones:
                self.assertNotIn(phone, text)
            self.assertNotIn("Địa chỉ giả", text)

    def test_reset_removes_only_qa_records(self):
        real_group = ItemGroup.objects.create(name="Nhóm thật thử")
        real_item = Item.objects.create(code="CA-THAT", name="Cá thật thử", item_group=real_group)
        # Khách có SĐT cùng tiền tố 09000000 nhưng không thuộc 20 khách QA (M1.1).
        real_customer = Customer.objects.create(phone="0900000050", name="Khách thử khác")
        real_user = User.objects.create_user("kho_thu", password="x")
        real_warehouse = Warehouse.objects.create(name="Kho thật thử")
        self.run_seed()
        self.assertTrue(self.manifest_path.exists())
        qa_owner = User.objects.get(username="qa_owner")
        # M1.2: Nhật ký do qa_owner làm trên mặt hàng KHÔNG phải QA.
        real_log = record_audit("update_item", actor=qa_owner, obj=real_item, changes={"name": "x"})
        # M1.3: phiếu hoàn tiền do qa_owner lập trên đơn KHÔNG phải QA.
        real_order = SalesOrder.objects.create(
            code="SO-THAT-1", customer=real_customer, status=SalesOrder.Status.PROCESSING,
            delivery_address="Địa chỉ thử", phone=real_customer.phone, total_amount=1000)
        real_invoice = SalesInvoice.objects.create(
            code="HD-THAT-1", sales_order=real_order, customer=real_customer,
            issued_at=real_order.created_at, amount=1000)
        real_refund = Refund.objects.create(sales_invoice=real_invoice, amount=1000, created_by=qa_owner,
                                            reason="thật")
        output = self.run_seed("--reset")
        self.assertFalse(self.manifest_path.exists())
        self.assertEqual(SalesOrder.objects.filter(code__startswith="QA-").count(), 0)
        self.assertEqual(DeliveryNote.objects.filter(code__startswith="QA-").count(), 0)
        self.assertEqual(Batch.objects.count(), 0)
        self.assertEqual(Customer.objects.filter(name__startswith="Khách QA Giả").count(), 0)
        self.assertEqual(Item.objects.filter(code__startswith="QA-").count(), 0)
        self.assertFalse(AuditLog.objects.filter(note__startswith="QA-audit-").exists())
        self.assertFalse(AuditLog.objects.filter(object_repr__startswith="QA-").exists())
        for obj in (real_item, real_customer, real_user, real_warehouse, real_log, real_order,
                    real_invoice, real_refund):
            self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists(), obj)
        # qa_owner còn bị dữ liệu ngoài QA tham chiếu: giữ, vô hiệu hoá, báo trong kết quả.
        qa_owner.refresh_from_db()
        self.assertFalse(qa_owner.is_active)
        self.assertIn("qa_owner", output)
        # Các tài khoản qa_ khác không bị tham chiếu thì đã xoá.
        self.assertEqual(set(User.objects.filter(username__startswith="qa_").values_list("username", flat=True)),
                         {"qa_owner"})

    def test_reset_result_reports_kept_users(self):
        from apps.accounts.qa_fixture.reset import reset_qa
        self.run_seed()
        item = Item.objects.get(code="QA-CA")
        Item.objects.create(code="CA-THAT2", name="x", item_group=item.item_group)
        owner = User.objects.get(username="qa_owner")
        record_audit("update_item", actor=owner, obj=Item.objects.get(code="CA-THAT2"))
        with override_settings(DEBUG=True):
            result = reset_qa()
        self.assertIn("User:qa_owner", result["kept"])

    def test_seed_after_reset_restores_the_same_codes(self):
        self.run_seed()
        codes = set(self.manifest()["orders"])
        self.run_seed("--reset")
        self.run_seed()
        self.assertEqual(set(self.manifest()["orders"]), codes)


class SeedQaCoverageTests(SeedQaBase):
    def setUp(self):
        super().setUp()
        self.run_seed()

    def test_users_cover_five_roles_combinations_and_superuser(self):
        groups = {u.username: set(u.groups.values_list("name", flat=True)) for u in User.objects.all()}
        self.assertEqual(groups["qa_owner"], {"owner"})
        self.assertEqual(groups["qa_manager"], {"manager"})
        self.assertEqual(groups["qa_warehouse"], {"warehouse_staff"})
        self.assertEqual(groups["qa_courier1"], {"delivery_staff"})
        self.assertEqual(groups["qa_courier2"], {"delivery_staff"})
        self.assertEqual(groups["qa_cs1"], {"customer_service"})
        self.assertEqual(groups["qa_warehouse_courier"], {"warehouse_staff", "delivery_staff"})
        self.assertEqual(groups["qa_warehouse_cs"], {"warehouse_staff", "customer_service"})
        self.assertEqual(groups["qa_nogroup"], set())
        self.assertTrue(User.objects.get(username="qa_superuser").is_superuser)
        self.assertEqual(len(groups), len(USERS))

    def test_password_comes_from_env_for_every_user(self):
        for user in User.objects.all():
            self.assertTrue(user.check_password(PASSWORD), user.username)

    def test_every_order_status_exists(self):
        statuses = set(SalesOrder.objects.values_list("status", flat=True))
        self.assertEqual(statuses, {s.value for s in SalesOrder.Status})
        cancelled = SalesOrder.objects.filter(status=SalesOrder.Status.CANCELLED)
        self.assertEqual(cancelled.count(), 2)
        for order in cancelled:
            self.assertTrue(order.cancel_note)

    def test_order_with_top_up_payment_is_completed(self):
        order = SalesOrder.objects.get(code="QA-SO-12")
        self.assertEqual(order.status, SalesOrder.Status.COMPLETED)
        self.assertEqual(order.payments.count(), 2)

    def test_every_delivery_status_exists_and_cancelled_notes_have_both_couriers(self):
        statuses = set(DeliveryNote.objects.values_list("status", flat=True))
        self.assertEqual(statuses, {s.value for s in DeliveryNote.Status})
        failed = DeliveryNote.objects.get(status=DeliveryNote.Status.FAILED)
        self.assertEqual(failed.assigned_to.username, "qa_courier2")
        self.assertTrue(failed.failure_reason)
        cancelled = {n.assigned_to.username for n in DeliveryNote.objects.filter(
            status=DeliveryNote.Status.CANCELLED)}
        self.assertEqual(cancelled, {"qa_courier1", "qa_courier2"})

    def test_confirmation_tasks_cover_pending_callback_escalated_refund_call(self):
        states = set(ConfirmationTask.objects.values_list("state", flat=True))
        self.assertTrue({"PENDING", "CALLBACK", "ESCALATED", "REFUND_CALL", "DONE"} <= states)

    def test_refunds_cover_pending_refunded_failed(self):
        self.assertEqual(set(Refund.objects.values_list("status", flat=True)),
                         {"PENDING", "REFUNDED", "FAILED"})

    def test_returns_cover_draft_approved_cancelled(self):
        self.assertEqual(set(ReturnToStock.all_objects.values_list("status", flat=True)),
                         {"DRAFT", "APPROVED", "CANCELLED"})

    def test_receipts_stocktake_batches_and_scripts(self):
        self.assertEqual(set(PurchaseReceipt.objects.values_list("status", flat=True)),
                         {"DRAFT", "SUBMITTED", "CANCELLED"})
        self.assertTrue(StockReconciliation.objects.filter(status="DRAFT").exists())
        batch_statuses = set(Batch.objects.values_list("status", flat=True))
        self.assertTrue({"NEAR_EXPIRY", "EXPIRED", "SELLING", "DRAFT", "CLOSED"} <= batch_statuses)
        self.assertEqual(CallScript.objects.count(), len(CallScript.Situation.values))

    def test_payments_have_orphan_unmatched_manual_and_duplicate_warning(self):
        by_match = {p.match_status for p in PaymentTransaction.objects.all()}
        self.assertTrue({"MATCHED", "UNDERPAID", "ORPHAN", "UNMATCHED", "OVERPAID"} <= by_match)
        self.assertTrue(PaymentTransaction.objects.filter(source="MANUAL").exists())
        for match in ("ORPHAN", "UNMATCHED", "OVERPAID"):
            self.assertTrue(PaymentTransaction.objects.filter(
                match_status=match).exclude(duplicate_warning="").exists(), match)

    def test_audit_log_has_user_system_and_ai_entries(self):
        kinds = set(AuditLog.objects.values_list("actor_kind", flat=True))
        self.assertEqual(kinds, {"user", "system", "ai"})
        self.assertGreaterEqual(AuditLog.objects.values("action").distinct().count(), 8)

    def test_stock_is_consistent_with_reservations(self):
        for batch in Batch.objects.all():
            self.assertGreaterEqual(batch.qty_available, batch.qty_reserved)
            self.assertGreaterEqual(batch.qty_reserved, 0)

    def test_ledger_sum_equals_stock_for_every_qa_batch(self):
        for batch in Batch.objects.all():
            total = StockLedgerEntry.objects.filter(batch=batch).aggregate(t=Sum("qty_change"))["t"] or 0
            self.assertEqual(total, batch.qty_available, batch.batch_id)

    def test_approved_return_went_through_service_and_restocked(self):
        entry = StockLedgerEntry.objects.filter(
            movement_type=StockLedgerEntry.MovementType.RETURN_RESTOCK, batch__batch_id="QA-LO-01")
        self.assertEqual(entry.count(), 1)
