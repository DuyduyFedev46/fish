"""
PV-03 và PV-07 (Lô 3) — đơn hàng và hoá đơn bán đọc phạm vi từ cấu hình; việc V1 "Xem hoá đơn bán" và V2 "Xem thông
tin khách trên đơn & hoá đơn". BR-PQ-33/34/35/36/37/38, bất biến 1 và 9. 02b §1.4, §1.5, §2.7.

Dùng chung dữ liệu giả của mốc PV-01 (`fixtures.build_scene`, giờ cố định 06/10/2026 10:00 giờ VN). Mỗi lần đổi cấu hình
trong test đều nạp lại user bằng `fresh` (bộ nhớ phân giải nằm trên đối tượng user, 02b §1.3 luật 5).
"""
from unittest import mock

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.accounts.capabilities import registry
from apps.accounts.models import GroupDataScope
from apps.common.tests.fixtures import make_user

from . import fixtures

V1 = "view_sales_invoices"
V2 = "view_order_customer_info"
V1_PERMS = ("sales.view_salesinvoice", "sales.view_salesinvoiceline")
V2_PERM = "sales.view_order_customer_info"
COST_KEYS = ("unit_cost", "cogs", "gross_profit", "landed_unit_cost", "purchase_rate")


def set_scope(group_name, key, value):
    GroupDataScope.objects.update_or_create(
        group=Group.objects.get(name=group_name), object_key=key, defaults={"value": value})


def _perm(perm):
    app_label, codename = perm.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def revoke(group_name, *perms):
    Group.objects.get(name=group_name).permissions.remove(*[_perm(p) for p in perms])


def grant(group_name, *perms):
    Group.objects.get(name=group_name).permissions.add(*[_perm(p) for p in perms])


class ScopeSceneBase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._now_patch = mock.patch("django.utils.timezone.now", return_value=fixtures.NOW)
        cls._now_patch.start()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._now_patch.stop()

    @classmethod
    def setUpTestData(cls):
        cls.scene = fixtures.build_scene()

    # --- helpers --------------------------------------------------------------
    def user(self, label):
        return User.objects.get(pk=self.scene.users[label].pk)

    def get(self, label, url, **params):
        client = APIClient()
        client.force_authenticate(self.user(label))
        return client.get(url, params)

    def codes_labels(self, response):
        rows = response.data["results"]
        return {self.scene.codes[row["code"]] for row in rows if row["code"] in self.scene.codes}

    def order(self, label):
        return self.scene.orders[label]


