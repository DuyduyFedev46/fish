"""
Lô 6 / B2 (ED-13, BR-PQ-31): danh bạ khách `GET/PATCH /api/sales/customer-directory/`.

Quyền = quyền Tầng 2 `sales.view_customer_list` (owner + manager); `PATCH` thêm `sales.change_customer`.
Bất biến 9: nhóm không có quyền nhận 403 và body không chứa dữ liệu khách; AuditLog không chép
tên/SĐT/địa chỉ. Bất biến 1: không có field giá vốn. Toàn bộ dữ liệu là giả.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for, make_user
from apps.sales.models import Customer, Refund, SalesInvoice, SalesOrder

FAKE_NAME = "Khách Thử A"
FAKE_PHONE = "0900000123"
FAKE_ADDRESS = "[Địa chỉ giao] Hẻm 9 Cảng Thử"
FAKE_NOTE = "Giao trước 11 giờ"
LIST_URL = "/api/sales/customer-directory/"
PERM = "sales.view_customer_list"

COST_WORDS = ("purchase_rate", "landed_unit_cost", "unit_cost", "profit", "cost")


def _at(day, hour=9):
    return datetime.datetime(2026, 10, day, hour, 0, tzinfo=datetime.timezone.utc)


class DirectoryBase(TestCase):
    def setUp(self):
        self.owner = make_user("dir_owner", roles.OWNER)
        self.manager = make_user("dir_manager", roles.MANAGER)
        self.warehouse = make_user("dir_kho", roles.WAREHOUSE_STAFF)
        self.courier = make_user("dir_giao", roles.DELIVERY_STAFF)
        self.service = make_user("dir_cs", roles.CUSTOMER_SERVICE)
        self.clients = {
            "owner": client_for(self.owner),
            "manager": client_for(self.manager),
            "warehouse": client_for(self.warehouse),
            "courier": client_for(self.courier),
            "service": client_for(self.service),
            "anonymous": client_for(None),
        }
        self.customer = Customer.objects.create(
            phone=FAKE_PHONE, name=FAKE_NAME, default_address=FAKE_ADDRESS, note=FAKE_NOTE,
        )

    def make_order(self, customer, code, status, *, invoice=None, day=1):
        order = SalesOrder.objects.create(
            code=code, customer=customer, status=status, delivery_address=FAKE_ADDRESS,
            phone=customer.phone, total_amount=Decimal(invoice or "100000"),
        )
        SalesOrder.objects.filter(pk=order.pk).update(created_at=_at(day))
        order.refresh_from_db()
        inv = None
        if invoice is not None:
            inv = SalesInvoice.objects.create(
                code=f"INV-{code}", sales_order=order, customer=customer, issued_at=_at(day),
                amount=Decimal(invoice), status=SalesInvoice.Status.ISSUED,
            )
        return order, inv

    def make_refund(self, invoice, amount, status=Refund.Status.REFUNDED, reason="Khách đổi ý Thử"):
        return Refund.objects.create(
            sales_invoice=invoice, amount=Decimal(amount), status=status, reason=reason,
            is_partial=True,
        )

    def seed_history(self):
        """6 đơn: 2 đơn có tiền còn hiệu lực, 1 đơn đã trả tiền rồi huỷ (hoàn đủ), 1 tự huỷ, 2 giữ chỗ."""
        S = SalesOrder.Status
        self.make_order(self.customer, "SO-D1", S.COMPLETED, invoice="500000", day=1)
        _, inv2 = self.make_order(self.customer, "SO-D2", S.PROCESSING, invoice="300000", day=2)
        self.make_refund(inv2, "50000")  # hoàn một phần, đơn vẫn còn hiệu lực
        _, inv3 = self.make_order(self.customer, "SO-D3", S.CANCELLED, invoice="400000", day=3)
        self.make_refund(inv3, "400000")  # huỷ đơn đã trả: không được tính hai lần
        self.make_order(self.customer, "SO-D4", S.AUTO_CANCELLED, day=4)
        self.make_order(self.customer, "SO-D5", S.BOOKED, day=5)
        self.make_order(self.customer, "SO-D6", S.BOOKED, day=6)

    def get(self, who, url=LIST_URL, **params):
        return self.clients[who].get(url, params)

    def detail_url(self, pk=None):
        return f"{LIST_URL}{pk or self.customer.pk}/"


class DirectoryListTests(DirectoryBase):
    def test_ed13_ac2_list_aggregates(self):
        self.seed_history()
        res = self.get("owner")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["count"], 1)
        row = body["results"][0]
        self.assertEqual(row["id"], self.customer.pk)
        self.assertEqual(row["name"], FAKE_NAME)
        self.assertEqual(row["phone"], FAKE_PHONE)
        self.assertEqual(row["note"], FAKE_NOTE)
        self.assertEqual(row["order_count"], 6)
        self.assertEqual(row["cancelled_count"], 2)
        # 500000 + 300000 - 50000; đơn CANCELLED đã bị loại cả hoá đơn lẫn khoản hoàn của nó.
        self.assertEqual(row["total_spent"], "750000")
        self.assertIsInstance(row["total_spent"], str)
        self.assertTrue(row["last_order_at"].startswith("2026-10-06"))
        self.assertNotIn("default_address", row)

    def test_ed13_ac2_customer_without_orders_has_zero_and_null(self):
        row = self.get("owner").json()["results"][0]
        self.assertEqual(row["order_count"], 0)
        self.assertEqual(row["cancelled_count"], 0)
        self.assertEqual(row["total_spent"], "0")
        self.assertIsNone(row["last_order_at"])

    def test_ed13_ac2_pending_refund_does_not_reduce_total_spent(self):
        _, inv = self.make_order(self.customer, "SO-D7", SalesOrder.Status.COMPLETED, invoice="200000")
        self.make_refund(inv, "200000", status=Refund.Status.PENDING)
        self.assertEqual(self.get("owner").json()["results"][0]["total_spent"], "200000")

    def test_ed13_ac2_two_customers_do_not_mix_totals(self):
        self.seed_history()
        other = Customer.objects.create(phone="0900000124", name="Khách Thử B")
        self.make_order(other, "SO-E1", SalesOrder.Status.COMPLETED, invoice="90000", day=7)
        rows = {r["phone"]: r for r in self.get("owner").json()["results"]}
        self.assertEqual(rows[FAKE_PHONE]["total_spent"], "750000")
        self.assertEqual(rows["0900000124"]["total_spent"], "90000")
        self.assertEqual(rows["0900000124"]["order_count"], 1)

    def test_ed13_list_search_by_name_without_accent_and_by_phone(self):
        Customer.objects.create(phone="0900000124", name="Trần Văn Khác")
        self.assertEqual(self.get("owner", q="khach thu").json()["count"], 1)
        self.assertEqual(self.get("owner", q="0000123").json()["count"], 1)
        self.assertEqual(self.get("owner", q="văn khác").json()["count"], 1)
        self.assertEqual(self.get("owner", q="khong co").json()["count"], 0)

    def test_ed13_list_search_by_short_digits_does_not_match_phone(self):
        # Dưới 4 chữ số: không dùng để dò SĐT (tránh liệt kê danh bạ bằng "0", "09"...).
        self.assertEqual(self.get("owner", q="090").json()["count"], 0)

    def test_ed13_list_ordering_last_order_desc_default_and_paginated(self):
        older = Customer.objects.create(phone="0900000124", name="Khách Thử B")
        self.make_order(older, "SO-F1", SalesOrder.Status.COMPLETED, invoice="1000", day=1)
        self.make_order(self.customer, "SO-F2", SalesOrder.Status.COMPLETED, invoice="1000", day=5)
        results = self.get("owner").json()["results"]
        self.assertEqual([r["phone"] for r in results], [FAKE_PHONE, "0900000124"])
        asc = self.get("owner", ordering="last_order_at").json()["results"]
        self.assertEqual([r["phone"] for r in asc], ["0900000124", FAKE_PHONE])
        self.assertEqual(self.get("owner").json()["next"], None)

    def test_ed13_list_pagination_is_standard_20(self):
        for i in range(25):
            Customer.objects.create(phone=f"09100{i:05d}", name=f"Khách Thử {i}")
        body = self.get("owner").json()
        self.assertEqual(body["count"], 26)
        self.assertEqual(len(body["results"]), 20)
        self.assertIsNotNone(body["next"])
        self.assertEqual(len(self.get("owner", page=2).json()["results"]), 6)

    def test_ed13_list_invalid_ordering_falls_back_not_500(self):
        self.assertEqual(self.get("owner", ordering="phone; drop").status_code, 200)

    def test_ed13_list_no_n_plus_one(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self.seed_history()
        self.get("owner")  # làm nóng cache quyền của user
        with CaptureQueriesContext(connection) as small:
            self.get("owner")
        for i in range(8):
            c = Customer.objects.create(phone=f"09200{i:05d}", name=f"Khách Thử {i}")
            self.make_order(c, f"SO-N{i}", SalesOrder.Status.COMPLETED, invoice="10000", day=3)
        with CaptureQueriesContext(connection) as large:
            self.assertEqual(self.get("owner").json()["count"], 9)
        self.assertEqual(len(large), len(small))

    def test_ed13_list_response_is_no_store(self):
        self.assertIn("no-store", self.get("owner").headers["Cache-Control"])
        self.assertIn("no-store", self.get("owner", url=self.detail_url()).headers["Cache-Control"])


class DirectoryDetailTests(DirectoryBase):
    def test_ed13_detail_contract(self):
        self.seed_history()
        res = self.get("manager", url=self.detail_url())
        self.assertEqual(res.status_code, 200)
        body = res.json()
        for key in (
            "id", "name", "phone", "note", "default_address", "created_at", "first_order_at",
            "last_order_at", "order_count", "cancelled_count", "total_spent", "orders", "refunds",
        ):
            self.assertIn(key, body)
        self.assertEqual(body["default_address"], FAKE_ADDRESS)
        self.assertTrue(body["first_order_at"].startswith("2026-10-01"))
        self.assertEqual(body["order_count"], 6)
        self.assertEqual(body["total_spent"], "750000")
        self.assertEqual(len(body["orders"]), 6)
        newest = body["orders"][0]
        self.assertEqual(newest["code"], "SO-D6")
        self.assertEqual(
            set(newest), {"id", "code", "status", "status_label", "total_amount", "created_at"},
        )
        self.assertEqual(newest["status"], "BOOKED")
        self.assertEqual(newest["status_label"], "Giữ chỗ")
        self.assertEqual(len(body["refunds"]), 2)
        refund = body["refunds"][0]
        self.assertEqual(
            set(refund), {"id", "order_code", "status", "status_label", "amount", "created_at"},
        )
        self.assertIn(refund["order_code"], {"SO-D2", "SO-D3"})
        self.assertEqual(refund["status_label"], "Đã hoàn tiền")

    def test_ed13_detail_does_not_expose_refund_free_text(self):
        self.seed_history()
        body = self.get("owner", url=self.detail_url()).content.decode()
        self.assertNotIn("Khách đổi ý Thử", body)

    def test_ed13_detail_orders_capped_at_50_newest(self):
        for i in range(55):
            self.make_order(self.customer, f"SO-M{i:03d}", SalesOrder.Status.BOOKED, day=1)
        body = self.get("owner", url=self.detail_url()).json()
        self.assertEqual(len(body["orders"]), 50)
        self.assertEqual(body["order_count"], 55)

    def test_ed13_detail_404(self):
        self.assertEqual(self.get("owner", url=self.detail_url(987654)).status_code, 404)

    def test_ed13_detail_customer_without_orders(self):
        body = self.get("owner", url=self.detail_url()).json()
        self.assertEqual(body["orders"], [])
        self.assertEqual(body["refunds"], [])
        self.assertIsNone(body["first_order_at"])


class DirectoryPermissionTests(DirectoryBase):
    def assert_no_personal_data(self, res):
        body = res.content.decode()
        for secret in (FAKE_NAME, FAKE_PHONE, FAKE_ADDRESS, FAKE_NOTE):
            self.assertNotIn(secret, body)

    def test_ed13_ac3_groups_without_permission_get_403_on_list_and_detail(self):
        for who in ("warehouse", "courier", "service"):
            for url in (LIST_URL, self.detail_url()):
                res = self.get(who, url=url)
                self.assertEqual(res.status_code, 403, (who, url))
                self.assert_no_personal_data(res)

    def test_ed13_ac3_anonymous_401(self):
        self.assertEqual(self.get("anonymous").status_code, 401)
        self.assertEqual(self.get("anonymous", url=self.detail_url()).status_code, 401)

    def test_ed13_ac1_owner_and_manager_can_read(self):
        for who in ("owner", "manager"):
            self.assertEqual(self.get(who).status_code, 200, who)
            self.assertEqual(self.get(who, url=self.detail_url()).status_code, 200, who)

    def test_ed13_ac1_permission_is_granted_to_owner_and_manager_only(self):
        perm = Permission.objects.get(content_type__app_label="sales", codename="view_customer_list")
        granted = set(Group.objects.filter(permissions=perm).values_list("name", flat=True))
        self.assertEqual(granted, {roles.OWNER, roles.MANAGER})

    def test_ed13_user_with_only_the_extra_perm_can_read_but_not_write(self):
        staff = make_user("dir_extra", perms=(PERM,))
        client = client_for(staff)
        self.assertEqual(client.get(LIST_URL).status_code, 200)
        self.assertEqual(client.get(self.detail_url()).status_code, 200)
        res = client.patch(self.detail_url(), {"note": "x"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_ed13_courier_with_tier1_view_customer_but_no_new_perm_gets_403(self):
        # `sales.view_customer` (Tầng 1, phạm vi dòng của NV giao) không mở danh bạ mới.
        self.assertTrue(self.courier.has_perm("sales.view_customer"))
        self.assertEqual(self.get("courier").status_code, 403)

    def test_ed13_owner_switching_off_manager_permission_blocks_manager(self):
        perm = Permission.objects.get(content_type__app_label="sales", codename="view_customer_list")
        Group.objects.get(name=roles.MANAGER).permissions.remove(perm)
        manager = make_user("dir_manager2", roles.MANAGER)  # bỏ cache quyền
        res = client_for(manager).get(LIST_URL)
        self.assertEqual(res.status_code, 403)
        self.assert_no_personal_data(res)

    def test_ed13_ac4_view_only_user_cannot_patch_and_data_unchanged(self):
        # Có quyền xem nhưng không có `change_customer` → 403, dữ liệu không đổi.
        staff = make_user("dir_view_only", perms=(PERM,))
        res = client_for(staff).patch(self.detail_url(), {"note": "Sửa trái phép"}, format="json")
        self.assertEqual(res.status_code, 403)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.note, FAKE_NOTE)

    def test_ed13_non_permitted_groups_cannot_patch(self):
        for who in ("warehouse", "courier", "service", "anonymous"):
            res = self.clients[who].patch(self.detail_url(), {"note": "x"}, format="json")
            self.assertIn(res.status_code, (401, 403), who)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.note, FAKE_NOTE)

    def test_ed13_post_put_delete_are_405_for_owner(self):
        client = self.clients["owner"]
        self.assertEqual(client.post(LIST_URL, {"phone": "0900000999"}, format="json").status_code, 405)
        self.assertEqual(client.put(self.detail_url(), {"name": "x"}, format="json").status_code, 405)
        self.assertEqual(client.delete(self.detail_url()).status_code, 405)
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_ed13_no_cost_fields_for_manager_token(self):
        self.seed_history()
        for url in (LIST_URL, self.detail_url()):
            body = self.get("manager", url=url).content.decode()
            for word in COST_WORDS:
                self.assertNotIn(word, body, (url, word))

    def test_ed13_ac7_delivery_apis_still_work_without_new_perm(self):
        # Hồi quy: NV giao vẫn xem phiếu giao của mình mà không cần quyền Xem khách hàng (BR-PQ-12).
        from apps.common.tests.fixtures import make_order_with_note

        _, _, note = make_order_with_note("SO-REG-1", "0900000777", assigned_to=self.courier)
        self.assertFalse(self.courier.has_perm(PERM))
        res = self.clients["courier"].get(f"/api/delivery/notes/{note.pk}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.clients["courier"].get("/api/sales/customers/").status_code, 200)


class DirectoryPatchTests(DirectoryBase):
    def patch(self, data, who="owner"):
        return self.clients[who].patch(self.detail_url(), data, format="json")

    def test_ed13_patch_allowed_fields_and_audit_has_no_values(self):
        new_address = "[Địa chỉ giao] Số 5 Đường Thử"
        res = self.patch({"name": "Khách Thử Đổi", "default_address": new_address, "note": "Gọi trước 30 phút"})
        self.assertEqual(res.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "Khách Thử Đổi")
        self.assertEqual(self.customer.default_address, new_address)
        self.assertEqual(self.customer.note, "Gọi trước 30 phút")
        self.assertEqual(self.customer.phone, FAKE_PHONE)
        body = res.json()
        self.assertEqual(body["name"], "Khách Thử Đổi")
        self.assertEqual(body["order_count"], 0)

        log = AuditLog.objects.get(action="update_customer")
        self.assertEqual(log.actor, self.owner)
        self.assertEqual(log.model_name, "sales.Customer")
        self.assertEqual(log.object_id, str(self.customer.pk))
        self.assertEqual(log.changes, {"fields": ["default_address", "name", "note"]})

    def test_ed13_ac5_audit_row_contains_no_personal_data_anywhere(self):
        self.patch({"name": "Khách Thử Đổi", "note": "Gọi trước 30 phút"})
        log = AuditLog.objects.get(action="update_customer")
        blob = " ".join(
            str(v) for v in (
                log.changes, log.note, log.object_repr, log.object_id, log.model_name, log.action,
            )
        )
        for secret in (FAKE_NAME, "Khách Thử Đổi", FAKE_PHONE, FAKE_ADDRESS, "Gọi trước", FAKE_NOTE):
            self.assertNotIn(secret, blob)

    def test_ed13_patch_manager_allowed(self):
        self.assertEqual(self.patch({"note": "Ghi chú mới"}, who="manager").status_code, 200)
        self.assertEqual(AuditLog.objects.get(action="update_customer").actor, self.manager)

    def test_ed13_patch_unknown_or_forbidden_field_is_400_and_nothing_saved(self):
        for payload in ({"id": 5}, {"created_at": "2020-01-01T00:00:00Z"}, {"order_count": 99},
                        {"total_spent": "1"}, {"note": "ok", "order_count": 1}, {"foo": 1}):
            res = self.patch(payload)
            self.assertEqual(res.status_code, 400, payload)
            self.assertEqual(res.json()["code"], "INPUT_NOT_ALLOWED", payload)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.note, FAKE_NOTE)
        self.assertFalse(AuditLog.objects.filter(action="update_customer").exists())

    def test_ed13_patch_empty_body_is_400(self):
        res = self.patch({})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(AuditLog.objects.filter(action="update_customer").exists())

    def test_ed13_patch_non_string_value_is_400(self):
        res = self.patch({"note": {"a": 1}})
        self.assertEqual(res.status_code, 400)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.note, FAKE_NOTE)

    def test_ed13_patch_unchanged_value_writes_no_audit(self):
        res = self.patch({"note": FAKE_NOTE})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(AuditLog.objects.filter(action="update_customer").exists())

    def test_ed13_patch_404(self):
        res = self.clients["owner"].patch(self.detail_url(987654), {"note": "x"}, format="json")
        self.assertEqual(res.status_code, 404)

    def test_ed13_patch_response_is_no_store(self):
        self.assertIn("no-store", self.patch({"note": "x"}).headers["Cache-Control"])
