"""
Phạm vi dữ liệu khách theo vai (SR-PII-01, SR-PII-02; bất biến 9, BR-PQ-12).

Quyết định Duy 01/10:
- Q-1: NV kho không xem danh bạ khách (`sales.view_customer` bị gỡ) -> 403 ở /api/sales/customers/.
- Q-2: NV kho vẫn thấy tên, SĐT đầy đủ, địa chỉ ở đơn hàng và phiếu giao.
- Q-3: NV giao chỉ thấy dữ liệu khách của phiếu đã kết thúc trong `DELIVERY_PII_RECENT_DAYS` ngày (giờ VN).

Quy ước khi dữ liệu khách bị ẩn: GIỮ khoá JSON, giá trị `null` (các vai khác không đổi contract).
Dữ liệu dùng toàn chuỗi giả (sentinel), không có dữ liệu thật.
"""
import datetime
import importlib
from decimal import Decimal

from django.apps import apps as django_apps
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts import roles
from apps.delivery.models import DeliveryNote
from apps.delivery.pii_scope import courier_visible_note_q, pii_cutoff
from apps.sales.models import Customer, SalesInvoice, SalesOrder

from .fixtures import client_for, make_user

# Chuỗi giả, duy nhất theo khách, để quét body response.
PII = {
    "A": {"name": "Sentinel Ten Alpha", "phone": "0911000001", "address": "Sentinel Dia Chi Alpha", "note": "Sentinel Ghi Chu Alpha", "default": "Sentinel Mac Dinh Alpha"},
    "B": {"name": "Sentinel Ten Beta", "phone": "0911000002", "address": "Sentinel Dia Chi Beta", "note": "Sentinel Ghi Chu Beta", "default": "Sentinel Mac Dinh Beta"},
    "C": {"name": "Sentinel Ten Gamma", "phone": "0911000003", "address": "Sentinel Dia Chi Gamma", "note": "Sentinel Ghi Chu Gamma", "default": "Sentinel Mac Dinh Gamma"},
}
INVOICE_ISSUED = datetime.datetime(2026, 9, 1, 8, 0, tzinfo=datetime.timezone.utc)


def make_case(key, code, *, courier=None, status=DeliveryNote.Status.PREPARING,
              completed_at=None, created_at=None):
    """Khách + đơn + hoá đơn + phiếu giao với dữ liệu cá nhân giả theo `PII[key]`."""
    data = PII[key]
    customer = Customer.objects.create(
        phone=data["phone"], name=data["name"], default_address=data["default"], note=data["note"],
    )
    order = SalesOrder.objects.create(
        code=code, customer=customer, status=SalesOrder.Status.PROCESSING,
        delivery_address=data["address"], phone=data["phone"], total_amount=Decimal("100000"),
    )
    invoice = SalesInvoice.objects.create(
        code=f"INV-{code}", sales_order=order, customer=customer, issued_at=INVOICE_ISSUED,
        amount=Decimal("100000"), status=SalesInvoice.Status.ISSUED,
    )
    note = invoice.delivery_notes.get()
    note.status = status
    note.assigned_to = courier
    note.completed_at = completed_at
    note.note = f"Ghi chu giao {key}"
    note.save()
    if created_at is not None:
        DeliveryNote.objects.filter(pk=note.pk).update(created_at=created_at)
        note.refresh_from_db()
    return order, customer, note


def body(resp):
    return resp.content.decode()


class CustomerDataScopeBase(TestCase):
    def setUp(self):
        self.owner = make_user("owner1", roles.OWNER)
        self.manager = make_user("manager1", roles.MANAGER)
        self.warehouse = make_user("warehouse1", roles.WAREHOUSE_STAFF)
        self.courier = make_user("courier1", roles.DELIVERY_STAFF)
        self.other_courier = make_user("courier2", roles.DELIVERY_STAFF)
        self.service = make_user("service1", roles.CUSTOMER_SERVICE)
        self.both = make_user("both1", roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF)
        self.order_a, self.customer_a, self.note_a = make_case("A", "SO-PII-A", courier=self.courier)
        self.order_b, self.customer_b, self.note_b = make_case("B", "SO-PII-B", courier=self.other_courier)
        self.order_c, self.customer_c, self.note_c = make_case("C", "SO-PII-C", courier=None)

    def get(self, user, url):
        return client_for(user).get(url)


