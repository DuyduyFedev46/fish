"""
PV-12 — Cổng phát hành phạm vi dữ liệu (Lô 6): quét endpoint bằng TOKEN THẬT và các sàn cứng S-1..S-8.

Dùng token thật (như console và như `auth/tests/test_no_role_gate.py`), không `force_authenticate`, để mọi lần gọi đi qua
cả lớp xác thực, tức là quét luôn cổng D-3 (`AUTH_NO_ROLE`). Bộ thu `Collector` của PV-01 giữ nguyên; ở đây chỉ đổi cách xác thực.

- AC1: ảnh chụp PV-01 xanh là `test_scope_snapshot.py` (chạy cùng suite); ở đây chỉ chốt không còn mục chờ Duy.
- AC2: mỗi đối tượng D1, D3..D7 × mỗi giá trị: tập dòng ở MỌI endpoint bằng nhau và bằng tập do hàm phạm vi trả.
- AC3 (S-1) giá vốn, AC4 (S-2) API công khai, AC5 (S-3) log/AuditLog, AC6 (S-4) cửa sổ, AC7 (S-6) xoá/tạo tay, AC8 grep.
- Lô 6: GET nhóm không còn khoá `scopes` cũ.

Mọi dữ liệu khách là GIẢ (fixtures.py).
"""
import logging
import re
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import Group, Permission, User
from django.core.cache import cache
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.accounts.data_scopes import catalog
from apps.accounts.models import AuditLog, GroupDataScope
from apps.common.cost_keys import COST_KEYS as CANONICAL_COST_KEYS
from apps.delivery.confirmation.scope import note_in_confirmation_scope
from apps.delivery.models import CustomerCall, DeliveryNote, LabelPrint
from apps.delivery.scope import scope_deliveries_for
from apps.inventory.models import ReturnToStock
from apps.inventory.returns.scope import scope_returns_for
from apps.purchasing.models import PurchaseReceipt
from apps.purchasing.receipts.scope import scope_receipts_for
from apps.sales.customers.scope import scope_customers_for
from apps.sales.models import Customer, SalesInvoice, SalesOrder
from apps.sales.orders.scope import scope_orders_for

from . import fixtures
from .snapshot import PENDING_DUY_DIFFS, Collector
from .test_scope_snapshot import load_baseline

# Nguồn chuẩn của repo (không tự chép tập con, M2 review Lô 6) + khoá `costs` (tổng chi phí mua lồng trong lô).
COST_KEYS = CANONICAL_COST_KEYS | {"costs"}
COST_PERMS = ("inventory.view_costprice", "reports.view_profitreport")
PROBE_GROUP = "pv12_probe"
BACKEND_APPS = Path(__file__).resolve().parents[3]  # backend/apps


def token_client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


class TokenCollector(Collector):
    """`Collector` của PV-01 nhưng mỗi tài khoản gọi bằng token thật."""

    def __init__(self, scene):
        self.scene = scene
        self.clients = {
            label: (token_client(user) if user is not None else APIClient()) for label, user in scene.users.items()
        }


def all_gate_perms():
    perms = set(fixtures.DIRECT_PERMISSIONS)
    for obj in catalog.OBJECTS:
        perms.update(obj.gate_perms)
    perms.update(("inventory.view_batch", "sales.view_salesorderline", "sales.view_customer"))
    return perms


def _perm(code):
    app_label, codename = code.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def set_scope(group, key, value):
    GroupDataScope.objects.update_or_create(group=group, object_key=key, defaults={"value": value})


def narrow_all(group):
    for obj in catalog.stored_objects():
        set_scope(group, obj.key, catalog.narrowest_value(obj))


def widen_all(group):
    for obj in catalog.stored_objects():
        set_scope(group, obj.key, catalog.widest_value(obj))


def facts_of(collector, user_label, endpoint):
    return set(collector.collect_user(user_label, only={endpoint})[endpoint])


def visible(facts):
    return {f.split(":", 1)[1] for f in facts if f.startswith("visible:")}


def status_ok(facts):
    return {f[len("status:"):].rsplit("=", 1)[0] for f in facts if f.startswith("status:") and f.endswith("=200")}


