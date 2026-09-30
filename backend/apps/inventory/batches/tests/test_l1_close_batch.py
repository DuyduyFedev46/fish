"""
S04 — Chốt lô đủ điều kiện và an toàn khi chạy đồng thời (L-1, BR-LO-04, BR-LO-05, BR-KK-05).
Test AC1 đến AC6.
"""
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, ReturnToStock, StockReconciliation, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesOrder, SalesOrderLine, SalesOrderLineBatch
from apps.accounts import roles


class CloseBatchS04Tests(TestCase):
    def setUp(self):
        self.g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=self.g)
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.today = timezone.localdate()

        self.chu = make_user("chu_s04", roles.OWNER)
        self.quan_ly = make_user("ql_s04", roles.MANAGER)
        self.nv_kho = make_user("kho_s04", roles.WAREHOUSE_STAFF)
        self.nv_giao = make_user("giao_s04", roles.DELIVERY_STAFF)

    def _create_ready_batch(self, qty="0", purchase_rate="80000"):
        """Tạo lô đã đủ điều kiện chốt: tồn 0, đã publish, đã kiểm kê APPROVED."""
        batch = batch_services.create_batch(
            item=self.item,
            supplier=self.sup,
            warehouse=self.wh,
            received_date=self.today,
            qty=Decimal(qty),
            purchase_rate=Decimal(purchase_rate),
        )
        batch_services.publish_batch(batch=batch, actor=None)
        batch.refresh_from_db()
        rec = StockReconciliation.objects.create(
            count_date=self.today,
            created_by=self.chu,
            approved_by=self.chu,
            status=StockReconciliation.Status.APPROVED,
        )
        rec.lines.create(batch=batch, system_qty=Decimal(qty), counted_qty=Decimal(qty))
        return batch

    def _attach_order(self, batch, status=SalesOrder.Status.BOOKED, phone="0900000001", name="Khách A"):
        customer, _ = Customer.objects.get_or_create(phone=phone, defaults={"name": name, "default_address": "1 Cảng Cá"})
        order = SalesOrder.objects.create(
            code=f"SO{uuid4().hex[:6].upper()}",
            customer=customer,
            status=status,
            delivery_address="1 Cảng Cá",
            phone=phone,
            total_amount=Decimal("100000"),
        )
        line = SalesOrderLine.objects.create(
            order=order,
            item=self.item,
            qty=Decimal("1"),
            rate=Decimal("100000"),
            amount=Decimal("100000"),
        )
        SalesOrderLineBatch.objects.create(
            order_line=line,
            batch=batch,
            component_item=self.item,
            qty=Decimal("1"),
            unit_cost=batch.landed_unit_cost,
        )
        return order

    # --- AC1: Còn đơn mở -> chặn (BOOKED, PAID, PROCESSING) ---

    def test_s04_ac1_open_order_booked_blocks_close(self):
        batch = self._create_ready_batch()
        self._attach_order(batch, status=SalesOrder.Status.BOOKED)

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body.get("code"), "BR-LO-04")
        self.assertEqual(body.get("detail"), "Còn 1 đơn đang mở tham chiếu lô, chưa chốt được (BR-LO-04).")

        batch.refresh_from_db()
        self.assertNotEqual(batch.status, Batch.Status.CLOSED)
        self.assertFalse(AuditLog.objects.filter(action="close_batch", object_id=str(batch.pk)).exists())

    def test_s04_ac1_open_order_paid_blocks_close(self):
        batch = self._create_ready_batch()
        self._attach_order(batch, status=SalesOrder.Status.PAID)

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "BR-LO-04")
        self.assertEqual(resp.json().get("detail"), "Còn 1 đơn đang mở tham chiếu lô, chưa chốt được (BR-LO-04).")

    def test_s04_ac1_open_order_processing_blocks_close(self):
        batch = self._create_ready_batch()
        self._attach_order(batch, status=SalesOrder.Status.PROCESSING)

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "BR-LO-04")
        self.assertEqual(resp.json().get("detail"), "Còn 1 đơn đang mở tham chiếu lô, chưa chốt được (BR-LO-04).")

    def test_s04_ac1_multiple_lines_same_order_distinct_count(self):
        batch = self._create_ready_batch()
        order = self._attach_order(batch, status=SalesOrder.Status.BOOKED)
        # Thêm 1 dòng nữa thuộc cùng đơn đó trỏ vào batch
        line2 = SalesOrderLine.objects.create(
            order=order,
            item=self.item,
            qty=Decimal("2"),
            rate=Decimal("100000"),
            amount=Decimal("200000"),
        )
        SalesOrderLineBatch.objects.create(
            order_line=line2,
            batch=batch,
            component_item=self.item,
            qty=Decimal("2"),
            unit_cost=batch.landed_unit_cost,
        )

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("detail"), "Còn 1 đơn đang mở tham chiếu lô, chưa chốt được (BR-LO-04).")

        # Thêm đơn mở thứ hai
        self._attach_order(batch, status=SalesOrder.Status.PAID, phone="0900000002", name="Khách B")
        resp2 = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp2.status_code, 400)
        self.assertEqual(resp2.json().get("detail"), "Còn 2 đơn đang mở tham chiếu lô, chưa chốt được (BR-LO-04).")

    def test_s04_ac1_closed_order_statuses_do_not_block_close(self):
        batch = self._create_ready_batch()
        self._attach_order(batch, status=SalesOrder.Status.COMPLETED)
        self._attach_order(batch, status=SalesOrder.Status.CANCELLED)
        self._attach_order(batch, status=SalesOrder.Status.AUTO_CANCELLED)

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 200)
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.CLOSED)

    def test_s04_ac1_error_message_contains_no_customer_pii(self):
        batch = self._create_ready_batch()
        secret_phone = "0900000099"
        secret_name = "Nguyễn Văn Tên Riêng"
        secret_address = "99 Đường Tuyệt Mật"
        self._attach_order(batch, status=SalesOrder.Status.BOOKED, phone=secret_phone, name=secret_name)

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        content = resp.content.decode("utf-8")
        self.assertNotIn(secret_phone, content)
        self.assertNotIn(secret_name, content)
        self.assertNotIn(secret_address, content)

    # --- AC2: Còn giữ chỗ hoặc hàng hoàn chờ duyệt -> chặn ---

    def test_s04_ac2_qty_reserved_blocks_close(self):
        batch = self._create_ready_batch()
        Batch.objects.filter(pk=batch.pk).update(qty_reserved=Decimal("3"))
        batch.refresh_from_db()

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "BR-LO-04")
        self.assertIn("giữ chỗ", resp.json().get("detail"))
        batch.refresh_from_db()
        self.assertNotEqual(batch.status, Batch.Status.CLOSED)

    def test_s04_ac2_draft_return_to_stock_blocks_close(self):
        batch = self._create_ready_batch()
        ReturnToStock.objects.create(
            batch=batch,
            qty=Decimal("1"),
            created_by=self.nv_kho,
            status=ReturnToStock.Status.DRAFT,
        )

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "BR-LO-04")
        self.assertEqual(resp.json().get("detail"), "Còn phiếu hàng hoàn đang chờ duyệt tham chiếu lô (BR-LO-04).")

    def test_s04_ac2_approved_return_to_stock_does_not_block_close(self):
        batch = self._create_ready_batch()
        ReturnToStock.objects.create(
            batch=batch,
            qty=Decimal("1"),
            created_by=self.nv_kho,
            approved_by=self.chu,
            status=ReturnToStock.Status.APPROVED,
        )

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 200)
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.CLOSED)

    # --- AC3: Chưa kiểm kê -> chặn (BR-KK-05) ---

    def test_s04_ac3_no_reconciliation_line_blocks_close(self):
        batch = batch_services.create_batch(
            item=self.item,
            supplier=self.sup,
            warehouse=self.wh,
            received_date=self.today,
            qty=Decimal("0"),
            purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=batch, actor=None)

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "BR-KK-05")
        self.assertEqual(resp.json().get("detail"), "Lô phải được kiểm kê và duyệt trước khi chốt (BR-KK-05).")

    def test_s04_ac3_draft_reconciliation_line_blocks_close(self):
        batch = batch_services.create_batch(
            item=self.item,
            supplier=self.sup,
            warehouse=self.wh,
            received_date=self.today,
            qty=Decimal("0"),
            purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=batch, actor=None)
        rec = StockReconciliation.objects.create(
            count_date=self.today,
            created_by=self.nv_kho,
            status=StockReconciliation.Status.DRAFT,
        )
        rec.lines.create(batch=batch, system_qty=Decimal("0"), counted_qty=Decimal("0"))

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "BR-KK-05")
        self.assertEqual(resp.json().get("detail"), "Lô phải được kiểm kê và duyệt trước khi chốt (BR-KK-05).")

    def test_s04_ac3_approved_plus_draft_reconciliation_blocks_close(self):
        batch = self._create_ready_batch()
        # Đã có 1 phiếu APPROVED, thêm 1 phiếu DRAFT
        rec_draft = StockReconciliation.objects.create(
            count_date=self.today,
            created_by=self.nv_kho,
            status=StockReconciliation.Status.DRAFT,
        )
        rec_draft.lines.create(batch=batch, system_qty=Decimal("0"), counted_qty=Decimal("0"))

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("code"), "BR-KK-05")
        self.assertEqual(resp.json().get("detail"), "Lô phải được kiểm kê và duyệt trước khi chốt (BR-KK-05).")

    # --- AC4: Đủ điều kiện -> chốt & Chốt lần 2 -> 400 ---

    def test_s04_ac4_happy_path_close_batch(self):
        batch = self._create_ready_batch()

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 200)

        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.CLOSED)
        self.assertEqual(batch.closed_by, self.chu)
        self.assertIsNotNone(batch.closed_at)

        # 1 dòng AuditLog close_batch
        logs = AuditLog.objects.filter(action="close_batch", object_id=str(batch.pk))
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().actor, self.chu)

    def test_s04_ac4_close_already_closed_batch_raises_br_lo_05(self):
        batch = self._create_ready_batch()
        client = client_for(self.chu)
        resp1 = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp1.status_code, 200)

        # Chốt lần hai
        resp2 = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp2.status_code, 400)
        self.assertEqual(resp2.json().get("code"), "BR-LO-05")
        self.assertEqual(resp2.json().get("detail"), "Lô đã chốt.")

    # --- AC5: Khoá đồng thời & FEFO không lấy lô đã chốt ---

    def test_s04_ac5_closed_batch_not_picked_by_allocate_fefo(self):
        batch = self._create_ready_batch()
        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 200)

        with self.assertRaises(BusinessError):
            batch_services.allocate_fefo(item=self.item, qty=Decimal("1"))

    def test_s04_ac5_select_for_update_and_atomic_execution(self):
        batch = self._create_ready_batch()

        was_in_atomic = []
        orig_sfu = Batch.objects.select_for_update

        def mock_sfu(*args, **kwargs):
            was_in_atomic.append(connection.in_atomic_block)
            return orig_sfu(*args, **kwargs)

        with mock.patch.object(Batch.objects, "select_for_update", side_effect=mock_sfu):
            batch_services.close_batch(batch=batch, actor=self.chu)

        self.assertTrue(len(was_in_atomic) > 0)
        self.assertTrue(was_in_atomic[0], "select_for_update phải được gọi bên trong khối transaction.atomic")

    # --- AC6: Phân quyền & Không rò giá vốn ---

    def test_s04_ac6_forbidden_roles_quan_ly_nv_kho_nv_giao_403(self):
        batch = self._create_ready_batch()
        for user in [self.quan_ly, self.nv_kho, self.nv_giao]:
            client = client_for(user)
            resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
            self.assertEqual(resp.status_code, 403)
            batch.refresh_from_db()
            self.assertNotEqual(batch.status, Batch.Status.CLOSED)

    def test_s04_ac6_unauthenticated_returns_401(self):
        batch = self._create_ready_batch()
        client = APIClient()
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 401)
        batch.refresh_from_db()
        self.assertNotEqual(batch.status, Batch.Status.CLOSED)

    def test_s04_ac6_no_cost_leak_in_error_responses(self):
        batch = self._create_ready_batch(purchase_rate="88888")
        self._attach_order(batch, status=SalesOrder.Status.BOOKED)

        client = client_for(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400)
        content = resp.content.decode("utf-8")
        self.assertNotIn("purchase_rate", content)
        self.assertNotIn("landed_unit_cost", content)
        self.assertNotIn("88888", content)

    def test_s04_ac6_quan_ly_cannot_see_cost_in_close_batch_audit_log(self):
        batch = self._create_ready_batch(purchase_rate="99999")
        client_chu = client_for(self.chu)
        resp_close = client_chu.post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp_close.status_code, 200)

        # Quản lý xem audit log close_batch
        client_ql = client_for(self.quan_ly)
        resp_audit = client_ql.get("/api/audit-logs/", {"action": "close_batch"})
        self.assertEqual(resp_audit.status_code, 200)
        results = resp_audit.json()["results"]
        self.assertTrue(len(results) >= 1)
        for r in results:
            changes_str = str(r.get("changes", {}))
            self.assertNotIn("landed_unit_cost", changes_str)
            self.assertNotIn("99999", changes_str)

        # Chủ xem audit log thì vẫn thấy landed_unit_cost
        resp_chu_audit = client_chu.get("/api/audit-logs/", {"action": "close_batch"})
        self.assertEqual(resp_chu_audit.status_code, 200)
        self.assertIn("landed_unit_cost", str(resp_chu_audit.json()["results"][0].get("changes", {})))