class MatrixTests(CustomerDataScopeBase):
    """Ma trận Group x 3 endpoint (danh sách + chi tiết), có đếm 200 > 0 để test không rỗng."""

    def test_matrix_status_and_counts(self):
        urls = {
            "orders": ("/api/sales/orders/", f"/api/sales/orders/{self.order_b.pk}/"),
            "customers": ("/api/sales/customers/", f"/api/sales/customers/{self.customer_b.pk}/"),
            "notes": ("/api/delivery/notes/", f"/api/delivery/notes/{self.note_b.pk}/"),
        }
        # (user, endpoint) -> (status danh sách, status chi tiết khách B, số dòng danh sách)
        expected = {
            (self.owner, "orders"): (200, 200, 3),
            (self.owner, "customers"): (200, 200, 3),
            (self.owner, "notes"): (200, 200, 3),
            (self.manager, "orders"): (200, 200, 3),
            (self.manager, "customers"): (200, 200, 3),
            (self.manager, "notes"): (200, 200, 3),
            (self.warehouse, "orders"): (200, 200, 3),
            (self.warehouse, "customers"): (403, 403, None),
            (self.warehouse, "notes"): (200, 200, 3),
            (self.courier, "orders"): (200, 404, 1),
            (self.courier, "customers"): (200, 404, 1),
            (self.courier, "notes"): (200, 404, 1),
            (self.service, "customers"): (403, 403, None),
            (self.service, "notes"): (403, 403, None),
        }
        ok_count = 0
        for (user, endpoint), (list_status, detail_status, count) in expected.items():
            list_url, detail_url = urls[endpoint]
            label = f"{user.username} {endpoint}"
            resp = self.get(user, list_url)
            self.assertEqual(resp.status_code, list_status, label)
            if count is not None:
                self.assertEqual(resp.json()["count"], count, label)
                ok_count += 1
            self.assertEqual(self.get(user, detail_url).status_code, detail_status, f"{label} detail")
        self.assertGreater(ok_count, 0)

    def test_matrix_unauthenticated_401(self):
        for url in ("/api/sales/orders/", "/api/sales/customers/", "/api/delivery/notes/"):
            self.assertEqual(client_for(None).get(url).status_code, 401, url)

    def test_service_orders_list_ok_but_never_sees_unrelated_customer(self):
        resp = self.get(self.service, "/api/sales/orders/")
        self.assertEqual(resp.status_code, 200)
        for data in PII.values():
            self.assertNotIn(data["phone"], body(resp))


