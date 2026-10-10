"""
PV-04, PV-05, PV-06 (Lô 4): phiếu giao, hàng hoàn, gọi xác nhận, khách hàng và phiếu nhập đọc phạm vi từ cấu hình
(D3, D5, D4, D7, D6). BR-PQ-33/34/35/36, BR-GH-06/18, BR-HV, BR-MH, bất biến 1 và 9, SR-PII-02. 02b §1.4, §1.5.

Dùng chung dữ liệu giả của mốc PV-01 (`fixtures.build_scene`, giờ cố định 06/10/2026 10:00 giờ VN). Mỗi lần đổi cấu hình
trong test đều nạp lại user qua `ScopeSceneBase.user` (bộ nhớ phân giải nằm trên đối tượng user, 02b §1.3 luật 5).
"""
import datetime
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.sales.models import Customer

from . import fixtures
from .test_orders_invoices_scope import ScopeSceneBase, grant, revoke, set_scope

UTC = datetime.timezone.utc
COST_KEYS = ("rate", "purchase_rate", "landed_unit_cost", "unit_cost", "purchase_amount", "allocated_amount")


def all_keys(node):
    """Mọi khoá JSON ở mọi độ sâu (để chứng minh không có khoá giá vốn)."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from all_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from all_keys(item)


class SceneApiBase(ScopeSceneBase):
    def post(self, label, url, body=None):
        client = APIClient()
        client.force_authenticate(self.user(label))
        return client.post(url, body or {}, format="json")

    def patch(self, label, url, body):
        client = APIClient()
        client.force_authenticate(self.user(label))
        return client.patch(url, body, format="json")

    def note(self, label):
        return self.scene.notes[label]

    def note_labels(self, response):
        by_code = {note.code: label for label, note in self.scene.notes.items()}
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        return {by_code[row["code"]] for row in rows}


# --- PV-04: phiếu giao (D3) và hàng hoàn (D5) --------------------------------------------------------------------------

class DeliveryNoteScopeTests(SceneApiBase):
    COURIER_NOTES = {
        "note_of_order_assigned_courier", "note_of_order_failed_courier", "note_of_order_ended_3_days",
        "note_of_order_ended_7_days_inside", "note_of_order_ended_8_days", "note_of_order_cancelled_courier",
    }

    def test_pv04_ac1_courier_with_assigned_scope_sees_only_own_notes(self):
        response = self.get("courier", "/api/delivery/notes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.note_labels(response), self.COURIER_NOTES)
        mine = self.get("courier", "/api/delivery/notes/", assigned_to="me")
        self.assertEqual(self.note_labels(mine), self.COURIER_NOTES)

    def test_pv04_ac1_changing_courier_scope_to_all_takes_effect_on_next_request(self):
        set_scope(roles.DELIVERY_STAFF, "deliveries", "all")
        response = self.get("courier", "/api/delivery/notes/")
        self.assertIn("note_of_order_assigned_other", self.note_labels(response))
        self.assertEqual(response.data["count"], len(self.scene.notes))

    def test_pv04_ac2_customer_service_with_default_assigned_sees_only_assigned_notes(self):
        grant(roles.CUSTOMER_SERVICE, "delivery.view_deliverynote")  # CSKH không có sẵn; chỉ để thử phạm vi mặc định
        response = self.get("customer_service", "/api/delivery/notes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)  # CSKH không có phiếu gán cho mình

    def test_pv04_warehouse_narrowed_to_assigned_sees_only_own_notes(self):
        set_scope(roles.WAREHOUSE_STAFF, "deliveries", "assigned")
        response = self.get("warehouse_staff", "/api/delivery/notes/")
        self.assertEqual(response.data["count"], 0)
        other = self.get("warehouse_staff", "/api/delivery/notes/", assigned_to=str(self.scene.users["courier"].pk))
        self.assertEqual(other.status_code, 403)  # hỏi phiếu của người khác không lộ gì

    def test_pv04_ac3_returns_scope_follows_d5_for_list_detail_timeline_and_form(self):
        courier_return = self.scene.returns["return_courier"]
        other_return = self.scene.returns["return_other"]
        listing = self.get("courier", "/api/inventory/returns/")
        self.assertEqual({row["id"] for row in listing.data["results"]}, {courier_return.pk})
        self.assertEqual(self.get("courier", f"/api/inventory/returns/{courier_return.pk}/").status_code, 200)
        self.assertEqual(self.get("courier", f"/api/inventory/returns/{other_return.pk}/").status_code, 404)
        self.assertEqual(self.get("courier", f"/api/guidance/return/{other_return.pk}/").status_code, 404)
        self.assertEqual(self.get("courier", f"/api/guidance/return/{courier_return.pk}/").status_code, 200)
        # Form tạo: phiếu giao ngoài D5 là 404, như không có.
        body = {"delivery_note": self.note("note_of_order_assigned_other").pk, "batch": self.scene.batch.pk, "qty": "1"}
        self.assertEqual(self.post("courier", "/api/inventory/returns/", body).status_code, 404)

    def test_pv04_ac3_d5_all_for_courier_opens_returns_and_form_independent_of_d3(self):
        set_scope(roles.DELIVERY_STAFF, "returns", "all")  # D3 vẫn `assigned`
        listing = self.get("courier", "/api/inventory/returns/")
        self.assertEqual(listing.data["count"], len(self.scene.returns))
        body = {"delivery_note": self.note("note_of_order_assigned_other").pk, "batch": self.scene.batch.pk, "qty": "1"}
        self.assertNotEqual(self.post("courier", "/api/inventory/returns/", body).status_code, 404)
        self.assertEqual(self.get("courier", "/api/delivery/notes/").data["count"], len(self.COURIER_NOTES))  # D3 giữ nguyên

    def test_pv04_ac3_d5_narrowed_for_warehouse_hides_other_courier_returns(self):
        set_scope(roles.WAREHOUSE_STAFF, "returns", "assigned_deliveries")
        listing = self.get("warehouse_staff", "/api/inventory/returns/")
        self.assertEqual(listing.data["count"], 0)  # NV kho không có phiếu gán; phiếu không gắn phiếu giao cũng ẩn

    def test_pv04_ac4_expired_note_hides_customer_data_for_assigned_scope(self):
        note = self.note("note_of_order_ended_8_days")
        body = self.get("courier", f"/api/delivery/notes/{note.pk}/").data
        self.assertIsNone(body["customer_name"])
        self.assertIsNone(body["phone"])
        self.assertIsNone(body["address"])
        inside = self.get("courier", f"/api/delivery/notes/{self.note('note_of_order_ended_7_days_inside').pk}/").data
        self.assertTrue(inside["customer_name"])

    def test_pv04_ac5_scope_all_has_no_window(self):
        set_scope(roles.DELIVERY_STAFF, "deliveries", "all")
        other_expired = self.note("note_of_order_ended_8_days")  # gán cho courier, quá 8 ngày
        body = self.get("courier", f"/api/delivery/notes/{other_expired.pk}/").data
        self.assertTrue(body["customer_name"])
        self.assertTrue(body["address"])
        self.assertTrue(body["phone"])

    def test_pv04_ac6_status_change_on_other_courier_note_is_404_and_unchanged(self):
        note = self.note("note_of_order_assigned_other")
        response = self.post("courier", f"/api/delivery/notes/{note.pk}/status/", {"to_status": "COMPLETED"})
        self.assertEqual(response.status_code, 404)
        note.refresh_from_db()
        self.assertEqual(note.status, "DELIVERING")

    def test_pv04_courier_still_sees_own_cancelled_note_for_br_gh_24(self):
        """W37 S2-AC2: phiếu CANCELLED gán cho mình hiện ra để nhận 400 BR-GH-24, không phải 404."""
        note = self.note("note_of_order_cancelled_courier")
        response = self.post("courier", f"/api/delivery/notes/{note.pk}/status/", {"to_status": "COMPLETED"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("BR-GH-24", response.content.decode())

    def test_pv04_ac7_gate_stays_closed_without_view_deliverynote(self):
        set_scope(roles.DELIVERY_STAFF, "deliveries", "all")
        revoke(roles.DELIVERY_STAFF, "delivery.view_deliverynote")
        self.assertEqual(self.get("courier", "/api/delivery/notes/").status_code, 403)

    def test_pv04_timeline_follows_d3(self):
        other = self.note("note_of_order_assigned_other")
        own = self.note("note_of_order_assigned_courier")
        self.assertEqual(self.get("courier", f"/api/guidance/delivery/{other.pk}/").status_code, 404)
        self.assertEqual(self.get("courier", f"/api/guidance/delivery/{own.pk}/").status_code, 200)
        set_scope(roles.DELIVERY_STAFF, "deliveries", "all")
        self.assertEqual(self.get("courier", f"/api/guidance/delivery/{other.pk}/").status_code, 200)

    def test_pv04_unauthenticated_is_401(self):
        self.assertEqual(APIClient().get("/api/delivery/notes/").status_code, 401)

    def test_pv04_no_cost_keys_in_note_and_return_bodies(self):
        for label, url in (
            ("warehouse_staff", "/api/delivery/notes/"),
            ("courier", "/api/delivery/notes/"),
            ("warehouse_staff", "/api/inventory/returns/"),
            ("courier", "/api/inventory/returns/"),
        ):
            keys = set(all_keys(self.get(label, url).json()))
            self.assertFalse(keys & {"purchase_rate", "landed_unit_cost", "unit_cost", "profit", "gross_profit"}, (label, url))

    # --- Lỗ dữ liệu cá nhân QA W37 N2: body của POST .../status/ -----------------------------------------------------

    def test_w37_n2_status_response_keeps_customer_data_when_v2_is_off(self):
        """Duy 08/10 câu 7: V2 không áp cho phiếu giao. Thu V2 của NV kho thì phản hồi đổi trạng thái và chi tiết vẫn có
        tên, SĐT, địa chỉ khách (cùng một luật cho danh sách, chi tiết, phản hồi)."""
        revoke(roles.WAREHOUSE_STAFF, "sales.view_order_customer_info")
        note = self.note("note_of_order_assigned_warehouse_courier")
        response = self.post("warehouse_staff", f"/api/delivery/notes/{note.pk}/status/", {"to_status": "COMPLETED"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["customer_name"])
        self.assertTrue(response.json()["address"])
        self.assertEqual(response.json()["order_status"], "COMPLETED")  # khoá W37 được giữ
        detail = self.get("warehouse_staff", f"/api/delivery/notes/{note.pk}/").json()
        self.assertTrue(detail["customer_name"])
        self.assertTrue(detail["phone"])
        self.assertTrue(detail["address"])

    def test_w37_n2_status_response_matches_detail_rule_when_v2_is_on(self):
        note = self.note("note_of_order_assigned_warehouse_courier")
        response = self.post("warehouse_staff", f"/api/delivery/notes/{note.pk}/status/", {"to_status": "COMPLETED"})
        detail = self.get("warehouse_staff", f"/api/delivery/notes/{note.pk}/").json()
        for key in ("customer_name", "address"):
            self.assertEqual(response.json()[key], detail[key], key)
        self.assertTrue(detail["customer_name"])

    def test_w37_n2_status_response_for_courier_in_window_keeps_customer_data(self):
        note = self.note("note_of_order_assigned_courier")
        response = self.post("courier", f"/api/delivery/notes/{note.pk}/status/", {"to_status": "COMPLETED"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["customer_name"])

    def test_w37_n2_courier_list_keeps_customer_data_without_v2(self):
        """Duy 08/10 câu 7: NV giao bị thu V2 vẫn thấy đủ tên, SĐT, địa chỉ trên phiếu của mình (còn trong cửa sổ)."""
        revoke(roles.DELIVERY_STAFF, "sales.view_order_customer_info")
        rows = self.get("courier", "/api/delivery/notes/", assigned_to="me").json()["results"]
        self.assertTrue(rows)
        for row in rows:
            if row["customer_name"] is None:  # phiếu đã quá cửa sổ SR-PII-02 vẫn che (luật còn lại)
                continue
            self.assertTrue(row["address"])
            if row["status"] in ("DELIVERING", "FAILED"):  # `phone` của dòng danh sách chỉ có khi đang giao hoặc giao thất bại
                self.assertTrue(row["phone"])
        self.assertTrue(any(row["customer_name"] for row in rows))

    def test_w37_n2_status_response_hides_customer_data_when_note_is_past_pii_window(self):
        """SR-PII-02 vẫn đúng cho phản hồi `status/`: phiếu quá cửa sổ thì tên và địa chỉ là null (luật còn lại sau câu 7).
        Giả lập quá cửa sổ ở serializer vì phiếu đã quá cửa sổ thì NV giao không mở được (D3), nên chỉ phản hồi mới thấy luật."""
        note = self.note("note_of_order_assigned_courier")
        with mock.patch("apps.delivery.serializers.is_note_pii_expired", return_value=True):
            response = self.post("courier", f"/api/delivery/notes/{note.pk}/status/", {"to_status": "COMPLETED"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["customer_name"])
        self.assertIsNone(response.json()["address"])
        self.assertNotIn("Khách Giả", response.content.decode())
        self.assertNotIn("Đường Giả", response.content.decode())


# --- PV-05: gọi xác nhận (D4) và khách hàng (D7) ----------------------------------------------------------------------

class ConfirmationScopeTests(SceneApiBase):
    def queue(self, label, order_label):
        return self.get(label, f"/api/confirmation/queue/{self.note(f'note_of_{order_label}').pk}/")

    def test_pv05_ac1_pending_or_called_recently(self):
        self.assertEqual(self.queue("customer_service", "order_confirming_pending").status_code, 200)  # A
        self.assertEqual(self.queue("customer_service", "order_called_recent_by_cs").status_code, 200)  # B
        self.assertEqual(self.queue("customer_service", "order_called_by_other_cs").status_code, 404)  # C'

    def test_pv05_ac2_rows_outside_scope_show_only_masked_phone(self):
        response = self.get("customer_service", "/api/confirmation/queue/", state="DONE")
        self.assertEqual(response.status_code, 200)
        rows = {row["order_code"]: row for row in response.json()["results"]}
        outside = rows[self.scene.orders["order_called_by_other_cs"].code]
        self.assertTrue(outside["phone_masked"])
        for key in ("phone", "customer_name", "address", "recipient_name", "recipient_phone"):
            self.assertIsNone(outside[key], key)
        text = response.content.decode()
        self.assertNotIn(self.scene.orders["order_called_by_other_cs"].phone, text)

    def test_pv05_ac3_all_pending_opens_every_note(self):
        set_scope(roles.CUSTOMER_SERVICE, "confirmation", "all_pending")
        self.assertEqual(self.queue("customer_service", "order_called_by_other_cs").status_code, 200)

    def test_pv05_manager_narrowed_to_called_recently_loses_other_notes(self):
        set_scope(roles.MANAGER, "confirmation", "pending_or_called_recently")
        self.assertEqual(self.queue("manager", "order_called_by_other_cs").status_code, 404)
        self.assertEqual(self.queue("manager", "order_confirming_pending").status_code, 200)

    def test_pv05_ac7_confirmation_gate_stays_closed_without_permission(self):
        set_scope(roles.WAREHOUSE_STAFF, "confirmation", "all_pending")
        self.assertEqual(self.queue("warehouse_staff", "order_confirming_pending").status_code, 403)
        self.assertEqual(APIClient().get("/api/confirmation/queue/").status_code, 401)

    def test_pv05_search_masks_outside_scope_by_d4(self):
        order = self.scene.orders["order_called_by_other_cs"]
        client = APIClient()
        client.force_authenticate(self.user("customer_service"))
        response = client.post("/api/confirmation/search/", {"q": order.code}, format="json")
        self.assertEqual(response.status_code, 200)
        row = response.json()["results"][0]
        self.assertFalse(row["in_scope"])
        self.assertNotIn(order.phone, response.content.decode())
        set_scope(roles.CUSTOMER_SERVICE, "confirmation", "all_pending")
        client.force_authenticate(self.user("customer_service"))
        row = client.post("/api/confirmation/search/", {"q": order.code}, format="json").json()["results"][0]
        self.assertTrue(row["in_scope"])


class UngroupedUserTests(SceneApiBase):
    """Người không nhóm, chỉ được gán quyền trực tiếp (UC-6, R9, D-3): giá trị hẹp nhất của từng đối tượng, riêng D4 là không có.

    Đây là chỗ hành vi ĐỔI so với trước Lô 4 (xem dev-notes Lô 4, "Lệch"); điều phối viên đếm số người này trước khi migrate."""

    def test_ungrouped_confirmation_scope_is_none_not_widened(self):
        direct = "direct_permissions"
        for order_label in ("order_confirming_pending", "order_confirming_escalated"):
            self.assertEqual(
                self.get(direct, f"/api/confirmation/queue/{self.note(f'note_of_{order_label}').pk}/").status_code, 404)
        rows = self.get(direct, "/api/confirmation/queue/").json()["results"]
        for row in rows:
            self.assertIsNone(row["customer_name"])
            self.assertIsNone(row["phone"])
            self.assertTrue(row["phone_masked"])

    def test_ungrouped_receipts_scope_is_created_by_me_today(self):
        grant_direct = self.user("direct_permissions")
        self.assertEqual(self.get("direct_permissions", "/api/purchasing/receipts/").json()["count"], 0)
        self.assertTrue(grant_direct.has_perm("purchasing.view_purchasereceipt"))

    def test_ungrouped_customers_scope_is_none_on_both_apis(self):
        self.assertEqual(self.get("direct_permissions", "/api/sales/customer-directory/").json()["count"], 0)
        self.assertEqual(self.get("direct_permissions", "/api/sales/customers/").json()["count"], 0)

    def test_ungrouped_deliveries_scope_stays_assigned(self):
        response = self.get("direct_permissions", "/api/delivery/notes/")
        self.assertEqual(self.note_labels(response), {"note_of_order_assigned_direct"})


class CustomerScopeTests(SceneApiBase):
    def setUp(self):
        grant(roles.DELIVERY_STAFF, "sales.view_customer_list")  # "Xem khách hàng" bật cho NV giao (D7 mặc định assigned_deliveries)

    def ids(self, response):
        data = response.json()
        rows = data["results"] if isinstance(data, dict) else data
        return {row["id"] for row in rows}

    def own_customers(self):
        return {self.scene.customers[f"customer_of_{label}"].pk for label in (
            "order_assigned_courier", "order_failed_courier", "order_ended_3_days", "order_ended_7_days_inside",
            "order_cancelled_courier")}

    def test_pv05_ac4_directory_and_legacy_return_the_same_set_for_courier(self):
        directory = self.ids(self.get("courier", "/api/sales/customer-directory/"))
        legacy = self.ids(self.get("courier", "/api/sales/customers/"))
        self.assertEqual(directory, legacy)
        self.assertEqual(directory, self.own_customers())  # trong cửa sổ: bỏ khách của phiếu quá 7 ngày

    def test_pv05_ac5_all_scope_returns_every_customer_on_both_apis(self):
        everyone = set(Customer.objects.values_list("pk", flat=True))
        for label in ("manager",):
            self.assertEqual(self.ids(self.get(label, "/api/sales/customer-directory/")), everyone)
            self.assertEqual(self.ids(self.get(label, "/api/sales/customers/")), everyone)
        set_scope(roles.DELIVERY_STAFF, "customers", "all")
        self.assertEqual(self.ids(self.get("courier", "/api/sales/customer-directory/")), everyone)
        legacy = self.get("courier", "/api/sales/customers/")
        self.assertEqual(self.ids(legacy), everyone)
        # D7 = all: API cũ trả đủ field (có địa chỉ mặc định), D7 hẹp hơn thì chỉ field cần để giao.
        self.assertIn("default_address", legacy.json()["results"][0])

    def test_pv05_legacy_api_shape_for_narrow_scope_has_no_note_or_address(self):
        rows = self.get("courier", "/api/sales/customers/").json()["results"]
        self.assertTrue(rows)
        for row in rows:
            self.assertNotIn("note", row)
            self.assertNotIn("default_address", row)

    def test_pv05_ac6_customer_outside_scope_is_404_or_empty(self):
        outside = self.scene.customers["customer_of_order_assigned_other"]
        self.assertEqual(self.get("courier", f"/api/sales/customer-directory/{outside.pk}/").status_code, 404)
        self.assertEqual(self.get("courier", f"/api/sales/customers/{outside.pk}/").status_code, 404)
        self.assertEqual(self.get("courier", f"/api/guidance/customer/{outside.pk}/").status_code, 404)
        own = self.scene.customers["customer_of_order_assigned_courier"]
        self.assertEqual(self.get("courier", f"/api/sales/customer-directory/{own.pk}/").status_code, 200)
        self.assertEqual(self.get("courier", f"/api/guidance/customer/{own.pk}/").status_code, 200)

    def test_pv05_ac6_order_filter_by_customer_outside_d7_is_empty_even_when_d1_is_all(self):
        outside = self.scene.customers["customer_of_order_assigned_other"]
        set_scope(roles.MANAGER, "customers", "assigned_deliveries")
        response = self.get("manager", "/api/sales/orders/", customer=str(outside.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        set_scope(roles.MANAGER, "customers", "all")
        again = self.get("manager", "/api/sales/orders/", customer=str(outside.pk))
        self.assertEqual(again.data["count"], 1)

    def _post_search(self, label, body):
        client = APIClient()
        client.force_authenticate(self.user(label))
        return client.post("/api/sales/orders/search/", body, format="json")

    def test_pv05_ac6_search_body_customer_outside_d7_is_empty_for_int_and_string(self):
        outside = self.scene.customers["customer_of_order_assigned_other"]
        set_scope(roles.MANAGER, "customers", "assigned_deliveries")
        for value in (outside.pk, str(outside.pk)):
            response = self._post_search("manager", {"customer": value})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["count"], 0)
        set_scope(roles.MANAGER, "customers", "all")
        for value in (outside.pk, str(outside.pk)):
            self.assertEqual(self._post_search("manager", {"customer": value}).json()["count"], 1)

    def test_pv05_ac6_search_body_customer_invalid_value_is_400(self):
        for value in ("abc", -1, 0, True, ["1"]):
            response = self._post_search("manager", {"customer": value})
            self.assertEqual(response.status_code, 400, value)

    def test_pv05_ac6_order_filter_by_customer_inside_d7_returns_rows(self):
        own = self.scene.customers["customer_of_order_assigned_courier"]
        response = self.get("courier", "/api/sales/orders/", customer=str(own.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_pv05_ac7_directory_gate_closed_when_view_customers_is_off_whatever_d7(self):
        revoke(roles.MANAGER, "sales.view_customer_list")
        self.assertEqual(self.get("manager", "/api/sales/customer-directory/").status_code, 403)
        self.assertEqual(self.get("manager", "/api/sales/orders/", customer="1").status_code, 403)
        # D7 đã lưu `all` mà nhóm mất việc: không còn là "tất cả" cho API cũ (tối đa assigned_deliveries, H1).
        legacy = self.get("manager", "/api/sales/customers/")
        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(legacy.data["count"], 0)  # Quản lý không có phiếu giao gán cho mình

    def test_pv05_d7_none_makes_directory_empty(self):
        set_scope(roles.MANAGER, "customers", "none")
        response = self.get("manager", "/api/sales/customer-directory/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        search = APIClient()
        search.force_authenticate(self.user("manager"))
        found = search.post("/api/sales/customer-directory/search/", {"q": "Khách"}, format="json")
        self.assertEqual(found.json()["count"], 0)

    def test_pv05_search_respects_d7(self):
        client = APIClient()
        client.force_authenticate(self.user("courier"))
        found = client.post("/api/sales/customer-directory/search/", {"q": "Khách Giả"}, format="json").json()
        self.assertEqual({row["id"] for row in found["results"]}, self.own_customers())

    def test_pv05_directory_for_narrow_scope_has_no_default_address_or_note(self):
        """Phạm vi hẹp (khách của phiếu mình giao): không có địa chỉ mặc định hay ghi chú nội bộ (bất biến 9, S-7)."""
        own = self.scene.customers["customer_of_order_assigned_courier"]
        detail = self.get("courier", f"/api/sales/customer-directory/{own.pk}/").json()
        self.assertNotIn("default_address", detail)
        self.assertNotIn("note", detail)
        self.assertNotIn("Đường Giả", str(detail))
        listing = self.get("courier", "/api/sales/customer-directory/").json()["results"]
        for row in listing:
            self.assertNotIn("note", row)
        manager_detail = self.get("manager", f"/api/sales/customer-directory/{own.pk}/").json()
        self.assertIn("default_address", manager_detail)

    def test_pv05_unauthenticated_is_401(self):
        self.assertEqual(APIClient().get("/api/sales/customer-directory/").status_code, 401)
        self.assertEqual(APIClient().get("/api/sales/customers/").status_code, 401)

    def test_pv05_ac8_old_name_based_scope_helpers_are_gone(self):
        banned = (
            "FULL_SCOPE_GROUPS", "CUSTOMER_DIRECTORY_GROUPS", "sees_customer_directory", "has_full_delivery_scope",
            "is_customer_service", "note_in_customer_service_scope",
        )
        root = Path(settings.BASE_DIR) / "apps"
        offenders = []
        for path in root.rglob("*.py"):
            parts = set(path.parts)
            if "tests" in parts or "migrations" in parts or path.name.startswith("test_"):
                continue
            text = path.read_text(encoding="utf-8")
            offenders += [f"{path.relative_to(root)}: {name}" for name in banned if name in text]
        self.assertEqual(offenders, [])


# --- PV-06: phiếu nhập (D6) --------------------------------------------------------------------------------------------

def vn(year, month, day, hour, minute):
    """Mốc giờ VN (UTC+7) đổi sang UTC."""
    return datetime.datetime(year, month, day, hour, minute, tzinfo=UTC) - datetime.timedelta(hours=7)


class ReceiptScopeTests(SceneApiBase):
    def receipt(self, label):
        return self.scene.receipts[label]

    def labels(self, response):
        by_pk = {receipt.pk: label for label, receipt in self.scene.receipts.items()}
        return {by_pk[row["id"]] for row in response.json()["results"]}

    ALL = {
        "receipt_warehouse_today", "receipt_warehouse_after_midnight", "receipt_warehouse_before_midnight",
        "receipt_manager_today", "receipt_owner_old",
    }

    def test_pv06_ac1_default_all_matches_today_for_warehouse(self):
        response = self.get("warehouse_staff", "/api/purchasing/receipts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.labels(response), self.ALL)

    def test_pv06_ac2_created_by_me_hides_other_people_receipts(self):
        set_scope(roles.WAREHOUSE_STAFF, "receipts", "created_by_me")
        response = self.get("warehouse_staff", "/api/purchasing/receipts/")
        self.assertEqual(self.labels(response), {
            "receipt_warehouse_today", "receipt_warehouse_after_midnight", "receipt_warehouse_before_midnight"})
        others = self.receipt("receipt_manager_today")
        self.assertEqual(self.get("warehouse_staff", f"/api/purchasing/receipts/{others.pk}/").status_code, 404)
        self.assertEqual(self.get("warehouse_staff", f"/api/guidance/receipt/{others.pk}/").status_code, 404)
        own = self.receipt("receipt_warehouse_before_midnight")
        self.assertEqual(self.get("warehouse_staff", f"/api/purchasing/receipts/{own.pk}/").status_code, 200)

    def test_pv06_ac3_created_by_me_today_uses_vietnam_calendar_day(self):
        set_scope(roles.WAREHOUSE_STAFF, "receipts", "created_by_me_today")
        response = self.get("warehouse_staff", "/api/purchasing/receipts/")
        # 10:00 giờ VN 06/10: phiếu 00:05 06/10 vào ngày; phiếu 23:50 05/10 (giờ VN) thì không.
        self.assertEqual(self.labels(response), {"receipt_warehouse_today", "receipt_warehouse_after_midnight"})
        old = self.receipt("receipt_warehouse_before_midnight")
        self.assertEqual(self.get("warehouse_staff", f"/api/purchasing/receipts/{old.pk}/").status_code, 404)

    def test_pv06_ac3_utc_day_boundary_is_not_used(self):
        """Phiếu 23:50 giờ VN 05/10 là 16:50 UTC 05/10; phiếu 00:05 giờ VN 06/10 là 17:05 UTC 05/10: cùng ngày UTC, khác ngày VN."""
        set_scope(roles.WAREHOUSE_STAFF, "receipts", "created_by_me_today")
        with mock.patch("django.utils.timezone.now", return_value=vn(2026, 10, 5, 23, 55)):
            response = self.get("warehouse_staff", "/api/purchasing/receipts/")
        self.assertEqual(self.labels(response), {"receipt_warehouse_before_midnight"})

    def test_pv06_ac4_draft_opened_before_midnight_cannot_be_saved_after_midnight(self):
        set_scope(roles.WAREHOUSE_STAFF, "receipts", "created_by_me_today")
        draft = self.receipt("receipt_warehouse_today")
        with mock.patch("django.utils.timezone.now", return_value=vn(2026, 10, 6, 23, 59)):
            self.assertEqual(self.get("warehouse_staff", f"/api/purchasing/receipts/{draft.pk}/").status_code, 200)
        with mock.patch("django.utils.timezone.now", return_value=vn(2026, 10, 7, 0, 1)):
            blocked = self.patch("warehouse_staff", f"/api/purchasing/receipts/{draft.pk}/", {"note": "sửa muộn"})
            submit = self.post("warehouse_staff", f"/api/purchasing/receipts/{draft.pk}/submit/")
            manager = self.patch("manager", f"/api/purchasing/receipts/{draft.pk}/", {"note": "quản lý sửa"})
        self.assertEqual(blocked.status_code, 404)
        self.assertEqual(submit.status_code, 404)
        self.assertEqual(manager.status_code, 200)  # Quản lý D6 = all vẫn thấy và sửa
        draft.refresh_from_db()
        self.assertEqual(draft.note, "quản lý sửa")  # bản nháp không đổi bởi lần 404, không mất

    def test_pv06_ac5_cancel_keeps_old_rule_even_outside_d6(self):
        set_scope(roles.WAREHOUSE_STAFF, "receipts", "created_by_me_today")
        old_own = self.receipt("receipt_warehouse_before_midnight")  # người tạo, hôm qua: ngoài D6
        response = self.post("warehouse_staff", f"/api/purchasing/receipts/{old_own.pk}/cancel/")
        self.assertEqual(response.status_code, 200)
        old_own.refresh_from_db()
        self.assertEqual(old_own.status, "CANCELLED")
        self.assertTrue(AuditLog.objects.filter(action="cancel_purchase_receipt", object_id=str(old_own.pk)).exists())

    def test_pv06_ac6_scope_all_does_not_open_cancel_for_other_creators(self):
        others = self.receipt("receipt_manager_today")
        response = self.post("warehouse_staff", f"/api/purchasing/receipts/{others.pk}/cancel/")
        self.assertEqual(response.status_code, 403)  # luật cũ: người tạo hoặc Quản lý/Chủ
        others.refresh_from_db()
        self.assertEqual(others.status, "DRAFT")

    def test_pv06_cancel_of_other_creator_outside_d6_is_404_not_403(self):
        set_scope(roles.WAREHOUSE_STAFF, "receipts", "created_by_me")
        others = self.receipt("receipt_manager_today")
        self.assertEqual(self.post("warehouse_staff", f"/api/purchasing/receipts/{others.pk}/cancel/").status_code, 404)

    def test_pv06_manager_with_narrow_d6_can_still_cancel_by_old_rule(self):
        set_scope(roles.MANAGER, "receipts", "created_by_me")
        warehouse_receipt = self.receipt("receipt_warehouse_today")
        self.assertEqual(self.get("manager", f"/api/purchasing/receipts/{warehouse_receipt.pk}/").status_code, 404)
        response = self.post("manager", f"/api/purchasing/receipts/{warehouse_receipt.pk}/cancel/")
        self.assertEqual(response.status_code, 200)  # D6 không mở thêm, cũng không chặn thêm luật huỷ

    def test_pv06_ac7_no_cost_keys_for_user_without_view_costprice(self):
        listing = self.get("warehouse_staff", "/api/purchasing/receipts/")
        self.assertEqual(listing.status_code, 200)
        self.assertFalse(set(all_keys(listing.json())) & set(COST_KEYS))
        detail = self.get("warehouse_staff", f"/api/purchasing/receipts/{self.receipt('receipt_manager_today').pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(set(all_keys(detail.json())) & set(COST_KEYS))

    def test_pv06_ac8_courier_has_no_receipt_permission(self):
        self.assertEqual(self.get("courier", "/api/purchasing/receipts/").status_code, 403)
        self.assertEqual(APIClient().get("/api/purchasing/receipts/").status_code, 401)

    def test_pv06_receive_batches_is_not_blocked_by_d6(self):
        """Tạo mới không phải đọc dòng: D6 chỉ lọc xem và sửa, không chặn nhập phiếu mới (Q-3b)."""
        set_scope(roles.WAREHOUSE_STAFF, "receipts", "created_by_me_today")
        body = {
            "supplier": self.scene.batch.supplier_id, "warehouse": self.scene.batch.warehouse_id,
            "received_date": "2026-10-06", "lines": [{"item_code": self.scene.batch.item.code, "qty": "5", "rate": "80000"}],
        }
        response = self.post("warehouse_staff", "/api/purchasing/receipts/receive-batches/", body)
        self.assertIn(response.status_code, (200, 201), response.content)

    def test_pv06_manager_and_owner_default_all(self):
        self.assertEqual(self.labels(self.get("manager", "/api/purchasing/receipts/")), self.ALL)
        self.assertEqual(self.labels(self.get("owner", "/api/purchasing/receipts/")), self.ALL)

    def test_pv06_gate_closed_when_scope_all_but_view_perm_revoked(self):
        revoke(roles.WAREHOUSE_STAFF, "purchasing.view_purchasereceipt")
        self.assertEqual(self.get("warehouse_staff", "/api/purchasing/receipts/").status_code, 403)