class ReleaseGateBase(TestCase):
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

    def deep_keys(self, node):
        found = set()
        if isinstance(node, dict):
            for key, value in node.items():
                found.add(key)
                found |= self.deep_keys(value)
        elif isinstance(node, list):
            for item in node:
                found |= self.deep_keys(item)
        return found


class SweepEqualityTests(ReleaseGateBase):
    """PV-12-AC2: mọi endpoint của một đối tượng cho CÙNG tập dòng, bằng tập do hàm phạm vi trả (BR-PQ-35, R2)."""

    # đối tượng -> (loại dòng ở Scene, [(endpoint của Collector, 'visible' | 'ok')])
    SWEEP = {
        "orders": ("orders", [
            ("orders.list", "visible"), ("orders.search_code", "visible"), ("orders.detail", "ok"),
            ("guidance.order", "ok"), ("ai.orders_detail", "ok"),
            ("invoices.list", "invoice_orders"), ("invoices.detail", "invoice_orders_ok"),
        ]),
        "deliveries": ("notes", [
            ("deliveries.list", "visible"), ("deliveries.detail", "ok"), ("guidance.delivery", "ok"),
        ]),
        "returns": ("returns", [("returns.list", "visible"), ("returns.detail", "ok"), ("guidance.return", "ok")]),
        "receipts": ("receipts", [
            ("receipts.list", "visible"), ("receipts.detail", "ok"), ("guidance.receipt", "ok"),
        ]),
        "customers": ("customers", [
            ("directory.list", "visible"), ("directory.search", "visible"), ("directory.detail", "ok"),
            ("customers.list", "visible"), ("customers.detail", "ok"), ("guidance.customer", "ok"),
        ]),
    }

    def setUp(self):
        scene = self.scene
        self.group = Group.objects.create(name=PROBE_GROUP)
        self.group.permissions.set([_perm(code) for code in sorted(all_gate_perms())])
        self.user = User.objects.create_user("pv12_probe", password="x")
        self.user.groups.add(self.group)
        scene.users["probe"] = self.user
        # Dựng dòng của probe: phiếu giao, cuộc gọi và phiếu nhập từng gán cho người mẫu nay thuộc probe.
        DeliveryNote.objects.filter(assigned_to=scene.users["courier"]).update(assigned_to=self.user)
        CustomerCall.objects.filter(created_by=scene.users["customer_service"]).update(created_by=self.user)
        PurchaseReceipt.objects.filter(created_by=scene.users["warehouse_staff"]).update(created_by=self.user)
        narrow_all(self.group)
        self.collector = TokenCollector(scene)

    def fresh_user(self):
        return User.objects.get(pk=self.user.pk)

    def invoiced_order_labels(self):
        return [label[len("invoice_of_"):] for label in self.scene.invoices]

    def expected(self, key):
        user = self.fresh_user()
        scene = self.scene
        if key == "orders":
            pks = scope_orders_for(user, SalesOrder.objects.all()).values_list("pk", flat=True)
            return {scene.labels("orders")[pk] for pk in pks}
        if key == "deliveries":
            pks = scope_deliveries_for(user, DeliveryNote.objects.all()).values_list("pk", flat=True)
            return {scene.labels("notes")[pk] for pk in pks}
        if key == "returns":
            pks = scope_returns_for(user, ReturnToStock.objects.all()).values_list("pk", flat=True)
            return {scene.labels("returns")[pk] for pk in pks}
        if key == "receipts":
            pks = scope_receipts_for(user, PurchaseReceipt.objects.all()).values_list("pk", flat=True)
            return {scene.labels("receipts")[pk] for pk in pks}
        if key == "customers":
            pks = scope_customers_for(user, Customer.objects.all()).values_list("pk", flat=True)
            return {scene.labels("customers")[pk] for pk in pks}
        raise AssertionError(key)

    def sweep(self, key):
        kind, endpoints = self.SWEEP[key]
        got = {}
        for endpoint, mode in endpoints:
            if endpoint == "orders.search_code":  # tìm theo mã đơn: không phụ thuộc cửa sổ dữ liệu khách như tìm theo tên
                facts = self.collector.list_facts("probe", "/api/sales/orders/search/", "orders", method="post",
                                                  body={"q": "SO-PV"})
            else:
                facts = facts_of(self.collector, "probe", endpoint)
            if mode == "invoice_orders":  # Hoá đơn bán (D2) đi theo D1: dòng hoá đơn gắn với đơn tương ứng
                got[endpoint] = self.invoice_order_labels(visible(facts))
            elif mode == "invoice_orders_ok":
                got[endpoint] = self.invoice_order_labels(status_ok(facts))
            else:
                got[endpoint] = visible(facts) if mode == "visible" else status_ok(facts)
        return got

    @staticmethod
    def invoice_order_labels(invoice_labels):
        prefix = "invoice_of_"
        return {label[len(prefix):] for label in invoice_labels}

    def test_pv12_ac2_every_endpoint_returns_the_same_rows_as_the_scope_function_for_every_value(self):
        for key in self.SWEEP:
            obj = catalog.BY_KEY[key]
            for option in obj.options:
                with self.subTest(object=key, value=option.value):
                    narrow_all(self.group)
                    set_scope(self.group, key, option.value)
                    self.assertEqual(self.fresh_user().groups.count(), 1)
                    expected = self.expected(key)
                    for endpoint, rows in self.sweep(key).items():
                        if endpoint.startswith("invoices."):  # chỉ đơn đã có hoá đơn mới có dòng hoá đơn
                            self.assertEqual(rows, expected & set(self.invoiced_order_labels()),
                                             f"{key}={option.value} @ {endpoint}")
                        else:
                            self.assertEqual(rows, expected, f"{key}={option.value} @ {endpoint}")

    def test_pv12_ac2_sweep_is_not_vacuous_widest_differs_from_narrowest(self):
        """Chống quét rỗng: giá trị rộng nhất thấy nhiều dòng hơn giá trị hẹp nhất ở mọi đối tượng quét được."""
        for key in ("orders", "deliveries", "returns", "receipts", "customers"):
            obj = catalog.BY_KEY[key]
            with self.subTest(object=key):
                narrow_all(self.group)
                narrow_rows = self.expected(key)
                set_scope(self.group, key, catalog.widest_value(obj))
                wide_rows = self.expected(key)
                self.assertLess(len(narrow_rows), len(wide_rows))
                self.assertGreater(len(wide_rows), 2)

    def test_pv12_ac2_confirmation_detail_and_queue_follow_scope_function(self):
        scene = self.scene
        labels = scene.labels("notes")
        for option in catalog.CONFIRMATION.options:
            with self.subTest(value=option.value):
                narrow_all(self.group)
                set_scope(self.group, "confirmation", option.value)
                user = self.fresh_user()
                notes = {labels[n.pk]: n for n in DeliveryNote.objects.select_related("confirmation")}
                expected = {label for label, note in notes.items() if note_in_confirmation_scope(user, note)}
                got_detail = status_ok(facts_of(self.collector, "probe", "confirmation.detail"))
                self.assertEqual(got_detail, expected)
                in_queue = set()
                for endpoint in ("confirmation.queue", "confirmation.queue_done", "confirmation.queue_escalated"):
                    facts = facts_of(self.collector, "probe", endpoint)
                    rows = visible(facts)
                    with_customer_data = {f.split(":")[1] for f in facts if f.startswith("pii:")}
                    # Hàng chờ liệt kê mọi mục theo trạng thái nhưng CHỈ mục trong phạm vi D4 mang dữ liệu khách (hiện trạng
                    # của PV-01, khoá bởi tệp mốc): tập dòng có dữ liệu khách phải bằng tập phạm vi giao với dòng hiện.
                    self.assertEqual(with_customer_data, rows & expected, endpoint)
                    in_queue |= rows
                self.assertTrue(in_queue)

    def test_pv12_ac2_ai_list_rows_stay_inside_scope(self):
        """Danh sách cho AI có giới hạn số dòng nên chỉ kiểm không mở thêm dòng ngoài phạm vi và không rỗng."""
        for key, endpoint in (("orders", "ai.orders_list"), ("deliveries", "ai.deliveries_list")):
            for option in catalog.BY_KEY[key].options:
                with self.subTest(object=key, value=option.value):
                    narrow_all(self.group)
                    set_scope(self.group, key, option.value)
                    rows = visible(facts_of(self.collector, "probe", endpoint))
                    expected = self.expected(key)
                    self.assertLessEqual(rows, expected)
                    self.assertTrue(rows)

    def test_pv12_ac2_dashboard_recent_orders_stay_inside_order_scope(self):
        for option in catalog.ORDERS.options:
            with self.subTest(value=option.value):
                narrow_all(self.group)
                set_scope(self.group, "orders", option.value)
                rows = visible(facts_of(self.collector, "probe", "dashboard.summary"))
                self.assertLessEqual(rows, self.expected("orders"))