class WarehouseStaffTests(CustomerDataScopeBase):
    """SR-PII-01: NV kho mất danh bạ khách nhưng giữ SĐT đầy đủ ở đơn và phiếu giao (Q-2)."""

    def test_sr_pii_01_ac2_customers_403_and_body_has_no_pii(self):
        for url in ("/api/sales/customers/", f"/api/sales/customers/{self.customer_a.pk}/"):
            resp = self.get(self.warehouse, url)
            self.assertEqual(resp.status_code, 403, url)
            for data in PII.values():
                self.assertNotIn(data["phone"], body(resp))
                self.assertNotIn(data["default"], body(resp))

    def test_sr_pii_01_ac3_orders_list_still_full_phone_and_name(self):
        resp = self.get(self.warehouse, "/api/sales/orders/")
        self.assertEqual(resp.status_code, 200)
        rows = {r["code"]: r for r in resp.json()["results"]}
        self.assertEqual(len(rows), 3)
        for key, code in (("A", "SO-PII-A"), ("B", "SO-PII-B"), ("C", "SO-PII-C")):
            self.assertEqual(rows[code]["customer_phone"], PII[key]["phone"])
            self.assertEqual(rows[code]["customer_name"], PII[key]["name"])

    def test_sr_pii_01_ac3_order_detail_still_full_customer(self):
        resp = self.get(self.warehouse, f"/api/sales/orders/{self.order_b.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["customer"], {
            "name": PII["B"]["name"], "phone": PII["B"]["phone"], "address": PII["B"]["address"],
        })

    def test_sr_pii_01_ac3_delivery_notes_still_name_and_address(self):
        resp = self.get(self.warehouse, "/api/delivery/notes/")
        self.assertEqual(resp.status_code, 200)
        rows = {r["code"]: r for r in resp.json()["results"]}
        row = rows[self.note_b.code]
        self.assertEqual(row["customer_name"], PII["B"]["name"])
        self.assertEqual(row["address"], PII["B"]["address"])
        detail = self.get(self.warehouse, f"/api/delivery/notes/{self.note_b.pk}/").json()
        self.assertEqual(detail["customer_name"], PII["B"]["name"])
        self.assertEqual(detail["address"], PII["B"]["address"])

    def test_sr_pii_01_dual_role_warehouse_and_courier_sees_only_own_customers(self):
        """Kiêm nhiệm nv_kho + nv_giao: perm view_customer đến từ nv_giao nên chỉ khách của phiếu mình,
        không vòng qua full scope của nv_kho để lấy danh bạ."""
        resp = self.get(self.both, "/api/sales/customers/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)  # phiếu nào cũng chưa gán cho `both`
        self.note_c.assigned_to = self.both
        self.note_c.save(update_fields=["assigned_to"])
        resp = self.get(self.both, "/api/sales/customers/")
        self.assertEqual([r["id"] for r in resp.json()["results"]], [self.customer_c.pk])
        self.assertEqual(self.get(self.both, f"/api/sales/customers/{self.customer_a.pk}/").status_code, 404)
        # Đơn và phiếu vẫn full scope (Q-2).
        self.assertEqual(self.get(self.both, "/api/sales/orders/").json()["count"], 3)

    def test_sr_pii_01_ac1_group_permission_removed_only_from_warehouse_staff(self):
        def has(name):
            return Group.objects.get(name=name).permissions.filter(
                content_type__app_label="sales", codename="view_customer"
            ).exists()

        self.assertFalse(has(roles.WAREHOUSE_STAFF))
        for name in (roles.OWNER, roles.MANAGER, roles.DELIVERY_STAFF):
            self.assertTrue(has(name), name)
        self.assertFalse(has(roles.CUSTOMER_SERVICE))


class MigrationTests(TestCase):
    """SR-PII-01 AC1/AC4: data migration idempotent, có reverse."""

    def setUp(self):
        self.module = importlib.import_module("apps.accounts.migrations.0012_revoke_customer_view_warehouse_staff")
        self.group = Group.objects.get(name=roles.WAREHOUSE_STAFF)

    def _has(self):
        return self.group.permissions.filter(content_type__app_label="sales", codename="view_customer").exists()

    def test_sr_pii_01_ac4_forwards_idempotent_and_backwards_restores(self):
        self.assertFalse(self._has())
        self.module.revoke_view_customer(django_apps, None)  # chạy lại: không lỗi, không đổi
        self.assertFalse(self._has())
        self.module.restore_view_customer(django_apps, None)
        self.assertTrue(self._has())
        self.module.restore_view_customer(django_apps, None)  # idempotent
        self.assertTrue(self._has())
        self.module.revoke_view_customer(django_apps, None)
        self.assertFalse(self._has())

    def test_sr_pii_01_ac1_other_groups_untouched_by_forwards(self):
        before = {
            g.name: set(g.permissions.values_list("pk", flat=True))
            for g in Group.objects.exclude(name=roles.WAREHOUSE_STAFF)
        }
        self.module.revoke_view_customer(django_apps, None)
        after = {
            g.name: set(g.permissions.values_list("pk", flat=True))
            for g in Group.objects.exclude(name=roles.WAREHOUSE_STAFF)
        }
        self.assertEqual(before, after)


class CourierWindowTests(CustomerDataScopeBase):
    """SR-PII-02: NV giao chỉ thấy dữ liệu khách của phiếu kết thúc trong 7 ngày (giờ VN)."""

    def _expire(self, days, status=DeliveryNote.Status.COMPLETED):
        self.note_a.status = status
        self.note_a.completed_at = timezone.now() - datetime.timedelta(days=days)
        self.note_a.save(update_fields=["status", "completed_at"])

    def assert_order_pii_hidden(self, hidden):
        resp = self.get(self.courier, "/api/sales/orders/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)  # vẫn thấy dòng lịch sử
        row = resp.json()["results"][0]
        self.assertEqual(row["code"], "SO-PII-A")
        detail = self.get(self.courier, f"/api/sales/orders/{self.order_a.pk}/")
        self.assertEqual(detail.status_code, 200)
        data = detail.json()
        self.assertEqual(data["code"], "SO-PII-A")
        text = body(resp) + body(detail)
        if hidden:
            self.assertIsNone(row["customer_name"])
            self.assertIsNone(row["customer_phone"])
            self.assertEqual(data["customer"], {"name": None, "phone": None, "address": None})
            for value in (PII["A"]["name"], PII["A"]["phone"], PII["A"]["address"]):
                self.assertNotIn(value, text)
        else:
            self.assertEqual(row["customer_phone"], PII["A"]["phone"])
            self.assertEqual(data["customer"]["address"], PII["A"]["address"])

    def test_sr_pii_02_ac3_active_note_visible(self):
        self.assert_order_pii_hidden(False)

    def test_sr_pii_02_ac3_completed_6_days_ago_visible(self):
        self._expire(6)
        self.assert_order_pii_hidden(False)

    def test_sr_pii_02_ac2_completed_8_days_ago_hidden_in_orders(self):
        self._expire(8)
        self.assert_order_pii_hidden(True)

    def test_sr_pii_02_ac2_completed_8_days_ago_hidden_in_notes(self):
        self._expire(8)
        resp = self.get(self.courier, "/api/delivery/notes/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)
        row = resp.json()["results"][0]
        self.assertEqual(row["code"], self.note_a.code)
        self.assertEqual(row["status"], "COMPLETED")
        self.assertIn("total_kg", row)
        self.assertIsNone(row["customer_name"])
        self.assertIsNone(row["address"])
        self.assertIsNone(row["note"])
        detail = self.get(self.courier, f"/api/delivery/notes/{self.note_a.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(detail.json()["customer_name"])
        self.assertIsNone(detail.json()["address"])
        self.assertIsNone(detail.json()["recipient_name"])
        for value in (PII["A"]["name"], PII["A"]["address"]):
            self.assertNotIn(value, body(resp) + body(detail))

    def test_sr_pii_02_ac3_completed_6_days_ago_notes_visible(self):
        self._expire(6)
        row = self.get(self.courier, "/api/delivery/notes/").json()["results"][0]
        self.assertEqual(row["customer_name"], PII["A"]["name"])
        self.assertEqual(row["address"], PII["A"]["address"])

    def test_sr_pii_02_ac2_expired_customer_not_returned(self):
        self._expire(8)
        resp = self.get(self.courier, "/api/sales/customers/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)
        self.assertEqual(self.get(self.courier, f"/api/sales/customers/{self.customer_a.pk}/").status_code, 404)
        for value in PII["A"].values():
            self.assertNotIn(value, body(resp))

    def test_sr_pii_02_ac3_recent_customer_returned(self):
        self._expire(6)
        resp = self.get(self.courier, "/api/sales/customers/")
        self.assertEqual([r["id"] for r in resp.json()["results"]], [self.customer_a.pk])

    def test_sr_pii_02_ac2_search_by_phone_cannot_find_expired_order(self):
        self._expire(8)
        resp = self.get(self.courier, f"/api/sales/orders/?q={PII['A']['phone']}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)
        resp = self.get(self.courier, f"/api/sales/orders/?q={PII['A']['name'][:12]}")
        self.assertEqual(resp.json()["count"], 0)
        # Tìm theo mã đơn vẫn chạy (không phải dữ liệu khách).
        self.assertEqual(self.get(self.courier, "/api/sales/orders/?q=SO-PII-A").json()["count"], 1)

    def test_sr_pii_02_ac3_search_by_phone_works_for_recent_order(self):
        self._expire(2)
        resp = self.get(self.courier, f"/api/sales/orders/?q={PII['A']['phone']}")
        self.assertEqual(resp.json()["count"], 1)

    def test_sr_pii_02_ac1_setting_changes_window(self):
        self._expire(3)
        self.assert_order_pii_hidden(False)
        with override_settings(DELIVERY_PII_RECENT_DAYS=2):
            self.assert_order_pii_hidden(True)

    def test_sr_pii_02_failed_note_old_is_not_terminal_so_visible(self):
        self.note_a.status = DeliveryNote.Status.FAILED
        self.note_a.save(update_fields=["status"])
        DeliveryNote.objects.filter(pk=self.note_a.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=30)
        )
        self.assert_order_pii_hidden(False)

    def test_sr_pii_02_cancelled_note_without_end_time_uses_created_at(self):
        self.note_a.status = DeliveryNote.Status.CANCELLED
        self.note_a.save(update_fields=["status"])
        DeliveryNote.objects.filter(pk=self.note_a.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=10)
        )
        self.assert_order_pii_hidden(True)

    def test_sr_pii_02_other_roles_unaffected_by_old_completed_note(self):
        self._expire(30)
        for user in (self.owner, self.manager, self.warehouse):
            rows = {r["code"]: r for r in self.get(user, "/api/sales/orders/").json()["results"]}
            self.assertEqual(rows["SO-PII-A"]["customer_phone"], PII["A"]["phone"], user.username)
            note_row = self.get(user, f"/api/delivery/notes/{self.note_a.pk}/").json()
            self.assertEqual(note_row["customer_name"], PII["A"]["name"], user.username)
            self.assertEqual(note_row["address"], PII["A"]["address"], user.username)
        self.assertEqual(self.get(self.owner, f"/api/sales/customers/{self.customer_a.pk}/").status_code, 200)

    def test_sr_pii_02_ac5_scope_unchanged_other_courier_notes_404(self):
        self._expire(1)
        self.assertEqual(self.get(self.courier, f"/api/sales/orders/{self.order_b.pk}/").status_code, 404)
        self.assertEqual(self.get(self.courier, f"/api/delivery/notes/{self.note_b.pk}/").status_code, 404)
        self.assertEqual(self.get(self.courier, f"/api/sales/customers/{self.customer_b.pk}/").status_code, 404)

    def test_sr_pii_02_set_status_response_also_redacted_for_expired_note(self):
        self._expire(8)
        resp = client_for(self.courier).post(
            f"/api/delivery/notes/{self.note_a.pk}/status/", {"to_status": "COMPLETED"}, format="json"
        )
        # Phiếu đã hoàn tất: nghiệp vụ từ chối, nhưng không được lộ dữ liệu khách trong phản hồi.
        for value in (PII["A"]["name"], PII["A"]["address"], PII["A"]["phone"]):
            self.assertNotIn(value, body(resp))

    def test_sr_pii_02_courier_with_customer_service_role_unchanged_for_own_recent(self):
        both = make_user("both2", roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE)
        self.note_c.assigned_to = both
        self.note_c.save(update_fields=["assigned_to"])
        resp = self.get(both, "/api/sales/orders/")
        rows = {r["code"]: r for r in resp.json()["results"]}
        self.assertEqual(rows["SO-PII-C"]["customer_phone"], PII["C"]["phone"])


class CourierCustomerSerializerTests(CustomerDataScopeBase):
    """SR-PII-02 AC4: nv_giao không thấy `note`, `default_address` của khách."""

    def test_sr_pii_02_ac4_courier_customer_has_no_note_or_default_address(self):
        for url in ("/api/sales/customers/", f"/api/sales/customers/{self.customer_a.pk}/"):
            resp = self.get(self.courier, url)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            row = data["results"][0] if "results" in data else data
            self.assertNotIn("note", row)
            self.assertNotIn("default_address", row)
            self.assertEqual(row["phone"], PII["A"]["phone"])
            self.assertEqual(row["name"], PII["A"]["name"])
            self.assertNotIn(PII["A"]["note"], body(resp))
            self.assertNotIn(PII["A"]["default"], body(resp))

    def test_sr_pii_02_ac4_owner_and_manager_keep_full_keys(self):
        for user in (self.owner, self.manager):
            row = self.get(user, f"/api/sales/customers/{self.customer_a.pk}/").json()
            self.assertEqual(row["note"], PII["A"]["note"])
            self.assertEqual(row["default_address"], PII["A"]["default"])

    def test_sr_pii_02_courier_cannot_write_customer(self):
        resp = client_for(self.courier).patch(
            f"/api/sales/customers/{self.customer_a.pk}/", {"name": "X"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)


class WindowBoundaryTests(TestCase):
    """Mốc theo NGÀY lịch giờ VN: phiếu kết thúc ngày D còn thấy tới hết ngày D+N, ẩn từ 00:00 ngày D+N+1."""

    def test_cutoff_is_start_of_vn_day_n_days_ago(self):
        tz = timezone.get_current_timezone()
        now = datetime.datetime(2026, 10, 10, 10, 0, tzinfo=tz)
        cutoff = pii_cutoff(now=now)
        self.assertEqual(timezone.localtime(cutoff), datetime.datetime(2026, 10, 3, 0, 0, tzinfo=tz))

    def test_boundary_notes_visible_or_hidden(self):
        tz = timezone.get_current_timezone()
        now = datetime.datetime(2026, 10, 10, 10, 0, tzinfo=tz)
        courier = make_user("courier_b", roles.DELIVERY_STAFF)
        _, _, edge_visible = make_case(
            "A", "SO-EDGE-1", courier=courier, status=DeliveryNote.Status.COMPLETED,
            completed_at=datetime.datetime(2026, 10, 3, 0, 1, tzinfo=tz),
        )
        _, _, edge_hidden = make_case(
            "B", "SO-EDGE-2", courier=courier, status=DeliveryNote.Status.COMPLETED,
            completed_at=datetime.datetime(2026, 10, 2, 23, 59, tzinfo=tz),
        )
        visible_ids = set(
            DeliveryNote.objects.filter(courier_visible_note_q(courier, now=now)).values_list("pk", flat=True)
        )
        self.assertIn(edge_visible.pk, visible_ids)
        self.assertNotIn(edge_hidden.pk, visible_ids)
