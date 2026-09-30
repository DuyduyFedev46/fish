"""
Test suite cho Story DW-24: Công tắc vùng đỏ của Chủ (DW-24-AC1..AC7, BR-AI-07, BR-AI-18, BR-AI-27).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction, AiConfigVersion, AiPolicyVersion
from apps.ai.registry import get_registry
from apps.common.tests.fixtures import client_for, make_user
from apps.accounts import roles

User = get_user_model()


class RedZoneSwitchTests(TestCase):
    def setUp(self):
        get_registry().build(force=True)

        self.u_chu = make_user("chu_rz", roles.OWNER)
        self.u_quanly = make_user("ql_rz", roles.MANAGER)
        self.u_kho = make_user("kho_rz", roles.WAREHOUSE_STAFF)

        self.client_chu = client_for(self.u_chu)
        self.client_quanly = client_for(self.u_quanly)
        self.client_kho = client_for(self.u_kho)

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_dw24_ac1_staging_policy_contains_3_red_zone_entries_default_closed(self):
        """DW-24-AC1: Staging, Chủ GET policy -> 3 mục vùng đỏ có can_do, cannot_do, legal_note, mặc định open=false."""
        res = self.client_chu.get("/api/ai/policy/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        red_zone = data.get("red_zone", [])
        self.assertEqual(len(red_zone), 3)

        rz_dict = {item["perm"]: item for item in red_zone}
        self.assertIn("inventory.close_batch", rz_dict)
        self.assertIn("sales.confirm_refund", rz_dict)
        self.assertIn("sales.confirm_payment_manual", rz_dict)

        # Mặc định open=False
        for perm, item in rz_dict.items():
            self.assertFalse(item["open"])
            self.assertTrue(len(item["can_do"]) > 5)
            self.assertTrue(len(item["cannot_do"]) > 5)
            self.assertTrue(len(item["legal_note"]) > 5)

        self.assertEqual(rz_dict["inventory.close_batch"]["delay_minutes"], 30)

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_dw24_ac2_chu_put_open_close_batch_allows_b_in_my_config(self):
        """DW-24-AC2: Chủ PUT mở inventory.close_batch -> GET my-config của Chủ có choices B, locked_reason=None."""
        res_put = self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "red_zone": {"inventory.close_batch": True},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        self.assertEqual(res_put.json()["version"], 1)

        # Kiểm tra AuditLog
        self.assertTrue(
            AuditLog.objects.filter(
                action="ai_policy_update",
                actor=self.u_chu,
            ).exists()
        )

        # GET my-config của Chủ
        res_cfg = self.client_chu.get("/api/ai/my-config/")
        self.assertEqual(res_cfg.status_code, status.HTTP_200_OK)
        cfg_data = res_cfg.json()

        # Tìm lệnh inventory.batch.close
        close_cmd = None
        for grp in cfg_data["groups"]:
            for cmd in grp["commands"]:
                if cmd["id"] == "inventory.batch.close":
                    close_cmd = cmd
                    break
        self.assertIsNotNone(close_cmd)
        self.assertIn("B", close_cmd["choices"])
        self.assertEqual(close_cmd["max_level"], "B")
        self.assertIsNone(close_cmd["locked_reason"])

        # Chủ PUT override lên B thành công
        res_override = self.client_chu.put(
            "/api/ai/my-config/",
            {
                "base_version": 0,
                "overrides": {"inventory.batch.close": "B"},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res_override.status_code, status.HTTP_200_OK)

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=False)
    def test_dw24_ac3_production_ready_false_blocks_opening_red_zone_400(self):
        """DW-24-AC3: AI_PRODUCTION_READY=false (production) -> PUT mở vùng đỏ bị chặn với 400 BR-AI-27."""
        res = self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "red_zone": {"inventory.close_batch": True},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["code"], "BR-AI-27")

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_dw24_ac4_closing_red_zone_downgrades_user_config_and_scheduled_actions(self):
        """DW-24-AC4: Chủ đang để B, có việc SCHEDULED -> Chủ đóng công tắc -> cấu hình rơi về C ngay; việc SCHEDULED về PENDING."""
        # 1. Mở vùng đỏ và Chủ đặt B
        self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "red_zone": {"inventory.close_batch": True},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.client_chu.put(
            "/api/ai/my-config/",
            {
                "base_version": 0,
                "overrides": {"inventory.batch.close": "B"},
                "acknowledge_responsibility": True,
            },
            format="json",
        )

        # 2. Tạo việc SCHEDULED cho lệnh chốt lô
        action = AiAction.objects.create(
            command="inventory.batch.close",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.B,
            status=AiAction.Status.SCHEDULED,
            owner=self.u_chu,
        )

        # 3. Chủ đóng lại công tắc
        res_close = self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 1,
                "red_zone": {"inventory.close_batch": False},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res_close.status_code, status.HTTP_200_OK)

        # 4. Kiểm tra cấu hình rơi về C ngay
        res_cfg = self.client_chu.get("/api/ai/my-config/")
        close_cmd = None
        for grp in res_cfg.json()["groups"]:
            for cmd in grp["commands"]:
                if cmd["id"] == "inventory.batch.close":
                    close_cmd = cmd
                    break
        self.assertEqual(close_cmd["level"], "C")
        self.assertNotIn("B", close_cmd["choices"])
        self.assertIsNotNone(close_cmd["locked_reason"])
        self.assertEqual(close_cmd["locked_reason"]["code"], "BR-AI-18")

        # 5. Việc SCHEDULED rơi về PENDING (mức C)
        action.refresh_from_db()
        self.assertEqual(action.status, AiAction.Status.PENDING)
        self.assertEqual(action.level, AiAction.Level.C)
        self.assertEqual(action.downgrade_reason["code"], "AI_RED_ZONE_CLOSED")

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True)
    def test_dw24_ac5_quan_ly_cannot_put_policy_or_see_red_zone_commands(self):
        """DW-24-AC5: quan_ly gọi PUT policy -> 403; gọi GET my-config -> không thấy 3 lệnh vùng đỏ."""
        res_put = self.client_quanly.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "global_mode": "c_only",
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res_put.status_code, status.HTTP_403_FORBIDDEN)

        # GET my-config của quan_ly
        res_cfg = self.client_quanly.get("/api/ai/my-config/")
        self.assertEqual(res_cfg.status_code, status.HTTP_200_OK)
        cfg_data = res_cfg.json()

        all_cmd_ids = [cmd["id"] for grp in cfg_data["groups"] for cmd in grp["commands"]]
        self.assertNotIn("inventory.batch.close", all_cmd_ids)
        self.assertNotIn("sales.refund.confirm", all_cmd_ids)
        self.assertNotIn("sales.salesorder.confirm_payment", all_cmd_ids)

    def test_dw24_ac6_action_with_red_zone_perm_follows_switch(self):
        """DW-24-AC6: Kiểm tra cơ chế khoá theo quyền: spec có quyền close_batch luôn tuân thủ công tắc vùng đỏ."""
        registry = get_registry()
        spec = registry.get("inventory.batch.close")
        self.assertIsNotNone(spec)
        self.assertTrue(spec.red_zone)
        self.assertIn("inventory.close_batch", spec.required_perms)

    @override_settings(AI_ENABLED=False)
    def test_dw24_ac7_ai_disabled_can_still_get_and_put_policy(self):
        """DW-24-AC7: AI_ENABLED=false -> Chủ vẫn GET và PUT policy bình thường."""
        res_get = self.client_chu.get("/api/ai/policy/")
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)

        res_put = self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "global_mode": "c_only",
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