class HardFloorTests(ReleaseGateBase):
    """PV-12-AC3..AC7: sàn cứng S-1..S-6 với token thật."""

    GROUPS = {
        "manager": roles.MANAGER, "warehouse_staff": roles.WAREHOUSE_STAFF, "courier": roles.DELIVERY_STAFF,
        "customer_service": roles.CUSTOMER_SERVICE,
    }

    def setUp(self):
        for label, group_name in self.GROUPS.items():
            group = Group.objects.get(name=group_name)
            widen_all(group)  # Given: mọi phạm vi rộng nhất
            group.permissions.remove(*[_perm(code) for code in COST_PERMS])  # Given: không có view_cost/view_profit
        self.clients = {label: token_client(self.scene.users[label]) for label in self.GROUPS}

    def urls(self):
        scene = self.scene
        batch = scene.batch.pk
        urls = ["/api/sales/orders/", "/api/sales/invoices/", "/api/sales/refunds/", "/api/delivery/notes/",
                "/api/inventory/returns/", "/api/purchasing/receipts/", "/api/confirmation/queue/",
                "/api/sales/customers/", "/api/sales/customer-directory/", "/api/dashboard/summary/",
                "/api/inventory/batches/", f"/api/inventory/batches/{batch}/"]
        urls += [f"/api/sales/orders/{o.pk}/" for o in scene.orders.values()]
        urls += [f"/api/sales/invoices/{o.pk}/" for o in scene.invoices.values()]
        urls += [f"/api/delivery/notes/{o.pk}/" for o in scene.notes.values()]
        urls += [f"/api/purchasing/receipts/{o.pk}/" for o in scene.receipts.values()]
        urls += [f"/api/inventory/returns/{o.pk}/" for o in scene.returns.values()]
        urls += [f"/api/sales/refunds/{o.pk}/" for o in scene.refunds.values()]
        # L1 (review Lô 6): các endpoint AC2 đã dùng, quét thêm giá vốn.
        urls += [f"/api/guidance/receipt/{o.pk}/" for o in scene.receipts.values()]
        urls += [f"/api/guidance/order/{o.pk}/" for o in scene.orders.values()]
        urls += [f"/api/delivery/notes/lookup/?code={n.code}.1" for n in scene.notes.values()]
        return urls

    def test_pv12_ac3_s1_no_cost_field_in_any_endpoint_for_non_owner_groups_at_widest_scope(self):
        checked = 0
        for label, client in self.clients.items():
            for url in self.urls():
                cache.clear()
                response = client.get(url)
                if response.status_code != 200:
                    continue
                with self.subTest(user=label, url=url):
                    leaked = self.deep_keys(response.json()) & COST_KEYS
                    self.assertEqual(leaked, set())
                checked += 1
        self.assertGreater(checked, 100)

    def test_pv12_ac3_s1_ai_detail_and_reports_batches_do_not_leak_cost(self):
        """L1: AI chi tiết đơn/phiếu giao không có khoá giá vốn; `reports/batches/` (lãi lỗ) không mở khi thiếu quyền."""
        for note in self.scene.notes.values():  # tem để `delivery/notes/lookup/` có dòng thật mà quét
            LabelPrint.objects.create(note=note, print_no=1, printed_by=self.scene.users["owner"])
        cache.clear()
        checked = 0
        for label, client in self.clients.items():
            with self.subTest(user=label, url="/api/reports/batches/"):
                cache.clear()
                self.assertNotEqual(client.get("/api/reports/batches/").status_code, 200)
            for command, kind in (("sales.salesorder.retrieve", "orders"), ("delivery.deliverynote.retrieve", "notes")):
                for obj in getattr(self.scene, kind).values():
                    cache.clear()
                    with override_settings(AI_ENABLED=True):
                        response = client.post(f"/api/ai/commands/{command}/call/",
                                               {"target_id": str(obj.pk), "args": {}}, format="json")
                    if response.status_code != 200:
                        continue
                    with self.subTest(user=label, command=command, target=obj.pk):
                        self.assertEqual(self.deep_keys(response.json()) & COST_KEYS, set())
                    checked += 1
            for url in (f"/api/delivery/notes/lookup/?code={n.code}.1" for n in self.scene.notes.values()):
                cache.clear()
                response = client.get(url)
                if response.status_code == 200:
                    self.assertEqual(self.deep_keys(response.json()) & COST_KEYS, set(), url)
                    checked += 1
        self.assertGreater(checked, 0)

    def test_pv12_ac3_s1_cost_fields_exist_for_owner_so_the_sweep_can_fail(self):
        """Đối chứng: Chủ thấy giá vốn ở chính các endpoint đó (không thì quét ở trên vô nghĩa)."""
        owner = token_client(self.scene.users["owner"])
        receipt = next(iter(self.scene.receipts.values()))
        keys = self.deep_keys(owner.get(f"/api/purchasing/receipts/{receipt.pk}/").json())
        self.assertTrue(keys & COST_KEYS)

    def test_pv12_ac4_s2_public_apis_never_return_name_phone_address(self):
        order = self.scene.orders["order_assigned_courier"]
        client = APIClient()
        bodies = [client.post("/api/shop/orders/lookup/", {"order_code": order.code, "phone": order.phone}, format="json"),
                  client.get("/api/shop/catalog/"), client.get("/api/public/site-info/")]
        self.assertEqual(bodies[0].status_code, 200)
        for response in bodies:
            self.assertEqual(response.status_code, 200)
            text = response.content.decode()
            for fake in fixtures.FAKE_STRINGS:
                self.assertNotIn(fake, text)
        self.assertTrue(set(bodies[0].json()) .isdisjoint({"phone", "customer", "delivery_address", "name", "address"}))

    def test_pv12_ac4_s2_wrong_phone_leaks_nothing(self):
        order = self.scene.orders["order_assigned_courier"]
        response = APIClient().post(
            "/api/shop/orders/lookup/", {"order_code": order.code, "phone": "0900000000"}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        for fake in fixtures.FAKE_STRINGS:
            self.assertNotIn(fake, response.content.decode())

    def test_pv12_ac5_s3_logs_and_audit_log_have_no_customer_personal_data(self):
        records = []

        class Capture(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage() + " " + str(record.args))

        root = logging.getLogger()
        handler, old_level = Capture(level=logging.DEBUG), root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            owner = token_client(self.scene.users["owner"])
            group = Group.objects.get(name=roles.DELIVERY_STAFF)
            version = owner.get(f"/api/staff/groups/{group.name}/").json()["version"]
            body = {"version": version, "scopes": {"orders": "all", "customers": "assigned_deliveries"},
                    "confirm_customer_data_widening": True}
            self.assertEqual(owner.post(f"/api/staff/groups/{group.name}/permissions-preview/", body, format="json")
                             .status_code, 200)
            self.assertEqual(owner.put(f"/api/staff/groups/{group.name}/capabilities/", body, format="json")
                             .status_code, 200)
            for label, client in self.clients.items():
                for url in self.urls()[:40]:
                    cache.clear()
                    client.get(url)
        finally:
            root.removeHandler(handler)
            root.setLevel(old_level)
        audit_text = " ".join(str(vars(row)) for row in AuditLog.objects.all())
        blob = " ".join(records) + " " + audit_text
        self.assertTrue(records, "bộ bắt log không bắt được gì: bài kiểm vô nghĩa")
        for fake in fixtures.FAKE_STRINGS:
            self.assertNotIn(fake, blob)

    def test_pv12_ac5_s3_ai_rows_carry_no_customer_personal_fields(self):
        """Ngữ cảnh AI: danh sách đơn/phiếu giao cho AI không có khoá tên, SĐT, địa chỉ (không thêm so với trước)."""
        collector = TokenCollector(self.scene)
        for endpoint in ("ai.orders_list", "ai.deliveries_list", "ai.orders_detail"):
            facts = facts_of(collector, "manager", endpoint)
            with self.subTest(endpoint=endpoint):
                baseline_pii = {f for f in facts if f.startswith("pii:")}
                before = {f for f in load_baseline()["manager"][endpoint] if f.startswith("pii:")}
                self.assertLessEqual(baseline_pii, before)

    def test_pv12_ac6_s4_window_hides_customer_data_of_old_finished_notes_and_no_key_changes_the_window(self):
        scene = self.scene
        group = Group.objects.get(name=roles.DELIVERY_STAFF)
        narrow_all(group)
        courier = token_client(scene.users["courier"])
        old_note = scene.notes["note_of_order_ended_8_days"]
        data = courier.get(f"/api/delivery/notes/{old_note.pk}/").json()
        self.assertEqual(self.pii_values(data), [])
        old_order = scene.orders["order_ended_8_days"]
        self.assertEqual(self.pii_values(courier.get(f"/api/sales/orders/{old_order.pk}/").json()), [])
        inside = courier.get(f"/api/delivery/notes/{scene.notes['note_of_order_ended_7_days_inside'].pk}/").json()
        self.assertTrue(self.pii_values(inside))  # đối chứng: trong cửa sổ vẫn có dữ liệu khách
        owner = token_client(scene.users["owner"])
        version = owner.get(f"/api/staff/groups/{group.name}/").json()["version"]
        delivery_days, confirmation_days = settings.DELIVERY_PII_RECENT_DAYS, settings.CONFIRMATION_PII_RECENT_DAYS
        scopes_before = dict(GroupDataScope.objects.filter(group=group).values_list("object_key", "value"))
        audit_before = AuditLog.objects.count()
        url = f"/api/staff/groups/{group.name}/capabilities/"
        for key in ("delivery_pii_recent_days", "DELIVERY_PII_RECENT_DAYS", "confirmation_pii_recent_days",
                    "window_days", "pii_window_days", "recent_days"):
            # Kèm một thay đổi HỢP LỆ: request chỉ có thể bị từ chối vì khoá lạ (không phải vì thân rỗng).
            top_level = owner.put(url, {"version": version, "scopes": {"receipts": "created_by_me"}, key: 365},
                                  format="json")
            with self.subTest(key=key, where="top_level"):
                self.assertEqual(top_level.status_code, 400)
                self.assertEqual(top_level.json()["code"], "INPUT_NOT_ALLOWED")
            nested = owner.put(url, {"version": version, "scopes": {key: 365}}, format="json")
            with self.subTest(key=key, where="in_scopes"):
                self.assertEqual(nested.status_code, 400)
                self.assertEqual(nested.json()["code"], "SCOPE_OBJECT_UNKNOWN")
        self.assertEqual(owner.get(f"/api/staff/groups/{group.name}/").json()["version"], version)
        self.assertEqual(dict(GroupDataScope.objects.filter(group=group).values_list("object_key", "value")),
                         scopes_before)
        self.assertEqual(AuditLog.objects.count(), audit_before)
        self.assertEqual((settings.DELIVERY_PII_RECENT_DAYS, settings.CONFIRMATION_PII_RECENT_DAYS),
                         (delivery_days, confirmation_days))
        detail = owner.get(f"/api/staff/groups/{group.name}/").content.decode().lower()
        self.assertNotIn("recent_days", detail)

    @staticmethod
    def pii_values(data):
        from .snapshot import pii_paths

        return sorted(pii_paths(data))

    def test_pv12_ac7_s6_no_delete_and_no_manual_create_even_at_widest_scope(self):
        scene = self.scene
        order = scene.orders["order_assigned_courier"]
        invoice = scene.invoices["invoice_of_order_assigned_courier"]
        receipt = scene.receipts["receipt_owner_old"]
        before = (SalesOrder.objects.count(), SalesInvoice.objects.count(), PurchaseReceipt.objects.count(),
                  AuditLog.objects.count())
        clients = dict(self.clients, owner=token_client(scene.users["owner"]),
                       superuser=token_client(scene.users["superuser"]))
        AuditLog.objects.first() or AuditLog.objects.create(action="seed", actor_kind="system")
        before = before[:3] + (AuditLog.objects.count(),)
        calls = (
            ("delete", f"/api/sales/orders/{order.pk}/"), ("delete", f"/api/sales/invoices/{invoice.pk}/"),
            ("delete", f"/api/purchasing/receipts/{receipt.pk}/"), ("delete", "/api/audit-logs/"),
            ("put", "/api/audit-logs/"), ("patch", "/api/audit-logs/"), ("post", "/api/sales/orders/"), ("post", "/api/sales/invoices/"),
        )
        for label, client in clients.items():
            for method, url in calls:
                with self.subTest(user=label, method=method, url=url):
                    response = getattr(client, method)(url, {}, format="json") if method != "delete" else client.delete(url)
                    # Route danh sách audit-logs chỉ có GET: DELETE/PUT/PATCH phải 405 (hoặc 403 khi không đủ quyền xem).
                    expected_codes = (403, 405) if url == "/api/audit-logs/" else (403, 404, 405)
                    self.assertIn(response.status_code, expected_codes)
        after = (SalesOrder.objects.count(), SalesInvoice.objects.count(), PurchaseReceipt.objects.count(),
                 AuditLog.objects.count())
        self.assertEqual(after, before)


class NoLegacyScopesTests(ReleaseGateBase):
    """Lô 6: bỏ khoá `scopes` cũ ở GET nhóm; `scopes` ở thân PUT/preview (02b §2.3) vẫn là đầu vào hợp lệ."""

    def test_pv12_group_detail_and_list_have_no_legacy_scopes_key(self):
        owner = token_client(self.scene.users["owner"])
        listing = owner.get("/api/staff/groups/").json()
        rows = listing if isinstance(listing, list) else listing.get("results", listing)
        for row in rows:
            self.assertNotIn("scopes", row)
        for group in Group.objects.filter(name__in=roles.ALL_ROLES):
            body = owner.get(f"/api/staff/groups/{group.name}/").json()
            self.assertNotIn("scopes", body, group.name)
            self.assertEqual(len(body["data_scopes"]), 8)

    def test_pv12_put_still_accepts_scopes_object_as_input(self):
        owner = token_client(self.scene.users["owner"])
        group = Group.objects.get(name=roles.WAREHOUSE_STAFF)
        version = owner.get(f"/api/staff/groups/{group.name}/").json()["version"]
        response = owner.put(f"/api/staff/groups/{group.name}/capabilities/",
                             {"version": version, "scopes": {"receipts": "created_by_me"}}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("scopes", response.json())


class SourceGrepTests(TestCase):
    """PV-12-AC8 (BR-PQ-33): không còn chỗ quyết phạm vi dòng bằng tên nhóm; bảng phạm vi cố định đã bỏ."""

    BANNED = (
        "FULL_SCOPE_GROUPS", "has_full_delivery_scope", "CUSTOMER_DIRECTORY_GROUPS", "sees_customer_directory",
        "is_customer_service", "GROUP_SCOPES", "legacy_scopes", "LEGACY_ORDERS", "LEGACY_DELIVERIES",
    )

    def source_files(self):
        for path in BACKEND_APPS.rglob("*.py"):
            parts = path.relative_to(BACKEND_APPS).parts
            if "tests" in parts or "migrations" in parts or path.name.startswith("test_"):
                continue
            yield path

    def test_pv12_ac8_no_banned_name_in_product_code(self):
        offenders = []
        for path in self.source_files():
            text = path.read_text(encoding="utf-8")
            offenders += [f"{path.relative_to(BACKEND_APPS)}: {name}" for name in self.BANNED if name in text]
        self.assertEqual(offenders, [])

    # Ngoại lệ có chủ đích (L3 review Lô 6): `can_cancel_any_receipt` so tên nhóm owner/manager nhưng là QUYỀN HÀNH ĐỘNG
    # (huỷ phiếu nhập của người khác, V-DW2, PV-06-AC5/6, 02b §2 dòng 98), không phải phạm vi đọc dòng nên AC8 không áp.
    # Nợ: đưa thành việc trong ma trận (BR-PQ-33, backlog sau đợt Shop). Chỉ ĐÚNG hàm này được phép; chỗ khác thì đỏ.
    # Cũng ngoại lệ hành động, phát hiện khi mở rộng quét sang services.py: chọn ai được GÁN phiếu giao (người nhận việc
    # phải thuộc nhóm `delivery_staff`, BR-GH-23), không quyết ai XEM dòng nào.
    GROUP_NAME_EXCEPTIONS = {
        "purchasing/receipts/services.py": ("can_cancel_any_receipt",),
        "delivery/services.py": ("list_deliverers", "assign_deliverer"),
    }
    EXPECTED_EXCEPTIONS_USED = [
        ("delivery/services.py", "assign_deliverer"), ("delivery/services.py", "list_deliverers"),
        ("purchasing/receipts/services.py", "can_cancel_any_receipt"),
    ]

    def test_pv12_ac8_services_read_group_names_only_in_declared_exceptions(self):
        """Quét `services.py` của mọi module có `scope.py` (module có phạm vi dòng): so tên nhóm chỉ được ở hàm ngoại lệ."""
        pattern = re.compile(r"roles\.[A-Z_]+|groups__name|groups\.filter\(name")
        offenders, used, scanned = [], set(), 0
        for path in self.source_files():
            if path.name != "services.py" or not (path.parent / "scope.py").exists():
                continue
            scanned += 1
            rel = path.relative_to(BACKEND_APPS).as_posix()
            allowed, current = self.GROUP_NAME_EXCEPTIONS.get(rel, ()), None
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                match = re.match(r"(?:async )?def (\w+)\(", line)
                if match:
                    current = match.group(1)
                elif line and not line[0].isspace() and not line.startswith(("#", ")", "@")):
                    current = None
                if not pattern.search(line.split("#", 1)[0]):
                    continue
                if current in allowed:
                    used.add((rel, current))
                elif "roles.ALL_ROLES" not in line:
                    offenders.append(f"{rel}:{number}")
        self.assertEqual(sorted(used), self.EXPECTED_EXCEPTIONS_USED,
                         "ngoại lệ đã khai nhưng không còn dùng: gỡ khỏi danh sách")
        self.assertGreater(scanned, 3, "quét không thấy module nào: bài kiểm vô nghĩa")
        self.assertEqual(offenders, [], "services.py so tên nhóm ngoài ngoại lệ đã khai (xem GROUP_NAME_EXCEPTIONS)")

    def test_pv12_ac8_scope_modules_never_read_group_names(self):
        """Mọi `scope.py` / `resolver.py` quyết phạm vi bằng cấu hình, không so tên nhóm."""
        pattern = re.compile(r"roles\.[A-Z_]+|groups__name|groups\.filter\(name|\"(owner|manager|warehouse_staff|delivery_staff|customer_service)\"")
        offenders = []
        for path in self.source_files():
            if path.name not in ("scope.py", "resolver.py", "pii_scope.py", "permissions.py"):
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("#", 1)[0]
                if pattern.search(code) and "ALL_ROLES" not in code and "roles.OWNER" not in code:
                    offenders.append(f"{path.relative_to(BACKEND_APPS)}:{number}")
        self.assertEqual(offenders, [])

    def test_pv12_ac1_no_pending_duy_diffs_left_in_snapshot_exceptions(self):
        self.assertEqual(PENDING_DUY_DIFFS, ())