class OrderListScopeTests(ScopeSceneBase):
    COURIER_ORDERS = {
        "order_assigned_courier", "order_failed_courier", "order_ended_3_days", "order_ended_7_days_inside",
        "order_ended_8_days", "order_cancelled_courier",
    }

    def test_pv03_ac1_courier_with_assigned_scope_sees_only_own_orders(self):
        response = self.get("courier", "/api/sales/orders/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.codes_labels(response), self.COURIER_ORDERS)
        self.assertEqual(response.data["count"], len(self.COURIER_ORDERS))

    def test_pv03_ac2_changing_scope_takes_effect_on_next_request(self):
        before = self.get("courier", "/api/sales/orders/")
        self.assertEqual(before.data["count"], len(self.COURIER_ORDERS))
        set_scope(roles.DELIVERY_STAFF, "orders", "all")
        after = self.get("courier", "/api/sales/orders/")
        self.assertEqual(after.data["count"], len(fixtures.ORDER_SPECS))
        self.assertIn("order_assigned_other", self.codes_labels(after))

    def test_pv03_ac3_customer_service_sees_assigned_and_confirmation_scope(self):
        response = self.get("customer_service", "/api/sales/orders/")
        labels = self.codes_labels(response)
        self.assertIn("order_confirming_pending", labels)
        self.assertIn("order_called_recent_by_cs", labels)
        self.assertNotIn("order_called_by_other_cs", labels)
        self.assertNotIn("order_assigned_other", labels)
        # Thu hẹp về "chỉ phiếu gán cho tôi": CSKH không có phiếu gán nên rỗng.
        set_scope(roles.CUSTOMER_SERVICE, "orders", "assigned_deliveries")
        narrowed = self.get("customer_service", "/api/sales/orders/")
        self.assertEqual(narrowed.data["count"], 0)

    def test_pv03_ac3_customer_service_widened_to_all_sees_every_order(self):
        set_scope(roles.CUSTOMER_SERVICE, "orders", "all")
        response = self.get("customer_service", "/api/sales/orders/")
        self.assertEqual(response.data["count"], len(fixtures.ORDER_SPECS))

    def test_pv03_ac4_out_of_scope_order_is_404_everywhere(self):
        other = self.order("order_assigned_other")
        for url in (
            f"/api/sales/orders/{other.pk}/",
            f"/api/guidance/order/{other.pk}/",
            f"/api/guidance/order/{other.code}/",
        ):
            self.assertEqual(self.get("courier", url).status_code, 404, url)
        own = self.order("order_assigned_courier")
        self.assertEqual(self.get("courier", f"/api/sales/orders/{own.pk}/").status_code, 200)

    @override_settings(AI_ENABLED=True)
    def test_pv03_ac5_ai_lookup_behaves_like_order_does_not_exist(self):
        other = self.order("order_assigned_other")
        client = APIClient()
        client.force_authenticate(self.user("courier"))
        response = client.post(
            "/api/ai/commands/sales.salesorder.retrieve/call/", {"target_id": str(other.pk), "args": {}}, format="json")
        self.assertEqual(response.status_code, 404)
        body = response.content.decode()
        self.assertNotIn(other.code, body)

    def test_pv03_ac7_gate_stays_closed_when_view_orders_is_off(self):
        """Phạm vi `all` không cấp quyền xem: tắt `view_orders` thì 403 như hôm nay (BR-PQ-34)."""
        revoke(roles.WAREHOUSE_STAFF, "sales.view_salesorder", "sales.view_salesorderline")
        set_scope(roles.WAREHOUSE_STAFF, "orders", "all")
        self.assertEqual(self.get("warehouse_staff", "/api/sales/orders/").status_code, 403)

    def test_pv03_ac8_no_cost_fields_for_user_without_view_cost(self):
        order = self.order("order_assigned_courier")
        for label, url in (
            ("warehouse_staff", f"/api/sales/orders/{order.pk}/"),
            ("warehouse_staff", "/api/sales/orders/"),
            ("warehouse_staff", "/api/sales/invoices/"),
            ("warehouse_staff", f"/api/sales/invoices/{self.scene.invoices['invoice_of_order_assigned_courier'].pk}/"),
            ("courier", f"/api/sales/orders/{order.pk}/"),
        ):
            response = self.get(label, url)
            self.assertEqual(response.status_code, 200, (label, url))
            text = response.content.decode()
            for key in COST_KEYS:
                self.assertNotIn(f'"{key}"', text, (label, url, key))

    def test_pv03_unauthenticated_is_401(self):
        self.assertEqual(APIClient().get("/api/sales/orders/").status_code, 401)
        self.assertEqual(APIClient().get("/api/sales/invoices/").status_code, 401)

    def search(self, label, q):
        """NEW-1: tìm theo SĐT/tên khách đi bằng POST search/ (GET `q` chỉ còn khớp mã đơn)."""
        client = APIClient()
        client.force_authenticate(self.user(label))
        return client.post("/api/sales/orders/search/", {"q": q}, format="json")

    def test_pv03_search_by_customer_phone_respects_scope_and_v2(self):
        """R2: tìm theo SĐT chỉ khớp đơn người gọi được xem khách; thiếu V2 thì không dò được SĐT."""
        other = self.order("order_assigned_other")
        phone = other.phone
        self.assertEqual(self.search("warehouse_staff", phone).data["count"], 1)
        revoke(roles.WAREHOUSE_STAFF, V2_PERM)
        self.assertEqual(self.search("warehouse_staff", phone).data["count"], 0)
        self.assertEqual(self.search("warehouse_staff", other.code).data["count"], 1)

    def test_pv03_search_by_customer_name_blocked_without_v2(self):
        other = self.order("order_assigned_other")
        name = other.customer.name
        self.assertEqual(self.search("warehouse_staff", name).data["count"], 1)
        revoke(roles.WAREHOUSE_STAFF, V2_PERM)
        self.assertEqual(self.search("warehouse_staff", name).data["count"], 0)

    def test_pv03_default_scope_for_union_user_is_widest(self):
        """Người K+G: K có D1 = all nên thấy mọi đơn (khớp hành vi hôm nay)."""
        response = self.get("warehouse_courier", "/api/sales/orders/")
        self.assertEqual(response.data["count"], len(fixtures.ORDER_SPECS))

    def test_pv03_cross_group_leak_is_closed(self):
        """R1b: K tắt `view_orders` nhưng D1 của K còn lưu `all`; người K+G chỉ thấy đơn của phiếu gán cho mình."""
        revoke(roles.WAREHOUSE_STAFF, "sales.view_salesorder", "sales.view_salesorderline")
        response = self.get("warehouse_courier", "/api/sales/orders/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.codes_labels(response), {"order_assigned_warehouse_courier"})


class InvoiceScopeTests(ScopeSceneBase):
    def _assign_one_note_to_warehouse(self):
        note = self.scene.notes["note_of_order_assigned_other"]
        note.assigned_to = self.scene.users["warehouse_staff"]
        note.save(update_fields=["assigned_to"])

    def test_pv03_ac6_invoice_list_totals_and_detail_follow_orders_scope(self):
        self._assign_one_note_to_warehouse()
        set_scope(roles.WAREHOUSE_STAFF, "orders", "assigned_deliveries")
        response = self.get("warehouse_staff", "/api/sales/invoices/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["order_code"], self.order("order_assigned_other").code)
        self.assertEqual(response.data["totals"]["amount"], "100000")
        mine = self.scene.invoices["invoice_of_order_assigned_other"]
        foreign = self.scene.invoices["invoice_of_order_assigned_courier"]
        self.assertEqual(self.get("warehouse_staff", f"/api/sales/invoices/{mine.pk}/").status_code, 200)
        self.assertEqual(self.get("warehouse_staff", f"/api/sales/invoices/{foreign.pk}/").status_code, 404)

    def test_pv03_invoice_list_default_for_warehouse_is_all(self):
        response = self.get("warehouse_staff", "/api/sales/invoices/")
        self.assertEqual(response.data["count"], len([s for s in fixtures.ORDER_SPECS if s.get("invoice", True)]))

    def test_pv07_ac6_invoice_scope_works_when_view_orders_is_off(self):
        """Q-7: V1 bật, `view_orders` tắt, D1 = assigned_deliveries: hoá đơn vẫn 200 và theo D1."""
        self._assign_one_note_to_warehouse()
        revoke(roles.WAREHOUSE_STAFF, "sales.view_salesorder", "sales.view_salesorderline")
        set_scope(roles.WAREHOUSE_STAFF, "orders", "assigned_deliveries")
        response = self.get("warehouse_staff", "/api/sales/invoices/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(self.get("warehouse_staff", "/api/sales/orders/").status_code, 403)

    def test_pv07_ac5_turning_v1_off_gives_403(self):
        revoke(roles.WAREHOUSE_STAFF, *V1_PERMS)
        self.assertEqual(self.get("warehouse_staff", "/api/sales/invoices/").status_code, 403)

    def test_pv07_ac2_warehouse_sees_customer_name_on_invoice_list(self):
        """Ngoại lệ đã duyệt (Q-4): trước đây rỗng, nay có giá trị."""
        response = self.get("warehouse_staff", "/api/sales/invoices/")
        names = {row["customer_name"] for row in response.data["results"]}
        self.assertIn(self.order("order_assigned_other").customer.name, names)
        self.assertNotIn(None, names)

    def test_pv07_ac3_turning_v2_off_hides_customer_on_invoice_list(self):
        revoke(roles.WAREHOUSE_STAFF, V2_PERM)
        response = self.get("warehouse_staff", "/api/sales/invoices/")
        self.assertEqual(response.status_code, 200)
        for row in response.data["results"]:
            self.assertIsNone(row["customer_name"])
            self.assertEqual(row["customer_hidden_reason"], "not_permitted")
            self.assertTrue(row["order_code"])
            self.assertTrue(row["amount"])

    def test_pv07_invoice_detail_has_no_personal_data_keys(self):
        """Chi tiết hoá đơn (SalesInvoiceSerializer) không có tên, SĐT, địa chỉ: liệt kê field tường minh."""
        invoice = self.scene.invoices["invoice_of_order_assigned_courier"]
        text = self.get("owner", f"/api/sales/invoices/{invoice.pk}/").content.decode()
        for fake in fixtures.FAKE_STRINGS:
            self.assertNotIn(fake, text)


class OrderCustomerInfoTests(ScopeSceneBase):
    def test_pv07_ac3_turning_v2_off_hides_customer_on_orders(self):
        revoke(roles.WAREHOUSE_STAFF, V2_PERM)
        order = self.order("order_assigned_courier")
        listing = self.get("warehouse_staff", "/api/sales/orders/")
        self.assertEqual(listing.status_code, 200)
        for row in listing.data["results"]:
            self.assertIsNone(row["customer_name"])
            self.assertIsNone(row["customer_phone"])
            self.assertEqual(row["customer_hidden_reason"], "not_permitted")
            self.assertTrue(row["status"])
            self.assertTrue(row["total_amount"])
        detail = self.get("warehouse_staff", f"/api/sales/orders/{order.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["customer"], {"name": None, "phone": None, "address": None})
        self.assertEqual(detail.data["customer_hidden_reason"], "not_permitted")
        self.assertEqual(detail.data["code"], order.code)
        self.assertEqual(detail.data["total_amount"], "100000")
        text = detail.content.decode()
        for fake in fixtures.FAKE_STRINGS:
            self.assertNotIn(fake, text)

    def test_pv07_cancel_note_stays_empty_when_customer_hidden(self):
        """`cancel_note` có thể chứa tên khách: luôn rỗng khi che (không chỉ khi quá cửa sổ)."""
        order = self.order("order_assigned_courier")
        order.cancel_note = "Khách Giả 04 xin huỷ"
        order.save(update_fields=["cancel_note"])
        self.assertEqual(
            self.get("warehouse_staff", f"/api/sales/orders/{order.pk}/").data["cancel_note"], "Khách Giả 04 xin huỷ")
        revoke(roles.WAREHOUSE_STAFF, V2_PERM)
        detail = self.get("warehouse_staff", f"/api/sales/orders/{order.pk}/")
        self.assertEqual(detail.data["cancel_note"], "")
        self.assertNotIn("Khách Giả", detail.content.decode())

    def test_pv07_ac4_window_hides_customer_for_courier_after_8_days(self):
        old = self.order("order_ended_8_days")
        detail = self.get("courier", f"/api/sales/orders/{old.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["customer"], {"name": None, "phone": None, "address": None})
        self.assertEqual(detail.data["customer_hidden_reason"], "expired")
        self.assertEqual(detail.data["cancel_note"], "")
        inside = self.order("order_ended_7_days_inside")
        visible = self.get("courier", f"/api/sales/orders/{inside.pk}/")
        self.assertEqual(visible.data["customer"]["name"], inside.customer.name)
        self.assertIsNone(visible.data["customer_hidden_reason"])

    def test_pv07_window_does_not_apply_when_scope_is_all(self):
        """Nhóm ở "Tất cả đơn" không bị cửa sổ (đúng như Chủ/Quản lý/NV kho hôm nay)."""
        set_scope(roles.DELIVERY_STAFF, "orders", "all")
        old = self.order("order_ended_8_days")
        detail = self.get("courier", f"/api/sales/orders/{old.pk}/")
        self.assertEqual(detail.data["customer"]["name"], old.customer.name)

    def test_pv07_reason_is_not_permitted_before_expired(self):
        revoke(roles.DELIVERY_STAFF, V2_PERM)
        old = self.order("order_ended_8_days")
        detail = self.get("courier", f"/api/sales/orders/{old.pk}/")
        self.assertEqual(detail.data["customer_hidden_reason"], "not_permitted")

    def test_pv07_confirmation_scope_still_gives_customer_data_to_customer_service(self):
        pending = self.order("order_confirming_pending")
        detail = self.get("customer_service", f"/api/sales/orders/{pending.pk}/")
        self.assertEqual(detail.data["customer"]["name"], pending.customer.name)

    def test_pv07_confirmation_branch_is_off_when_scope_is_assigned_only(self):
        set_scope(roles.CUSTOMER_SERVICE, "orders", "assigned_deliveries")
        pending = self.order("order_confirming_pending")
        self.assertEqual(self.get("customer_service", f"/api/sales/orders/{pending.pk}/").status_code, 404)

    def test_pv07_public_lookup_never_returns_personal_data(self):
        """AC9: V2 bật cho mọi nhóm; tra đơn công khai vẫn không có tên, SĐT, địa chỉ đầy đủ."""
        order = self.order("order_booked_unpaid")
        response = APIClient().get(f"/api/shop/orders/{order.code}/", {"phone_last4": order.phone[-4:]})
        self.assertEqual(response.status_code, 200)
        text = response.content.decode()
        for fake in fixtures.FAKE_STRINGS:
            self.assertNotIn(fake, text)


class CustomerInfoCapabilityRegistryTests(TestCase):
    def test_pv07_ac8_v1_v2_registered_outside_owner_only_with_disjoint_perms(self):
        v1, v2 = registry.BY_KEY[V1], registry.BY_KEY[V2]
        self.assertEqual(v1.perms, V1_PERMS)
        self.assertEqual(v2.perms, (V2_PERM,))
        self.assertEqual((v1.section, v2.section), (registry.SECTION_SALES, registry.SECTION_SALES))
        self.assertFalse(v1.owner_only)
        self.assertFalse(v2.owner_only)
        others = {p for c in registry.CAPABILITIES if c.key not in (V1, V2) for p in c.perms}
        self.assertFalse(others & set(v1.perms + v2.perms))
        self.assertEqual(v2.label, "Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền")

    def test_pv07_ac1_matrix_after_migration(self):
        expected_v1 = {roles.OWNER: "on", roles.MANAGER: "on", roles.WAREHOUSE_STAFF: "on",
                       roles.DELIVERY_STAFF: "off", roles.CUSTOMER_SERVICE: "off"}
        expected_v2 = {name: "on" for name in roles.ALL_ROLES}
        owner = make_user("pv07_owner", roles.OWNER)
        manager = make_user("pv07_manager", roles.MANAGER)
        # `manage_staff` đủ để đọc ma trận: chủ.
        client = APIClient()
        client.force_authenticate(owner)
        for code in roles.ALL_ROLES:
            body = client.get(f"/api/staff/groups/{code}/").data
            self.assertEqual(body["capabilities"][V1], expected_v1[code], code)
            self.assertEqual(body["capabilities"][V2], expected_v2[code], code)
        self.assertTrue(manager)

    def test_pv07_ac7_owner_group_is_locked(self):
        owner = make_user("pv07_owner2", roles.OWNER)
        client = APIClient()
        client.force_authenticate(owner)
        response = client.put(f"/api/staff/groups/{roles.OWNER}/capabilities/", {"capabilities": {V2: True}},
                              format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "GROUP_LOCKED")

    def test_pv07_permission_is_declared_on_sales_order_model(self):
        self.assertTrue(Permission.objects.filter(
            content_type__app_label="sales", codename="view_order_customer_info").exists())
        for name in roles.ALL_ROLES:
            self.assertTrue(
                Group.objects.get(name=name).permissions.filter(codename="view_order_customer_info").exists(), name)

    def test_pv07_invoices_row_gate_capability_is_registry_key(self):
        """Review 06/10, lệch 2: từ Lô 3 dòng `invoices` trỏ tới việc V1 thật."""
        owner = make_user("pv07_owner3", roles.OWNER)
        client = APIClient()
        client.force_authenticate(owner)
        rows = {row["key"]: row for row in client.get(f"/api/staff/groups/{roles.MANAGER}/").data["data_scopes"]}
        self.assertEqual(rows["invoices"]["gate_capability"], V1)


class RefundScopeTests(ScopeSceneBase):
    def test_pv07_refund_names_follow_v2(self):
        listing = self.get("manager", "/api/sales/refunds/")
        self.assertEqual(listing.status_code, 200)
        names = {row["customer_name"] for row in listing.data["results"]}
        self.assertIn(self.order("order_assigned_courier").customer.name, names)
        revoke(roles.MANAGER, V2_PERM)
        hidden = self.get("manager", "/api/sales/refunds/")
        for row in hidden.data["results"]:
            self.assertIsNone(row["customer_name"])
            self.assertIsNone(row["customer_phone"])
            self.assertEqual(row["customer_hidden_reason"], "not_permitted")
            self.assertTrue(row["order_code"])
        text = hidden.content.decode()
        for fake in fixtures.FAKE_STRINGS:
            self.assertNotIn(fake, text)


class QueryBudgetTests(ScopeSceneBase):
    """R8 (02b §4): phân giải phạm vi thêm tối đa 3 truy vấn cho một request danh sách, dù gọi nhiều lần (nhớ trên user)."""

    def _count(self, label, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        client = APIClient()
        client.force_authenticate(self.user(label))
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(client.get(url).status_code, 200)
        return len(queries)

    def test_pv03_resolver_adds_at_most_three_queries_to_order_and_invoice_lists(self):
        from apps.accounts.data_scopes import resolver

        constant = {obj.key: resolver.Resolved("all", None) for obj in resolver.catalog.OBJECTS}
        for label, url in (("courier", "/api/sales/orders/"), ("warehouse_staff", "/api/sales/invoices/")):
            with_resolver = self._count(label, url)
            with mock.patch("apps.accounts.data_scopes.resolver.resolve_data_scopes", return_value=constant):
                baseline = self._count(label, url)
            self.assertLessEqual(with_resolver - baseline, 3, (label, url, with_resolver, baseline))
