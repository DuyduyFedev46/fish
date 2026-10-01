"""
RA-04 (A1-03, BR-AI-22): Chủ tắt AI của nhân viên thì chỉ Chủ bật lại được.
Nhân viên tự tắt thì vẫn tự bật lại được. Đường PUT /my-config/ không đổi được `killed`.
"""
from django.test import TestCase, override_settings

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.ai.models.config import AiConfigVersion
from apps.ai.policy.effective import effective_level
from apps.ai.registry import get_registry
from apps.common.tests.fixtures import client_for, make_user

WRITE_COMMAND_ID = "purchasing.purchasereceipt.receive_batches"
LOCKED_DETAIL = "Chủ đã tắt AI của bạn — chỉ Chủ bật lại được."


@override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="B")
class KillOwnershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        get_registry().build(force=True)
        cls.owner = make_user("ra04_owner", roles.OWNER)
        cls.warehouse = make_user("ra04_kho", roles.WAREHOUSE_STAFF)
        cls.dual = make_user("ra04_dual", roles.OWNER, roles.WAREHOUSE_STAFF)
        cls.spec = get_registry().get_spec(WRITE_COMMAND_ID)

    def setUp(self):
        # Nhân viên đặt lệnh ghi ở mức B để thấy rõ tắt khẩn hạ mức về C (V-DW4) rồi bật lại trả về B.
        for user in (self.warehouse, self.dual):
            AiConfigVersion.objects.create(
                user=user, version=1, overrides={WRITE_COMMAND_ID: "B"}, created_by=user,
            )

    def _owner_kill(self, target, killed):
        return client_for(self.owner).post(
            f"/api/ai/policy/users/{target.pk}/kill/", {"killed": killed}, format="json"
        )

    def _self_kill(self, user, killed):
        return client_for(user).post("/api/ai/my-config/kill/", {"killed": killed}, format="json")

    def _latest(self, user):
        return AiConfigVersion.objects.filter(user=user).order_by("-version").first()

    def _level(self, user):
        return effective_level(user, self.spec)

    def test_staff_cannot_reenable_ai_killed_by_owner(self):
        self.assertEqual(self._level(self.warehouse), "B")
        self.assertEqual(self._owner_kill(self.warehouse, True).status_code, 200)
        before = AiConfigVersion.objects.filter(user=self.warehouse).count()
        audits_before = AuditLog.objects.filter(action="ai_config_kill").count()

        resp = self._self_kill(self.warehouse, False)

        self.assertEqual(resp.status_code, 403, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "BR-AI-22")
        self.assertEqual(body["detail"], LOCKED_DETAIL)
        self.assertTrue(self._latest(self.warehouse).killed)
        self.assertEqual(AiConfigVersion.objects.filter(user=self.warehouse).count(), before)
        self.assertEqual(AuditLog.objects.filter(action="ai_config_kill").count(), audits_before)
        self.assertEqual(self._level(self.warehouse), "C")

    def test_staff_can_reenable_ai_they_killed_themselves(self):
        self.assertEqual(self._self_kill(self.warehouse, True).status_code, 200)
        self.assertEqual(self._level(self.warehouse), "C")
        resp = self._self_kill(self.warehouse, False)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(resp.json()["killed"])
        self.assertFalse(self._latest(self.warehouse).killed)
        self.assertEqual(self._level(self.warehouse), "B")

    def test_owner_can_reenable_ai_of_staff_and_staff_can_toggle_again(self):
        self._owner_kill(self.warehouse, True)
        resp = self._owner_kill(self.warehouse, False)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(resp.json()["killed"])
        self.assertEqual(self._level(self.warehouse), "B")
        # Sau khi Chủ bật lại, khoá của lần tắt cũ hết hiệu lực: nhân viên tự tắt/bật bình thường.
        self.assertEqual(self._self_kill(self.warehouse, True).status_code, 200)
        self.assertEqual(self._self_kill(self.warehouse, False).status_code, 200)

    def test_user_who_is_owner_and_warehouse_can_self_kill_and_reenable(self):
        self.assertEqual(self._self_kill(self.dual, True).status_code, 200)
        self.assertEqual(self._self_kill(self.dual, False).status_code, 200)
        self.assertFalse(self._latest(self.dual).killed)

    def test_owner_kill_after_staff_self_kill_still_locks(self):
        self._self_kill(self.warehouse, True)
        self._owner_kill(self.warehouse, True)
        self.assertEqual(self._self_kill(self.warehouse, False).status_code, 403)
        self.assertTrue(self._latest(self.warehouse).killed)

    def test_lock_survives_staff_saving_config_while_killed(self):
        self._owner_kill(self.warehouse, True)
        version = self._latest(self.warehouse).version
        resp = client_for(self.warehouse).put(
            "/api/ai/my-config/",
            {"base_version": version, "groups": {}, "overrides": {}, "acknowledge_responsibility": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(self._latest(self.warehouse).killed)
        self.assertEqual(self._self_kill(self.warehouse, False).status_code, 403)
        self.assertTrue(self._latest(self.warehouse).killed)

    def test_put_my_config_cannot_change_killed(self):
        self._owner_kill(self.warehouse, True)
        version = self._latest(self.warehouse).version
        resp = client_for(self.warehouse).put(
            "/api/ai/my-config/",
            {"base_version": version, "groups": {}, "overrides": {}, "killed": False,
             "acknowledge_responsibility": True},
            format="json",
        )
        self.assertIn(resp.status_code, (200, 400))
        self.assertTrue(self._latest(self.warehouse).killed)
        self.assertEqual(self._level(self.warehouse), "C")

    def test_kill_by_staff_is_still_allowed_when_not_killed(self):
        resp = self._self_kill(self.warehouse, True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["killed"])

    def test_audit_log_written_for_owner_reenable_and_self_toggle(self):
        self._owner_kill(self.warehouse, True)
        self._owner_kill(self.warehouse, False)
        self.assertEqual(AuditLog.objects.filter(action="ai_config_kill", actor=self.owner).count(), 2)
        self._self_kill(self.warehouse, True)
        self._self_kill(self.warehouse, False)
        self.assertEqual(AuditLog.objects.filter(action="ai_config_kill", actor=self.warehouse).count(), 2)

    def test_unauthenticated_cannot_kill(self):
        resp = client_for(None).post("/api/ai/my-config/kill/", {"killed": False}, format="json")
        self.assertEqual(resp.status_code, 401)
