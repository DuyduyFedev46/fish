"""
Unit tests cho Lô 1: CS-01, CS-02, CS-03 (2026-09-28-cskh-xac-nhan-in-tem).
Bảo vệ Bất biến 1 (không rò giá vốn) và Bất biến 9 (phạm vi dữ liệu cá nhân).
"""
import datetime
from decimal import Decimal
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_order_with_note, make_user
from apps.delivery.models import (
    ConfirmationTask,
    CustomerCall,
    DeliveryNote,
    LabelPrint,
)
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine, SalesInvoiceLineBatch, SalesOrder
from apps.accounts import roles


class CskhL1Tests(TestCase):
    def setUp(self):
        # Các Group cơ bản đã có từ 0002
        self.chu = make_user("chu_test", roles.OWNER)
        self.ql = make_user("ql_test", roles.MANAGER)
        self.kho = make_user("kho_test", roles.WAREHOUSE_STAFF)
        self.giao = make_user("giao_test", roles.DELIVERY_STAFF)
        self.giao2 = make_user("giao2_test", roles.DELIVERY_STAFF)
        self.cs1 = make_user("cs1_test", roles.CUSTOMER_SERVICE)
        self.cs2 = make_user("cs2_test", roles.CUSTOMER_SERVICE)

        # Master data
        self.group = ItemGroup.objects.create(name="Cá biển")
        self.item = Item.objects.create(code="CA-THU", name="Cá thu Côn Đảo", item_group=self.group)
        self.supplier = Supplier.objects.create(name="Cảng cá Trần Phú")
        self.warehouse = Warehouse.objects.create(name="Kho Vũng Tàu")
        self.batch = batch_services.create_batch(
            item=self.item,
            supplier=self.supplier,
            warehouse=self.warehouse,
            received_date=timezone.localdate(),
            qty=Decimal("100"),
            purchase_rate=Decimal("150000"),
            shelf_life_days=30,
        )

    def _create_order_invoice_note(self, code_suffix, phone=None, status=DeliveryNote.Status.PREPARING, assigned_to=None):
        if phone is None:
            phone = f"09{abs(hash(code_suffix)) % 100000000:08d}"
        customer, _ = Customer.objects.get_or_create(
            phone=phone,
            defaults={"name": f"Khách {code_suffix}", "default_address": "123 Đường Cảng"},
        )
        order = SalesOrder.objects.create(
            code=f"SO-{code_suffix}",
            customer=customer,
            status=SalesOrder.Status.PROCESSING,
            delivery_address="123 Đường Cảng",
            phone=phone,
            total_amount=Decimal("300000"),
        )
        invoice = SalesInvoice.objects.create(
            code=f"INV-{code_suffix}",
            sales_order=order,
            customer=customer,
            issued_at=timezone.now(),
            amount=Decimal("300000"),
            status=SalesInvoice.Status.ISSUED,
        )
        inv_line = SalesInvoiceLine.objects.create(
            invoice=invoice,
            item=self.item,
            qty=Decimal("2.000"),
            rate=Decimal("150000"),
            amount=Decimal("300000"),
        )
        SalesInvoiceLineBatch.objects.create(
            invoice_line=inv_line,
            batch=self.batch,
            component_item=self.item,
            qty=Decimal("2.000"),
            unit_cost=Decimal("120000"),
        )
        note = DeliveryNote.objects.get(sales_invoice=invoice)
        note.code = f"GH-{code_suffix}"
        note.status = status
        note.assigned_to = assigned_to
        note.save(update_fields=["code", "status", "assigned_to"])
        return order, invoice, note

    # =========================================================================
    # CS-01: Group cskh và phạm vi xem dữ liệu khách
    # =========================================================================

    def test_cs01_ac1_group_cskh_permissions_and_idempotent_migration(self):
        """CS-01-AC1: Group cskh có đủ 4 quyền; các group khác có quyền tương ứng."""
        cskh_group = Group.objects.get(name=roles.CUSTOMER_SERVICE)
        perm_codes = set(cskh_group.permissions.values_list("codename", flat=True))
        expected_cskh = {
            "view_salesorder",
            "view_salesorderline",
            "confirm_with_customer",
            "change_recipient",
        }
        self.assertEqual(perm_codes, expected_cskh)

        # Chạy lại logic migration (idempotent)
        import importlib
        migration_mod = importlib.import_module("apps.accounts.migrations.0011_seed_group_cskh")
        from django.apps import apps
        migration_mod.grant(apps, None)

        cskh_group = Group.objects.get(name=roles.CUSTOMER_SERVICE)
        perm_codes = set(cskh_group.permissions.values_list("codename", flat=True))
        self.assertEqual(perm_codes, expected_cskh)

    def test_cs01_ac2_me_endpoint_for_cskh(self):
        """CS-01-AC2: cs1 gọi /api/auth/me/ -> home=cskh-queue, can_view_cost=False."""
        client = client_for(self.cs1)
        resp = client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["home"], "cskh-queue")
        self.assertFalse(data["can_view_cost"])
        self.assertFalse(data["can_view_profit"])
        self.assertEqual(data["group_labels"], [{"code": roles.CUSTOMER_SERVICE, "label": "CSKH"}])
        cap_codes = [c["code"] for c in data["capabilities"]]
        self.assertIn("delivery.confirm_with_customer", cap_codes)
        self.assertIn("delivery.change_recipient", cap_codes)

    def test_cs01_ac3_cskh_order_scope_filtering(self):
        """CS-01-AC3: D1 (CONFIRMING/PENDING), D2 (CONFIRMING/ESCALATED), D3 (READY), D4 (PREPARING, đã gọi 2 ngày trước)."""
        o1, _, n1 = self._create_order_invoice_note("D1", status=DeliveryNote.Status.CONFIRMING)
        ConfirmationTask.objects.update_or_create(note=n1, defaults={"state": ConfirmationTask.State.PENDING})

        o2, _, n2 = self._create_order_invoice_note("D2", status=DeliveryNote.Status.CONFIRMING)
        ConfirmationTask.objects.update_or_create(note=n2, defaults={"state": ConfirmationTask.State.ESCALATED})

        o3, _, n3 = self._create_order_invoice_note("D3", status=DeliveryNote.Status.READY)

        o4, _, n4 = self._create_order_invoice_note("D4", status=DeliveryNote.Status.PREPARING)
        # cs1 đã gọi 2 ngày trước
        two_days_ago = timezone.now() - datetime.timedelta(days=2)
        call = CustomerCall.objects.create(
            note=n4,
            result=CustomerCall.Result.CALLBACK,
            created_by=self.cs1,
        )
        CustomerCall.objects.filter(pk=call.pk).update(created_at=two_days_ago)

        client = client_for(self.cs1)
        resp = client.get("/api/sales/orders/")
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", [])
        order_ids = [r["id"] for r in results]

        self.assertIn(o1.id, order_ids)
        self.assertIn(o2.id, order_ids)
        self.assertIn(o4.id, order_ids)
        self.assertNotIn(o3.id, order_ids)

    def test_cs01_ac4_cskh_out_of_scope_404_and_customer_403(self):
        """CS-01-AC4: Đơn ngoài phạm vi trả 404; truy cập CustomerViewSet trả 403."""
        o3, _, _ = self._create_order_invoice_note("D3", status=DeliveryNote.Status.READY)
        client = client_for(self.cs1)

        # Xem đơn ngoài phạm vi -> 404
        resp = client.get(f"/api/sales/orders/{o3.id}/")
        self.assertEqual(resp.status_code, 404)

        # Xem customer -> 403 vì cskh không có sales.view_customer
        resp = client.get(f"/api/sales/customers/{o3.customer.id}/")
        self.assertEqual(resp.status_code, 403)

    def test_cs01_ac5_cskh_pii_recent_days(self):
        """CS-01-AC5: Cuộc gọi cách đây 8 ngày -> 404; CONFIRMATION_PII_RECENT_DAYS=10 -> 200."""
        o5, _, n5 = self._create_order_invoice_note("D5", status=DeliveryNote.Status.PREPARING)
        eight_days_ago = timezone.now() - datetime.timedelta(days=8)
        call = CustomerCall.objects.create(
            note=n5,
            result=CustomerCall.Result.CALLBACK,
            created_by=self.cs1,
        )
        CustomerCall.objects.filter(pk=call.pk).update(created_at=eight_days_ago)

        client = client_for(self.cs1)
        # Mặc định CONFIRMATION_PII_RECENT_DAYS = 7 ngày -> quá hạn -> 404
        resp = client.get(f"/api/sales/orders/{o5.id}/")
        self.assertEqual(resp.status_code, 404)

        # Mở rộng tham số thành 10 ngày -> 200
        with override_settings(CONFIRMATION_PII_RECENT_DAYS=10):
            resp2 = client.get(f"/api/sales/orders/{o5.id}/")
            self.assertEqual(resp2.status_code, 200)

    def test_cs01_ac6_cskh_scope_by_user(self):
        """CS-01-AC6: cs2 gọi hôm qua, cs1 xem đơn đó -> 404 (tính theo từng user)."""
        o6, _, n6 = self._create_order_invoice_note("D6", status=DeliveryNote.Status.PREPARING)
        yesterday = timezone.now() - datetime.timedelta(days=1)
        call = CustomerCall.objects.create(
            note=n6,
            result=CustomerCall.Result.CALLBACK,
            created_by=self.cs2,
        )
        CustomerCall.objects.filter(pk=call.pk).update(created_at=yesterday)

        client = client_for(self.cs1)
        resp = client.get(f"/api/sales/orders/{o6.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_cs01_ac7_cskh_matrix_403(self):
        """CS-01-AC7: cs1 gọi các endpoint ngoài phạm vi -> 403."""
        _, _, note = self._create_order_invoice_note("N1", status=DeliveryNote.Status.PREPARING)
        client = client_for(self.cs1)

        # GET /api/delivery/notes/ -> 403
        resp = client.get("/api/delivery/notes/")
        self.assertEqual(resp.status_code, 403)

        # POST /api/delivery/notes/{id}/status/ -> 403
        resp = client.post(f"/api/delivery/notes/{note.id}/status/", {"to_status": "READY"})
        self.assertEqual(resp.status_code, 403)

    # =========================================================================
    # CS-02: Bảng phiếu giao theo trạng thái
    # =========================================================================

    def test_cs02_ac1_deliveries_grouped_by_status(self):
        """CS-02-AC1: NV kho mở GET /api/delivery/notes/?status=... không chứa CANCELLED."""
        _, _, n1 = self._create_order_invoice_note("N1", status=DeliveryNote.Status.CONFIRMING)
        _, _, n2 = self._create_order_invoice_note("N2", status=DeliveryNote.Status.PREPARING)
        _, _, n3 = self._create_order_invoice_note("N3", status=DeliveryNote.Status.READY)
        _, _, n4 = self._create_order_invoice_note("N4", status=DeliveryNote.Status.CANCELLED)

        client = client_for(self.kho)
        resp = client.get("/api/delivery/notes/?status=CONFIRMING,PREPARING,READY")
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", [])
        note_ids = [r["id"] for r in results]
        self.assertIn(n1.id, note_ids)
        self.assertIn(n2.id, note_ids)
        self.assertIn(n3.id, note_ids)
        self.assertNotIn(n4.id, note_ids)

    def test_cs02_ac2_deliveries_ordering_and_unprinted_label(self):
        """CS-02-AC2: Phiếu PREPARING chưa in tem có label.printed=False; xếp confirmed_at null/cũ lên đầu."""
        t1 = timezone.now() - datetime.timedelta(hours=2)
        t2 = timezone.now() - datetime.timedelta(hours=1)

        _, _, n_old = self._create_order_invoice_note("N_OLD", status=DeliveryNote.Status.PREPARING)
        DeliveryNote.objects.filter(pk=n_old.pk).update(confirmed_at=t1)

        _, _, n_new = self._create_order_invoice_note("N_NEW", status=DeliveryNote.Status.PREPARING)
        DeliveryNote.objects.filter(pk=n_new.pk).update(confirmed_at=t2)

        client = client_for(self.kho)
        resp = client.get("/api/delivery/notes/?status=PREPARING")
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", [])
        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0]["id"], n_old.id)
        self.assertFalse(results[0]["label"]["printed"])

    def test_cs02_ac3_confirming_available_actions_empty(self):
        """CS-02-AC3: Phiếu CONFIRMING có available_actions = []."""
        _, _, n_conf = self._create_order_invoice_note("N_CONF", status=DeliveryNote.Status.CONFIRMING)
        client = client_for(self.kho)
        resp = client.get(f"/api/delivery/notes/{n_conf.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["available_actions"], [])

    def test_cs02_ac4_giao_only_sees_assigned_notes(self):
        """CS-02-AC4: giao1 chỉ thấy phiếu gán cho mình."""
        _, _, n_mine = self._create_order_invoice_note("MINE", status=DeliveryNote.Status.DELIVERING, assigned_to=self.giao)
        _, _, n_other = self._create_order_invoice_note("OTHER", status=DeliveryNote.Status.DELIVERING, assigned_to=self.giao2)

        client = client_for(self.giao)
        resp = client.get("/api/delivery/notes/")
        self.assertEqual(resp.status_code, 200)
        note_ids = [r["id"] for r in resp.json().get("results", [])]
        self.assertIn(n_mine.id, note_ids)
        self.assertNotIn(n_other.id, note_ids)

    def test_cs02_ac7_no_cost_leak_in_delivery_notes(self):
        """CS-02-AC7 & X-AC3: Không có khoá giá vốn ở list hay detail phiếu giao."""
        _, _, note = self._create_order_invoice_note("COST_TEST", status=DeliveryNote.Status.PREPARING)
        client = client_for(self.kho)

        # List
        resp_list = client.get("/api/delivery/notes/").json()
        list_str = str(resp_list).lower()
        for forbidden in ("unit_cost", "purchase_rate", "landed_unit_cost", "rate", "margin", "profit"):
            self.assertNotIn(f"'{forbidden}'", list_str)

        # Detail
        resp_detail = client.get(f"/api/delivery/notes/{note.id}/").json()
        detail_str = str(resp_detail).lower()
        for forbidden in ("unit_cost", "purchase_rate", "landed_unit_cost", "rate", "margin", "profit"):
            self.assertNotIn(f"'{forbidden}'", detail_str)

    # =========================================================================
    # CS-03: Chi tiết phiếu soạn và "Đã đóng gói"
    # =========================================================================

    def test_cs03_ac1_detail_lines_with_expiry(self):
        """CS-03-AC1: Detail có lines gồm item_name, qty_kg, batch_id, expiry_date."""
        _, _, note = self._create_order_invoice_note("DETAIL_TEST", status=DeliveryNote.Status.PREPARING)
        client = client_for(self.kho)
        resp = client.get(f"/api/delivery/notes/{note.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("lines", data)
        self.assertEqual(len(data["lines"]), 1)
        line = data["lines"][0]
        self.assertEqual(line["item_name"], "Cá thu Côn Đảo")
        self.assertEqual(line["qty_kg"], "2.000")
        self.assertEqual(line["batch_id"], self.batch.batch_id)
        self.assertEqual(line["expiry_date"], self.batch.expiry_date.isoformat())

    def test_cs03_ac2_pack_delivery_note_advance_to_ready(self):
        """CS-03-AC2: NV kho bấm "Đã đóng gói" (to_status=READY) thành công, tạo 1 AuditLog."""
        _, _, note = self._create_order_invoice_note("PACK_TEST", status=DeliveryNote.Status.PREPARING)
        client = client_for(self.kho)

        init_audit_count = AuditLog.objects.filter(action="delivery_advance_status", object_id=str(note.id)).count()
        resp = client.post(
            f"/api/delivery/notes/{note.id}/status/",
            {"to_status": "READY", "from_status": "PREPARING"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "READY")
        self.assertFalse(data["already"])

        new_audit_count = AuditLog.objects.filter(action="delivery_advance_status", object_id=str(note.id)).count()
        self.assertEqual(new_audit_count, init_audit_count + 1)

    def test_cs03_ac3_advance_status_idempotent_already_true(self):
        """CS-03-AC3: Gửi lại cùng from_status=PREPARING khi đã READY -> already=True, không sinh AuditLog mới."""
        _, _, note = self._create_order_invoice_note("ALREADY_TEST", status=DeliveryNote.Status.PREPARING)
        client = client_for(self.kho)

        # Lần 1: chuyển READY
        client.post(
            f"/api/delivery/notes/{note.id}/status/",
            {"to_status": "READY", "from_status": "PREPARING"},
            format="json",
        )
        audit_count_after_1 = AuditLog.objects.filter(action="delivery_advance_status", object_id=str(note.id)).count()

        # Lần 2: gửi lại
        resp = client.post(
            f"/api/delivery/notes/{note.id}/status/",
            {"to_status": "READY", "from_status": "PREPARING"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "READY")
        self.assertTrue(data["already"])

        audit_count_after_2 = AuditLog.objects.filter(action="delivery_advance_status", object_id=str(note.id)).count()
        self.assertEqual(audit_count_after_2, audit_count_after_1)

    def test_cs03_ac4_invalid_transition_returns_400_br_gh_05(self):
        """CS-03-AC4: PREPARING -> COMPLETED -> 400 BR-GH-05."""
        _, _, note = self._create_order_invoice_note("INVALID_STEP", status=DeliveryNote.Status.PREPARING)
        client = client_for(self.kho)
        resp = client.post(
            f"/api/delivery/notes/{note.id}/status/",
            {"to_status": "COMPLETED"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "BR-GH-05")

    def test_cs03_ac5_cancelled_note_returns_400_br_gh_07(self):
        """CS-03-AC5: CANCELLED -> bất kỳ -> 400 BR-GH-07."""
        _, _, note = self._create_order_invoice_note("CANCELLED_NOTE", status=DeliveryNote.Status.CANCELLED)
        client = client_for(self.kho)
        resp = client.post(
            f"/api/delivery/notes/{note.id}/status/",
            {"to_status": "READY"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "BR-GH-07")

    def test_cs03_ac6_giao_cannot_pack_403(self):
        """CS-03-AC6: NV giao không được đóng gói (PREPARING -> READY) -> 403."""
        _, _, note = self._create_order_invoice_note(
            "GIAO_NO_PACK", status=DeliveryNote.Status.PREPARING, assigned_to=self.giao
        )
        client = client_for(self.giao)
        resp = client.post(
            f"/api/delivery/notes/{note.id}/status/",
            {"to_status": "READY"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
