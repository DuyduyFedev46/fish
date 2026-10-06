"""B4 · Registry: mọi codename tồn tại, các việc rời nhau, danh sách "Chỉ Chủ" đúng T9 (BR-PQ-32)."""
from django.contrib.auth.models import Permission
from django.test import TestCase

from apps.accounts import roles
from apps.accounts.auth.services import CAPABILITY_LABELS
from apps.accounts.capabilities import registry

from .base import group_perms

EXPECTED_OWNER_ONLY = {
    "confirm_payment", "confirm_refund", "add_cost", "close_batch", "set_price",
    "view_cost", "view_profit", "manage_staff", "ai_policy",
}


class RegistryTests(TestCase):
    def test_every_codename_in_registry_exists_as_permission(self):
        missing = []
        for capability in registry.CAPABILITIES:
            for perm in capability.perms:
                app_label, codename = perm.split(".")
                if not Permission.objects.filter(content_type__app_label=app_label, codename=codename).exists():
                    missing.append(perm)
        self.assertEqual(missing, [])

    def test_perms_of_different_capabilities_are_disjoint(self):
        seen = {}
        for capability in registry.CAPABILITIES:
            for perm in capability.perms:
                self.assertNotIn(perm, seen, f"{perm} nằm ở cả {seen.get(perm)} và {capability.key}")
                seen[perm] = capability.key

    def test_keys_are_unique_and_nonempty(self):
        keys = [c.key for c in registry.CAPABILITIES]
        self.assertEqual(len(keys), len(set(keys)))
        for capability in registry.CAPABILITIES:
            self.assertTrue(capability.perms, capability.key)
            self.assertTrue(capability.label and capability.section, capability.key)

    def test_owner_only_list_matches_t9(self):
        self.assertEqual({c.key for c in registry.CAPABILITIES if c.owner_only}, EXPECTED_OWNER_ONLY)

    def test_owner_group_holds_every_registry_permission(self):
        held = group_perms(roles.OWNER)
        for capability in registry.CAPABILITIES:
            self.assertTrue(set(capability.perms) <= held, capability.key)

    def test_every_default_scope_group_is_a_real_role(self):
        # PV-02: bảng phạm vi cố định cũ đã thay bằng `data_scopes/catalog.py`; nhóm mặc định phải là vai thật (trừ Chủ).
        from apps.accounts.data_scopes import catalog

        self.assertEqual(set(catalog.DEFAULT_GROUPS), set(roles.ALL_ROLES) - {roles.OWNER})

    def test_tier2_permission_labels_use_one_name_per_action(self):
        # 02b §0c: một việc một tên ("Lập phiếu hoàn", "Xác nhận đã nhận tiền").
        self.assertEqual(CAPABILITY_LABELS["sales.create_refund"], "Lập phiếu hoàn")
        self.assertEqual(CAPABILITY_LABELS["sales.confirm_payment_manual"], "Xác nhận đã nhận tiền")
        labels = {c.key: c.label for c in registry.CAPABILITIES}
        self.assertEqual(labels["create_refund"], CAPABILITY_LABELS["sales.create_refund"])
        self.assertEqual(labels["confirm_payment"], CAPABILITY_LABELS["sales.confirm_payment_manual"])


class CreateReturnCapabilityTests(TestCase):
    """TLA-L2 (Lô 14): ô "Ghi hàng hoàn về kho" để Chủ cấp/gỡ quyền tạo phiếu hàng hoàn cho từng nhóm."""

    def test_create_return_capability_maps_to_add_returntostock(self):
        capability = registry.BY_KEY["create_return"]
        self.assertEqual(capability.perms, ("inventory.add_returntostock",))
        self.assertEqual(capability.section, registry.SECTION_STOCK)
        self.assertEqual(capability.label, "Ghi hàng hoàn về kho")
        self.assertFalse(capability.owner_only)
        self.assertEqual(capability.requires, ())

    def test_create_return_is_not_mixed_with_approve_return(self):
        # Hai việc tách nhau: duyệt hàng hoàn không kéo theo quyền ghi phiếu.
        self.assertNotIn("inventory.add_returntostock", registry.BY_KEY["approve_return"].perms)
