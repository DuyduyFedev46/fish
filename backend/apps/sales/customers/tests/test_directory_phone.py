"""
Lô bổ sung A #5 (Duy chốt 02/10): `PATCH /api/sales/customer-directory/{id}/` nhận thêm `phone`.

Quyền `sales.change_customer` (cộng `view_customer_list`); chuẩn hoá bằng `apps.common.pii.normalize_phone`;
trùng khách khác -> 400 `CUSTOMER_PHONE_TAKEN` không lặp lại số; AuditLog chỉ ghi tên field (bất biến 9).
Toàn bộ dữ liệu là giả.
"""
from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for, make_user
from apps.sales.customers.tests.test_directory_api import (
    FAKE_ADDRESS, FAKE_NAME, FAKE_PHONE, PERM, DirectoryBase,
)
from apps.sales.models import Customer, SalesOrder

NEW_PHONE = "0900000777"
OTHER_PHONE = "0900000888"


class DirectoryPhoneEditTests(DirectoryBase):
    def patch(self, data, who="owner"):
        return self.clients[who].patch(self.detail_url(), data, format="json")

    def test_phone_edit_saves_and_returns_new_phone(self):
        res = self.patch({"phone": NEW_PHONE})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["phone"], NEW_PHONE)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone, NEW_PHONE)

    def test_manager_can_edit_phone(self):
        self.assertEqual(self.patch({"phone": NEW_PHONE}, who="manager").status_code, 200)

    def test_phone_is_normalized_like_shop_input(self):
        for raw in (" 0900 000 777 ", "+84 900 000 777", "0900.000.777", "84900000777"):
            Customer.objects.filter(pk=self.customer.pk).update(phone=FAKE_PHONE)
            res = self.patch({"phone": raw})
            self.assertEqual(res.status_code, 200, raw)
            self.assertEqual(res.json()["phone"], NEW_PHONE, raw)

    def test_invalid_phone_is_400_and_unchanged(self):
        for raw in ("", "   ", "abc", "12345", "090000", "0900000123456789", "+1 202 555 0100"):
            res = self.patch({"phone": raw})
            self.assertEqual(res.status_code, 400, raw)
            self.assertEqual(res.json()["code"], "INVALID_PHONE", raw)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone, FAKE_PHONE)
        self.assertFalse(AuditLog.objects.filter(action="update_customer").exists())

    def test_non_string_phone_is_400(self):
        for raw in ({"a": 1}, ["0900000777"], None):
            self.assertEqual(self.patch({"phone": raw}).status_code, 400, raw)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone, FAKE_PHONE)

    def test_phone_taken_by_other_customer_is_400_without_echoing_number(self):
        Customer.objects.create(phone=OTHER_PHONE, name="Khách Thử B")
        res = self.patch({"phone": OTHER_PHONE})
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertEqual(body["code"], "CUSTOMER_PHONE_TAKEN")
        self.assertNotIn(OTHER_PHONE, res.content.decode())
        self.assertNotIn("Khách Thử B", res.content.decode())
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone, FAKE_PHONE)
        self.assertFalse(AuditLog.objects.filter(action="update_customer").exists())

    def test_phone_taken_even_when_typed_in_another_format(self):
        Customer.objects.create(phone=OTHER_PHONE, name="Khách Thử B")
        res = self.patch({"phone": "+84 900 000 888"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "CUSTOMER_PHONE_TAKEN")

    def test_phone_taken_by_customer_stored_with_plus84_form(self):
        # Shop lưu SĐT đúng như khách gõ (có thể "+84…"), nên so cả dạng này.
        Customer.objects.create(phone="+84900000888", name="Khách Thử B")
        res = self.patch({"phone": OTHER_PHONE})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "CUSTOMER_PHONE_TAKEN")

    def test_same_phone_again_is_noop_without_audit(self):
        res = self.patch({"phone": FAKE_PHONE})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(AuditLog.objects.filter(action="update_customer").exists())

    def test_audit_has_field_name_only_no_values(self):
        self.patch({"phone": NEW_PHONE, "name": "Khách Thử Đổi"})
        log = AuditLog.objects.get(action="update_customer")
        self.assertEqual(log.changes, {"fields": ["name", "phone"]})
        blob = " ".join(str(v) for v in (log.changes, log.note, log.object_repr, log.object_id))
        for secret in (FAKE_PHONE, NEW_PHONE, FAKE_NAME, "Khách Thử Đổi", FAKE_ADDRESS):
            self.assertNotIn(secret, blob)

    def test_old_orders_stay_linked_to_the_customer(self):
        order, _ = self.make_order(self.customer, "SO-P1", SalesOrder.Status.COMPLETED, invoice="200000")
        self.assertEqual(self.patch({"phone": NEW_PHONE}).status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.customer_id, self.customer.pk)
        self.assertEqual(order.phone, FAKE_PHONE)  # số lúc đặt đơn giữ nguyên (chứng từ)
        body = self.clients["owner"].get(self.detail_url()).json()
        self.assertEqual([o["code"] for o in body["orders"]], ["SO-P1"])
        self.assertEqual(body["order_count"], 1)

    def test_phone_edit_without_permission_is_403_and_unchanged(self):
        view_only = make_user("dir_phone_view_only", perms=(PERM,))
        res = client_for(view_only).patch(self.detail_url(), {"phone": NEW_PHONE}, format="json")
        self.assertEqual(res.status_code, 403)
        for who in ("warehouse", "courier", "service"):
            res = self.patch({"phone": NEW_PHONE}, who=who)
            self.assertEqual(res.status_code, 403, who)
        self.assertEqual(self.patch({"phone": NEW_PHONE}, who="anonymous").status_code, 401)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone, FAKE_PHONE)

    def test_error_responses_do_not_leak_personal_data(self):
        Customer.objects.create(phone=OTHER_PHONE, name="Khách Thử B")
        for payload in ({"phone": OTHER_PHONE}, {"phone": "abc"}):
            raw = self.patch(payload).content.decode()
            for secret in (FAKE_PHONE, OTHER_PHONE, FAKE_NAME, FAKE_ADDRESS):
                self.assertNotIn(secret, raw)
