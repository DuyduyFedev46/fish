"""
PV-14 (Lô 7 BE) — `GET /api/auth/me/` có khoá `data_scopes`: 8 dòng phạm vi dữ liệu của CHÍNH người đăng nhập (02b §6.1.3).

Dùng token thật (như `test_no_role_gate.py`) vì `force_authenticate` bỏ qua cổng D-3. Dữ liệu toàn bộ là giả.
"""
from django.contrib.auth.models import Group, User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.accounts.capabilities.tests.base import put_caps
from apps.accounts.data_scopes import catalog
from apps.accounts.data_scopes.resolver import resolve_data_scope
from apps.common.tests.fixtures import make_order_with_note, make_user
from apps.delivery.confirmation.scope import confirmation_scope_value
from apps.delivery.scope import deliveries_scope_value
from apps.inventory.returns.scope import returns_scope_value
from apps.purchasing.receipts.scope import receipts_scope_value
from apps.sales.customers.scope import customers_scope_value
from apps.sales.orders.scope import orders_scope_value

ME = "/api/auth/me/"
KEYS = ["orders", "invoices", "deliveries", "confirmation", "returns", "receipts", "customers", "audit_log"]
ROW_KEYS = {"key", "label", "value", "value_label", "via_group"}
FAKE_PHONE = "0900000042"
# Số truy vấn gốc của `/me` cho NV kho (đo trước khi sửa, 10/10). Giới hạn Lô 7: tăng tối đa 3.
BASELINE_QUERIES = 6
MAX_EXTRA_QUERIES = 3

DEFAULTS = {
    roles.OWNER: ["all", "all", "all", "all_pending", "all", "all", "all", "all"],
    roles.MANAGER: ["all", "all", "all", "all_pending", "all", "all", "all", "all"],
    roles.WAREHOUSE_STAFF: ["all", "all", "all", "none", "all", "all", "none", "none"],
    roles.DELIVERY_STAFF: ["assigned_deliveries", "none", "assigned", "none", "assigned_deliveries", "none",
                           "assigned_deliveries", "none"],
    roles.CUSTOMER_SERVICE: ["assigned_or_confirmation", "none", "none", "pending_or_called_recently", "none",
                             "none", "none", "none"],
}

SCOPE_FUNCTIONS = {
    "orders": orders_scope_value,
    "invoices": lambda user: resolve_data_scope(user, "invoices"),
    "deliveries": deliveries_scope_value,
    "confirmation": confirmation_scope_value,
    "returns": returns_scope_value,
    "receipts": receipts_scope_value,
    "customers": customers_scope_value,
}


def token_client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def scopes_of(user):
    response = token_client(user).get(ME)
    assert response.status_code == 200, response.content
    return {row["key"]: row for row in response.json()["data_scopes"]}


def values_of(user):
    rows = scopes_of(user)
    return [rows[key]["value"] for key in KEYS]


def owner_client():
    return token_client(make_user("chu", roles.OWNER))


