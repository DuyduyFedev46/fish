"""
Lô 6 / B2 (BR-PQ-31): MỘT hàm quyền "xem được danh bạ khách" cho mọi chỗ dùng
(`can_view_customer_directory`), cộng các chỗ của Lô 2 và Lô 3 đã chuyển sang hàm đó:
- Dòng thời gian `GET /api/guidance/customer/<id>/` (Lô 2, R2).
- Lọc `GET /api/sales/orders/?customer=<id>` (Lô 3, R3).
- Nhãn quyền ở `GET /api/auth/me/` và chặn AI đọc danh bạ khách (bất biến 9).
Toàn bộ dữ liệu là giả.
"""
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from apps.accounts import roles
from apps.accounts.auth.services import CAPABILITY_LABELS
from apps.accounts.models import AuditLog
from apps.ai.policy import rules
from apps.common.audit import record_audit
from apps.common.tests.fixtures import client_for, make_user
from apps.sales.customers.permissions import (
    VIEW_CUSTOMER_LIST_PERM,
    can_view_customer_directory,
)
from apps.sales.models import Customer
from apps.sales.orders.scope import can_filter_orders_by_customer

FAKE_NAME = "Khách Thử A"
FAKE_PHONE = "0900000123"
PERM = "sales.view_customer_list"


class PermissionBase(TestCase):
    def setUp(self):
        self.users = {
            "owner": make_user("pm_owner", roles.OWNER),
            "manager": make_user("pm_manager", roles.MANAGER),
            "warehouse": make_user("pm_kho", roles.WAREHOUSE_STAFF),
            "courier": make_user("pm_giao", roles.DELIVERY_STAFF),
            "service": make_user("pm_cs", roles.CUSTOMER_SERVICE),
        }
        self.clients = {k: client_for(u) for k, u in self.users.items()}
        self.clients["anonymous"] = client_for(None)
        self.customer = Customer.objects.create(phone=FAKE_PHONE, name=FAKE_NAME)


