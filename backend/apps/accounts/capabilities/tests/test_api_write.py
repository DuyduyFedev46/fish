"""B4 · ED-39-AC2..AC5 — PUT /api/staff/groups/{code}/capabilities/ và chặn leo quyền (BR-PQ-32)."""
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from apps.accounts import roles
from apps.accounts.capabilities import registry
from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for, make_user

from .base import detail_url, group_perms, make_staff, put_url, token_client, put_caps

ACTION = "change_group_capabilities"


def registry_perms():
    return {perm for c in registry.CAPABILITIES for perm in c.perms}


class SetCapabilitiesTests(TestCase):
    def setUp(self):
        self.owner = make_staff("owner1", roles.OWNER, display_name="Chủ Thử")
        self.warehouse = make_staff("kho1", roles.WAREHOUSE_STAFF)
        self.manager = make_staff("manager1", roles.MANAGER)
        self.client = client_for(self.owner)

    def put(self, code, changes, client=None):
        return put_caps(client or self.client, code, changes)

    def test_ed39_owner_turns_capability_on_and_gets_detail_body(self):
        self.assertNotIn("inventory.approve_returntostock", group_perms(roles.WAREHOUSE_STAFF))
        response = self.put(roles.WAREHOUSE_STAFF, {"approve_return": True})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], roles.WAREHOUSE_STAFF)
        self.assertEqual(body["capabilities"]["approve_return"], "on")
        self.assertIn("registry", body)
        self.assertIn("inventory.approve_returntostock", group_perms(roles.WAREHOUSE_STAFF))

    def test_ed39_owner_turns_capability_off(self):
        response = self.put(roles.MANAGER, {"publish_batch": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["capabilities"]["publish_batch"], "off")
        self.assertNotIn("inventory.publish_batch", group_perms(roles.MANAGER))

    def test_ed39_ac2_new_permission_takes_effect_on_next_request_same_token(self):
        manager_client = token_client(self.manager)
        directory = "/api/sales/customer-directory/"
        self.assertEqual(manager_client.get(directory).status_code, 200)
        self.assertEqual(self.put(roles.MANAGER, {"view_customers": False}).status_code, 200)
        self.assertEqual(manager_client.get(directory).status_code, 403)  # ngay, không đăng nhập lại
        self.assertNotIn(
            "sales.view_customer_list", manager_client.get("/api/auth/me/").json()["permissions"]
        )
        # Q-7: D7 vẫn lưu `all`, nên bật lại việc là mở rộng dữ liệu khách và phải xác nhận (02b §2.5).
        self.assertEqual(self.put(roles.MANAGER, {"view_customers": True}).json()["code"], "CUSTOMER_DATA_WIDENING_UNCONFIRMED")
        put_caps(self.client, roles.MANAGER, {"view_customers": True}, confirm_customer_data_widening=True)
        self.assertEqual(manager_client.get(directory).status_code, 200)

    def test_ed39_ac2_member_gains_permission_immediately(self):
        warehouse_client = token_client(self.warehouse)
        perms = warehouse_client.get("/api/auth/me/").json()["permissions"]
        self.assertNotIn("inventory.approve_returntostock", perms)
        self.put(roles.WAREHOUSE_STAFF, {"approve_return": True})
        perms = warehouse_client.get("/api/auth/me/").json()["permissions"]
        self.assertIn("inventory.approve_returntostock", perms)

    def test_ed39_ac2_audit_row_has_only_capability_keys_and_states(self):
        self.put(roles.MANAGER, {"view_customers": False, "publish_batch": False})
        rows = AuditLog.objects.filter(action=ACTION)
        self.assertEqual(rows.count(), 1)
        row = rows.get()
        group = Group.objects.get(name=roles.MANAGER)
        self.assertEqual(row.actor, self.owner)
        self.assertEqual(row.actor_kind, "user")
        self.assertEqual(row.model_name, "auth.Group")
        self.assertEqual(row.object_id, str(group.pk))
        self.assertEqual(row.changes, {
            "view_customers": {"from": "on", "to": "off"},
            "publish_batch": {"from": "on", "to": "off"},
        })
        self.assertEqual(row.note, "")
        for value in row.changes.values():  # chỉ mã việc và trạng thái, không tên/SĐT
            self.assertEqual(set(value), {"from", "to"})

    def test_ed39_noop_put_returns_200_and_writes_no_audit(self):
        response = self.put(roles.MANAGER, {"view_orders": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AuditLog.objects.filter(action=ACTION).count(), 0)

    def test_ed39_only_changed_keys_are_audited(self):
        self.put(roles.MANAGER, {"view_orders": True, "publish_batch": False})
        self.assertEqual(AuditLog.objects.get(action=ACTION).changes,
                         {"publish_batch": {"from": "on", "to": "off"}})

    def test_ed39_partial_state_is_reported_and_turning_on_grants_all_perms(self):
        group = Group.objects.get(name=roles.WAREHOUSE_STAFF)
        group.permissions.remove(Permission.objects.get(codename="change_stockreconciliation"))
        rows = {r["code"]: r for r in self.client.get("/api/staff/groups/").json()}
        self.assertEqual(rows[roles.WAREHOUSE_STAFF]["capabilities"]["count_stock"], "partial")
        response = self.put(roles.WAREHOUSE_STAFF, {"count_stock": True})
        self.assertEqual(response.json()["capabilities"]["count_stock"], "on")
        self.assertEqual(AuditLog.objects.get(action=ACTION).changes,
                         {"count_stock": {"from": "partial", "to": "on"}})

    def test_ed39_turning_off_partial_removes_remaining_perms(self):
        group = Group.objects.get(name=roles.WAREHOUSE_STAFF)
        group.permissions.remove(Permission.objects.get(codename="change_stockreconciliation"))
        response = self.put(roles.WAREHOUSE_STAFF, {"count_stock": False})
        self.assertEqual(response.json()["capabilities"]["count_stock"], "off")
        self.assertFalse({"inventory.add_stockreconciliation", "inventory.change_stockreconciliation"}
                         & group_perms(roles.WAREHOUSE_STAFF))

    def test_ed39_permissions_outside_registry_are_untouched(self):
        outside_before = {code: group_perms(code) - registry_perms() for code in roles.ALL_ROLES}
        self.put(roles.MANAGER, {"view_orders": False, "view_customers": False, "publish_batch": False})
        self.put(roles.WAREHOUSE_STAFF, {"approve_return": True})
        for code in roles.ALL_ROLES:
            self.assertEqual(group_perms(code) - registry_perms(), outside_before[code], code)

    def test_ed39_only_the_target_group_changes(self):
        before = {code: group_perms(code) for code in roles.ALL_ROLES if code != roles.WAREHOUSE_STAFF}
        self.put(roles.WAREHOUSE_STAFF, {"approve_return": True})
        for code, perms in before.items():
            self.assertEqual(group_perms(code), perms, code)

    def test_ed39_last_changed_fields_update_after_put(self):
        self.put(roles.MANAGER, {"publish_batch": False})
        rows = {r["code"]: r for r in self.client.get("/api/staff/groups/").json()}
        self.assertEqual(rows[roles.MANAGER]["last_changed_by"], "Chủ Thử")
        self.assertTrue(rows[roles.MANAGER]["last_changed_at"])
        self.assertIsNone(rows[roles.WAREHOUSE_STAFF]["last_changed_by"])


class PrivilegeEscalationTests(TestCase):
    def setUp(self):
        self.owner = make_staff("owner1", roles.OWNER)
        self.manager = make_staff("manager1", roles.MANAGER)
        self.client = client_for(self.owner)

    def snapshot(self):
        return {code: group_perms(code) for code in roles.ALL_ROLES}

    def put(self, code, changes, client=None):
        return put_caps(client or self.client, code, changes)

    def assert_nothing_changed(self, before):
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(AuditLog.objects.filter(action=ACTION).count(), 0)

    def test_ed39_ac5_manager_cannot_grant_itself_anything(self):
        before = self.snapshot()
        response = self.put(roles.MANAGER, {"view_cost": True}, client=client_for(self.manager))
        self.assertEqual(response.status_code, 403)
        response = self.put(roles.MANAGER, {"view_orders": False}, client=token_client(self.manager))
        self.assertEqual(response.status_code, 403)
        self.assert_nothing_changed(before)

    def test_ed39_ac5_other_roles_and_anonymous_cannot_write(self):
        before = self.snapshot()
        for username, groups in [("kho1", [roles.WAREHOUSE_STAFF]), ("giao1", [roles.DELIVERY_STAFF]),
                                 ("cs1", [roles.CUSTOMER_SERVICE]), ("nogroup", [])]:
            client = client_for(make_user(username, *groups))
            self.assertEqual(self.put(roles.WAREHOUSE_STAFF, {"approve_return": True}, client=client).status_code,
                             403, username)
        self.assertEqual(self.put(roles.MANAGER, {"view_orders": False}, client=client_for(None)).status_code, 401)
        self.assert_nothing_changed(before)

    def test_ed39_non_owner_holding_manage_staff_still_cannot_write(self):
        # Quyền gán trực tiếp `manage_staff` đủ để ĐỌC (như /api/staff/), nhưng ghi ma trận chỉ nhóm Chủ.
        helper = make_staff("helper1", roles.MANAGER)
        helper.user_permissions.add(Permission.objects.get(codename="manage_staff"))
        client = token_client(helper)
        self.assertEqual(client.get("/api/staff/groups/").status_code, 200)
        before = self.snapshot()
        response = self.put(roles.MANAGER, {"view_cost": True}, client=client)
        self.assertEqual(response.status_code, 403)
        self.assert_nothing_changed(before)

    def test_ed39_ac3_owner_only_capability_cannot_be_given_to_other_groups(self):
        before = self.snapshot()
        owner_only = [c.key for c in registry.CAPABILITIES if c.owner_only]
        self.assertTrue(owner_only)
        for code in (roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE):
            for key in owner_only:
                response = self.put(code, {key: True})
                self.assertEqual(response.status_code, 400, (code, key))
                self.assertEqual(response.json()["code"], "BR-PQ-32", (code, key))
        self.assert_nothing_changed(before)

    def test_ed39_ac3_mixed_request_is_all_or_nothing(self):
        before = self.snapshot()
        response = self.put(roles.WAREHOUSE_STAFF, {"approve_return": True, "view_cost": True})
        self.assertEqual(response.status_code, 400)
        self.assert_nothing_changed(before)

    def test_ed39_ac4_owner_group_is_locked(self):
        before = self.snapshot()
        for changes in ({"view_orders": False}, {"manage_staff": False}, {"view_orders": True}):
            response = self.put(roles.OWNER, changes)
            self.assertEqual(response.status_code, 400, changes)
            self.assertEqual(response.json()["code"], "GROUP_LOCKED", changes)
        self.assert_nothing_changed(before)

    def test_ed39_owner_keeps_manage_staff_so_the_matrix_cannot_lock_everyone_out(self):
        self.put(roles.OWNER, {"manage_staff": False})
        self.assertIn("accounts.manage_staff", group_perms(roles.OWNER))

    def test_ed39_unknown_key_is_rejected_with_input_not_allowed(self):
        before = self.snapshot()
        for key in ("nope", "sales.view_salesorder", "is_superuser", ""):
            response = self.put(roles.MANAGER, {key: True})
            self.assertEqual(response.status_code, 400, key)
            self.assertEqual(response.json()["code"], "INPUT_NOT_ALLOWED", key)
        self.assert_nothing_changed(before)

    def test_ed39_malformed_bodies_are_400_and_change_nothing(self):
        before = self.snapshot()
        url = put_url(roles.MANAGER)
        for body in (
            {}, {"capabilities": {}}, {"capabilities": []}, {"capabilities": "on"}, {"capabilities": None},
            {"capabilities": {"view_orders": "yes"}}, {"capabilities": {"view_orders": 1}},
            {"capabilities": {"view_orders": None}},
            {"capabilities": {"view_orders": False}, "permissions": ["sales.view_salesorder"]},
        ):
            self.assertEqual(self.client.put(url, body, format="json").status_code, 400, body)
        self.assert_nothing_changed(before)

    def test_ed39_unknown_group_is_404(self):
        for code in ("nope", "chu", "quan_ly"):
            self.assertEqual(self.put(code, {"view_orders": True}).status_code, 404, code)

    def test_ed39_other_methods_are_not_allowed(self):
        url = put_url(roles.MANAGER)
        for method in ("post", "patch", "delete"):
            response = getattr(self.client, method)(url, {"capabilities": {"view_orders": False}}, format="json")
            self.assertEqual(response.status_code, 405, method)
        self.assertEqual(self.client.delete(detail_url(roles.MANAGER)).status_code, 405)
