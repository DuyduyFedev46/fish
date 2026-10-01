"""
P8b Lô 4a (R5): `legacy_ids` đổi khoá cũ sang khoá tiếng Anh để đọc phiên bản AI đã ghim và nhận ghi theo tên cũ.

Dữ liệu cũ (`AiConfigVersion` / `AiPolicyVersion` append-only, không UPDATE) vẫn mang khoá tiếng Việt; mọi chỗ đọc
đều đi qua các hàm này để tính ra đúng mức như khoá mới.
"""
from django.test import SimpleTestCase, TestCase, override_settings

from apps.accounts import roles
from apps.ai import command_groups
from apps.ai.models.config import AiConfigVersion
from apps.ai.models.policy import AiPolicyVersion
from apps.ai.policy.effective import effective_level
from apps.ai.registry import get_registry, legacy_ids
from apps.ai.settings.services import get_cap_for_command
from apps.common.tests.fixtures import make_user

OLD_RECEIVE_ID = "purchasing.purchasereceipt.nhap_lo"  # naming: allow - id lệnh cũ, dữ liệu trước Lô 4
NEW_RECEIVE_ID = "purchasing.purchasereceipt.receive_batches"


class LegacyIdMappingTests(SimpleTestCase):
    def test_command_id_old_maps_to_new_and_new_is_unchanged(self):
        self.assertEqual(legacy_ids.normalize_command_id(OLD_RECEIVE_ID), NEW_RECEIVE_ID)
        self.assertEqual(legacy_ids.normalize_command_id(NEW_RECEIVE_ID), NEW_RECEIVE_ID)
        self.assertEqual(legacy_ids.normalize_command_id("inventory.batch.close"), "inventory.batch.close")

    def test_group_key_old_maps_to_new(self):
        self.assertEqual(legacy_ids.normalize_group_key("thu_mua"), command_groups.PURCHASING)  # naming: allow - khoá cũ
        self.assertEqual(legacy_ids.normalize_group_key("ban_hang"), command_groups.SALES)  # naming: allow - khoá cũ
        self.assertEqual(legacy_ids.normalize_group_key("cskh"), command_groups.CUSTOMER_SERVICE)  # naming: allow - khoá cũ
        self.assertEqual(legacy_ids.normalize_group_key(command_groups.SALES), command_groups.SALES)

    def test_new_values_are_english(self):
        self.assertEqual(
            (command_groups.PURCHASING, command_groups.SALES, command_groups.CUSTOMER_SERVICE),
            ("purchasing", "sales", "customer_service"),
        )
        self.assertEqual(
            (command_groups.SENSITIVITY_HIGH, command_groups.SENSITIVITY_MEDIUM, command_groups.SENSITIVITY_LOW),
            ("high", "medium", "low"),
        )

    def test_command_keys_normalize_full_id_and_bare_alias_and_new_key_wins(self):
        out = legacy_ids.normalize_command_keys(
            {OLD_RECEIVE_ID: {"kg": 1}, "nhap_lo": {"kg": 2}, "inventory.batch.close": {"kg": 3}}  # naming: allow - khoá cũ
        )
        self.assertEqual(set(out), {NEW_RECEIVE_ID, "inventory.batch.close", "receive_batches"})
        both = legacy_ids.normalize_command_keys({OLD_RECEIVE_ID: "OFF", NEW_RECEIVE_ID: "C"})
        self.assertEqual(both, {NEW_RECEIVE_ID: "C"}, "khoá mới thắng khi cùng có khoá cũ")

    def test_group_levels_normalize_keys_and_keep_values(self):
        out = legacy_ids.normalize_group_levels({"thu_mua": {"read": "A", "write": "C"}, "sales": {"read": "OFF"}})  # naming: allow - khoá cũ
        self.assertEqual(out, {"purchasing": {"read": "A", "write": "C"}, "sales": {"read": "OFF"}})

    def test_normalize_is_pure_and_tolerates_empty_or_non_dict(self):
        source = {OLD_RECEIVE_ID: "C"}
        legacy_ids.normalize_command_keys(source)
        self.assertEqual(source, {OLD_RECEIVE_ID: "C"}, "không sửa đối tượng truyền vào")
        self.assertEqual(legacy_ids.normalize_command_keys(None), {})
        self.assertEqual(legacy_ids.normalize_group_levels({}), {})

    def test_legacy_role_names_cover_all_five_roles(self):
        self.assertEqual(
            roles.LEGACY_ROLE_NAMES,
            {
                "chu": roles.OWNER,  # naming: allow - tên Group cũ
                "quan_ly": roles.MANAGER,  # naming: allow - tên Group cũ
                "nv_kho": roles.WAREHOUSE_STAFF,  # naming: allow - tên Group cũ
                "nv_giao": roles.DELIVERY_STAFF,  # naming: allow - tên Group cũ
                "cskh": roles.CUSTOMER_SERVICE,  # naming: allow - tên Group cũ
            },
        )
        self.assertEqual(roles.normalize_role_name("nv_kho"), roles.WAREHOUSE_STAFF)  # naming: allow - tên Group cũ
        self.assertEqual(roles.normalize_role_name(roles.OWNER), roles.OWNER)
        self.assertEqual(roles.normalize_role_name("khong_co"), "khong_co")


