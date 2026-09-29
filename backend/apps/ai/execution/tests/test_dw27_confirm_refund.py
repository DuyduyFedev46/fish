"""
Test cho DW-27: Xác nhận hoàn tiền - AI luôn chuyển Chủ kèm việc cần làm (DW-27-AC1..AC5, BR-AI-07, BR-HT-03, BR-HT-07).
"""
import datetime
from decimal import Decimal
from django.contrib.auth.models import User, Group, Permission
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.ai.models import AiAction, AiConfigVersion, AiPolicyVersion
from apps.catalog.models.items import Item, ItemGroup
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models.suppliers import Supplier
from apps.sales.models import Customer, Refund, SalesInvoice, SalesOrder, SalesOrderLine, SalesOrderLineBatch


@override_settings(
    AI_ENABLED=True,
    AI_PRODUCTION_READY=True,
    AI_WRITE_LEVELS_ALLOWED="B",
    TESTING=True,
)
class ConfirmRefundAiTests(APITestCase):
    def setUp(self):
        # 1. Tạo Group
        self.chu_group, _ = Group.objects.get_or_create(name="chu")
        self.quan_ly_group, _ = Group.objects.get_or_create(name="quan_ly")
        self.nv_kho_group, _ = Group.objects.get_or_create(name="nv_kho")

        # Gán quyền
        for perm in Permission.objects.filter(
            codename__in=[
                "manage_ai_policy",
                "confirm_refund",
                "create_refund",
                "view_refund",
                "view_costprice",
            ]
        ):
            self.chu_group.permissions.add(perm)

        for perm in Permission.objects.filter(
            codename__in=[
                "create_refund",
                "view_refund",
            ]
        ):
            self.quan_ly_group.permissions.add(perm)

        # 2. Tạo users
        self.chu_user = User.objects.create_user(
            username="chu_vua_dw27", password="password", first_name="Duy", last_name="Chủ"
        )
        self.chu_user.groups.add(self.chu_group)

        self.quan_ly = User.objects.create_user(
            username="quan_ly_dw27", password="password", first_name="Linh", last_name="QL"
        )
        self.quan_ly.groups.add(self.quan_ly_group)

        # 3. Tạo chính sách mở công tắc confirm_refund
        self.policy = AiPolicyVersion.objects.create(
            version=1,
            global_mode="on",
            red_zone_open={"sales.confirm_refund": True},
            created_by=self.chu_user,
        )

        # Cấu hình Chủ chọn override mức B cho lệnh sales.refund.confirm
        self.chu_config = AiConfigVersion.objects.create(
            user=self.chu_user,
            version=1,
            group_levels={"read": "A", "write": "B"},
            overrides={"sales.refund.confirm": "B"},
            created_by=self.chu_user,
        )

        # 4. Tạo dữ liệu bán hàng & phiếu hoàn PENDING
        self.customer = Customer.objects.create(
            phone="0987654321",
            name="Khách Hàng DW27",
            default_address="123 Phố Test, Hà Nội",
        )
        self.item_group, _ = ItemGroup.objects.get_or_create(name="Nhóm cá")
        self.item = Item.objects.create(name="Cá bớp test", code="ITM-BOP-27", item_group=self.item_group)
        self.supplier = Supplier.objects.create(name="NCC Cảng 27")
        self.warehouse, _ = Warehouse.objects.get_or_create(name="Kho Lạnh 27")

        today = timezone.localdate()
        self.batch = Batch.objects.create(
            batch_id="LO-DW27-01",
            item=self.item,
            supplier=self.supplier,
            warehouse=self.warehouse,
            received_date=today,
            expiry_date=today + datetime.timedelta(days=30),
            qty_received=Decimal("50"),
            qty_available=Decimal("50"),
            purchase_rate=Decimal("150000"),
            landed_unit_cost=Decimal("150000"),
            status=Batch.Status.SELLING,
        )

        self.order = SalesOrder.objects.create(
            code="SO-DW27-001",
            customer=self.customer,
            total_amount=Decimal("300000"),
            status=SalesOrder.Status.PAID,
        )
        self.order_line = SalesOrderLine.objects.create(
            order=self.order,
            item=self.item,
            qty=Decimal("2"),
            rate=Decimal("150000"),
            amount=Decimal("300000"),
        )
        SalesOrderLineBatch.objects.create(
            order_line=self.order_line,
            batch=self.batch,
            component_item=self.item,
            qty=Decimal("2"),
            unit_cost=Decimal("150000"),
        )
        self.invoice = SalesInvoice.objects.create(
            code="INV-DW27-001",
            sales_order=self.order,
            customer=self.customer,
            issued_at=timezone.now(),
            amount=Decimal("300000"),
            status=SalesInvoice.Status.ISSUED,
        )

        self.refund = Refund.objects.create(
            sales_invoice=self.invoice,
            amount=Decimal("300000"),
            reason="Khách đổi ý trả hàng",
            status=Refund.Status.PENDING,
            created_by=self.chu_user,
        )

        self.client_chu = self.client_class()
        self.client_chu.force_authenticate(user=self.chu_user)

        self.client_ql = self.client_class()
        self.client_ql.force_authenticate(user=self.quan_ly)

    def test_dw27_ac1_confirm_refund_always_downgrades_to_c_with_ai_no_evidence(self):
        """
        DW-27-AC1: Phiếu hoàn PENDING, công tắc confirm_refund mở, Chủ đặt B
        -> AI call sales.refund.confirm luôn hạ C với downgrade_reason.code=AI_NO_EVIDENCE;
        tạo việc chuyển "chuyển X đ cho phiếu RF-..., rồi nhập mã giao dịch".
        """
        res = self.client_chu.post(
            "/api/ai/commands/sales.refund.confirm/call/",
            {
                "target_id": self.refund.id,
                "args": {},
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data
        self.assertEqual(data["outcome"], "proposal")
        self.assertEqual(data["level"], "C")
        self.assertEqual(data["downgrade_reason"]["code"], "AI_NO_EVIDENCE")
        self.assertIn("bằng chứng", data["downgrade_reason"]["text"])

        # Kiểm tra việc chuyển được tạo trong DB
        action_id = data["action_id"]
        action = AiAction.objects.get(id=action_id)
        self.assertEqual(action.command, "sales.refund.confirm")
        self.assertEqual(action.status, AiAction.Status.ESCALATED)
        self.assertEqual(action.assignee_group, "chu")
        self.assertIn("RF-", action.args.get("summary", ""))

        # Phiếu hoàn vẫn giữ trạng thái PENDING
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, Refund.Status.PENDING)

    def test_dw27_ac2_args_with_bank_txn_ref_never_auto_executed(self):
        """
        DW-27-AC2 (lỗi): Dù args do model điền có bank_txn_ref
        -> call vẫn chỉ C; bank_txn_ref từ model không bao giờ được ghi tự động.
        """
        fake_ref = "FT2609289999"
        res = self.client_chu.post(
            "/api/ai/commands/sales.refund.confirm/call/",
            {
                "target_id": self.refund.id,
                "args": {"bank_txn_ref": fake_ref},
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["outcome"], "proposal")
        self.assertEqual(res.data["level"], "C")
        self.assertEqual(res.data["downgrade_reason"]["code"], "AI_NO_EVIDENCE")

        # Kiểm tra DB: phiếu hoàn không bị ghi bank_txn_ref giả
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, Refund.Status.PENDING)
        self.assertNotEqual(self.refund.bank_txn_ref, fake_ref)

    def test_dw27_ac3_quan_ly_cannot_see_or_call_confirm_refund_404(self):
        """
        DW-27-AC3 (quyền): quan_ly (có create_refund) xem index/my-config
        không có sales.refund.confirm; gọi call -> 404 COMMAND_UNKNOWN.
        """
        # 1. Gọi my-config
        res_cfg = self.client_ql.get("/api/ai/my-config/")
        self.assertEqual(res_cfg.status_code, status.HTTP_200_OK)
        cmd_ids = [cmd["id"] for cmd in res_cfg.data.get("commands", [])]
        self.assertNotIn("sales.refund.confirm", cmd_ids)

        # 2. Gọi call lệnh sales.refund.confirm
        res_call = self.client_ql.post(
            "/api/ai/commands/sales.refund.confirm/call/",
            {
                "target_id": self.refund.id,
                "args": {},
            },
            format="json",
        )
        self.assertEqual(res_call.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res_call.data.get("code"), "COMMAND_UNKNOWN")

    def test_dw27_ac4_escalated_action_view_has_no_pii(self):
        """
        DW-27-AC4 (PII): Việc chuyển khi xem chỉ có mã phiếu, số tiền, hạn;
        không có tên/số tài khoản của khách (bất biến 9).
        """
        # Gọi call để sinh việc chuyển
        res_call = self.client_chu.post(
            "/api/ai/commands/sales.refund.confirm/call/",
            {
                "target_id": self.refund.id,
                "args": {},
            },
            format="json",
        )
        action_id = res_call.data["action_id"]

        # Xem chi tiết action
        res_detail = self.client_chu.get(f"/api/ai/actions/{action_id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        detail_str = str(res_detail.data)

        # Kiểm tra không chứa tên khách, SĐT khách
        self.assertNotIn("Khách Hàng DW27", detail_str)
        self.assertNotIn("0987654321", detail_str)
        self.assertNotIn("123 Phố Test", detail_str)

    @override_settings(AI_ENABLED=False)
    def test_dw27_ac5_manual_confirm_works_when_ai_disabled(self):
        """
        DW-27-AC5 (AI tắt): AI_ENABLED=false -> Chủ xác nhận tay trên ERP vẫn chạy bình thường.
        """
        res = self.client_chu.post(
            f"/api/sales/refunds/{self.refund.id}/confirm/",
            {"bank_txn_ref": "FTREAL12345"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, Refund.Status.REFUNDED)
        self.assertEqual(self.refund.bank_txn_ref, "FTREAL12345")
