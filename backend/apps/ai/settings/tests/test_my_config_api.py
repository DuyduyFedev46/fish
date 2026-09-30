"""
Test suite cho Story DW-12: Màn 'AI của tôi' (DW-12-AC1 .. DW-12-AC11).
"""
import subprocess
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog
from apps.ai.models.config import AiConfigVersion
from apps.ai.models.policy import AiPolicyVersion
from apps.ai.registry import get_registry
from apps.ai import command_groups
from apps.accounts import roles


User = get_user_model()


class MyConfigApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        get_registry().build(force=True)

        # 4 nhóm người dùng theo phân quyền
        cls.g_chu, _ = Group.objects.get_or_create(name=roles.OWNER)
        cls.g_quan_ly, _ = Group.objects.get_or_create(name=roles.MANAGER)
        cls.g_nv_kho, _ = Group.objects.get_or_create(name=roles.WAREHOUSE_STAFF)
        cls.g_nv_giao, _ = Group.objects.get_or_create(name=roles.DELIVERY_STAFF)

        # Gán quyền mẫu
        p_close = Permission.objects.filter(codename="close_batch").first()
        p_view_batch = Permission.objects.filter(codename="view_batch").first()
        p_change_batch = Permission.objects.filter(codename="change_batch").first()
        p_view_receipt = Permission.objects.filter(codename="view_purchasereceipt").first()
        p_submit_receipt = Permission.objects.filter(codename="submit_purchasereceipt").first()
        p_confirm_refund = Permission.objects.filter(codename="confirm_refund").first()
        p_view_refund = Permission.objects.filter(codename="view_refund").first()
        p_manage_ai = Permission.objects.filter(codename="manage_ai_policy").first()

        for p in [p_close, p_view_batch, p_change_batch, p_view_receipt, p_submit_receipt, p_confirm_refund, p_view_refund, p_manage_ai]:
            if p:
                cls.g_chu.permissions.add(p)

        for p in [p_view_batch, p_view_receipt, p_submit_receipt]:
            if p:
                cls.g_nv_kho.permissions.add(p)

        cls.user_chu = User.objects.create_user(username="owner_user", password="x", first_name="Duy", last_name="Chủ")
        cls.user_chu.groups.add(cls.g_chu)

        cls.user_kho = User.objects.create_user(username="kho_user", password="x", first_name="Kho", last_name="1")
        cls.user_kho.groups.add(cls.g_nv_kho)

    def setUp(self):
        # Đảm bảo reset registry và policy
        AiConfigVersion.objects.all().delete()
        AiPolicyVersion.objects.all().delete()

    @override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="C")
    def test_dw12_ac1_nv_kho_chua_cau_hinh(self):
        """DW-12-AC1: nv_kho chưa cấu hình -> chỉ lệnh trong quyền, chia 3 nhóm; ghi=C (OFF, C), đọc=A (OFF, A)."""
        self.client.force_authenticate(user=self.user_kho)
        resp = self.client.get("/api/ai/my-config/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.json()
        self.assertTrue(data["ai_enabled"])
        self.assertEqual(data["version"], 0)
        self.assertFalse(data["killed"])
        self.assertEqual(data["write_levels_allowed"], ["OFF", "C"])

        groups = {g["group"]: g for g in data["groups"]}
        self.assertIn(command_groups.PURCHASING, groups)

        # Lệnh trong nhóm thu mua của nv_kho: có batch.list (đọc), submit_purchasereceipt nếu có
        commands = {c["id"]: c for c in groups[command_groups.PURCHASING]["commands"]}
        if "inventory.batch.list" in commands:
            cmd = commands["inventory.batch.list"]
            self.assertEqual(cmd["kind"], "read")
            self.assertEqual(cmd["level"], "A")
            self.assertEqual(cmd["choices"], ["OFF", "A"])

        # nv_kho không có quyền chốt lô -> không có inventory.batch.close
        self.assertNotIn("inventory.batch.close", commands)

    @override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="C")
    def test_dw12_ac2_put_hieu_luc_tuc_thi(self):
        """DW-12-AC2: Tick trách nhiệm -> PUT đặt list=OFF -> version+1, AuditLog, call trả 404 ngay."""
        self.client.force_authenticate(user=self.user_kho)

        # PUT đặt inventory.batch.list = OFF
        payload = {
            "base_version": 0,
            "groups": {command_groups.PURCHASING: {"read": "A", "write": "C"}},
            "overrides": {"inventory.batch.list": "OFF"},
            "acknowledge_responsibility": True,
        }
        resp = self.client.put("/api/ai/my-config/", data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["version"], 1)

        # 1 dòng AiConfigVersion mới, created_by = user_kho
        cfg = AiConfigVersion.objects.filter(user=self.user_kho).latest("version")
        self.assertEqual(cfg.version, 1)
        self.assertEqual(cfg.overrides.get("inventory.batch.list"), "OFF")

        # Có AuditLog
        self.assertTrue(AuditLog.objects.filter(action="ai_config_update", actor=self.user_kho).exists())

        # Call lệnh đó ngay sau -> 404 (COMMAND_UNKNOWN vì effective_level = OFF)
        call_resp = self.client.post(
            "/api/ai/commands/inventory.batch.list/call/",
            data={"args": {}},
            format="json",
        )
        self.assertEqual(call_resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(call_resp.json().get("code"), "COMMAND_UNKNOWN")

    @override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="C")
    def test_dw12_ac3_loi_chua_tick_vuot_tran_xung_dot(self):
        """DW-12-AC3: Không tick -> 400 BR-AI-14; vượt trần -> 400 BR-AI-19; base_version cũ -> 409 AI_CONFIG_CONFLICT."""
        self.client.force_authenticate(user=self.user_kho)

        # 1. Không tick trách nhiệm
        p1 = {
            "base_version": 0,
            "overrides": {},
            "acknowledge_responsibility": False,
        }
        r1 = self.client.put("/api/ai/my-config/", data=p1, format="json")
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r1.json().get("code"), "BR-AI-14")

        # 2. Vượt trần C (đặt B khi env trần C)
        p2 = {
            "base_version": 0,
            "overrides": {"purchasing.purchasereceipt.submit": "B"},
            "acknowledge_responsibility": True,
        }
        r2 = self.client.put("/api/ai/my-config/", data=p2, format="json")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r2.json().get("code"), "BR-AI-19")
        self.assertIn("purchasing.purchasereceipt.submit", r2.json().get("errors", {}))

        # 3. base_version cũ (xung đột phiên bản)
        # Tạo 1 config version 1 trước
        AiConfigVersion.objects.create(
            user=self.user_kho,
            version=1,
            created_by=self.user_kho,
        )
        p3 = {
            "base_version": 0,  # cũ hơn version 1
            "overrides": {},
            "acknowledge_responsibility": True,
        }
        r3 = self.client.put("/api/ai/my-config/", data=p3, format="json")
        self.assertEqual(r3.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(r3.json().get("code"), "AI_CONFIG_CONFLICT")
        self.assertEqual(r3.json().get("current_version"), 1)

    @override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="C")
    def test_dw12_ac4_quyenh1_lenh_ngoai_quyen(self):
        """DW-12-AC4: nv_kho PUT lệnh sales.refund.confirm -> 400 BR-AI-19 'Lệnh ngoài quyền của bạn'."""
        self.client.force_authenticate(user=self.user_kho)
        payload = {
            "base_version": 0,
            "overrides": {"sales.refund.confirm": "C"},
            "acknowledge_responsibility": True,
        }
        resp = self.client.put("/api/ai/my-config/", data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.json().get("code"), "BR-AI-19")
        self.assertIn("sales.refund.confirm", resp.json().get("errors", {}))
        self.assertIn("ngoài quyền", resp.json()["errors"]["sales.refund.confirm"].lower())

    @override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="C")
    def test_dw12_ac5_doi_group_lenh_tu_dong_vo_hieu(self):
        """DW-12-AC5: nv_kho có override; bị gỡ khỏi nv_kho -> GET không còn lệnh; call -> 404; override vẫn nằm trong DB."""
        self.client.force_authenticate(user=self.user_kho)
        # Cấu hình override cho inventory.batch.list
        AiConfigVersion.objects.create(
            user=self.user_kho,
            version=1,
            overrides={"inventory.batch.list": "A"},
            created_by=self.user_kho,
        )

        # Gỡ user khỏi g_nv_kho
        self.user_kho.groups.clear()

        # GET my-config -> không còn inventory.batch.list vì thiếu quyền
        resp = self.client.get("/api/ai/my-config/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        all_cmd_ids = [
            c["id"]
            for g in resp.json()["groups"]
            for c in g["commands"]
        ]
        self.assertNotIn("inventory.batch.list", all_cmd_ids)

        # Call -> 404
        call_resp = self.client.post("/api/ai/commands/inventory.batch.list/call/", data={"args": {}}, format="json")
        self.assertEqual(call_resp.status_code, status.HTTP_404_NOT_FOUND)

        # DB phiên bản cũ vẫn lưu override (append-only)
        old_cfg = AiConfigVersion.objects.get(user=self.user_kho, version=1)
        self.assertEqual(old_cfg.overrides.get("inventory.batch.list"), "A")

    @override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="C")
    def test_dw12_ac6_tat_ai_cua_toi(self):
        """DW-12-AC6: POST /api/ai/my-config/kill/ {"killed": true} -> version+1 killed=true; bật lại được."""
        self.client.force_authenticate(user=self.user_kho)
        resp = self.client.post("/api/ai/my-config/kill/", data={"killed": True}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["killed"], True)
        self.assertEqual(resp.json()["version"], 1)

        cfg = AiConfigVersion.objects.get(user=self.user_kho, version=1)
        self.assertTrue(cfg.killed)

        # Bật lại
        resp2 = self.client.post("/api/ai/my-config/kill/", data={"killed": False}, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertFalse(resp2.json()["killed"])
        self.assertEqual(resp2.json()["version"], 2)

    @override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="C")
    def test_dw12_ac7_vung_do_choices_va_locked_reason(self):
        """DW-12-AC7: chu GET -> inventory.batch.close có choices=["OFF", "C"], locked_reason.code="BR-AI-18"."""
        self.client.force_authenticate(user=self.user_chu)
        resp = self.client.get("/api/ai/my-config/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        groups = {g["group"]: g for g in resp.json()["groups"]}
        thu_mua_cmds = {c["id"]: c for c in groups[command_groups.PURCHASING]["commands"]}
        self.assertIn("inventory.batch.close", thu_mua_cmds)

        cmd = thu_mua_cmds["inventory.batch.close"]
        self.assertEqual(cmd["choices"], ["OFF", "C"])
        self.assertTrue(cmd["red_zone"])
        self.assertIsNotNone(cmd["locked_reason"])
        self.assertEqual(cmd["locked_reason"]["code"], "BR-AI-18")

    def test_dw12_ac8_khong_co_endpoint_sua_ho(self):
        """DW-12-AC8: PUT /api/ai/policy/users/<id>/config/ -> 405 Method Not Allowed."""
        self.client.force_authenticate(user=self.user_chu)
        resp = self.client.put(f"/api/ai/policy/users/{self.user_kho.id}/config/", data={}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @override_settings(AI_ENABLED=False)
    def test_dw12_ac9_ai_tat_van_200(self):
        """DW-12-AC9: AI_ENABLED=false -> GET/PUT/kill vẫn 200, ai_enabled=false."""
        self.client.force_authenticate(user=self.user_kho)

        # GET
        r1 = self.client.get("/api/ai/my-config/")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertFalse(r1.json()["ai_enabled"])

        # PUT
        r2 = self.client.put(
            "/api/ai/my-config/",
            data={"base_version": 0, "acknowledge_responsibility": True},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)

        # Kill
        r3 = self.client.post("/api/ai/my-config/kill/", data={"killed": True}, format="json")
        self.assertEqual(r3.status_code, status.HTTP_200_OK)

    @override_settings(AI_ENABLED=True)
    def test_dw12_ac10_group_khong_hard_code_va_discipline_grep(self):
        """DW-12-AC10: Group cskh chỉ lệnh qua quyền; grep không có hardcoded group name."""
        g_cskh, _ = Group.objects.get_or_create(name=roles.CUSTOMER_SERVICE)
        p_view_refund = Permission.objects.filter(codename="view_refund").first()
        if p_view_refund:
            g_cskh.permissions.add(p_view_refund)

        u_cskh = User.objects.create_user(username="nv_cskh", password="x")
        u_cskh.groups.add(g_cskh)

        self.client.force_authenticate(user=u_cskh)
        resp = self.client.get("/api/ai/my-config/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Chỉ có các lệnh mà cskh có quyền
        all_cmd_ids = [
            c["id"]
            for g in resp.json()["groups"]
            for c in g["commands"]
        ]
        self.assertNotIn("inventory.batch.close", all_cmd_ids)
        self.assertNotIn("inventory.batch.list", all_cmd_ids)

        # Test kỷ luật grep trong backend/apps/ai
        cmd = 'grep -rnE "\"(chu|quan_ly|nv_kho|nv_giao|cskh)\"" backend/apps/ai --include="*.py" | grep -v tests | grep -v "0002_grant_manage_ai_policy.py"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        self.assertEqual(res.stdout.strip(), "", f"Phát hiện hardcoded group trong apps/ai: {res.stdout}")

    def test_dw12_ac11_my_config_versions_khong_pii(self):
        """DW-12-AC11: GET /api/ai/my-config/versions/ chỉ tên nhân viên, không dữ liệu khách."""
        AiConfigVersion.objects.create(
            user=self.user_kho,
            version=1,
            created_by=self.user_kho,
            overrides={"inventory.batch.list": "OFF"},
        )
        self.client.force_authenticate(user=self.user_kho)
        resp = self.client.get("/api/ai/my-config/versions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.json()
        results = data.get("results", [])
        self.assertTrue(len(results) >= 1)
        first = results[0]
        self.assertIn("version", first)
        self.assertIn("created_by_display", first)
        self.assertIn("changes", first)
        # Không có phone, customer, address
        raw_text = str(data).lower()
        self.assertNotIn("phone", raw_text)
        self.assertNotIn("delivery_address", raw_text)
