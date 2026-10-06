"""B4 · ED-39-AC1 — GET /api/staff/groups/ và /api/staff/groups/{code}/ (chỉ Chủ đọc được)."""
from django.test import TestCase

from apps.accounts import roles
from apps.accounts.capabilities import registry
from apps.accounts.models import StaffProfile
from apps.common.tests.fixtures import client_for, make_user

from .base import ALL_CODES, LIST_URL, detail_url, make_staff, put_url, token_client

LIST_KEYS = {"id", "code", "label", "member_count", "members", "can_view_cost",
             "last_changed_at", "last_changed_by", "capabilities", "version", "data_scope_values"}  # PV-02 thêm 2 khoá
DETAIL_EXTRA = {"registry", "scopes", "timeline", "data_scopes"}
MEMBER_LIST_KEYS = {"id", "display_name"}
MEMBER_DETAIL_KEYS = {"id", "display_name", "username", "other_groups", "is_active", "added_at"}


class GroupReadTests(TestCase):
    def setUp(self):
        self.owner = make_staff("owner1", roles.OWNER, display_name="Chủ Thử")
        self.manager = make_staff("manager1", roles.MANAGER, display_name="Quản Lý Thử")
        self.client = client_for(self.owner)

    def by_code(self, rows):
        return {row["code"]: row for row in rows}

    def test_ed39_ac1_owner_lists_five_groups_in_role_order(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([g["code"] for g in body], ALL_CODES)
        self.assertEqual([g["label"] for g in body],
                         ["Chủ", "Quản lý", "Nhân viên kho", "Nhân viên giao", "CSKH"])
        for row in body:
            self.assertEqual(set(row), LIST_KEYS)
            self.assertEqual(set(row["capabilities"]), {c.key for c in registry.CAPABILITIES})
            self.assertTrue(set(row["capabilities"].values()) <= {"on", "off", "partial"})

    def test_ed39_ac1_states_match_database(self):
        rows = self.by_code(self.client.get(LIST_URL).json())
        self.assertTrue(all(state == "on" for state in rows[roles.OWNER]["capabilities"].values()))
        manager = rows[roles.MANAGER]["capabilities"]
        self.assertEqual(manager["view_orders"], "on")
        self.assertEqual(manager["view_customers"], "on")
        self.assertEqual(manager["confirm_payment"], "off")  # chỉ Chủ
        self.assertEqual(manager["view_cost"], "off")
        delivery = rows[roles.DELIVERY_STAFF]["capabilities"]
        self.assertEqual(delivery["deliver"], "on")
        self.assertEqual(delivery["view_customers"], "off")
        self.assertEqual(rows[roles.CUSTOMER_SERVICE]["capabilities"]["confirm_calls"], "on")

    def test_ed39_can_view_cost_flag_follows_group(self):
        rows = self.by_code(self.client.get(LIST_URL).json())
        self.assertTrue(rows[roles.OWNER]["can_view_cost"])
        for code in ALL_CODES[1:]:
            self.assertFalse(rows[code]["can_view_cost"], code)

    def test_ed39_member_count_counts_active_members_only(self):
        gone = make_staff("manager2", roles.MANAGER)
        gone.is_active = False
        gone.save(update_fields=["is_active"])
        row = self.by_code(self.client.get(LIST_URL).json())[roles.MANAGER]
        self.assertEqual(row["member_count"], 1)
        self.assertEqual(row["members"], [{"id": self.manager.pk, "display_name": "Quản Lý Thử"}])
        for member in row["members"]:
            self.assertEqual(set(member), MEMBER_LIST_KEYS)

    def test_ed39_never_changed_group_has_null_audit_fields(self):
        row = self.by_code(self.client.get(LIST_URL).json())[roles.MANAGER]
        self.assertIsNone(row["last_changed_at"])
        self.assertIsNone(row["last_changed_by"])

    def test_ed39_list_has_no_staff_phone_or_password(self):
        StaffProfile.objects.filter(user=self.manager).update(phone="0900000321")
        text = self.client.get(LIST_URL).content.decode()
        self.assertNotIn("0900000321", text)
        self.assertNotIn("password", text)

    def test_ed39_detail_has_registry_scopes_and_full_members(self):
        inactive = make_staff("manager3", roles.MANAGER, roles.DELIVERY_STAFF, display_name="Nghỉ Thử")
        inactive.is_active = False
        inactive.save(update_fields=["is_active"])
        response = self.client.get(detail_url(roles.MANAGER))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), LIST_KEYS | DETAIL_EXTRA)
        self.assertEqual(body["member_count"], 1)  # chỉ người đang làm
        members = {m["username"]: m for m in body["members"]}
        self.assertEqual(set(members), {"manager1", "manager3"})  # đủ, kể cả người nghỉ
        for member in members.values():
            self.assertEqual(set(member), MEMBER_DETAIL_KEYS)
        self.assertEqual(members["manager3"]["other_groups"], [roles.DELIVERY_STAFF])
        self.assertFalse(members["manager3"]["is_active"])
        self.assertTrue(members["manager1"]["added_at"])
        self.assertEqual(
            body["registry"][0], {"key": "view_orders", "label": "Xem đơn", "section": "Bán hàng", "owner_only": False,
             "requires": []}
        )
        self.assertEqual({r["key"] for r in body["registry"] if r["owner_only"]},
                         {c.key for c in registry.CAPABILITIES if c.owner_only})

    def test_ed39_detail_scopes_are_fixed_read_only_text_per_group(self):
        delivery = self.client.get(detail_url(roles.DELIVERY_STAFF)).json()["scopes"]
        self.assertEqual(delivery["orders"], "Được gán")
        warehouse = self.client.get(detail_url(roles.WAREHOUSE_STAFF)).json()["scopes"]
        self.assertEqual(warehouse["customers"], "Không xem")
        manager = self.client.get(detail_url(roles.MANAGER)).json()["scopes"]
        self.assertEqual(manager["customers"], "Tất cả khách")

    def test_ed39_detail_unknown_group_is_404(self):
        for code in ("nope", "chu", "quan_ly", "9"):
            self.assertEqual(self.client.get(detail_url(code)).status_code, 404, code)

    def test_ed39_detail_works_with_real_token_auth(self):
        self.assertEqual(token_client(self.owner).get(detail_url(roles.OWNER)).status_code, 200)

    def test_ed39_staff_router_still_serves_staff_detail_and_list(self):
        # route "groups/" khai trước router: không làm hỏng /api/staff/ và /api/staff/<pk>/.
        self.assertEqual(self.client.get("/api/staff/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/staff/{self.manager.pk}/").status_code, 200)


