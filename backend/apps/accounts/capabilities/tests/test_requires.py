"""
B4 · M1 (techlead Lô 14) — việc phụ thuộc nhau (`requires`): không cho ma trận rơi vào trạng thái "bật nhưng không dùng được".

Ca gốc: `POST /api/delivery/notes/{id}/status/` khai `required_perms=("delivery.change_deliverynote",)` (việc `deliver`) và chỉ
SAU ĐÓ mới kiểm `pack_deliverynote` khi chuyển READY. Tắt `deliver` thì người có `pack_print` vẫn thấy "bật" nhưng bị 403.
"""
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings

from apps.accounts import roles
from apps.accounts.capabilities import registry, services
from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for, make_user

from .base import group_perms, make_staff, put_url, token_client, put_caps

DEPENDENCY_CODE = "CAPABILITY_REQUIRES"


@override_settings(AI_ENABLED=True)  # các ca này kiểm ma trận ĐỦ việc; nhánh tắt ở test_ai_hidden
class RegistryRequiresTests(TestCase):
    def test_pack_print_requires_deliver(self):
        self.assertEqual(registry.BY_KEY["pack_print"].requires, ("deliver",))

    def test_every_required_key_exists_and_is_not_self(self):
        for capability in registry.CAPABILITIES:
            for key in capability.requires:
                self.assertIn(key, registry.BY_KEY, capability.key)
                self.assertNotEqual(key, capability.key)

    def test_requires_has_no_cycle(self):
        def walk(key, seen):
            self.assertNotIn(key, seen, f"vòng phụ thuộc quanh {key}")
            for nxt in registry.BY_KEY[key].requires:
                walk(nxt, seen | {key})
        for capability in registry.CAPABILITIES:
            walk(capability.key, frozenset())

    def test_no_owner_only_capability_is_required_by_a_grantable_one(self):
        # Việc cần việc "Chỉ Chủ" sẽ không bao giờ bật được cho nhóm khác: dead end.
        for capability in registry.CAPABILITIES:
            if capability.owner_only:
                continue
            for key in capability.requires:
                self.assertFalse(registry.BY_KEY[key].owner_only, f"{capability.key} -> {key}")

    def test_seed_groups_satisfy_every_requires(self):
        for group in services.list_groups():
            states = group["capabilities"]
            for capability in registry.CAPABILITIES:
                if states[capability.key] == registry.STATE_OFF:
                    continue
                for key in capability.requires:
                    self.assertEqual(states[key], registry.STATE_ON, f"{group['code']}: {capability.key} -> {key}")

    def test_actions_spanning_several_capabilities_are_covered_by_requires(self):
        """Quét mọi @action có `required_perms` (router): nếu một action đòi perm của >1 việc thì việc này phải
        khai `requires` việc kia. Thêm action mới đòi hai việc mà quên khai thì test đỏ."""
        from config.api_urls import router

        owner_of = {perm: c.key for c in registry.CAPABILITIES for perm in c.perms}

        def reaches(start, goal, seen=()):
            return any(nxt == goal or reaches(nxt, goal, seen + (start,))
                       for nxt in registry.BY_KEY[start].requires if nxt not in seen)

        scanned = 0
        for _prefix, viewset, _basename in router.registry:
            for name in dir(viewset):
                kwargs = getattr(getattr(viewset, name, None), "kwargs", None) or {}
                keys = {owner_of[p] for p in kwargs.get("required_perms", ()) if p in owner_of}
                scanned += bool(keys)
                if len(keys) < 2:
                    continue
                for a in keys:
                    for b in keys:
                        if a != b and not (reaches(a, b) or reaches(b, a)):
                            self.fail(f"{viewset.__name__}.{name} đòi cả {a} và {b} nhưng registry không khai requires")
        self.assertGreater(scanned, 20)  # quét thật sự thấy các action (hiện 30), không rỗng


