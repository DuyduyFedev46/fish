"""
L5-code (Lô 17b-BE): chi tiết hàng chờ gọi xác nhận có `note_code` (mã phiếu giao) để FE hiện mã thật.
Mã phiếu không phải dữ liệu cá nhân nên có cả khi đơn ngoài phạm vi (tên, SĐT, địa chỉ vẫn ẩn). Dữ liệu giả.
"""
from apps.common.tests.fixtures import client_for, confirm_note_for_test, make_user
from apps.delivery.models import ConfirmationTask, DeliveryNote

from .test_confirmation_queue_and_labels import ConfirmationL2BaseTestCase

QUEUE = "/api/confirmation/queue/"


class ConfirmationNoteCodeTests(ConfirmationL2BaseTestCase):
    def test_l5_code_detail_and_list_carry_note_code(self):
        _, _, note, _ = self._create_paid_order("DH-NC-1", "0904440001")
        detail = client_for(self.cs1).get(f"{QUEUE}{note.pk}/")
        self.assertEqual(detail.status_code, 200, detail.content)
        self.assertEqual(detail.json()["note_code"], note.code)
        rows = client_for(self.cs1).get(QUEUE).json()["results"]
        self.assertEqual([r["note_code"] for r in rows if r["note_id"] == note.pk], [note.code])

    def test_l5_code_out_of_scope_detail_still_404_and_list_row_masks_personal_data(self):
        _, _, note, task = self._create_paid_order("DH-NC-2", "0904440002")
        confirm_note_for_test(note)
        note.status = DeliveryNote.Status.READY
        note.save(update_fields=["status"])
        task.state = ConfirmationTask.State.DONE
        task.save(update_fields=["state"])
        res = client_for(self.cs1).get(f"{QUEUE}{note.pk}/")
        self.assertEqual(res.status_code, 404)
        self.assertNotIn(note.code, res.content.decode())
        row = [r for r in client_for(self.cs1).get(f"{QUEUE}?state=DONE").json()["results"] if r["note_id"] == note.pk][0]
        self.assertFalse(row["in_scope"])
        self.assertEqual(row["note_code"], note.code)  # mã phiếu không phải dữ liệu cá nhân
        self.assertIsNone(row["phone"])
        self.assertIsNone(row["customer_name"])
        self.assertIsNone(row["address"])

    def test_l5_code_unknown_note_is_404_and_group_without_permission_does_not_see_it(self):
        _, _, note, _ = self._create_paid_order("DH-NC-3", "0904440003")
        self.assertEqual(client_for(self.cs1).get(f"{QUEUE}999999/").status_code, 404)
        res = client_for(make_user("nobody_nc")).get(f"{QUEUE}{note.pk}/")
        self.assertNotIn(note.code, res.content.decode())


class ConfirmationPermissionMessageTests(ConfirmationL2BaseTestCase):
    """QA 17b Low: câu lỗi quyền dùng tên chuẩn "Gọi xác nhận", không còn chữ "CSKH"."""

    def test_permission_messages_use_standard_name(self):
        self.warehouse_user = self.kho  # naming: allow - tên thuộc tính của ConfirmationL2BaseTestCase
        _, _, note, _ = self._create_paid_order("DH-NC-4", "0904440004")
        client = client_for(self.warehouse_user)
        calls = (
            client.get(QUEUE),
            client.get(f"{QUEUE}{note.pk}/"),
            client.post(f"{QUEUE}{note.pk}/claim/", {}, format="json"),
            client.post("/api/confirmation/search/", {"q": "x"}, format="json"),
        )
        for res in calls:
            self.assertEqual(res.status_code, 403, res.content)
            detail = res.json()["detail"]
            self.assertNotIn("CSKH", detail)
            self.assertIn("Gọi xác nhận", detail)
