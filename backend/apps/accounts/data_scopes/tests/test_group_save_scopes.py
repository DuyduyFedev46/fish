"""
PV-08, PV-09 (BE), PV-10 (BE) — Lô 5: Chủ lưu phạm vi cùng việc, cảnh báo mở rộng dữ liệu khách, khoá lạc quan `version`.
BR-PQ-36, R1, R6, R8, Q-8, Q-9, S-8; 02b §2.1–§2.5. Dùng lại dữ liệu giả của mốc PV-01 (`fixtures.build_scene`).

Phần "đối chiếu mock F1" (4 ca trong review re-review a1b5b31, M1) nằm ở `MockParityTests`.
"""
import json
from unittest import mock

from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.accounts.capabilities.tests.base import detail_url, put_url
from apps.accounts.models import AuditLog, GroupAccessConfig, GroupDataScope

from . import fixtures
from .test_orders_invoices_scope import ScopeSceneBase, grant, revoke, set_scope

SCOPE_ACTION = "change_group_data_scopes"
CAPABILITY_ACTION = "change_group_capabilities"
WIDENING_CODE = "CUSTOMER_DATA_WIDENING_UNCONFIRMED"


class SaveBase(ScopeSceneBase):
    def client_of(self, label):
        client = APIClient()
        client.force_authenticate(self.user(label))
        return client

    def group_version(self, code):
        return self.client_of("owner").get(detail_url(code)).json()["version"]

    def put(self, code, *, label="owner", version=None, **body):
        if version is None:
            version = self.group_version(code)
        return self.client_of(label).put(put_url(code), {"version": version, **body}, format="json")

    def preview(self, code, *, label="owner", **body):
        return self.client_of(label).post(f"/api/staff/groups/{code}/permissions-preview/", body, format="json")

    def audits(self, action, code=None):
        rows = AuditLog.objects.filter(action=action)
        if code:
            rows = rows.filter(object_id=str(Group.objects.get(name=code).pk))
        return list(rows.order_by("id"))

    def stored(self, code, key):
        return GroupDataScope.objects.get(group__name=code, object_key=key).value


# --- PV-08 -------------------------------------------------------------------------------------------------------------

