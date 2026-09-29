"""
Test cho chuyển việc + nút "Nhờ" (DW-23-AC1..AC7, BR-AI-25, Q-M20).
"""
import datetime
from decimal import Decimal
from django.contrib.auth.models import User, Group, Permission
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.ai.models import AiAction
from apps.catalog.models.items import Item, ItemGroup
from apps.purchasing.models.suppliers import Supplier
from apps.inventory.models import Batch, Warehouse


class EscalateGuidanceStepTests(APITestCase):
    def setUp(self):
        # 1. Tạo nhóm
        self.chu_group, _ = Group.objects.get_or_create(name="chu")
        self.quan_ly_group, _ = Group.objects.get_or_create(name="quan_ly")
        self.nv_kho_group, _ = Group.objects.get_or_create(name="nv_kho")

        # Gán quyền
        for perm in Permission.objects.filter(
            codename__in=["manage_ai_policy", "close_batch", "view_batch", "view_costprice", "publish_batch"]
        ):
            self.chu_group.permissions.add(perm)

        for perm in Permission.objects.filter(codename__in=["view_batch"]):
            self.quan_ly_group.permissions.add(perm)
            self.nv_kho_group.permissions.add(perm)

        # 2. Tạo users
        self.chu_user = User.objects.create_user(
            username="chu_vua", password="password", first_name="Duy", last_name="Chủ"
        )
        self.chu_user.groups.add(self.chu_group)

        self.quan_ly = User.objects.create_user(
            username="quan_ly_1", password="password", first_name="Linh", last_name="QL"
        )
        self.quan_ly.groups.add(self.quan_ly_group)

        self.nv_kho = User.objects.create_user(
            username="nv_kho_1", password="password", first_name="Tuấn", last_name="Kho"
        )
        self.nv_kho.groups.add(self.nv_kho_group)

        # 3. Tạo dữ liệu lô hàng
        self.item_group, _ = ItemGroup.objects.get_or_create(name="Nhóm cá")
        self.item = Item.objects.create(name="Cá thu test", code="ITM-TEST", item_group=self.item_group)
        self.supplier = Supplier.objects.create(name="NCC Cảng")
        self.warehouse, _ = Warehouse.objects.get_or_create(name="Kho Lạnh 1")

        today = timezone.localdate()
        self.batch = Batch.objects.create(
            batch_id="LO-TEST-001",
            item=self.item,
            supplier=self.supplier,
            warehouse=self.warehouse,
            received_date=today,
            expiry_date=today + datetime.timedelta(days=30),
            qty_received=Decimal("100"),
            qty_available=Decimal("0"),  # Để thỏa điều kiện check_close_batch
            purchase_rate=Decimal("120000"),
            landed_unit_cost=Decimal("120000"),
            status=Batch.Status.SELLING,
        )

        self.draft_batch = Batch.objects.create(
            batch_id="LO-TEST-DRAFT",
            item=self.item,
            supplier=self.supplier,
            warehouse=self.warehouse,
            received_date=today,
            expiry_date=today + datetime.timedelta(days=30),
            qty_received=Decimal("100"),
            qty_available=Decimal("100"),
            purchase_rate=Decimal("120000"),
            landed_unit_cost=Decimal("120000"),
            status=Batch.Status.DRAFT,
        )

    def test_dw23_ac1_nv_kho_escalate_close_batch_to_chu(self):
        """
        DW-23-AC1: NV kho xem lô, bước "Chốt lô" allowed=false -> bấm "Nhờ"
        -> AiAction ESCALATED, assignee_group=chu; Chủ thấy trong tab "Được chuyển" (BR-AI-25, Q-M20).
        """
        self.client.force_authenticate(user=self.nv_kho)

        res = self.client.post(
            "/api/ai/actions/escalate/",
            {
                "doc_type": "batch",
                "doc_id": self.batch.pk,
                "step_key": "close",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        action_id = res.data["action_id"]
        self.assertEqual(res.data["assignee_group"], "chu")

        # Kiểm tra action trong DB
        action = AiAction.objects.get(id=action_id)
        self.assertEqual(action.status, AiAction.Status.ESCALATED)
        self.assertEqual(action.assignee_group, "chu")
        self.assertEqual(action.owner, self.nv_kho)

        # Chủ đăng nhập -> vào tab "Được chuyển" (status=ESCALATED)
        self.client.force_authenticate(user=self.chu_user)
        list_res = self.client.get("/api/ai/actions/?status=ESCALATED")
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        # Danh sách trả về chứa action vừa chuyển
        results = list_res.data.get("results", list_res.data) if isinstance(list_res.data, dict) else list_res.data
        action_ids = [a["id"] for a in results]
        self.assertIn(str(action.id), action_ids)

    @override_settings(AI_ENABLED=True)
    def test_dw23_ac2_job_b_error_escalates_to_permitted_group(self):
        """
        DW-23-AC2: Job B (DW-21) gặp BusinessError -> job chạy -> ESCALATED cho chủ AI
        hoặc Group có quyền (tiền/chốt lô -> chu).
        """
        from unittest.mock import patch

        action_err = AiAction.objects.create(
            command="inventory.batch.close",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.B,
            status=AiAction.Status.SCHEDULED,
            owner=self.chu_user,
            execute_after=timezone.now() - datetime.timedelta(minutes=1),
            target_model="batch",
            target_id="999999",  # ID không tồn tại -> dispatch lỗi
        )

        with patch("apps.ai.management.commands.run_due_ai_actions.effective_level", return_value="B"):
            call_command("run_due_ai_actions")

        action_err.refresh_from_db()
        self.assertEqual(action_err.status, AiAction.Status.ESCALATED)
        self.assertEqual(action_err.assignee_group, "chu")

    @override_settings(AI_ENABLED=True)
    def test_dw23_ac3_overdue_2h_escalates_to_chu_no_execution(self):
        """
        DW-23-AC3: Việc khách chờ quá 2 giờ -> job nhắc -> đẩy lên chu; KHÔNG tự thực thi.
        """
        past_time = timezone.now() - datetime.timedelta(hours=3)
        pending_act = AiAction.objects.create(
            command="sales.order.confirm",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.C,
            status=AiAction.Status.PENDING,
            owner=self.nv_kho,
            assignee_group="",
        )
        AiAction.objects.filter(pk=pending_act.pk).update(created_at=past_time)

        call_command("run_due_ai_actions")

        pending_act.refresh_from_db()
        self.assertEqual(pending_act.status, AiAction.Status.ESCALATED)
        self.assertEqual(pending_act.assignee_group, "chu")
        self.assertIsNone(pending_act.executed_at)  # Không tự thực thi

    def test_dw23_ac4_quan_ly_view_no_cost_price(self):
        """
        DW-23-AC4: Việc chuyển tới quan_ly về lô -> xem -> không số giá vốn (lọc theo người nhận, Bất biến 1).
        """
        escalated_act = AiAction.objects.create(
            command="inventory.batch.inspect",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.C,
            status=AiAction.Status.ESCALATED,
            owner=self.nv_kho,
            assignee_group="quan_ly",
            target_model="batch",
            target_id=self.batch.batch_id,
            args={
                "batch_id": self.batch.batch_id,
                "unit_cost": 120000,
                "purchase_cost": 12000000,
                "note": "Kiểm tra chất lượng lô cá",
            },
        )

        # quan_ly đăng nhập xem chi tiết
        self.client.force_authenticate(user=self.quan_ly)
        res = self.client.get(f"/api/ai/actions/{escalated_act.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        args_preview = res.data["args_preview"]
        # unit_cost và purchase_cost phải bị lọc sạch
        self.assertNotIn("unit_cost", args_preview)
        self.assertNotIn("purchase_cost", args_preview)
        self.assertIn("batch_id", args_preview)

    def test_dw23_ac5_order_action_no_pii(self):
        """
        DW-23-AC5: Việc đụng đơn -> xem -> chỉ mã đơn, việc cần làm, hạn, không có PII (Bất biến 9).
        """
        escalated_act = AiAction.objects.create(
            command="delivery.deliverynote.deliver",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.C,
            status=AiAction.Status.ESCALATED,
            owner=self.nv_kho,
            assignee_group="chu",
            target_model="order",
            target_id="ORD-9999",
            args={
                "customer_name": "Trần Thị B (Dữ liệu giả)",
                "phone": "0912345678",
                "shipping_address": "456 Đường Demo",
                "delivery_slot": "14:00 - 16:00",
            },
        )

        self.client.force_authenticate(user=self.chu_user)
        res = self.client.get(f"/api/ai/actions/{escalated_act.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["target"], {"type": "order", "code": "ORD-9999"})
        content_str = str(res.data)
        self.assertNotIn("0912345678", content_str)
        self.assertNotIn("Trần Thị B", content_str)
        self.assertNotIn("456 Đường Demo", content_str)

    def test_dw23_ac6_errors_already_allowed_or_step_missing(self):
        """
        DW-23-AC6: Người gửi tự làm được bước; bước không tồn tại -> 400.
        """
        # 1. Bước không tồn tại
        self.client.force_authenticate(user=self.nv_kho)
        res_missing = self.client.post(
            "/api/ai/actions/escalate/",
            {
                "doc_type": "batch",
                "doc_id": self.batch.pk,
                "step_key": "step_khong_ton_tai",
            },
            format="json",
        )
        self.assertEqual(res_missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_missing.data["code"], "STEP_NOT_FOUND")

        # 2. Người gửi tự làm được bước (Chủ vựa tự làm được bước publish trên lô DRAFT)
        self.client.force_authenticate(user=self.chu_user)
        res_allowed = self.client.post(
            "/api/ai/actions/escalate/",
            {
                "doc_type": "batch",
                "doc_id": self.draft_batch.pk,
                "step_key": "publish",
            },
            format="json",
        )
        self.assertEqual(res_allowed.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_allowed.data["code"], "BR-AI-25")

    @override_settings(AI_ENABLED=False)
    def test_dw23_ac7_ai_disabled_escalate_still_works(self):
        """
        DW-23-AC7: AI_ENABLED=false -> bấm "Nhờ" vẫn chạy (không cần model, BR-AI-10).
        """
        self.client.force_authenticate(user=self.nv_kho)
        res = self.client.post(
            "/api/ai/actions/escalate/",
            {
                "doc_type": "batch",
                "doc_id": self.batch.pk,
                "step_key": "close",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["assignee_group"], "chu")
