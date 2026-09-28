"""
Test DW-14: Cung cấp trường `ai` trên NextStep của khối Guidance theo effective_level.

Acceptance Criteria:
- DW-14-AC2: Chủ mở lô -> bước chốt có ai={"level": "C", "label": "AI soạn nháp chốt lô"};
             Quản lý thiếu quyền chốt lô -> bước chốt có ai=null.
- DW-14-AC8: AI_ENABLED=false -> bước chốt có ai=null (guidance vẫn trả 200).
"""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status

from apps.catalog.models import Item, ItemGroup
from apps.common.guidance.steps import NextStep, resolve_step_ai, step_to_dict
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier


@override_settings(AI_ENABLED=True)
class GuidanceAiFieldTestCase(TestCase):
    def setUp(self):
        self.chu = make_user("chu_dw14", "chu")
        self.ql = make_user("ql_dw14", "quan_ly")
        self.kho = make_user("kho_dw14", "nv_kho")

        self.c_chu = client_for(self.chu)
        self.c_ql = client_for(self.ql)
        self.c_kho = client_for(self.kho)

        group = ItemGroup.objects.create(name="Cá biển")
        self.item = Item.objects.create(name="Cá thu", code="CA-001", item_group=group)
        self.sup = Supplier.objects.create(name="Vựa Phú Quốc")
        self.wh = Warehouse.objects.create(name="Kho chính")

        today = timezone.localdate()
        self.batch = batch_services.create_batch(
            item=self.item,
            supplier=self.sup,
            warehouse=self.wh,
            received_date=today,
            qty=Decimal("100"),
            purchase_rate=Decimal("150000"),
            shelf_life_days=30,
        )

    def test_dw14_ac2_chu_mo_lo_buoc_chot_co_ai_level_c(self):
        """DW-14-AC2: Chủ mở lô -> bước chốt có ai={'level': 'C', 'label': 'AI soạn nháp chốt lô'}."""
        resp = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()

        steps = {s["key"]: s for s in data["next_steps"]}
        self.assertIn("close", steps)
        close_step = steps["close"]

        self.assertIsNotNone(close_step.get("ai"))
        self.assertEqual(close_step["ai"]["level"], "C")
        self.assertEqual(close_step["ai"]["label"], "AI soạn nháp chốt lô")

    def test_dw14_ac2_quan_ly_thieu_quyen_buoc_chot_ai_null(self):
        """DW-14-AC2: Quản lý thiếu quyền chốt lô -> bước chốt có ai=null."""
        resp = self.c_ql.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()

        steps = {s["key"]: s for s in data["next_steps"]}
        self.assertIn("close", steps)
        close_step = steps["close"]

        # Quản lý không có quyền inventory.close_batch -> ai=null
        self.assertIsNone(close_step.get("ai"))

    @override_settings(AI_ENABLED=False)
    def test_dw14_ac8_ai_disabled_ai_null(self):
        """DW-14-AC8: AI_ENABLED=false -> guidance vẫn 200, nhưng ai=null."""
        resp = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()

        steps = {s["key"]: s for s in data["next_steps"]}
        self.assertIn("close", steps)
        close_step = steps["close"]
        self.assertIsNone(close_step.get("ai"))

    def test_resolve_step_ai_unit(self):
        """Kiểm thử unit test hàm resolve_step_ai và step_to_dict với các điều kiện."""
        step_no_cmd = NextStep(key="test", label="Test", actor="user", allowed=True, command=None)
        self.assertIsNone(resolve_step_ai(step_no_cmd, self.chu))

        step_close = NextStep(key="close", label="Chốt lô", actor="user", allowed=True, command="inventory.batch.close")
        self.assertIsNone(resolve_step_ai(step_close, None))

        step_fake = NextStep(key="fake", label="Lệnh giả", actor="user", allowed=True, command="fake.command.id")
        self.assertIsNone(resolve_step_ai(step_fake, self.chu))

        d = step_to_dict(step_close, user=self.chu)
        self.assertEqual(d["ai"], {"level": "C", "label": "AI soạn nháp chốt lô"})