class MeDataScopesTests(TestCase):
    def test_pv14_ac1_warehouse_plus_courier_takes_widest_with_group(self):
        user = make_user("kho_giao", roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF)
        rows = scopes_of(user)
        self.assertEqual((rows["orders"]["value"], rows["orders"]["via_group"]), ("all", roles.WAREHOUSE_STAFF))
        self.assertEqual((rows["customers"]["value"], rows["customers"]["via_group"]),
                         ("assigned_deliveries", roles.DELIVERY_STAFF))
        self.assertEqual((rows["invoices"]["value"], rows["invoices"]["via_group"]), ("all", roles.WAREHOUSE_STAFF))
        self.assertEqual(rows["invoices"]["value_label"], "Hoá đơn của tất cả đơn")
        self.assertEqual(rows["customers"]["value_label"], "Khách của phiếu giao gán cho tôi (trong cửa sổ)")

    def test_pv14_ac2_no_group_user_sees_nothing_even_with_direct_permission(self):
        user = make_user("khong_nhom", perms=("sales.view_salesorder",))
        client = token_client(user)
        response = client.get(ME)
        self.assertEqual(response.status_code, 200, response.content)
        rows = response.json()["data_scopes"]
        self.assertEqual([row["key"] for row in rows], KEYS)
        for row in rows:
            self.assertEqual((row["value"], row["value_label"], row["via_group"]), ("none", "Không xem", None))
        blocked = client.get("/api/sales/orders/")
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json().get("code"), "AUTH_NO_ROLE")

    def test_pv14_ac3_courier_has_eight_rows_with_none_where_no_access(self):
        user = make_user("giao", roles.DELIVERY_STAFF)
        response = token_client(user).get(ME).json()["data_scopes"]
        self.assertEqual([row["key"] for row in response], KEYS)
        for row in response:
            self.assertEqual(set(row), ROW_KEYS)
        rows = {row["key"]: row for row in response}
        for key in ("invoices", "receipts", "audit_log", "confirmation"):
            self.assertEqual(rows[key]["value"], "none", key)
            self.assertEqual(rows[key]["value_label"], "Không xem")
            self.assertIsNone(rows[key]["via_group"])
        self.assertEqual([row["label"] for row in response],
                         [catalog.BY_KEY[key].label for key in KEYS])

    def test_pv14_default_table_for_each_single_group_and_superuser(self):
        for group, expected in DEFAULTS.items():
            with self.subTest(group=group):
                self.assertEqual(values_of(make_user(f"u_{group}", group)), expected)
        admin = User.objects.create_superuser("quan_tri", password="x")
        rows = scopes_of(admin)
        self.assertEqual([rows[key]["value"] for key in KEYS], DEFAULTS[roles.OWNER])
        self.assertTrue(all(row["via_group"] is None for row in rows.values()))
        owner_rows = scopes_of(User.objects.get(username=f"u_{roles.OWNER}"))
        self.assertTrue(all(row["via_group"] == roles.OWNER for row in owner_rows.values()))
        self.assertEqual(owner_rows["audit_log"]["value_label"], "Tất cả")

    def test_pv14_value_label_none_and_invoices_have_dedicated_text(self):
        rows = scopes_of(make_user("cs", roles.CUSTOMER_SERVICE))
        self.assertEqual(rows["orders"]["value_label"], "Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận")
        self.assertEqual(rows["confirmation"]["via_group"], roles.CUSTOMER_SERVICE)
        manager = scopes_of(make_user("ql", roles.MANAGER))
        self.assertEqual(manager["invoices"]["value_label"], "Hoá đơn của tất cả đơn")
        courier = make_user("giao_v", roles.DELIVERY_STAFF, perms=("sales.view_salesinvoice",))
        # Quyền gán riêng, nhóm không đủ điều kiện: rank 0, via_group null.
        row = scopes_of(courier)["invoices"]
        self.assertEqual((row["value"], row["via_group"]), ("assigned_deliveries", None))
        self.assertEqual(row["value_label"], "Hoá đơn của đơn có phiếu giao gán cho tôi")

    def test_pv14_ac1_value_matches_the_scope_function_views_use(self):
        """Chống lệch kiểu R2: dòng nào khác `none` thì value phải bằng hàm phạm vi mà view dùng."""
        people = [make_user(f"p_{g}", g) for g in roles.ALL_ROLES]
        people += [
            make_user("kho_giao2", roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF),
            make_user("kho_cs", roles.WAREHOUSE_STAFF, roles.CUSTOMER_SERVICE),
            User.objects.create_superuser("root", password="x"),
        ]
        checked = 0
        for person in people:
            rows = scopes_of(person)
            fresh = User.objects.get(pk=person.pk)
            for key, function in SCOPE_FUNCTIONS.items():
                if rows[key]["value"] == "none":
                    continue
                checked += 1
                self.assertEqual(rows[key]["value"], function(fresh), (person.username, key))
        self.assertGreater(checked, 40)

    def test_pv14_confirmation_row_calls_confirmation_scope_value(self):
        from unittest import mock

        user = make_user("cs2", roles.CUSTOMER_SERVICE)
        with mock.patch("apps.delivery.confirmation.scope.confirmation_scope_value", return_value="all_pending") as spy:
            rows = scopes_of(user)
        self.assertTrue(spy.called)
        self.assertEqual(rows["confirmation"]["value"], "all_pending")

    def test_pv14_cap_d7_stays_assigned_when_view_customers_capability_is_off(self):
        courier = make_user("giao_d7", roles.DELIVERY_STAFF)
        response = put_caps(owner_client(), roles.DELIVERY_STAFF, scopes={"customers": "all"}, confirm_customer_data_widening=True)
        self.assertEqual(response.status_code, 200, response.content)
        row = scopes_of(courier)["customers"]
        self.assertEqual(row["value"], "assigned_deliveries")
        self.assertEqual(row["value"], customers_scope_value(User.objects.get(pk=courier.pk)))

    def test_pv14_direct_confirm_permission_in_ineligible_group_gives_none(self):
        user = make_user("kho_goi", roles.WAREHOUSE_STAFF, perms=("delivery.confirm_with_customer",))
        # NV kho mặc định có quyền gọi xác nhận qua nhóm trong migration cũ? Chỉ ép tình huống nhóm không đủ điều kiện.
        group = Group.objects.get(name=roles.WAREHOUSE_STAFF)
        group.permissions.remove(*group.permissions.filter(codename="confirm_with_customer"))
        user = User.objects.get(pk=user.pk)
        self.assertEqual(confirmation_scope_value(user), "none")
        row = scopes_of(user)["confirmation"]
        self.assertEqual((row["value"], row["via_group"]), ("none", None))

    def test_pv14_br_pq_36_owner_change_applies_on_next_request(self):
        warehouse = make_user("kho_36", roles.WAREHOUSE_STAFF)
        self.assertEqual(scopes_of(warehouse)["receipts"]["value"], "all")
        response = put_caps(owner_client(), roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me_today"})
        self.assertEqual(response.status_code, 200, response.content)
        row = scopes_of(warehouse)["receipts"]
        self.assertEqual(row["value"], "created_by_me_today")
        self.assertEqual(row["value_label"], "Do tôi tạo trong ngày")

    def test_pv14_ac6_old_keys_kept_and_types_unchanged(self):
        body = token_client(make_user("kho_k", roles.WAREHOUSE_STAFF)).get(ME).json()
        self.assertEqual(set(body), {
            "id", "username", "display_name", "phone", "groups", "permissions", "can_view_cost", "can_view_profit",
            "home", "group_labels", "capabilities", "must_change_password", "is_superuser", "ai_features_enabled",
            "data_scopes"})
        self.assertIsInstance(body["permissions"], list)
        self.assertIsInstance(body["group_labels"], list)
        self.assertIsInstance(body["data_scopes"], list)

    def test_pv14_no_leak_of_cost_customer_data_or_other_group_config(self):
        make_order_with_note("DH-PV14", FAKE_PHONE)
        for group in (roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE):
            raw = token_client(make_user(f"leak_{group}", group)).get(ME).content.decode()
            for text in ("purchase_rate", "landed_unit_cost", "unit_cost", FAKE_PHONE, "DH-PV14",
                         "CONFIRMATION_PII_RECENT_DAYS", "row_version", "version"):
                self.assertNotIn(text, raw, (group, text))
        # Giá trị cấu hình của nhóm người đó không thuộc không xuất hiện: NV giao không thấy "created_by_me_today" của kho.
        put_caps(owner_client(), roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me_today"})
        courier_raw = token_client(make_user("giao_x", roles.DELIVERY_STAFF)).get(ME).content.decode()
        self.assertNotIn("created_by_me_today", courier_raw)

    def test_pv14_query_budget_grows_at_most_three(self):
        client = token_client(make_user("kho_q", roles.WAREHOUSE_STAFF))
        client.get(ME)
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(client.get(ME).status_code, 200)
        self.assertLessEqual(len(queries), BASELINE_QUERIES + MAX_EXTRA_QUERIES, [q["sql"][:80] for q in queries])

    def test_pv14_requires_login(self):
        self.assertEqual(APIClient().get(ME).status_code, 401)

    def test_pv14_ac5_courier_still_forbidden_on_other_group_config(self):
        courier = make_user("giao_ac5", roles.DELIVERY_STAFF)
        self.assertEqual(token_client(courier).get(f"/api/staff/groups/{roles.MANAGER}/").status_code, 403)