@override_settings(AI_ENABLED=True)
class PinnedOldVersionsStillComputeTests(TestCase):
    """Phiên bản cũ (khoá tiếng Việt) và phiên bản mới (khoá tiếng Anh) phải cho cùng mức hiệu lực."""

    @classmethod
    def setUpTestData(cls):
        get_registry().build(force=True)
        cls.owner = make_user("legacy_owner", roles.OWNER)
        cls.receive = get_registry().get_spec(NEW_RECEIVE_ID)
        cls.close_batch = get_registry().get_spec("inventory.batch.close")

    def _config(self, **kwargs):
        return AiConfigVersion(user=self.owner, version=1, created_by=self.owner, **kwargs)

    def test_old_override_key_applies_to_renamed_command(self):
        old = self._config(overrides={OLD_RECEIVE_ID: "OFF"})
        new = self._config(overrides={NEW_RECEIVE_ID: "OFF"})
        self.assertEqual(effective_level(self.owner, self.receive, config_version=old), "OFF")
        self.assertEqual(
            effective_level(self.owner, self.receive, config_version=old),
            effective_level(self.owner, self.receive, config_version=new),
        )

    def test_old_group_key_applies_to_group_renamed(self):
        old = self._config(group_levels={"thu_mua": {"write": "OFF"}})  # naming: allow - khoá cũ
        new = self._config(group_levels={"purchasing": {"write": "OFF"}})
        self.assertEqual(effective_level(self.owner, self.receive, config_version=old), "OFF")
        self.assertEqual(
            effective_level(self.owner, self.receive, config_version=old),
            effective_level(self.owner, self.receive, config_version=new),
        )

    def test_old_cap_key_in_pinned_policy_still_limits_level(self):
        policy_old = AiPolicyVersion(version=1, created_by=self.owner, caps={OLD_RECEIVE_ID: {"max_level": "C"}})
        policy_new = AiPolicyVersion(version=1, created_by=self.owner, caps={NEW_RECEIVE_ID: {"max_level": "C"}})
        cfg = self._config()
        self.assertEqual(
            effective_level(self.owner, self.receive, config_version=cfg, policy_version=policy_old),
            effective_level(self.owner, self.receive, config_version=cfg, policy_version=policy_new),
        )

    def test_get_cap_for_command_finds_cap_stored_under_old_id_or_old_alias(self):
        self.assertEqual(get_cap_for_command({OLD_RECEIVE_ID: {"kg": 5}}, NEW_RECEIVE_ID), {"kg": 5})
        self.assertEqual(get_cap_for_command({"nhap_lo": {"kg": 6}}, NEW_RECEIVE_ID), {"kg": 6})  # naming: allow - khoá cũ
        self.assertEqual(get_cap_for_command({NEW_RECEIVE_ID: {"kg": 7}}, NEW_RECEIVE_ID), {"kg": 7})
        self.assertIsNone(get_cap_for_command({"inventory.batch.close": {"kg": 1}}, NEW_RECEIVE_ID))
