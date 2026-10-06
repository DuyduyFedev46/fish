"""Lô dọn chữ AI — `/api/auth/me/` có `ai_features_enabled`, `capabilities` bỏ `ai.*` khi tắt (02b 2.1)."""
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user

URL = "/api/auth/me/"


class MeAiFlagTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner_fake", roles.OWNER)

    @override_settings(AI_ENABLED=False)
    def test_off_hides_ai_capability_but_keeps_raw_permissions(self):
        body = client_for(self.owner).get(URL).json()
        self.assertIs(body["ai_features_enabled"], False)
        self.assertFalse([c for c in body["capabilities"] if c["code"].startswith("ai.")])
        self.assertIn("ai.manage_ai_policy", body["permissions"])
        self.assertTrue(body["capabilities"])  # các việc khác còn nguyên

    @override_settings(AI_ENABLED=True)
    def test_on_shows_ai_capability(self):
        body = client_for(self.owner).get(URL).json()
        self.assertIs(body["ai_features_enabled"], True)
        self.assertIn("ai.manage_ai_policy", [c["code"] for c in body["capabilities"]])
        self.assertIn("ai.manage_ai_policy", body["permissions"])

    @override_settings(AI_ENABLED=True)
    def test_emergency_off_switch_does_not_flip_flag(self):
        """Chủ tắt khẩn (global_mode=off thật trong DB): cờ giao diện vẫn theo env, để còn màn bật lại."""
        from apps.ai.models.policy import AiPolicyVersion
        from apps.ai.status.services import is_ai_enabled

        AiPolicyVersion.objects.create(
            version=999, global_mode=AiPolicyVersion.GlobalMode.OFF, created_by=self.owner)
        self.assertFalse(is_ai_enabled())  # công tắc tắt khẩn đang có hiệu lực
        body = client_for(self.owner).get(URL).json()
        self.assertIs(body["ai_features_enabled"], True)
        self.assertIn("ai.manage_ai_policy", [c["code"] for c in body["capabilities"]])

    def test_anonymous_gets_401(self):
        self.assertEqual(APIClient().get(URL).status_code, 401)
