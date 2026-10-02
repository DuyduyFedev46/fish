"""
GET /api/ai/status/ (S05, Lô bổ sung A #1): luôn 200 kể cả AI tắt, ngân sách chỉ Chủ thấy.
"""
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts import roles
from apps.ai.models.policy import AiPolicyVersion
from apps.common.tests.fixtures import client_for, make_user

URL = "/api/ai/status/"
MODEL_SETTINGS = {
    "AI_MODEL_NAME": "qwen-test",
    "AI_MODEL_VERSION": "v1",
    "AI_MODEL_GGUF_URL": "https://example.test/model.gguf",
}


class AiStatusApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("owner_st", roles.OWNER)
        cls.manager = make_user("manager_st", roles.MANAGER)
        cls.warehouse = make_user("kho_st", roles.WAREHOUSE_STAFF)
        cls.courier = make_user("giao_st", roles.DELIVERY_STAFF)

    def test_anonymous_gets_401(self):
        self.assertEqual(client_for(None).get(URL).status_code, 401)

    @override_settings(AI_ENABLED=False, **MODEL_SETTINGS)
    def test_ai_off_returns_200_with_everything_closed(self):
        res = client_for(self.owner).get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json(),
            {"ai_enabled": False, "cloud_enabled": False, "model": None, "budget": None},
        )

    @override_settings(AI_ENABLED=True, AI_CLOUD_ENABLED=False, **MODEL_SETTINGS)
    def test_ai_on_shape_for_every_role(self):
        for user in (self.owner, self.manager, self.warehouse, self.courier):
            res = client_for(user).get(URL)
            self.assertEqual(res.status_code, 200, user.username)
            body = res.json()
            self.assertEqual(set(body), {"ai_enabled", "cloud_enabled", "model", "budget"})
            self.assertIs(body["ai_enabled"], True)
            self.assertIs(body["cloud_enabled"], False)
            self.assertEqual(
                body["model"],
                {"name": "qwen-test", "version": "v1", "gguf_url": "https://example.test/model.gguf"},
            )

    @override_settings(AI_ENABLED=True, AI_CLOUD_ENABLED=True, **MODEL_SETTINGS)
    def test_cloud_enabled_follows_its_own_switch(self):
        self.assertIs(client_for(self.warehouse).get(URL).json()["cloud_enabled"], True)

    @override_settings(AI_ENABLED=False, AI_CLOUD_ENABLED=True, **MODEL_SETTINGS)
    def test_cloud_never_on_when_ai_off(self):
        self.assertIs(client_for(self.owner).get(URL).json()["cloud_enabled"], False)

    @override_settings(AI_ENABLED=True, AI_MODEL_NAME="", AI_MODEL_VERSION="", AI_MODEL_GGUF_URL="")
    def test_model_null_when_not_chosen_yet(self):
        res = client_for(self.manager).get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.json()["model"])

    @override_settings(AI_ENABLED=True, AI_MODEL_NAME="x", AI_MODEL_VERSION="", AI_MODEL_GGUF_URL="")
    def test_model_null_when_url_missing(self):
        self.assertIsNone(client_for(self.manager).get(URL).json()["model"])

    @override_settings(
        AI_ENABLED=True, AI_CLOUD_MONTHLY_BUDGET_VND=200000, AI_CLOUD_ALERT_PCT=80, **MODEL_SETTINGS
    )
    def test_budget_only_for_owner(self):
        body = client_for(self.owner).get(URL).json()
        self.assertEqual(body["budget"], {"spent_vnd": 0, "limit_vnd": 200000, "status": "ok"})
        for user in (self.manager, self.warehouse, self.courier):
            self.assertIsNone(client_for(user).get(URL).json()["budget"], user.username)

    @override_settings(AI_ENABLED=True, **MODEL_SETTINGS)
    def test_global_mode_off_from_owner_policy_turns_status_off(self):
        AiPolicyVersion.objects.create(version=1, global_mode="off", created_by=self.owner)
        body = client_for(self.manager).get(URL).json()
        self.assertEqual(
            body, {"ai_enabled": False, "cloud_enabled": False, "model": None, "budget": None}
        )

    @override_settings(AI_ENABLED=True, **MODEL_SETTINGS)
    def test_policy_c_only_or_on_keeps_ai_enabled(self):
        AiPolicyVersion.objects.create(version=1, global_mode="off", created_by=self.owner)
        AiPolicyVersion.objects.create(version=2, global_mode="c_only", created_by=self.owner)
        self.assertIs(client_for(self.manager).get(URL).json()["ai_enabled"], True)

    @override_settings(AI_ENABLED=True, **MODEL_SETTINGS)
    def test_response_has_no_secrets_or_personal_data(self):
        text = client_for(self.owner).get(URL).content.decode()
        for needle in ("key", "token", "secret", "password", "phone", "address"):
            self.assertNotIn(needle, text.lower())

    @override_settings(AI_ENABLED=True, **MODEL_SETTINGS)
    def test_write_methods_not_allowed(self):
        self.assertEqual(client_for(self.owner).post(URL, {}, format="json").status_code, 405)
