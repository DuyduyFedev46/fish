"""PV-02-AC3..AC5 — hàm phân giải phạm vi (BR-PQ-33/34, UC-6, S-5). 02b §1.3."""
from django.contrib.auth.models import Group, Permission, User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts import roles
from apps.accounts.data_scopes import catalog, resolver
from apps.accounts.models import GroupDataScope
from apps.common.tests.fixtures import make_user


def set_scope(group_name, key, value):
    GroupDataScope.objects.update_or_create(
        group=Group.objects.get(name=group_name), object_key=key, defaults={"value": value},
    )


def grant(group_name, perm):
    app_label, codename = perm.split(".")
    Group.objects.get(name=group_name).permissions.add(
        Permission.objects.get(content_type__app_label=app_label, codename=codename)
    )


def revoke(group_name, perm):
    app_label, codename = perm.split(".")
    Group.objects.get(name=group_name).permissions.remove(
        Permission.objects.get(content_type__app_label=app_label, codename=codename)
    )


def fresh(user):
    return User.objects.get(pk=user.pk)


class ResolverTests(TestCase):
    def test_pv02_ac3_union_of_groups_takes_widest(self):
        """Người thuộc K (D1 = all) và G (D1 = assigned_deliveries): trả `all`, nhóm gốc là K."""
        user = make_user("pv_k_g", roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF)
        result = resolver.resolve_data_scope(user, "orders")
        self.assertEqual(result, "all")
        full = resolver.resolve_data_scopes(fresh(user))["orders"]
        self.assertEqual((full.value, full.via_group), ("all", roles.WAREHOUSE_STAFF))

    def test_pv02_ac3_default_matrix_per_group_equals_todays_behaviour(self):
        """Giá trị phân giải của từng nhóm trên DB mới = hành vi hôm nay (D-1). `via_group` None = không nhóm đủ điều kiện."""
        narrow = {"orders": "assigned_deliveries", "invoices": "assigned_deliveries", "deliveries": "assigned",
                  "confirmation": "pending_or_called_recently", "returns": "assigned_deliveries",
                  "receipts": "created_by_me_today", "customers": "none", "audit_log": "none"}
        expected = {
            roles.OWNER: {"orders": "all", "invoices": "all", "deliveries": "all", "confirmation": "all_pending",
                          "returns": "all", "receipts": "all", "customers": "all", "audit_log": "all"},
            roles.MANAGER: {"orders": "all", "invoices": "all", "deliveries": "all", "confirmation": "all_pending",
                            "returns": "all", "receipts": "all", "customers": "all", "audit_log": "all"},
            # K không có việc gọi xác nhận, không xem khách, không xem nhật ký: rank 0.
            roles.WAREHOUSE_STAFF: {**narrow, "orders": "all", "invoices": "all", "deliveries": "all", "returns": "all",
                                    "receipts": "all"},
            # G chỉ phiếu của mình; không xem hoá đơn, phiếu nhập, nhật ký, không gọi xác nhận.
            roles.DELIVERY_STAFF: {**narrow, "customers": "assigned_deliveries"},
            # C: đơn gán hoặc trong phạm vi gọi; gọi xác nhận có; còn lại rank 0.
            roles.CUSTOMER_SERVICE: {**narrow, "orders": "assigned_or_confirmation"},
        }
        for group, row in expected.items():
            user = make_user(f"pv_matrix_{group}", group)
            actual = {key: r.value for key, r in resolver.resolve_data_scopes(user).items()}
            self.assertEqual(actual, row, group)

    def test_pv02_ac3_via_group_is_none_when_no_group_is_eligible(self):
        user = make_user("pv_via", roles.CUSTOMER_SERVICE)
        resolved = resolver.resolve_data_scopes(user)
        self.assertEqual(resolved["orders"].via_group, roles.CUSTOMER_SERVICE)
        self.assertEqual(resolved["confirmation"].via_group, roles.CUSTOMER_SERVICE)
        self.assertIsNone(resolved["deliveries"].via_group)
        self.assertIsNone(resolved["customers"].via_group)

    def test_pv02_ac4_user_without_group_gets_rank_zero_everywhere(self):
        """UC-6: không nhóm, quyền gán trực tiếp -> giá trị hẹp nhất của mọi đối tượng."""
        user = make_user("pv_direct", perms=("sales.view_salesorder",))
        resolved = resolver.resolve_data_scopes(user)
        self.assertEqual(
            {key: r.value for key, r in resolved.items()},
            {"orders": "assigned_deliveries", "invoices": "assigned_deliveries", "deliveries": "assigned",
             "confirmation": "pending_or_called_recently", "returns": "assigned_deliveries",
             "receipts": "created_by_me_today", "customers": "none", "audit_log": "none"},
        )
        for r in resolved.values():
            self.assertIsNone(r.via_group)

    def test_pv02_ac4_group_missing_config_row_is_rank_zero(self):
        GroupDataScope.objects.filter(group__name=roles.MANAGER, object_key="receipts").delete()
        user = make_user("pv_mgr", roles.MANAGER)
        self.assertEqual(resolver.resolve_data_scope(user, "receipts"), "created_by_me_today")
        self.assertEqual(resolver.resolve_data_scope(make_user("pv_mgr2", roles.MANAGER), "orders"), "all")

    def test_pv02_ac4_stored_value_not_in_options_falls_back_to_rank_zero(self):
        set_scope(roles.MANAGER, "orders", "tat_ca_khong_hop_le")
        user = make_user("pv_mgr_bad", roles.MANAGER)
        self.assertEqual(resolver.resolve_data_scope(user, "orders"), "assigned_deliveries")

    def test_pv02_ac5_owner_and_superuser_get_widest_everywhere(self):
        owner = make_user("pv_owner", roles.OWNER)
        superuser = User.objects.create_superuser("pv_super", password="x")
        for user, via in ((owner, roles.OWNER), (superuser, None)):
            resolved = resolver.resolve_data_scopes(fresh(user))
            self.assertEqual(
                {key: r.value for key, r in resolved.items()},
                {"orders": "all", "invoices": "all", "deliveries": "all", "confirmation": "all_pending",
                 "returns": "all", "receipts": "all", "customers": "all", "audit_log": "all"},
            )
            self.assertEqual({r.via_group for r in resolved.values()}, {via})

    def test_pv02_r1b_ineligible_group_value_does_not_leak(self):
        """K+G, Chủ tắt `view_orders` của K nhưng D1 của K vẫn lưu `all` (Q-7): người này chỉ thấy đơn gán (G)."""
        revoke(roles.WAREHOUSE_STAFF, "sales.view_salesorder")
        # G cũng không được có view_salesorder để chứng minh nhóm đủ điều kiện duy nhất là không còn -> thử riêng.
        user = make_user("pv_kg_leak", roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF)
        result = resolver.resolve_data_scopes(user)["orders"]
        self.assertEqual((result.value, result.via_group), ("assigned_deliveries", roles.DELIVERY_STAFF))

    def test_pv02_r1b_no_eligible_group_gives_rank_zero_with_no_via_group(self):
        revoke(roles.WAREHOUSE_STAFF, "sales.view_salesorder")
        user = make_user("pv_k_only", roles.WAREHOUSE_STAFF)
        result = resolver.resolve_data_scopes(user)["orders"]
        self.assertEqual((result.value, result.via_group), ("assigned_deliveries", None))

    def test_pv02_invoices_follow_orders_of_groups_that_can_view_invoices(self):
        """D2 lấy giá trị D1 CỦA CHÍNH nhóm có quyền xem hoá đơn; nhóm không có quyền xem hoá đơn không đóng góp."""
        set_scope(roles.DELIVERY_STAFF, "orders", "all")
        grant(roles.DELIVERY_STAFF, "sales.view_salesinvoice")
        user = make_user("pv_g_inv", roles.DELIVERY_STAFF)
        self.assertEqual(resolver.resolve_data_scope(user, "invoices"), "all")
        revoke(roles.DELIVERY_STAFF, "sales.view_salesinvoice")
        user = make_user("pv_g_inv2", roles.DELIVERY_STAFF)
        self.assertEqual(resolver.resolve_data_scope(user, "invoices"), "assigned_deliveries")  # rank 0 của D1

    def test_pv02_audit_log_is_all_only_with_view_auditlog_group(self):
        self.assertEqual(resolver.resolve_data_scope(make_user("pv_a1", roles.MANAGER), "audit_log"), "all")
        self.assertEqual(resolver.resolve_data_scope(make_user("pv_a2", roles.WAREHOUSE_STAFF), "audit_log"), "none")

    def test_pv02_customers_follow_stored_value_when_group_eligible(self):
        revoke(roles.MANAGER, "sales.view_customer_list")  # vẫn còn view_customer (Tầng 1) nên còn đủ điều kiện
        user = make_user("pv_mgr_c", roles.MANAGER)
        self.assertEqual(resolver.resolve_data_scope(user, "customers"), "all")

    def test_pv02_unknown_key_raises_keyerror(self):
        with self.assertRaises(KeyError):
            resolver.resolve_data_scope(make_user("pv_x", roles.MANAGER), "khong_co")

    def test_pv02_anonymous_user_gets_rank_zero_without_queries(self):
        from django.contrib.auth.models import AnonymousUser

        with CaptureQueriesContext(connection) as queries:
            resolved = resolver.resolve_data_scopes(AnonymousUser())
        self.assertEqual(len(queries), 0)
        self.assertEqual(resolved["orders"].value, "assigned_deliveries")

    def test_pv02_resolves_all_eight_objects_in_at_most_three_queries(self):
        user = make_user("pv_q", roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF)
        with CaptureQueriesContext(connection) as queries:
            resolver.resolve_data_scopes(user)
        self.assertLessEqual(len(queries), 3)

    def test_pv02_result_is_remembered_on_user_object(self):
        user = make_user("pv_cache", roles.WAREHOUSE_STAFF)
        resolver.resolve_data_scopes(user)
        with CaptureQueriesContext(connection) as queries:
            resolver.resolve_data_scope(user, "orders")
            resolver.resolve_data_scope(user, "receipts")
        self.assertEqual(len(queries), 0)

    def test_pv02_new_user_object_sees_changed_config_next_request(self):
        """BR-PQ-36: cấu hình đổi thì lần phân giải trên đối tượng user MỚI (request kế tiếp) thấy ngay."""
        user = make_user("pv_next", roles.MANAGER)
        self.assertEqual(resolver.resolve_data_scope(user, "receipts"), "all")
        set_scope(roles.MANAGER, "receipts", "created_by_me")
        self.assertEqual(resolver.resolve_data_scope(fresh(user), "receipts"), "created_by_me")

    def test_pv02_overrides_preview_does_not_touch_cache_or_db(self):
        user = make_user("pv_ov", roles.MANAGER)
        group_id = Group.objects.get(name=roles.MANAGER).pk
        preview = resolver.resolve_data_scopes(user, overrides={group_id: {"receipts": "created_by_me_today"}})
        self.assertEqual(preview["receipts"].value, "created_by_me_today")
        self.assertEqual(resolver.resolve_data_scope(user, "receipts"), "all")  # bản thật không bị nhớ lẫn
        self.assertEqual(GroupDataScope.objects.get(group_id=group_id, object_key="receipts").value, "all")

    def test_pv02_ties_pick_first_group_in_role_order(self):
        user = make_user("pv_tie", roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE, roles.MANAGER)
        result = resolver.resolve_data_scopes(user)["receipts"]  # cả ba đều `all`
        self.assertEqual(result.via_group, roles.MANAGER)