class SaveScopesTests(SaveBase):
    def test_pv08_ac1_owner_changes_scope_with_audit_and_new_version(self):
        before = self.group_version(roles.WAREHOUSE_STAFF)
        response = self.put(roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me_today"})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(int(body["version"]), int(before) + 1)
        self.assertEqual(body["data_scope_values"]["receipts"], "created_by_me_today")
        row = next(r for r in body["data_scopes"] if r["key"] == "receipts")
        self.assertEqual(row["value"], "created_by_me_today")
        self.assertEqual(self.stored(roles.WAREHOUSE_STAFF, "receipts"), "created_by_me_today")
        rows = self.audits(SCOPE_ACTION, roles.WAREHOUSE_STAFF)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].changes, {"receipts": {"from": "all", "to": "created_by_me_today"}})
        self.assertEqual(rows[0].actor_id, self.scene.users["owner"].pk)
        self.assertEqual(rows[0].model_name, "auth.Group")

    def test_pv08_ac2_capabilities_and_scopes_together_one_audit_each_one_version_bump(self):
        before = int(self.group_version(roles.WAREHOUSE_STAFF))
        response = self.put(
            roles.WAREHOUSE_STAFF, capabilities={"approve_return": True}, scopes={"receipts": "created_by_me"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(int(response.json()["version"]), before + 1)
        self.assertEqual(len(self.audits(CAPABILITY_ACTION, roles.WAREHOUSE_STAFF)), 1)
        self.assertEqual(len(self.audits(SCOPE_ACTION, roles.WAREHOUSE_STAFF)), 1)

    def test_pv08_ac3_same_value_is_ok_without_audit_or_version_bump(self):
        before = self.group_version(roles.WAREHOUSE_STAFF)
        response = self.put(roles.WAREHOUSE_STAFF, scopes={"receipts": "all"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], before)
        self.assertEqual(self.audits(SCOPE_ACTION), [])
        self.assertEqual(self.group_version(roles.WAREHOUSE_STAFF), before)

    def test_pv08_ac4_one_bad_value_saves_nothing(self):
        before = self.group_version(roles.WAREHOUSE_STAFF)
        response = self.put(
            roles.WAREHOUSE_STAFF, scopes={"receipts": "mine", "returns": "assigned_deliveries"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "SCOPE_VALUE_INVALID")
        response = self.put(
            roles.WAREHOUSE_STAFF, scopes={"returns": "assigned_deliveries", "receipts": 7})
        self.assertEqual(response.json()["code"], "SCOPE_VALUE_INVALID")
        self.assertEqual(self.stored(roles.WAREHOUSE_STAFF, "returns"), "all")
        self.assertEqual(self.group_version(roles.WAREHOUSE_STAFF), before)
        self.assertEqual(self.audits(SCOPE_ACTION), [])

    def test_pv08_ac5_unknown_readonly_and_owner_group(self):
        cases = (
            (roles.WAREHOUSE_STAFF, {"stock": "all"}, "SCOPE_OBJECT_UNKNOWN"),
            (roles.WAREHOUSE_STAFF, {"invoices": "all"}, "SCOPE_READ_ONLY"),
            (roles.WAREHOUSE_STAFF, {"audit_log": "all"}, "SCOPE_READ_ONLY"),
            (roles.OWNER, {"receipts": "all"}, "GROUP_LOCKED"),
        )
        for code, scopes, expected in cases:
            response = self.put(code, version="1", scopes=scopes)
            self.assertEqual(response.status_code, 400, scopes)
            self.assertEqual(response.json()["code"], expected, scopes)
        self.assertEqual(self.audits(SCOPE_ACTION), [])

    def test_pv08_ac6_audit_failure_leaves_configuration_unchanged(self):
        before = self.group_version(roles.WAREHOUSE_STAFF)
        client = self.client_of("owner")
        client.raise_request_exception = False
        with mock.patch("apps.accounts.capabilities.services.record_audit", side_effect=RuntimeError("audit down")):
            response = client.put(
                put_url(roles.WAREHOUSE_STAFF),
                {"version": before, "capabilities": {"approve_return": True}, "scopes": {"receipts": "created_by_me"}},
                format="json")
        self.assertGreaterEqual(response.status_code, 400)
        self.assertEqual(self.stored(roles.WAREHOUSE_STAFF, "receipts"), "all")
        self.assertEqual(self.group_version(roles.WAREHOUSE_STAFF), before)
        self.assertNotIn("inventory.approve_returntostock", self.group_perms(roles.WAREHOUSE_STAFF))

    @staticmethod
    def group_perms(code):
        from apps.accounts.capabilities.tests.base import group_perms
        return group_perms(code)

    def test_pv08_ac7_manager_and_warehouse_cannot_write_or_preview(self):
        grant(roles.MANAGER, "accounts.manage_staff")
        before = self.group_version(roles.WAREHOUSE_STAFF)
        for label in ("manager", "warehouse_staff", "courier"):
            response = self.put(roles.WAREHOUSE_STAFF, label=label, version=before, scopes={"receipts": "created_by_me"})
            self.assertEqual(response.status_code, 403, label)
            self.assertEqual(self.preview(roles.WAREHOUSE_STAFF, label=label, scopes={"receipts": "created_by_me"})
                             .status_code, 403, label)
        self.assertEqual(self.stored(roles.WAREHOUSE_STAFF, "receipts"), "all")
        self.assertEqual(self.audits(SCOPE_ACTION), [])
        self.assertEqual(APIClient().put(put_url(roles.WAREHOUSE_STAFF), {}, format="json").status_code, 401)

    def test_pv08_ac8_timeline_event_has_sentence_without_raw_changes(self):
        self.put(roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me_today"})
        body = self.client_of("owner").get(detail_url(roles.WAREHOUSE_STAFF)).json()
        events = [e for e in body["timeline"] if e["kind"] == SCOPE_ACTION]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["label"], "Đổi phạm vi Phiếu nhập: Tất cả phiếu → Do tôi tạo trong ngày")
        self.assertEqual(events[0]["actor"]["kind"], "user")
        self.assertNotIn("changes", events[0])
        self.assertIsNotNone(body["last_changed_at"])
        self.assertTrue(body["last_changed_by"])

    def test_pv08_ac8_one_timeline_event_per_object(self):
        self.put(roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me", "returns": "assigned_deliveries"})
        body = self.client_of("owner").get(detail_url(roles.WAREHOUSE_STAFF)).json()
        labels = sorted(e["label"] for e in body["timeline"] if e["kind"] == SCOPE_ACTION)
        self.assertEqual(len(labels), 2)

    def test_pv08_ac9_audit_has_codes_only_no_personal_data(self):
        self.put(roles.DELIVERY_STAFF, scopes={"orders": "all"}, confirm_customer_data_widening=True)
        row = self.audits(SCOPE_ACTION, roles.DELIVERY_STAFF)[0]
        self.assertEqual(
            row.changes, {"orders": {"from": "assigned_deliveries", "to": "all"}, "customer_data_widening_confirmed": True})
        self.assertEqual(row.note, "")
        text = json.dumps(row.changes) + row.object_repr + row.note
        for fake in fixtures.FAKE_STRINGS:
            self.assertNotIn(fake, text)

    def test_pv08_ac10_scope_change_takes_effect_on_next_request_with_old_token(self):
        from apps.accounts.capabilities.tests.base import token_client

        courier = self.user("courier")
        client = token_client(courier)
        before = client.get("/api/sales/orders/").json()["count"]
        self.assertLess(before, len(fixtures.ORDER_SPECS))
        response = self.put(roles.DELIVERY_STAFF, scopes={"orders": "all"}, confirm_customer_data_widening=True)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(client.get("/api/sales/orders/").json()["count"], len(fixtures.ORDER_SPECS))

    def test_pv08_unknown_body_key_and_empty_body(self):
        for body, code in (({"permissions": []}, "INPUT_NOT_ALLOWED"), ({}, "INVALID_INPUT"),
                           ({"capabilities": {}, "scopes": {}}, "INVALID_INPUT"),
                           ({"scopes": []}, "INVALID_INPUT"), ({"scopes": {"receipts": "all"}, "confirm_customer_data_widening": "yes"},
                                                              "INVALID_INPUT")):
            response = self.put(roles.WAREHOUSE_STAFF, **body)
            self.assertEqual(response.status_code, 400, body)
            self.assertEqual(response.json()["code"], code, body)

    def test_pv08_owner_only_capability_still_blocked(self):
        response = self.put(roles.WAREHOUSE_STAFF, capabilities={"manage_staff": True})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "BR-PQ-32")

    def test_pv08_po_q1_view_customers_on_with_d7_none_is_rejected(self):
        before = self.group_version(roles.WAREHOUSE_STAFF)
        response = self.put(roles.WAREHOUSE_STAFF, capabilities={"view_customers": True})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "SCOPE_VALUE_INVALID")
        self.assertEqual(self.group_version(roles.WAREHOUSE_STAFF), before)
        self.assertNotIn("sales.view_customer_list", self.group_perms(roles.WAREHOUSE_STAFF))

    def test_pv08_po_q1_view_customers_on_with_d7_all_in_same_request(self):
        response = self.put(
            roles.WAREHOUSE_STAFF, capabilities={"view_customers": True}, scopes={"customers": "all"},
            confirm_customer_data_widening=True)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.stored(roles.WAREHOUSE_STAFF, "customers"), "all")
        self.assertIn("sales.view_customer_list", self.group_perms(roles.WAREHOUSE_STAFF))
        directory = self.get("warehouse_staff", "/api/sales/customer-directory/")
        self.assertEqual(directory.status_code, 200)

    def test_pv08_requires_error_comes_before_po_q1(self):
        # `pack_print` cần `deliver`: lỗi requires thắng lỗi phạm vi (02b §2.3 thứ tự 9 trước 10).
        response = self.put(roles.CUSTOMER_SERVICE, capabilities={"pack_print": True})
        self.assertEqual(response.json()["code"], "CAPABILITY_REQUIRES")

    def test_pv08_d7_row_note_when_stored_all_but_view_customers_off(self):
        """L4 (review 06/10): D7 lưu `all` mà nhóm thiếu `view_customer_list` thì giá trị hiệu lực chỉ `assigned_deliveries`; có `note`."""
        set_scope(roles.DELIVERY_STAFF, "customers", "all")
        body = self.client_of("owner").get(detail_url(roles.DELIVERY_STAFF)).json()
        row = next(r for r in body["data_scopes"] if r["key"] == "customers")
        self.assertEqual(row["value"], "all")
        self.assertEqual(row["note"], "Bật Xem khách hàng để thấy tất cả khách")
        grant(roles.DELIVERY_STAFF, "sales.view_customer_list")
        body = self.client_of("owner").get(detail_url(roles.DELIVERY_STAFF)).json()
        self.assertIsNone(next(r for r in body["data_scopes"] if r["key"] == "customers")["note"])
        manager = self.client_of("owner").get(detail_url(roles.MANAGER)).json()
        self.assertIsNone(next(r for r in manager["data_scopes"] if r["key"] == "customers")["note"])

    def test_pv08_me_has_is_superuser(self):
        for label, expected in (("superuser", True), ("owner", False), ("courier", False)):
            body = self.client_of(label).get("/api/auth/me/").json()
            self.assertIs(body["is_superuser"], expected, label)


# --- PV-09 -------------------------------------------------------------------------------------------------------------

class PreviewAndWideningTests(SaveBase):
    def active_members(self, code):
        from django.contrib.auth.models import User
        return list(User.objects.filter(groups__name=code, is_active=True).order_by("username"))

    def test_pv09_ac1_preview_reports_members_and_writes_nothing(self):
        version = self.group_version(roles.DELIVERY_STAFF)
        response = self.preview(roles.DELIVERY_STAFF, scopes={"orders": "all"})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        members = self.active_members(roles.DELIVERY_STAFF)
        self.assertTrue(body["widens_customer_data"])
        self.assertEqual(body["affected_count"], len(members))
        self.assertEqual({m["id"] for m in body["affected_members"]}, {m.pk for m in members})
        for member in body["affected_members"]:
            self.assertEqual(set(member), {"id", "display_name"})
        self.assertEqual(
            body["message"], f"{len(members)} người trong nhóm sẽ thấy tên, SĐT, địa chỉ khách của mọi đơn.")
        self.assertEqual(body["widened"], [{"key": "orders", "from": "assigned_deliveries", "to": "all"}])
        self.assertEqual(self.group_version(roles.DELIVERY_STAFF), version)
        self.assertEqual(self.stored(roles.DELIVERY_STAFF, "orders"), "assigned_deliveries")
        self.assertEqual(self.audits(SCOPE_ACTION), [])

    def test_pv09_ac2_put_without_confirmation_is_blocked_with_impact(self):
        version = self.group_version(roles.DELIVERY_STAFF)
        response = self.put(roles.DELIVERY_STAFF, scopes={"orders": "all"})
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["code"], WIDENING_CODE)
        self.assertTrue(body["impact"]["widens_customer_data"])
        self.assertEqual(body["impact"], self.preview(roles.DELIVERY_STAFF, scopes={"orders": "all"}).json())
        self.assertEqual(self.group_version(roles.DELIVERY_STAFF), version)
        self.assertEqual(self.stored(roles.DELIVERY_STAFF, "orders"), "assigned_deliveries")

    def test_pv09_ac3_confirmed_put_records_flag(self):
        response = self.put(roles.DELIVERY_STAFF, scopes={"orders": "all"}, confirm_customer_data_widening=True)
        self.assertEqual(response.status_code, 200)
        row = self.audits(SCOPE_ACTION, roles.DELIVERY_STAFF)[0]
        self.assertIs(row.changes["customer_data_widening_confirmed"], True)

    def test_pv09_ac4_turning_v2_on_needs_confirmation(self):
        revoke(roles.WAREHOUSE_STAFF, "sales.view_order_customer_info")
        response = self.put(roles.WAREHOUSE_STAFF, capabilities={"view_order_customer_info": True})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], WIDENING_CODE)
        self.assertEqual(response.json()["impact"]["widened"][0]["key"], "view_order_customer_info")
        ok = self.put(
            roles.WAREHOUSE_STAFF, capabilities={"view_order_customer_info": True}, confirm_customer_data_widening=True)
        self.assertEqual(ok.status_code, 200)
        row = self.audits(CAPABILITY_ACTION, roles.WAREHOUSE_STAFF)[-1]
        self.assertIs(row.changes["customer_data_widening_confirmed"], True)
        # Dòng thời gian bỏ qua khoá cờ, không thành dòng "một việc".
        body = self.client_of("owner").get(detail_url(roles.WAREHOUSE_STAFF)).json()
        labels = [e["label"] for e in body["timeline"] if e["kind"] == CAPABILITY_ACTION]
        self.assertEqual(len(labels), 1)
        self.assertTrue(labels[0].startswith("Bật việc"))

    def test_pv09_turning_v2_off_does_not_need_confirmation(self):
        response = self.put(roles.WAREHOUSE_STAFF, capabilities={"view_order_customer_info": False})
        self.assertEqual(response.status_code, 200)

    def test_pv09_ac5_narrowing_counts_open_rows_and_needs_no_confirmation(self):
        response = self.preview(roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me"})
        body = response.json()
        self.assertFalse(body["widens_customer_data"])
        self.assertEqual([n["key"] for n in body["narrowed"]], ["receipts"])
        # Phiếu nhập Nháp: 5 phiếu của scene; `warehouse_courier` không tạo phiếu nào nên mất cả 5 (gộp không trùng).
        self.assertEqual(body["narrowed"][0]["rows_losing_access"], 5)
        self.assertEqual(body["narrowed"][0]["from"], "all")
        self.assertEqual(body["narrowed"][0]["to"], "created_by_me")
        self.assertEqual(self.put(roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me"}).status_code, 200)

    def test_pv09_narrowing_does_not_count_finished_rows(self):
        from apps.purchasing.models import PurchaseReceipt

        PurchaseReceipt.objects.filter(supplier__isnull=False).exclude(created_by=self.scene.users["warehouse_staff"]).update(
            status=PurchaseReceipt.Status.CANCELLED)
        body = self.preview(roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me"}).json()
        self.assertEqual(body["narrowed"][0]["rows_losing_access"], 3)  # chỉ còn 3 phiếu Nháp của NV kho, nên NV kiêm giao mất 3

    def test_pv09_ac6_member_of_two_groups_is_listed_as_wider_elsewhere(self):
        set_scope(roles.DELIVERY_STAFF, "orders", "all")
        body = self.preview(roles.DELIVERY_STAFF, scopes={"orders": "assigned_deliveries"}).json()
        wider = [w for w in body["already_wider_elsewhere"] if w["key"] == "orders"]
        self.assertEqual(len(wider), 1)
        self.assertEqual(wider[0]["id"], self.scene.users["warehouse_courier"].pk)
        self.assertEqual(wider[0]["via_group"], roles.WAREHOUSE_STAFF)
        self.assertEqual(set(wider[0]), {"id", "display_name", "via_group", "key"})

    def test_pv09_ac7_receipts_is_not_customer_data(self):
        set_scope(roles.WAREHOUSE_STAFF, "receipts", "created_by_me")
        response = self.put(roles.WAREHOUSE_STAFF, scopes={"receipts": "all"})
        self.assertEqual(response.status_code, 200)

    def test_pv09_ac9_preview_body_has_no_customer_personal_data(self):
        text = self.preview(roles.DELIVERY_STAFF, scopes={"orders": "all", "customers": "all"}).content.decode()
        for fake in fixtures.FAKE_STRINGS:
            self.assertNotIn(fake, text)
        self.assertNotIn("Khách Giả", text)

    def test_pv09_re_enabling_view_orders_on_group_storing_all_needs_confirmation(self):
        """R1 (02b §2.5): Q-7 giữ giá trị khi tắt việc, nên bật lại việc trên nhóm đang lưu `all` mở dữ liệu khách."""
        set_scope(roles.DELIVERY_STAFF, "orders", "all")
        off = self.put(roles.DELIVERY_STAFF, capabilities={"view_orders": False})
        self.assertEqual(off.status_code, 200, off.content)  # NV giao đang có `view_orders` Tầng 1
        again = self.put(roles.DELIVERY_STAFF, capabilities={"view_orders": True})
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.json()["code"], WIDENING_CODE)

    def test_pv09_invoices_gate_opening_counts_as_widening(self):
        revoke(roles.MANAGER, "sales.view_salesinvoice", "sales.view_salesinvoiceline")
        body = self.preview(roles.MANAGER, capabilities={"view_sales_invoices": True}).json()
        self.assertTrue(body["widens_customer_data"])
        self.assertIn("invoices", [w["key"] for w in body["widened"]])

    def test_pv09_preview_validates_like_put(self):
        cases = (
            ({"scopes": {"receipts": "mine"}}, "SCOPE_VALUE_INVALID"),
            ({"scopes": {"stock": "all"}}, "SCOPE_OBJECT_UNKNOWN"),
            ({"capabilities": {"manage_staff": True}}, "BR-PQ-32"),
            ({"capabilities": {"pack_print": True}}, "CAPABILITY_REQUIRES"),
            ({"capabilities": {"view_customers": True}}, "SCOPE_VALUE_INVALID"),  # PO-Q1 (NV kho, D7 = none)
            ({}, "INVALID_INPUT"),
        )
        for body, code in cases:
            group = roles.CUSTOMER_SERVICE if "pack_print" in json.dumps(body) else roles.WAREHOUSE_STAFF
            response = self.preview(group, **body)
            self.assertEqual(response.status_code, 400, body)
            self.assertEqual(response.json()["code"], code, body)
        self.assertEqual(self.preview(roles.OWNER, scopes={"receipts": "all"}).json()["code"], "GROUP_LOCKED")
        self.assertEqual(self.preview("nope", scopes={"receipts": "all"}).status_code, 404)


class MockParityTests(SaveBase):
    """4 ca đối chiếu mock F1 (review re-review a1b5b31, M1): rank HIỆU LỰC của D7 bị chặn trần `assigned_deliveries` khi việc tắt."""

    def test_case1_courier_d7_assigned_to_all_while_view_customers_off_is_not_widening_nor_narrowing(self):
        body = self.preview(roles.DELIVERY_STAFF, scopes={"customers": "all"}).json()
        self.assertFalse(body["widens_customer_data"])
        self.assertEqual(body["widened"], [])
        self.assertEqual(body["narrowed"], [])

    def test_case2_courier_stored_all_then_turning_view_customers_on_is_widening(self):
        set_scope(roles.DELIVERY_STAFF, "customers", "all")
        body = self.preview(roles.DELIVERY_STAFF, capabilities={"view_customers": True}).json()
        self.assertTrue(body["widens_customer_data"])
        self.assertEqual(body["widened"], [{"key": "customers", "from": "all", "to": "all"}])  # giá trị ĐÃ LƯU (L11)

    def test_case3_manager_off_then_on_with_d7_all_is_widening(self):
        revoke(roles.MANAGER, "sales.view_customer_list")
        body = self.preview(roles.MANAGER, capabilities={"view_customers": True}).json()
        self.assertTrue(body["widens_customer_data"])
        self.assertEqual(body["widened"], [{"key": "customers", "from": "all", "to": "all"}])

    def test_case3b_manager_turning_view_customers_off_is_narrowing_not_widening(self):
        body = self.preview(roles.MANAGER, capabilities={"view_customers": False}).json()
        self.assertFalse(body["widens_customer_data"])

    def test_case4_warehouse_gate_opens_with_d7_all_in_the_same_request(self):
        body = self.preview(roles.WAREHOUSE_STAFF, capabilities={"view_customers": True}, scopes={"customers": "all"}).json()
        self.assertTrue(body["widens_customer_data"])
        self.assertEqual(body["widened"], [{"key": "customers", "from": "none", "to": "all"}])
        self.assertEqual(
            body["message"].split(" người")[0], str(len(body["affected_members"])))
        # Không kèm D7 thì PO-Q1 chặn (xem PreviewAndWideningTests.test_pv09_preview_validates_like_put).
        self.assertEqual(
            self.preview(roles.WAREHOUSE_STAFF, capabilities={"view_customers": True}).json()["code"],
            "SCOPE_VALUE_INVALID")

    def test_case5_two_widened_objects_message_lists_labels(self):
        body = self.preview(roles.DELIVERY_STAFF, scopes={"orders": "all", "deliveries": "all"}).json()
        self.assertTrue(body["message"].endswith("ở: Đơn hàng, Phiếu giao."), body["message"])


# --- PV-10 -------------------------------------------------------------------------------------------------------------

class VersionTests(SaveBase):
    def test_pv10_ac1_second_save_with_old_version_gets_409(self):
        version = self.group_version(roles.WAREHOUSE_STAFF)
        first = self.put(roles.WAREHOUSE_STAFF, version=version, scopes={"receipts": "created_by_me"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(int(first.json()["version"]), int(version) + 1)
        second = self.put(roles.WAREHOUSE_STAFF, version=version, scopes={"receipts": "created_by_me_today"})
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "GROUP_CHANGED")
        self.assertEqual(second.json()["detail"], "Nhóm này vừa được người khác đổi. Tải lại để xem bản mới.")
        self.assertEqual(self.stored(roles.WAREHOUSE_STAFF, "receipts"), "created_by_me")
        self.assertEqual(len(self.audits(SCOPE_ACTION, roles.WAREHOUSE_STAFF)), 1)

    def test_pv10_ac2_capability_change_then_scope_change_with_old_version_is_409(self):
        version = self.group_version(roles.WAREHOUSE_STAFF)
        self.assertEqual(self.put(roles.WAREHOUSE_STAFF, version=version, capabilities={"approve_return": True}).status_code, 200)
        response = self.put(roles.WAREHOUSE_STAFF, version=version, scopes={"receipts": "created_by_me"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.stored(roles.WAREHOUSE_STAFF, "receipts"), "all")

    def test_pv10_ac3_other_group_has_its_own_version(self):
        manager_version = self.group_version(roles.MANAGER)
        self.assertEqual(self.put(roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me"}).status_code, 200)
        self.assertEqual(self.put(roles.MANAGER, version=manager_version, scopes={"receipts": "created_by_me"}).status_code, 200)

    def test_pv10_ac4_missing_or_bad_version_is_400(self):
        before = self.group_version(roles.WAREHOUSE_STAFF)
        client = self.client_of("owner")
        for body in ({"scopes": {"receipts": "created_by_me"}},
                     {"version": 3, "scopes": {"receipts": "created_by_me"}},
                     {"version": "", "scopes": {"receipts": "created_by_me"}},
                     {"version": None, "capabilities": {"approve_return": True}}):
            response = client.put(put_url(roles.WAREHOUSE_STAFF), body, format="json")
            self.assertEqual(response.status_code, 400, body)
            self.assertEqual(response.json()["code"], "INVALID_INPUT", body)
        self.assertEqual(self.group_version(roles.WAREHOUSE_STAFF), before)
        self.assertEqual(self.stored(roles.WAREHOUSE_STAFF, "receipts"), "all")

    def test_pv10_non_numeric_version_is_409_not_500(self):
        response = self.put(roles.WAREHOUSE_STAFF, version="abc", scopes={"receipts": "created_by_me"})
        self.assertEqual(response.status_code, 409)

    def test_pv10_validation_errors_come_before_the_version_check(self):
        """02b §2.3: kiểm 1–7 trước bước 8 (CAS): thân sai kể cả khi `version` cũ vẫn là 400, không phải 409."""
        response = self.put(roles.WAREHOUSE_STAFF, version="999", scopes={"receipts": "mine"})
        self.assertEqual(response.status_code, 400)

    def test_pv10_version_increments_once_per_real_change_and_not_on_noop(self):
        start = int(self.group_version(roles.WAREHOUSE_STAFF))
        self.put(roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me", "returns": "assigned_deliveries"})
        self.assertEqual(int(self.group_version(roles.WAREHOUSE_STAFF)), start + 1)
        self.put(roles.WAREHOUSE_STAFF, scopes={"receipts": "created_by_me"})
        self.assertEqual(int(self.group_version(roles.WAREHOUSE_STAFF)), start + 1)

    def test_pv10_group_without_config_row_is_treated_as_version_one_and_gets_row_on_save(self):
        GroupAccessConfig.objects.filter(group__name=roles.WAREHOUSE_STAFF).delete()
        self.assertEqual(self.group_version(roles.WAREHOUSE_STAFF), "1")
        response = self.put(roles.WAREHOUSE_STAFF, version="1", scopes={"receipts": "created_by_me"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], "2")

    def test_pv10_stale_version_409_precedes_widening_check(self):
        version = self.group_version(roles.DELIVERY_STAFF)
        self.put(roles.DELIVERY_STAFF, scopes={"deliveries": "assigned"})  # không đổi gì (đang assigned): không tăng version
        self.put(roles.DELIVERY_STAFF, scopes={"returns": "all"}, confirm_customer_data_widening=True)
        response = self.put(roles.DELIVERY_STAFF, version=version, scopes={"orders": "all"})
        self.assertEqual(response.status_code, 409)  # chưa tới bước 11 (xác nhận mở rộng)
