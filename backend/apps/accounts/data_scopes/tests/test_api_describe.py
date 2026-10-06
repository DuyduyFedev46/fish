"""PV-02-AC6..AC9 — GET /api/staff/groups/ và /api/staff/groups/<code>/ có `version`, `data_scopes` (02b §2.1, §2.2)."""
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from apps.accounts import roles
from apps.accounts.capabilities.tests.base import LIST_URL, detail_url, make_staff
from apps.accounts.models import GroupAccessConfig, GroupDataScope
from apps.common.tests.fixtures import client_for, make_user

ORDER = ["orders", "invoices", "deliveries", "confirmation", "returns", "receipts", "customers", "audit_log"]
ROW_KEYS = {"key", "label", "value", "editable", "customer_data", "gate_capability", "inactive_reason", "note", "options"}
OPTION_KEYS = {"value", "label", "rank"}
EDITABLE_KEYS = ["orders", "deliveries", "confirmation", "returns", "receipts", "customers"]


class DataScopesDescribeTests(TestCase):
    def setUp(self):
        self.owner = make_staff("owner1", roles.OWNER, display_name="Chủ Thử")
        self.client = client_for(self.owner)

    def rows(self, code):
        body = self.client.get(detail_url(code)).json()
        return body, {row["key"]: row for row in body["data_scopes"]}

    def test_pv02_ac6_detail_has_version_and_eight_rows_in_order(self):
        body, rows = self.rows(roles.WAREHOUSE_STAFF)
        self.assertEqual(body["version"], "1")
        self.assertEqual([row["key"] for row in body["data_scopes"]], ORDER)
        for row in body["data_scopes"]:
            self.assertEqual(set(row), ROW_KEYS, row["key"])
            for option in row["options"]:
                self.assertEqual(set(option), OPTION_KEYS)

    def test_pv02_ac6_legacy_scopes_still_present_and_built_from_config(self):
        body, _ = self.rows(roles.DELIVERY_STAFF)
        self.assertEqual(body["scopes"]["orders"], "Được gán")
        self.assertEqual(body["scopes"]["deliveries"], "Được gán")
        self.assertEqual(body["scopes"]["customers"], "Được gán")
        # Chữ sai "Trong phạm vi gọi" không còn: CSKH thấy đơn của mình hoặc đang chờ gọi.
        body, _ = self.rows(roles.CUSTOMER_SERVICE)
        self.assertNotIn("Trong phạm vi gọi", body["scopes"].values())

    def test_pv02_ac6_legacy_scopes_follow_stored_config(self):
        GroupDataScope.objects.filter(group__name=roles.WAREHOUSE_STAFF, object_key="orders").update(
            value="assigned_deliveries")
        body, _ = self.rows(roles.WAREHOUSE_STAFF)
        self.assertEqual(body["scopes"]["orders"], "Được gán")

    def test_pv02_ac6_row_values_follow_contract_for_editable_objects(self):
        _, rows = self.rows(roles.DELIVERY_STAFF)
        self.assertEqual(rows["orders"]["value"], "assigned_deliveries")
        self.assertTrue(rows["orders"]["editable"])
        self.assertTrue(rows["orders"]["customer_data"])
        self.assertEqual(
            rows["orders"]["options"],
            [{"value": "assigned_deliveries", "label": "Đơn có phiếu giao gán cho tôi", "rank": 0},
             {"value": "assigned_or_confirmation",
              "label": "Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận", "rank": 1},
             {"value": "all", "label": "Tất cả đơn", "rank": 2}],
        )
        self.assertEqual(rows["orders"]["gate_capability"], "view_orders")
        self.assertFalse(rows["receipts"]["customer_data"])
        self.assertEqual(rows["customers"]["value"], "assigned_deliveries")

    def test_pv02_ac6_read_only_rows_have_no_options(self):
        _, rows = self.rows(roles.MANAGER)
        invoices = rows["invoices"]
        self.assertEqual((invoices["value"], invoices["editable"], invoices["note"], invoices["options"]),
                         ("follows_orders", False, "Theo Đơn hàng", []))
        audit = rows["audit_log"]
        self.assertEqual((audit["value"], audit["editable"], audit["options"]), ("all", False, []))
        _, warehouse_rows = self.rows(roles.WAREHOUSE_STAFF)
        self.assertEqual(warehouse_rows["audit_log"]["value"], "none")

    def test_pv02_ac6_only_six_objects_editable(self):
        _, rows = self.rows(roles.MANAGER)
        self.assertEqual([k for k in ORDER if rows[k]["editable"]], EDITABLE_KEYS)

    def test_pv02_ac6_gate_capability_is_null_when_not_in_registry(self):
        """Việc V1 `view_sales_invoices` chưa có ở registry (PV-07): trả null để FE không trỏ tới việc không tồn tại."""
        from apps.accounts.capabilities import registry

        _, rows = self.rows(roles.MANAGER)
        for row in rows.values():
            self.assertTrue(row["gate_capability"] is None or row["gate_capability"] in registry.BY_KEY)
        self.assertIsNone(rows["deliveries"]["gate_capability"])
        self.assertEqual(rows["customers"]["gate_capability"], "view_customers")

    def test_pv02_ac6_list_has_version_and_scope_values(self):
        rows = {row["code"]: row for row in self.client.get(LIST_URL).json()}
        manager = rows[roles.MANAGER]
        self.assertEqual(manager["version"], "1")
        self.assertEqual(list(manager["data_scope_values"]), EDITABLE_KEYS)
        self.assertEqual(manager["data_scope_values"]["customers"], "all")
        self.assertEqual(rows[roles.WAREHOUSE_STAFF]["data_scope_values"]["customers"], "none")
        self.assertEqual(rows[roles.OWNER]["data_scope_values"], {
            "orders": "all", "deliveries": "all", "confirmation": "all_pending", "returns": "all", "receipts": "all",
            "customers": "all"})

    def test_pv02_ac6_version_is_string_of_row_version(self):
        GroupAccessConfig.objects.filter(group__name=roles.MANAGER).update(row_version=41)
        body, _ = self.rows(roles.MANAGER)
        self.assertEqual(body["version"], "41")
        rows = {row["code"]: row for row in self.client.get(LIST_URL).json()}
        self.assertEqual(rows[roles.MANAGER]["version"], "41")

    def test_pv02_ac7_inactive_reason_set_but_value_kept(self):
        """Nhóm G tắt `view_orders`: ô Đơn hàng mờ nhưng giá trị đã lưu giữ nguyên (Q-7)."""
        group = Group.objects.get(name=roles.DELIVERY_STAFF)
        group.permissions.remove(Permission.objects.get(content_type__app_label="sales", codename="view_salesorder"))
        GroupDataScope.objects.filter(group=group, object_key="orders").update(value="all")
        _, rows = self.rows(roles.DELIVERY_STAFF)
        self.assertEqual(rows["orders"]["value"], "all")
        self.assertEqual(rows["orders"]["inactive_reason"], 'Không xem — bật việc "Xem đơn" trước')
        self.assertTrue(rows["orders"]["editable"])

    def test_pv02_ac7_object_active_has_null_inactive_reason(self):
        _, rows = self.rows(roles.DELIVERY_STAFF)
        self.assertIsNone(rows["orders"]["inactive_reason"])
        self.assertIsNone(rows["deliveries"]["inactive_reason"])

    def test_pv02_ac7_group_without_tier1_view_permission_says_so(self):
        """D3/D5 là quyền Tầng 1 ngoài registry: chữ là 'Nhóm không có quyền xem ...', Chủ không bật được ở đây."""
        _, rows = self.rows(roles.CUSTOMER_SERVICE)
        self.assertEqual(rows["deliveries"]["inactive_reason"], "Nhóm không có quyền xem phiếu giao")
        self.assertEqual(rows["returns"]["inactive_reason"], "Nhóm không có quyền xem hàng hoàn")

    def test_pv02_ac7_confirmation_inactive_for_group_without_confirm_calls(self):
        _, rows = self.rows(roles.DELIVERY_STAFF)
        self.assertEqual(rows["confirmation"]["value"], "pending_or_called_recently")
        self.assertEqual(rows["confirmation"]["inactive_reason"], 'Không xem — bật việc "Gọi xác nhận đơn" trước')

    def test_pv02_ac8_owner_group_is_widest_and_locked(self):
        body, rows = self.rows(roles.OWNER)
        self.assertEqual(len(body["data_scopes"]), 8)
        for key in EDITABLE_KEYS:
            widest = max(rows[key]["options"], key=lambda o: o["rank"])["value"]
            self.assertEqual(rows[key]["value"], widest, key)
            self.assertFalse(rows[key]["editable"], key)
        for row in rows.values():
            self.assertEqual(row["note"], "Chủ luôn thấy tất cả", row["key"])
            self.assertIsNone(row["inactive_reason"], row["key"])
        self.assertFalse(rows["invoices"]["editable"])
        self.assertEqual(rows["audit_log"]["value"], "all")

    def test_pv02_ac9_permissions_unchanged_for_reading(self):
        manager = make_staff("manager1", roles.MANAGER)
        manager_client = client_for(manager)
        self.assertEqual(manager_client.get(LIST_URL).status_code, 403)  # Quản lý không có manage_staff mặc định
        manager.user_permissions.add(Permission.objects.get(content_type__app_label="accounts", codename="manage_staff"))
        manager = type(manager).objects.get(pk=manager.pk)
        body = client_for(manager).get(detail_url(roles.WAREHOUSE_STAFF)).json()
        self.assertIn("data_scopes", body)  # có manage_staff gán trực tiếp: đọc như B4 hiện có
        for username, groups in [("kho1", [roles.WAREHOUSE_STAFF]), ("giao1", [roles.DELIVERY_STAFF]),
                                 ("cs1", [roles.CUSTOMER_SERVICE]), ("nogroup", [])]:
            client = client_for(make_user(username, *groups))
            for url in (LIST_URL, detail_url(roles.MANAGER)):
                self.assertEqual(client.get(url).status_code, 403, (username, url))
        self.assertEqual(client_for(None).get(detail_url(roles.MANAGER)).status_code, 401)

    def test_pv02_no_customer_data_or_cost_in_describe(self):
        """Mô tả phạm vi chỉ là mã và nhãn cố định: không tên/SĐT/địa chỉ, không giá vốn (bất biến 1, 9)."""
        text = self.client.get(detail_url(roles.DELIVERY_STAFF)).content.decode().lower()
        for banned in ("landed_unit_cost", "purchase_rate", "unit_cost", "password"):
            self.assertNotIn(banned, text)
