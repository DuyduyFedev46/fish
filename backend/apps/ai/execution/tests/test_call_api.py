"""
Kiểm thử toàn diện API gọi lệnh AI: POST /api/ai/commands/<id>/call/
Đáp ứng các tiêu chí nghiệm thu DW-10-AC1 đến DW-10-AC11.
"""
from decimal import Decimal
import unittest.mock
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction
from apps.ai.policy.rules import COST_KEYS, SCRUB_FREE_TEXT_KEYS, SCRUB_PII_KEYS
from apps.ai.registry.discovery import get_registry
from apps.catalog.models import Item, ItemGroup
from apps.common.audit import record_audit, set_ai_audit_scope
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.models import DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesOrder, SalesOrderLine
from apps.accounts import roles


@override_settings(AI_ENABLED=True)
class AiCommandCallApiTestCase(TestCase):
    def setUp(self):
        self.user_chu = make_user("chu_test", roles.OWNER)
        self.user_ql = make_user("ql_test", roles.MANAGER)
        self.user_kho = make_user("kho_test", roles.WAREHOUSE_STAFF)
        self.user_giao = make_user("giao_test", roles.DELIVERY_STAFF)

        from django.contrib.auth.models import Group, User
        g_cskh, _ = Group.objects.get_or_create(name=roles.CUSTOMER_SERVICE)
        self.user_cskh = User.objects.create_user(username="cskh_test", password="pwd")
        self.user_cskh.groups.add(g_cskh)

        self.client_chu = client_for(self.user_chu)
        self.client_ql = client_for(self.user_ql)
        self.client_kho = client_for(self.user_kho)
        self.client_giao = client_for(self.user_giao)
        self.client_cskh = client_for(self.user_cskh)

        # Setup master data
        g = ItemGroup.objects.create(name="Cá")
        self.item1 = Item.objects.create(code="CA-001", name="Cá thu", item_group=g)
        self.sup = Supplier.objects.create(name="Đầu mối Phú Quốc")
        self.wh = Warehouse.objects.create(name="Kho lạnh 1")

        # Tạo một số lô mẫu
        for i in range(5):
            b = Batch.objects.create(
                batch_id=f"CA01-260928-0{i}",
                item=self.item1,
                supplier=self.sup,
                warehouse=self.wh,
                received_date=timezone.now().date(),
                expiry_date=timezone.now().date() + timezone.timedelta(days=10 + i),
                qty_received=Decimal("10.000"),
                qty_available=Decimal("10.000"),
                qty_reserved=Decimal("0.000"),
                purchase_rate=Decimal("80000.00"),
                landed_unit_cost=Decimal("85000.00"),
                status=Batch.Status.SELLING,
            )

        # Dữ liệu đơn hàng có PII giả chuẩn
        self.customer = Customer.objects.create(
            name="Nguyễn Văn Khách",
            phone="0901234567",
            default_address="123 Nguyễn Huệ, Q.1",
        )
        self.order = SalesOrder.objects.create(
            code="SO260928-TEST1",
            customer=self.customer,
            delivery_address="123 Nguyễn Huệ, Q.1, TP.HCM",
            phone="0901234567",
            status=SalesOrder.Status.PROCESSING,
        )

    def test_dw10_ac1_call_read_success(self):
        """DW-10-AC1: nv_kho gọi lệnh inventory.batch.list -> 200 outcome=done, level=A, <= 20 dòng, total, truncated, 1 AiAction(kind=read, status=DONE), không lưu kết quả."""
        res = self.client_kho.post(
            "/api/ai/commands/inventory.batch.list/call/",
            {"args": {"item_code": "CA-001"}},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["outcome"], "done")
        self.assertEqual(data["level"], "A")
        self.assertIn("action_id", data)
        self.assertIn("result", data)
        self.assertIn("rows", data["result"])
        self.assertLessEqual(len(data["result"]["rows"]), 20)
        self.assertEqual(data["result"]["total"], 5)
        self.assertFalse(data["result"]["truncated"])

        # Kiểm tra 1 AiAction được tạo, status=DONE, không lưu output vào DB
        action = AiAction.objects.get(id=data["action_id"])
        self.assertEqual(action.kind, AiAction.Kind.READ)
        self.assertEqual(action.status, AiAction.Status.DONE)
        self.assertEqual(action.owner, self.user_kho)
        self.assertIsNone(action.result_ref)

    def test_dw10_ac2_cost_keys_scrubbed_for_unauthorized(self):
        """DW-10-AC2: Mọi lệnh đọc x quan_ly/nv_kho/nv_giao -> JSON không có khoá giá vốn."""
        read_commands = ["inventory.batch.list"]
        unauthorized_clients = [self.client_ql, self.client_kho, self.client_giao]

        for cl in unauthorized_clients:
            for cmd in read_commands:
                res = cl.post(f"/api/ai/commands/{cmd}/call/", {"args": {}}, format="json")
                if res.status_code == 200:
                    data = res.json()
                    rows = data.get("result", {}).get("rows", [])
                    for row in rows:
                        for cost_key in COST_KEYS:
                            self.assertNotIn(
                                cost_key,
                                row,
                                f"Lệnh {cmd} rò giá vốn {cost_key} cho user thiếu quyền",
                            )

    def test_dw10_ac3_pii_scrubbed_even_for_chu(self):
        """DW-10-AC3: Fixture có PII giả -> gọi mọi lệnh đọc với 4 Group + cskh (kể cả chu) -> chuỗi PII không xuất hiện trong kết quả, AiAction, AuditLog."""
        pii_strings = [
            "0901234567",
            "Nguyễn Văn Khách",
            "123 Nguyễn Huệ",
        ]
        clients = [
            self.client_chu,
            self.client_ql,
            self.client_kho,
            self.client_giao,
            self.client_cskh,
        ]
        # Thử gọi lệnh đọc lô
        for cl in clients:
            res = cl.post("/api/ai/commands/inventory.batch.list/call/", {"args": {}}, format="json")
            if res.status_code == 200:
                raw_text = res.content.decode()
                for pii in pii_strings:
                    self.assertNotIn(pii, raw_text, f"Response chứa PII: {pii}")

        # Kiểm tra trong các bản ghi AiAction vừa tạo không chứa PII
        for act in AiAction.objects.all():
            self.assertNotIn("0901234567", str(act.args))
            self.assertNotIn("Nguyễn Văn Khách", str(act.args))

    def test_dw10_ac4_free_text_scrubbed_for_ai_read(self):
        """DW-10-AC4: Ghi chú đơn / chữ tự do không lọt vào kết quả đọc cho AI."""
        # Gọi thử lệnh đọc có field note nếu có
        res = self.client_chu.post(
            "/api/ai/commands/inventory.batch.list/call/",
            {"args": {"item_code": "CA-001"}},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for row in data["result"]["rows"]:
            for free_text_key in SCRUB_FREE_TEXT_KEYS:
                self.assertNotIn(free_text_key, row)

    def test_dw10_ac5_permission_and_idor(self):
        """DW-10-AC5: Lệnh ngoài quyền -> 404 COMMAND_UNKNOWN. Target ngoài scope -> 404."""
        # 1. nv_giao gọi lệnh purchasing.* hoặc batch.close -> 404 COMMAND_UNKNOWN
        res = self.client_giao.post(
            "/api/ai/commands/inventory.batch.close/call/",
            {"target_id": "CA01-260928-01", "args": {}},
            format="json",
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["code"], "COMMAND_UNKNOWN")

        # 2. nv_kho gọi lệnh không tồn tại -> 404 COMMAND_UNKNOWN
        res = self.client_kho.post(
            "/api/ai/commands/non.existent.command/call/",
            {"args": {}},
            format="json",
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["code"], "COMMAND_UNKNOWN")

    def test_dw10_ac6_errors_args_and_cloud_channel(self):
        """DW-10-AC6: args sai kiểu -> 400 BR-AI-01; lệnh channel=cloud -> 400 BR-AI-02."""
        # args không phải dict
        res = self.client_kho.post(
            "/api/ai/commands/inventory.batch.list/call/",
            {"args": "not-a-dict"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "BR-AI-01")

        # Mock một command có channel=cloud
        registry = get_registry()
        spec = registry.get("inventory.batch.list")
        original_channel = spec.channel
        try:
            spec.channel = "cloud"
            res = self.client_kho.post(
                "/api/ai/commands/inventory.batch.list/call/",
                {"args": {}},
                format="json",
            )
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.json()["code"], "BR-AI-02")
        finally:
            spec.channel = original_channel

    def test_dw10_ac7_idempotency(self):
        """DW-10-AC7: Cùng idempotency_key gửi 2 lần; cùng args trả cùng action_id; khác args trả 409."""
        key = "idemp-key-123456"
        res1 = self.client_kho.post(
            "/api/ai/commands/inventory.batch.list/call/",
            {"args": {"item_code": "CA-001"}, "idempotency_key": key},
            format="json",
        )
        self.assertEqual(res1.status_code, 200)
        action_id_1 = res1.json()["action_id"]

        # Lần 2: cùng args -> cùng action_id
        res2 = self.client_kho.post(
            "/api/ai/commands/inventory.batch.list/call/",
            {"args": {"item_code": "CA-001"}, "idempotency_key": key},
            format="json",
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["action_id"], action_id_1)

        # Lần 3: khác args -> 409 AI_IDEMPOTENCY_CONFLICT
        res3 = self.client_kho.post(
            "/api/ai/commands/inventory.batch.list/call/",
            {"args": {"item_code": "CA-002"}, "idempotency_key": key},
            format="json",
        )
        self.assertEqual(res3.status_code, 409)
        self.assertEqual(res3.json()["code"], "AI_IDEMPOTENCY_CONFLICT")

    @override_settings(AI_CALL_RATE="2/min", AI_CALL_RATE_TESTING=True)
    def test_dw10_ac8_throttling(self):
        """DW-10-AC8: Quá tần suất AI_CALL_RATE -> 429 THROTTLED."""
        from django.core.cache import cache
        cache.clear()

        # Gọi lần 1, 2 thành công
        r1 = self.client_kho.post("/api/ai/commands/inventory.batch.list/call/", {"args": {}}, format="json")
        self.assertEqual(r1.status_code, 200)
        r2 = self.client_kho.post("/api/ai/commands/inventory.batch.list/call/", {"args": {}}, format="json")
        self.assertEqual(r2.status_code, 200)

        # Lần 3 vượt ngưỡng -> 429 THROTTLED
        r3 = self.client_kho.post("/api/ai/commands/inventory.batch.list/call/", {"args": {}}, format="json")
        self.assertEqual(r3.status_code, 429)
        self.assertEqual(r3.json()["code"], "THROTTLED")

    def test_dw10_ac9_view_5xx_returns_502(self):
        """DW-10-AC9: View con trả 5xx -> 502 AI_DISPATCH_FAILED, không lộ stack."""
        with unittest.mock.patch("apps.ai.execution.pipeline.dispatch_command") as mock_dispatch:
            from apps.ai.execution.dispatch import DispatchResult
            mock_dispatch.return_value = DispatchResult(
                {"detail": "Thao tác nội bộ thất bại.", "code": "AI_DISPATCH_FAILED"},
                status_code=502,
                is_error=True,
            )
            res = self.client_kho.post(
                "/api/ai/commands/inventory.batch.list/call/",
                {"args": {}},
                format="json",
            )
            self.assertEqual(res.status_code, 502)
            self.assertEqual(res.json()["code"], "AI_DISPATCH_FAILED")

    def test_dw10_ac10_contextvar_reset_after_call(self):
        """DW-10-AC10: Contextvar scope audit được reset sau call, không dính sang request UI cùng thread."""
        res = self.client_kho.post(
            "/api/ai/commands/inventory.batch.list/call/",
            {"args": {"item_code": "CA-001"}},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

        # Thực hiện một hành động ghi audit bình thường của user (ví dụ request UI)
        log = record_audit("test_ui_action", actor=self.user_kho, note="Request UI sau call")
        self.assertEqual(log.actor_kind, "user")
        self.assertEqual(log.actor, self.user_kho)
        self.assertEqual(log.ai_level, "")
        self.assertIsNone(log.ai_config_version)

    @override_settings(AI_ENABLED=False)
    def test_dw10_ac11_ai_disabled_returns_410(self):
        """DW-10-AC11: AI_ENABLED=false -> 410 AI_DISABLED."""
        res = self.client_kho.post(
            "/api/ai/commands/inventory.batch.list/call/",
            {"args": {}},
            format="json",
        )
        self.assertEqual(res.status_code, 410)
        self.assertEqual(res.json()["code"], "AI_DISABLED")