class GroupReadPermissionTests(TestCase):
    def test_ed39_ac5_non_owner_roles_get_403_on_every_read_endpoint(self):
        make_staff("owner1", roles.OWNER)
        for username, groups in [
            ("manager1", [roles.MANAGER]), ("kho1", [roles.WAREHOUSE_STAFF]),
            ("giao1", [roles.DELIVERY_STAFF]), ("cs1", [roles.CUSTOMER_SERVICE]), ("nogroup", []),
        ]:
            client = client_for(make_user(username, *groups))
            for url in (LIST_URL, detail_url(roles.MANAGER)):
                self.assertEqual(client.get(url).status_code, 403, (username, url))

    def test_ed39_anonymous_gets_401(self):
        client = client_for(None)
        for url in (LIST_URL, detail_url(roles.MANAGER)):
            self.assertEqual(client.get(url).status_code, 401, url)


class DynamicCustomerScopeTests(TestCase):
    """M2 (techlead Lô 14) — `scopes.customers` theo quyền thực tế, không theo bảng cố định (bất biến 9)."""

    def setUp(self):
        self.owner = make_staff("owner1", roles.OWNER)
        self.client = client_for(self.owner)

    def customers_scope(self, code):
        return self.client.get(detail_url(code)).json()["scopes"]["customers"]

    def test_ed39_scope_customers_all_when_group_has_view_customer_list(self):
        for code in (roles.OWNER, roles.MANAGER):
            self.assertEqual(self.customers_scope(code), "Tất cả khách", code)

    def test_ed39_scope_customers_turns_all_after_owner_enables_view_customers(self):
        self.assertEqual(self.customers_scope(roles.DELIVERY_STAFF), "Được gán")
        self.assertEqual(self.customers_scope(roles.WAREHOUSE_STAFF), "Không xem")
        for code in (roles.DELIVERY_STAFF, roles.WAREHOUSE_STAFF, roles.CUSTOMER_SERVICE):
            response = self.client.put(put_url(code), {"capabilities": {"view_customers": True}}, format="json")
            self.assertEqual(response.status_code, 200, code)
            self.assertEqual(response.json()["scopes"]["customers"], "Tất cả khách", code)
            self.assertEqual(self.customers_scope(code), "Tất cả khách", code)

    def test_ed39_scope_customers_reverts_after_owner_disables_view_customers(self):
        self.client.put(put_url(roles.DELIVERY_STAFF), {"capabilities": {"view_customers": True}}, format="json")
        self.client.put(put_url(roles.DELIVERY_STAFF), {"capabilities": {"view_customers": False}}, format="json")
        self.assertEqual(self.customers_scope(roles.DELIVERY_STAFF), "Được gán")

    def test_ed39_scope_customers_none_when_manager_loses_view_customers(self):
        # Bảng cố định cũ ghi "Tất cả" cho Quản lý kể cả khi đã tắt quyền: sai.
        self.client.put(put_url(roles.MANAGER), {"capabilities": {"view_customers": False}}, format="json")
        self.assertEqual(self.customers_scope(roles.MANAGER), "Không xem")

    def test_ed39_scope_customers_matches_directory_access(self):
        # Chuỗi hiển thị khớp hành vi thật: nhóm "Tất cả khách" vào được danh bạ khách, nhóm khác thì không.
        from apps.accounts.capabilities import services
        for group in services.list_groups():
            code = group["code"]
            member = make_staff(f"probe_{code}", code)
            status = token_client(member).get("/api/sales/customer-directory/").status_code
            shown = self.customers_scope(code) == "Tất cả khách"
            self.assertEqual(status == 200, shown, code)
