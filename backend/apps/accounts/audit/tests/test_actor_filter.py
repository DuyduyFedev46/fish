"""R16 (ERP theo design, 02b §3.8) — lọc nhật ký theo người làm: GET /api/audit-logs/?actor=<user id>."""
from django.test import TestCase, override_settings

from apps.accounts import roles
from apps.common.audit import record_audit
from apps.common.tests.fixtures import client_for, make_user

URL = "/api/audit-logs/"


@override_settings(AI_ENABLED=True)  # dòng AI chỉ hiện khi AI bật (TL-D3-L4)
class AuditActorFilterTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner1", roles.OWNER)
        self.manager = make_user("manager1", roles.MANAGER)
        self.warehouse = make_user("kho1", roles.WAREHOUSE_STAFF)
        record_audit("close_batch", actor=self.owner)
        record_audit("publish_batch", actor=self.manager)
        record_audit("publish_batch", actor=self.manager)
        record_audit("cancel_expired_orders")  # Hệ thống
        record_audit("propose_x", actor_kind="ai", ai_actor=self.manager)  # AI thay manager: actor rỗng
        self.client = client_for(self.owner)

    def actions(self, query):
        response = self.client.get(f"{URL}{query}")
        self.assertEqual(response.status_code, 200, response.content)
        return sorted(r["action"] for r in response.json()["results"])

    def test_r16_filter_by_actor_returns_only_that_users_rows(self):
        self.assertEqual(self.actions(f"?actor={self.manager.pk}"), ["publish_batch", "publish_batch"])
        self.assertEqual(self.actions(f"?actor={self.owner.pk}"), ["close_batch"])

    def test_r16_actor_without_rows_returns_empty_page(self):
        response = self.client.get(f"{URL}?actor={self.warehouse.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
        self.assertEqual(response.json()["results"], [])

    def test_r16_unknown_user_id_returns_empty_page_not_error(self):
        self.assertEqual(self.client.get(f"{URL}?actor=999999").json()["count"], 0)

    def test_r16_without_actor_param_returns_everything(self):
        self.assertEqual(self.client.get(URL).json()["count"], 5)
        self.assertEqual(self.client.get(f"{URL}?actor=").json()["count"], 5)  # rỗng = không lọc

    def test_r16_combines_with_existing_filters(self):
        self.assertEqual(self.actions(f"?actor={self.manager.pk}&action=publish_batch"),
                         ["publish_batch", "publish_batch"])
        self.assertEqual(self.actions(f"?actor={self.manager.pk}&action=close_batch"), [])

    def test_r16_invalid_actor_is_400_and_does_not_echo_the_value(self):
        for raw in ("abc", "0", "-1", "1.5", "+1", "1 2", "%20", "１２", "9" * 30, "9223372036854775808", "1,2"):
            response = self.client.get(URL, {"actor": raw})
            self.assertEqual(response.status_code, 400, raw)
            body = response.json()
            self.assertEqual(body["code"], "INVALID_FILTER", raw)
            self.assertNotIn(raw, body["detail"])

    def test_r16_huge_digit_string_is_400_not_500(self):
        self.assertEqual(self.client.get(URL, {"actor": "9" * 5000}).status_code, 400)

    def test_r16_actor_param_is_not_an_injection_vector(self):
        self.assertEqual(self.client.get(URL, {"actor": "1 OR 1=1"}).status_code, 400)

    def test_r16_manager_can_view_audit_log_and_filter(self):
        # 02b Q1 (mặc định): giữ như code — Chủ và Quản lý xem nhật ký.
        response = client_for(self.manager).get(f"{URL}?actor={self.manager.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)

    def test_r16_roles_without_view_auditlog_get_403_even_with_filter(self):
        for username, groups in [("kho2", [roles.WAREHOUSE_STAFF]), ("giao1", [roles.DELIVERY_STAFF]),
                                 ("cs1", [roles.CUSTOMER_SERVICE]), ("nogroup", [])]:
            client = client_for(make_user(username, *groups))
            self.assertEqual(client.get(f"{URL}?actor={self.manager.pk}").status_code, 403, username)

    def test_r16_anonymous_gets_401(self):
        self.assertEqual(client_for(None).get(f"{URL}?actor={self.manager.pk}").status_code, 401)
