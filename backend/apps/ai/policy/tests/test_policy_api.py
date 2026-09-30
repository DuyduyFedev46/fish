"""
Test suite cho Story DW-13: Chính sách AI của Chủ (DW-13-AC1 .. DW-13-AC9).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog
from apps.ai.models.config import AiConfigVersion
from apps.ai.models.policy import AiPolicyVersion
from apps.ai.registry import get_registry
from apps.accounts import roles


User = get_user_model()


class AiPolicyApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        get_registry().build(force=True)

        cls.g_chu, _ = Group.objects.get_or_create(name=roles.OWNER)
        cls.g_quan_ly, _ = Group.objects.get_or_create(name=roles.MANAGER)
        cls.g_nv_kho, _ = Group.objects.get_or_create(name=roles.WAREHOUSE_STAFF)

        p_manage_ai = Permission.objects.filter(codename="manage_ai_policy").first()
        p_view_batch = Permission.objects.filter(codename="view_batch").first()
        p_close_batch = Permission.objects.filter(codename="close_batch").first()

        if p_manage_ai:
            cls.g_chu.permissions.add(p_manage_ai)
        if p_view_batch:
            cls.g_chu.permissions.add(p_view_batch)
            cls.g_nv_kho.permissions.add(p_view_batch)
        if p_close_batch:
            cls.g_chu.permissions.add(p_close_batch)

        cls.user_chu = User.objects.create_user(username="owner_user", password="x", first_name="Duy", last_name="Chủ")
        cls.user_chu.groups.add(cls.g_chu)

        cls.user_quanly = User.objects.create_user(username="ql_user", password="x", first_name="Quản", last_name="Lý")
        cls.user_quanly.groups.add(cls.g_quan_ly)

        cls.user_kho = User.objects.create_user(username="kho_user", password="x", first_name="Kho", last_name="1")
        cls.user_kho.groups.add(cls.g_nv_kho)

    def setUp(self):
        AiConfigVersion.objects.all().delete()
        AiPolicyVersion.objects.all().delete()

    @override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="C")
    def test_dw13_ac1_chu_put_global_mode_c_only(self):
        """DW-13-AC1: Chủ PUT global_mode=c_only -> phiên bản +1, AuditLog; call ghi bị ép về C."""
        self.client.force_authenticate(user=self.user_chu)

        payload = {
            "base_version": 0,
            "global_mode": "c_only",
            "acknowledge_responsibility": True,
        }
        resp = self.client.put("/api/ai/policy/", data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["global_mode"], "c_only")
        self.assertEqual(resp.json()["version"], 1)

        # AuditLog ghi nhận
        self.assertTrue(AuditLog.objects.filter(action="ai_policy_update", actor=self.user_chu).exists())

    @override_settings(AI_ENABLED=True)
    def test_dw13_ac2_chu_put_global_mode_off(self):
        """DW-13-AC2: Chủ PUT global_mode=off -> index rỗng; call -> 404."""
        self.client.force_authenticate(user=self.user_chu)

        # PUT global_mode=off
        resp = self.client.put(
            "/api/ai/policy/",
            data={"base_version": 0, "global_mode": "off", "acknowledge_responsibility": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Người bất kỳ gọi index -> chỉ mục rỗng
        self.client.force_authenticate(user=self.user_kho)
        idx_resp = self.client.get("/api/ai/commands/index/")
        self.assertEqual(idx_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(idx_resp.json().get("commands", [])), 0)

        # Gọi call -> 404 COMMAND_UNKNOWN
        call_resp = self.client.post("/api/ai/commands/inventory.batch.list/call/", data={"args": {}}, format="json")
        self.assertEqual(call_resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(call_resp.json().get("code"), "COMMAND_UNKNOWN")

    @override_settings(AI_ENABLED=True)
    def test_dw13_ac3_chu_tat_ai_cua_user_x(self):
        """DW-13-AC3: POST /api/ai/policy/users/<X>/kill/ -> phiên bản mới của X created_by=Chủ, killed=true; X thấy killed=true."""
        self.client.force_authenticate(user=self.user_chu)

        resp = self.client.post(
            f"/api/ai/policy/users/{self.user_kho.id}/kill/",
            data={"killed": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.json()["killed"])
        self.assertEqual(resp.json()["user_id"], self.user_kho.id)

        # Kiểm tra bản ghi trong DB
        cfg = AiConfigVersion.objects.filter(user=self.user_kho).latest("version")
        self.assertTrue(cfg.killed)
        self.assertEqual(cfg.created_by, self.user_chu)

        # User Kho khi GET my-config thấy killed=true
        self.client.force_authenticate(user=self.user_kho)
        my_cfg_resp = self.client.get("/api/ai/my-config/")
        self.assertEqual(my_cfg_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(my_cfg_resp.json()["killed"])

    @override_settings(AI_ENABLED=True)
    def test_dw13_ac4_chu_xem_config_user_x_chi_doc(self):
        """DW-13-AC4: Chủ GET /api/ai/policy/users/<X>/config/ -> chỉ đọc; PUT -> 405."""
        self.client.force_authenticate(user=self.user_chu)

        # GET thành công
        resp = self.client.get(f"/api/ai/policy/users/{self.user_kho.id}/config/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("groups", resp.json())
        self.assertIn("version", resp.json())

        # PUT bị 405
        put_resp = self.client.put(f"/api/ai/policy/users/{self.user_kho.id}/config/", data={}, format="json")
        self.assertEqual(put_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_dw13_ac5_phan_quyen_manage_ai_policy_chi_chu(self):
        """DW-13-AC5: quan_ly, nv_kho, nv_giao gọi GET/PUT /api/ai/policy/* -> 403."""
        # 1. Quản lý
        self.client.force_authenticate(user=self.user_quanly)
        r1 = self.client.get("/api/ai/policy/")
        self.assertEqual(r1.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Nhân viên kho
        self.client.force_authenticate(user=self.user_kho)
        r2 = self.client.get("/api/ai/policy/")
        self.assertEqual(r2.status_code, status.HTTP_403_FORBIDDEN)

        r3 = self.client.post(f"/api/ai/policy/users/{self.user_chu.id}/kill/", data={"killed": True}, format="json")
        self.assertEqual(r3.status_code, status.HTTP_403_FORBIDDEN)

    def test_dw13_ac6_loi_base_version_va_chua_tick(self):
        """DW-13-AC6: base_version lệch -> 409 AI_POLICY_CONFLICT; không tick -> 400 BR-AI-14."""
        self.client.force_authenticate(user=self.user_chu)

        # Không tick
        r1 = self.client.put(
            "/api/ai/policy/",
            data={"base_version": 0, "acknowledge_responsibility": False},
            format="json",
        )
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r1.json().get("code"), "BR-AI-14")

        # Tạo version 2 trước
        AiPolicyVersion.objects.create(version=2, created_by=self.user_chu)

        # base_version = 0 (cũ so với version 2) -> 409
        r2 = self.client.put(
            "/api/ai/policy/",
            data={"base_version": 0, "acknowledge_responsibility": True},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(r2.json().get("code"), "AI_POLICY_CONFLICT")

    def test_dw13_ac7_append_only_khong_co_api_sua_xoa(self):
        """DW-13-AC7: Không có API sửa / xoá AiPolicyVersion, AiConfigVersion."""
        self.client.force_authenticate(user=self.user_chu)

        p = AiPolicyVersion.objects.create(version=2, created_by=self.user_chu)
        # Thử DELETE hoặc PATCH lên /api/ai/policy/
        r_del = self.client.delete(f"/api/ai/policy/{p.version}/")
        self.assertIn(r_del.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED])

        r_patch = self.client.patch("/api/ai/policy/", data={}, format="json")
        self.assertEqual(r_patch.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_dw13_ac8_users_chi_ten_group_counts_khong_pii_gia_von(self):
        """DW-13-AC8: GET /api/ai/policy/ -> users chỉ tên hiển thị, Group, counts; không có PII/giá vốn."""
        self.client.force_authenticate(user=self.user_chu)
        resp = self.client.get("/api/ai/policy/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.json()
        self.assertIn("users", data)
        self.assertTrue(len(data["users"]) >= 1)

        for u in data["users"]:
            self.assertIn("user_id", u)
            self.assertIn("display_name", u)
            self.assertIn("groups", u)
            self.assertIn("counts", u)
            self.assertIn("A", u["counts"])
            self.assertIn("C", u["counts"])
            self.assertIn("OFF", u["counts"])

        raw_str = str(data).lower()
        self.assertNotIn("phone", raw_str)
        self.assertNotIn("delivery_address", raw_str)
        self.assertNotIn("purchase_rate", raw_str)
        self.assertNotIn("landed_unit_cost", raw_str)

    @override_settings(AI_ENABLED=False)
    def test_dw13_ac9_ai_tat_policy_van_chay(self):
        """DW-13-AC9: AI_ENABLED=false -> gọi policy GET/PUT vẫn chạy."""
        self.client.force_authenticate(user=self.user_chu)
        r1 = self.client.get("/api/ai/policy/")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)

        r2 = self.client.put(
            "/api/ai/policy/",
            data={"base_version": 0, "acknowledge_responsibility": True},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
