"""
QA5-B2 (02b §3.8 R2): quyền xem dòng thời gian phiếu giao = quyền xem chi tiết.

CSKH (`customer_service`) xem chi tiết phiếu trong phạm vi gọi xác nhận
(`note_in_customer_service_scope`), nên `GET /api/guidance/delivery/<note_id>/` phải trả 200 với phiếu trong
phạm vi và 404 với phiếu ngoài phạm vi. Dòng thời gian không chứa dữ liệu khách (bất biến 9). SĐT và tên là giả.
"""
from django.test import TestCase

from apps.accounts import roles
from apps.common.audit import record_audit
from apps.common.tests.fixtures import client_for, confirm_note_for_test, make_confirming_note, make_user
from apps.delivery.models import CustomerCall, DeliveryNote

FAKE_PHONE = "0900000042"
FAKE_ADDRESS = "1 Cảng"
FAKE_NAME_PART = "Khách TLCS"


class DeliveryTimelineCustomerServiceTests(TestCase):
    def setUp(self):
        self.owner = make_user("tl_owner", roles.OWNER)
        self.warehouse = make_user("tl_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("tl_courier", roles.DELIVERY_STAFF)
        self.other_courier = make_user("tl_courier2", roles.DELIVERY_STAFF)
        self.cs2 = make_user("tl_cs2", roles.CUSTOMER_SERVICE)
        self.cs3 = make_user("tl_cs3", roles.CUSTOMER_SERVICE)

        _, _, self.open_note = make_confirming_note("TLCS1", FAKE_PHONE)
        _, _, self.closed_note = make_confirming_note("TLCS2", "0900000043")
        confirm_note_for_test(self.closed_note)
        record_audit(
            "delivery_call_recorded", actor=self.cs2, obj=self.open_note,
            changes={"phone": {"to": FAKE_PHONE}, "address": {"to": FAKE_ADDRESS}},
            note=f"Gọi {FAKE_PHONE} {FAKE_NAME_PART}",
        )

    def _get(self, user, note_id):
        return client_for(user).get(f"/api/guidance/delivery/{note_id}/")

    def test_qa5_b2_cs_in_scope_gets_timeline(self):
        self.assertEqual(self.open_note.status, DeliveryNote.Status.CONFIRMING)
        resp = self._get(self.cs2, self.open_note.pk)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp["Cache-Control"], "no-store")
        data = resp.json()
        self.assertEqual(data["doc"]["type"], "delivery")
        self.assertEqual(data["doc"]["id"], self.open_note.pk)
        self.assertEqual(data["next_steps"], [])
        self.assertTrue(any(row["label"] == "Ghi nhận cuộc gọi xác nhận" for row in data["timeline"]))

    def test_qa5_b2_cs_out_of_scope_gets_404_same_as_detail(self):
        resp = self._get(self.cs2, self.closed_note.pk)
        self.assertEqual(resp.status_code, 404, resp.content)
        detail = client_for(self.cs2).get(f"/api/confirmation/queue/{self.closed_note.pk}/")
        self.assertEqual(detail.status_code, 404)

    def test_qa5_b2_cs_scope_equals_detail_scope_for_recent_call(self):
        """Phiếu đã đóng nhưng chính CSKH này vừa gọi trong cửa sổ cho phép: chi tiết 200 thì timeline cũng 200."""
        CustomerCall.objects.create(
            note=self.closed_note, result=CustomerCall.Result.CONFIRMED, created_by=self.cs3,
        )
        self.assertEqual(client_for(self.cs3).get(f"/api/confirmation/queue/{self.closed_note.pk}/").status_code, 200)
        self.assertEqual(self._get(self.cs3, self.closed_note.pk).status_code, 200)
        # CSKH khác không gọi phiếu này: ngoài phạm vi ở cả hai nơi.
        self.assertEqual(self._get(self.cs2, self.closed_note.pk).status_code, 404)

    def test_qa5_b2_cs_missing_or_bad_id_gets_404(self):
        self.assertEqual(self._get(self.cs2, 999999).status_code, 404)
        self.assertEqual(self._get(self.cs2, "abc").status_code, 404)

    def test_qa5_b2_body_has_no_customer_personal_data(self):
        resp = self._get(self.cs2, self.open_note.pk)
        self.assertEqual(resp.status_code, 200)
        text = resp.content.decode()
        for secret in (FAKE_PHONE, FAKE_ADDRESS, FAKE_NAME_PART, "0900000043"):
            self.assertNotIn(secret, text)

    def test_qa5_b2_unrelated_user_still_403_and_anonymous_401(self):
        nobody = make_user("tl_nobody")
        self.assertEqual(self._get(nobody, self.open_note.pk).status_code, 403)
        self.assertEqual(self._get(None, self.open_note.pk).status_code, 401)

    def test_qa5_b2_owner_and_warehouse_unchanged(self):
        self.assertEqual(self._get(self.owner, self.open_note.pk).status_code, 200)
        self.assertEqual(self._get(self.owner, self.closed_note.pk).status_code, 200)
        self.assertEqual(self._get(self.warehouse, self.open_note.pk).status_code, 200)
        self.assertEqual(self._get(self.warehouse, self.closed_note.pk).status_code, 200)

    def test_qa5_b2_delivery_staff_scope_unchanged(self):
        self.closed_note.assigned_to = self.courier
        self.closed_note.save(update_fields=["assigned_to"])
        self.assertEqual(self._get(self.courier, self.closed_note.pk).status_code, 200)
        self.assertEqual(self._get(self.other_courier, self.closed_note.pk).status_code, 404)
        self.assertEqual(self._get(self.courier, self.open_note.pk).status_code, 404)