class RequiresWriteTests(TestCase):
    def setUp(self):
        self.owner = make_staff("owner1", roles.OWNER, display_name="Chủ Thử")
        self.client = client_for(self.owner)

    def put(self, code, changes):
        return put_caps(self.client, code, changes)

    def assert_rejected(self, response, snapshot):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], DEPENDENCY_CODE)
        self.assertEqual({c: group_perms(c) for c in roles.ALL_ROLES}, snapshot)  # không đổi gì
        self.assertEqual(self.audit_count(), self.audit_before)  # không ghi audit

    def audit_count(self):
        return AuditLog.objects.filter(action=services.ACTION_CHANGE_CAPABILITIES).count()

    def snapshot(self):
        self.audit_before = self.audit_count()
        return {c: group_perms(c) for c in roles.ALL_ROLES}

    def test_m1_turning_off_deliver_while_pack_print_is_on_is_400(self):
        before = self.snapshot()
        response = self.put(roles.WAREHOUSE_STAFF, {"deliver": False})
        self.assert_rejected(response, before)
        detail = response.json()["detail"]
        self.assertIn("Giao hàng, báo kết quả giao", detail)  # nói rõ việc nào
        self.assertIn("Soạn hàng, in tem", detail)
        self.assertIn("cùng", detail)  # gợi ý đổi cùng lúc

    def test_m1_turning_on_pack_print_while_deliver_is_off_is_400(self):
        self.assertEqual(self.put(roles.CUSTOMER_SERVICE, {"pack_print": False}).status_code, 200)  # đã off
        before = self.snapshot()
        response = self.put(roles.CUSTOMER_SERVICE, {"pack_print": True})
        self.assert_rejected(response, before)
        self.assertIn("Giao hàng, báo kết quả giao", response.json()["detail"])
        self.assertIn("Soạn hàng, in tem", response.json()["detail"])

    def test_m1_turning_both_off_in_one_request_is_allowed(self):
        response = self.put(roles.WAREHOUSE_STAFF, {"deliver": False, "pack_print": False})
        self.assertEqual(response.status_code, 200)
        states = response.json()["capabilities"]
        self.assertEqual((states["deliver"], states["pack_print"]), ("off", "off"))

    def test_m1_turning_both_on_in_one_request_is_allowed(self):
        response = self.put(roles.CUSTOMER_SERVICE, {"deliver": True, "pack_print": True})
        self.assertEqual(response.status_code, 200)
        states = response.json()["capabilities"]
        self.assertEqual((states["deliver"], states["pack_print"]), ("on", "on"))

    def test_m1_turning_deliver_on_alone_is_allowed(self):
        self.assertEqual(self.put(roles.CUSTOMER_SERVICE, {"deliver": True}).status_code, 200)

    def test_m1_turning_pack_print_off_alone_is_allowed(self):
        self.assertEqual(self.put(roles.WAREHOUSE_STAFF, {"pack_print": False}).status_code, 200)

    def test_m1_off_deliver_after_pack_print_off_is_allowed_in_two_requests(self):
        self.assertEqual(self.put(roles.WAREHOUSE_STAFF, {"pack_print": False}).status_code, 200)
        self.assertEqual(self.put(roles.WAREHOUSE_STAFF, {"deliver": False}).status_code, 200)

    def test_m1_partial_pack_print_counts_as_still_enabled(self):
        group = Group.objects.get(name=roles.WAREHOUSE_STAFF)
        group.permissions.remove(Permission.objects.get(codename="print_label"))  # pack_print = partial
        before = self.snapshot()
        self.assert_rejected(self.put(roles.WAREHOUSE_STAFF, {"deliver": False}), before)

    def test_m1_after_both_turned_off_turning_on_pack_print_alone_is_400(self):
        self.put(roles.WAREHOUSE_STAFF, {"deliver": False, "pack_print": False})
        before = self.snapshot()
        self.assert_rejected(self.put(roles.WAREHOUSE_STAFF, {"pack_print": True}), before)

    def test_m1_request_with_valid_and_conflicting_keys_is_all_or_nothing(self):
        before = self.snapshot()
        response = self.put(roles.WAREHOUSE_STAFF, {"approve_return": True, "deliver": False})
        self.assert_rejected(response, before)
        self.assertNotIn("inventory.approve_returntostock", group_perms(roles.WAREHOUSE_STAFF))

    def test_m1_untouched_existing_inconsistency_does_not_block_unrelated_changes(self):
        # Dữ liệu cũ lệch (pack_print on, deliver off) không chặn việc không liên quan.
        group = Group.objects.get(name=roles.CUSTOMER_SERVICE)
        group.permissions.add(*Permission.objects.filter(codename__in=["pack_deliverynote", "print_label"]))
        response = self.put(roles.CUSTOMER_SERVICE, {"approve_return": True})
        self.assertEqual(response.status_code, 200)

    def test_m1_non_owner_still_gets_403_before_dependency_check(self):
        manager = make_staff("manager1", roles.MANAGER)
        response = put_caps(token_client(manager), roles.WAREHOUSE_STAFF, {"deliver": False})
        self.assertEqual(response.status_code, 403)

    def test_m1_reproduction_warehouse_staff_cannot_pack_when_only_deliver_is_turned_off_directly(self):
        """Ca techlead tái hiện: ép tắt `deliver` bằng DB (bỏ qua service) thì kho bị 403 khi chuyển READY."""
        Group.objects.get(name=roles.WAREHOUSE_STAFF).permissions.remove(
            Permission.objects.get(codename="change_deliverynote"))
        warehouse = make_user("kho2", roles.WAREHOUSE_STAFF)
        response = client_for(warehouse).post(
            "/api/delivery/notes/1/status/", {"to_status": "READY"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("delivery.change_deliverynote", response.json()["detail"])

    def test_m1_detail_registry_lists_requires(self):
        body = self.client.get("/api/staff/groups/warehouse_staff/").json()
        by_key = {row["key"]: row for row in body["registry"]}
        self.assertEqual(by_key["pack_print"]["requires"], ["deliver"])
        self.assertEqual(by_key["deliver"]["requires"], [])
