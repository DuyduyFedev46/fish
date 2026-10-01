"""
P8b Lô 4a (R5): `PUT /api/ai/policy/` (caps) và `PUT /api/ai/my-config/` (groups, overrides, limits) nhận khoá CŨ,
chuẩn hoá sang khoá mới TRƯỚC khi lưu phiên bản; kết quả lưu và mức hiệu lực giống hệt khi gửi khoá mới.
"""
from django.test import TestCase, override_settings

from apps.accounts import roles
from apps.ai.models.config import AiConfigVersion
from apps.ai.models.policy import AiPolicyVersion
from apps.ai.policy.effective import effective_level
from apps.ai.registry import get_registry
from apps.common.tests.fixtures import client_for, make_user

OLD_ID = "purchasing.purchasereceipt.nhap_lo"  # naming: allow - id lệnh cũ mà FE cũ còn gửi
NEW_ID = "purchasing.purchasereceipt.receive_batches"


@override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="C")
class LegacyKeysWritePathTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        get_registry().build(force=True)
        cls.owner = make_user("legacy_ai_owner", roles.OWNER)
        cls.warehouse = make_user("legacy_ai_kho", roles.WAREHOUSE_STAFF)

    def _put_policy(self, caps):
        latest = AiPolicyVersion.objects.order_by("-version").first()
        return client_for(self.owner).put(
            "/api/ai/policy/",
            {"base_version": latest.version if latest else 0, "caps": caps, "acknowledge_responsibility": True},
            format="json",
        )

    def _put_config(self, **body):
        latest = AiConfigVersion.objects.filter(user=self.warehouse).order_by("-version").first()
        payload = {"base_version": latest.version if latest else 0, "acknowledge_responsibility": True, **body}
        return client_for(self.warehouse).put("/api/ai/my-config/", payload, format="json")

    def test_p8b_l4_policy_caps_with_old_command_id_stored_under_new_id(self):
        resp = self._put_policy({OLD_ID: {"kg": 200, "vnd": 30000000, "daily": 20}})
        self.assertEqual(resp.status_code, 200, resp.content)
        stored = AiPolicyVersion.objects.order_by("-version").first().caps
        self.assertEqual(stored, {NEW_ID: {"kg": 200, "vnd": 30000000, "daily": 20}})
        self.assertEqual(client_for(self.owner).get("/api/ai/policy/").json()["caps"], stored)

    def test_p8b_l4_policy_caps_old_and_new_keys_give_identical_stored_result(self):
        self._put_policy({OLD_ID: {"kg": 10}})
        old_style = AiPolicyVersion.objects.order_by("-version").first().caps
        AiPolicyVersion.objects.all().delete()
        self._put_policy({NEW_ID: {"kg": 10}})
        self.assertEqual(AiPolicyVersion.objects.order_by("-version").first().caps, old_style)

    def test_p8b_l4_policy_caps_validation_still_applies_to_old_key(self):
        resp = self._put_policy({OLD_ID: {"kg": -1}})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-AI-19")

    def test_p8b_l4_my_config_groups_overrides_limits_with_old_keys_stored_new(self):
        resp = self._put_config(
            groups={"thu_mua": {"read": "A", "write": "C"}},  # naming: allow - khoá cũ
            overrides={OLD_ID: "OFF"},
            limits={OLD_ID: {"kg": "50", "vnd": "1000000"}},
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        stored = AiConfigVersion.objects.filter(user=self.warehouse).order_by("-version").first()
        self.assertEqual(stored.group_levels, {"purchasing": {"read": "A", "write": "C"}})
        self.assertEqual(stored.overrides, {NEW_ID: "OFF"})
        self.assertEqual(stored.limits, {NEW_ID: {"kg": "50", "vnd": "1000000"}})

    def test_p8b_l4_my_config_old_and_new_keys_give_same_effective_level(self):
        spec = get_registry().get_spec(NEW_ID)
        self._put_config(overrides={OLD_ID: "OFF"}, groups={})
        old_cfg = AiConfigVersion.objects.filter(user=self.warehouse).order_by("-version").first()
        level_old = effective_level(self.warehouse, spec, config_version=old_cfg)
        AiConfigVersion.objects.all().delete()
        self._put_config(overrides={NEW_ID: "OFF"}, groups={})
        new_cfg = AiConfigVersion.objects.filter(user=self.warehouse).order_by("-version").first()
        self.assertEqual(level_old, effective_level(self.warehouse, spec, config_version=new_cfg))
        self.assertEqual(old_cfg.overrides, new_cfg.overrides)

    def test_p8b_l4_my_config_returns_new_group_keys_even_when_pinned_version_has_old_keys(self):
        AiConfigVersion.objects.create(
            user=self.warehouse, version=1, created_by=self.warehouse,
            group_levels={"thu_mua": {"read": "OFF"}}, overrides={}, limits={},  # naming: allow - khoá cũ
        )
        data = client_for(self.warehouse).get("/api/ai/my-config/").json()
        groups = {g["group"]: g for g in data["groups"]}
        self.assertEqual(set(groups), {"purchasing", "sales", "customer_service"})
        self.assertEqual(groups["purchasing"]["read_level"], "OFF", "mức đã cấu hình theo khoá cũ vẫn được áp dụng")

    def test_p8b_l4_limits_old_key_is_checked_against_cap_stored_under_old_key(self):
        """Phiên bản chính sách cũ (khoá cũ) vẫn là trần cho ngưỡng gửi bằng khoá mới."""
        AiPolicyVersion.objects.create(version=1, created_by=self.owner, caps={OLD_ID: {"kg": 100}})
        resp = self._put_config(limits={NEW_ID: {"kg": "250"}}, groups={}, overrides={})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-AI-19")

    def test_p8b_l4_unknown_old_style_command_is_still_rejected(self):
        resp = self._put_config(overrides={"purchasing.khong_co.nhap_lo": "OFF"}, groups={})  # naming: allow - id giả
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-AI-19")

    def _history_changes(self):
        results = client_for(self.warehouse).get("/api/ai/my-config/versions/").json()
        results = results["results"] if isinstance(results, dict) else results
        return {row["version"]: row["changes"] for row in results}

    def test_p8b_l4_history_shows_no_change_for_the_p8b_key_rename_version(self):
        """Phiên bản P8b chỉ đổi tên khoá, giá trị giữ nguyên: lịch sử không được hiện như người dùng đổi mức."""
        AiConfigVersion.objects.create(
            user=self.warehouse, version=1, created_by=self.warehouse, overrides={OLD_ID: "OFF"}, limits={}, group_levels={},
        )
        AiConfigVersion.objects.create(
            user=self.warehouse, version=2, created_by=self.warehouse, overrides={NEW_ID: "OFF"}, limits={}, group_levels={},
            note="P8b: đổi khoá sang tiếng Anh, giá trị giữ nguyên",
        )
        changes = self._history_changes()
        self.assertEqual(changes[2], [])

    def test_p8b_l4_history_still_shows_a_real_level_change_across_the_rename(self):
        AiConfigVersion.objects.create(
            user=self.warehouse, version=1, created_by=self.warehouse, overrides={OLD_ID: "OFF"}, limits={}, group_levels={},
        )
        AiConfigVersion.objects.create(
            user=self.warehouse, version=2, created_by=self.warehouse, overrides={NEW_ID: "C"}, limits={}, group_levels={},
        )
        self.assertEqual(
            self._history_changes()[2], [{"scope": "override", "key": NEW_ID, "from": "OFF", "to": "C"}]
        )

    def test_p8b_l4_put_after_old_pinned_version_does_not_report_unchanged_override_as_changed(self):
        from apps.accounts.models import AuditLog

        AiConfigVersion.objects.create(
            user=self.warehouse, version=1, created_by=self.warehouse, overrides={OLD_ID: "OFF"}, limits={}, group_levels={},
        )
        resp = self._put_config(overrides={NEW_ID: "OFF"}, groups={})
        self.assertEqual(resp.status_code, 200, resp.content)
        audit = AuditLog.objects.filter(action="ai_config_update").order_by("-id").first()
        self.assertFalse(audit.changes, "không đổi mức thì không có thay đổi nào trong nhật ký")