class SinglePermissionFunctionTests(PermissionBase):
    def test_perm_constant_is_the_tier2_code(self):
        self.assertEqual(VIEW_CUSTOMER_LIST_PERM, PERM)
        self.assertIn(("view_customer_list", "Xem khách hàng"), list(Customer._meta.permissions))

    def test_function_true_only_for_owner_and_manager(self):
        expected = {"owner": True, "manager": True, "warehouse": False, "courier": False, "service": False}
        for key, want in expected.items():
            self.assertEqual(can_view_customer_directory(self.users[key]), want, key)

    def test_function_follows_has_perm_not_group_name(self):
        extra = make_user("pm_extra", perms=(PERM,))
        self.assertTrue(can_view_customer_directory(extra))
        manager = self.users["manager"]
        Group.objects.get(name=roles.MANAGER).permissions.remove(
            Permission.objects.get(content_type__app_label="sales", codename="view_customer_list")
        )
        manager = type(manager).objects.get(pk=manager.pk)
        self.assertFalse(can_view_customer_directory(manager))

    def test_function_rejects_anonymous_and_none(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(can_view_customer_directory(AnonymousUser()))
        self.assertFalse(can_view_customer_directory(None))

    def test_order_filter_helper_uses_the_same_function(self):
        for key, user in self.users.items():
            self.assertEqual(can_filter_orders_by_customer(user), can_view_customer_directory(user), key)
        extra = make_user("pm_extra2", perms=(PERM,))
        self.assertTrue(can_filter_orders_by_customer(extra))

    def test_no_duplicate_group_name_check_left_in_the_two_callers(self):
        import inspect

        from apps.sales.customers import next_steps
        from apps.sales.orders import scope

        for module in (next_steps, scope):
            source = inspect.getsource(module)
            self.assertNotIn("sees_customer_directory", source.replace("# ", ""), module.__name__)
            self.assertNotIn("_meta.permissions", source, module.__name__)


class CustomerTimelineWithNewPermissionTests(PermissionBase):
    """Nợ Lô 6 (00-can-duy-quyet): provider `customer` dùng `sales.view_customer_list`."""

    def url(self):
        return f"/api/guidance/customer/{self.customer.pk}/"

    def test_timeline_owner_and_manager_200_with_no_personal_data(self):
        record_audit(
            "update_customer", actor=self.users["manager"], obj=self.customer,
            changes={"fields": ["note"]},
        )
        for who in ("owner", "manager"):
            res = self.clients[who].get(self.url())
            self.assertEqual(res.status_code, 200, who)
            body = res.content.decode()
            self.assertNotIn(FAKE_NAME, body)
            self.assertNotIn(FAKE_PHONE, body)
            self.assertIn("no-store", res.headers["Cache-Control"])

    def test_timeline_three_groups_without_permission_403(self):
        for who in ("warehouse", "courier", "service"):
            res = self.clients[who].get(self.url())
            self.assertEqual(res.status_code, 403, who)
            self.assertNotIn(FAKE_PHONE, res.content.decode())
        self.assertEqual(self.clients["anonymous"].get(self.url()).status_code, 401)

    def test_timeline_user_with_only_the_new_permission_can_read(self):
        # PV-05: dòng thời gian khách theo D7 của nhóm; Chủ bật "Xem khách hàng" cho nhóm NV kho kèm D7 = all.
        from apps.accounts.models import GroupDataScope

        warehouse_group = Group.objects.get(name=roles.WAREHOUSE_STAFF)
        warehouse_group.permissions.add(Permission.objects.get(content_type__app_label="sales", codename="view_customer_list"))
        GroupDataScope.objects.update_or_create(group=warehouse_group, object_key="customers", defaults={"value": "all"})
        extra = make_user("pm_tl_extra", roles.WAREHOUSE_STAFF)
        self.assertEqual(client_for(extra).get(self.url()).status_code, 200)

    def test_timeline_follows_permission_switch_off_for_manager(self):
        Group.objects.get(name=roles.MANAGER).permissions.remove(
            Permission.objects.get(content_type__app_label="sales", codename="view_customer_list")
        )
        manager = make_user("pm_manager_off", roles.MANAGER)
        self.assertEqual(client_for(manager).get(self.url()).status_code, 403)

    def test_timeline_shows_directory_edit_without_values(self):
        client = client_for(self.users["owner"])
        res = client.patch(
            f"/api/sales/customer-directory/{self.customer.pk}/", {"note": "Ghi chú Thử"}, format="json",
        )
        self.assertEqual(res.status_code, 200)
        body = client.get(self.url()).json()
        self.assertTrue(any(e["kind"] == "update_customer" for e in body["timeline"]))
        raw = str(body)
        self.assertNotIn("Ghi chú Thử", raw)
        self.assertNotIn(FAKE_NAME, raw)
        self.assertEqual(AuditLog.objects.filter(action="update_customer").count(), 1)


class OrderListCustomerFilterTests(PermissionBase):
    """Lô 3 (R3): `?customer=` vẫn 403 với nhóm không có quyền, kiểm trước mọi tham số khác."""

    def test_filter_403_for_three_groups_without_permission(self):
        for who in ("warehouse", "courier", "service"):
            res = self.clients[who].get("/api/sales/orders/", {"customer": self.customer.pk})
            self.assertEqual(res.status_code, 403, who)
            self.assertNotIn(FAKE_PHONE, res.content.decode())

    def test_filter_allowed_for_owner_manager_and_extra_perm(self):
        for who in ("owner", "manager"):
            res = self.clients[who].get("/api/sales/orders/", {"customer": self.customer.pk})
            self.assertEqual(res.status_code, 200, who)
        extra = make_user("pm_of_extra", perms=(PERM, "sales.view_salesorder"))
        res = client_for(extra).get("/api/sales/orders/", {"customer": self.customer.pk})
        self.assertEqual(res.status_code, 200)

    def test_filter_blocked_when_owner_switches_permission_off_for_manager(self):
        Group.objects.get(name=roles.MANAGER).permissions.remove(
            Permission.objects.get(content_type__app_label="sales", codename="view_customer_list")
        )
        manager = make_user("pm_of_manager", roles.MANAGER)
        res = client_for(manager).get("/api/sales/orders/", {"customer": self.customer.pk})
        self.assertEqual(res.status_code, 403)

    def test_empty_customer_param_is_not_a_filter_for_any_group(self):
        res = self.clients["warehouse"].get("/api/sales/orders/", {"customer": ""})
        self.assertEqual(res.status_code, 200)


class CapabilityLabelAndAiPolicyTests(PermissionBase):
    def test_capability_label_is_present_and_shown_in_me(self):
        self.assertEqual(CAPABILITY_LABELS[PERM], "Xem khách hàng")
        owner_caps = self.clients["owner"].get("/api/auth/me/").json()["capabilities"]
        self.assertIn({"code": PERM, "label": "Xem khách hàng"}, owner_caps)
        warehouse_caps = self.clients["warehouse"].get("/api/auth/me/").json()["capabilities"]
        self.assertNotIn(PERM, [c["code"] for c in warehouse_caps])

    def test_ai_policy_forbids_customer_directory_and_old_customer_endpoint(self):
        for path in ("/api/sales/customer-directory/", "/api/sales/customers/"):
            self.assertTrue(rules.is_url_forbidden(path), path)
            self.assertTrue(rules.is_url_forbidden(f"{path}12/"), path)

    def test_ai_scrubs_default_address_key(self):
        self.assertIn("default_address", rules.SCRUB_PII_KEYS)
