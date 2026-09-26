"""
Bug fix B-DELIVERY-MARKFAILED (04-qa-report.md, lô L9): `set_status` gán thẳng tuple
`(note, needs_decision)` của `services.mark_failed` vào serializer khi `to_status=FAILED`,
làm hỏng JSON trả về (`assigned_to`/`completed_at` bị None sai). Test HTTP cho mọi nhánh
`to_status` của `POST /api/delivery/notes/{id}/status/` để đảm bảo body luôn đúng, không
chỉ nhánh FAILED.
"""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.tests.fixtures import make_order_with_note
from apps.delivery.models import DeliveryNote


class SetStatusHttpTests(TestCase):
    """BR-GH-04/05/06 — mọi nhánh `to_status` của action `set_status` qua HTTP."""

    def setUp(self):
        self.nv_giao = User.objects.create_user("giao1", password="x")
        self.nv_giao.groups.add(Group.objects.get(name="nv_giao"))
        self.nv_giao2 = User.objects.create_user("giao2", password="x")
        self.nv_giao2.groups.add(Group.objects.get(name="nv_giao"))
        self.client = APIClient()
        self.client.force_authenticate(self.nv_giao)

    def _url(self, note):
        return f"/api/delivery/notes/{note.pk}/status/"

    def _post(self, note, to_status):
        return self.client.post(self._url(note), {"to_status": to_status}, format="json")

    def test_ac_ready_returns_full_note_json(self):
        """PREPARING -> READY (nhánh advance_status) — body đầy đủ, không lỗi."""
        _, _, note = make_order_with_note("SO-R1", "0900000101", assigned_to=self.nv_giao)
        resp = self._post(note, DeliveryNote.Status.READY)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], DeliveryNote.Status.READY)
        self.assertEqual(body["assigned_to"], self.nv_giao.pk)

    def test_ac_delivering_returns_full_note_json(self):
        """READY -> DELIVERING — body đầy đủ, không lỗi."""
        _, _, note = make_order_with_note("SO-R2", "0900000102", assigned_to=self.nv_giao)
        note.status = DeliveryNote.Status.READY
        note.save(update_fields=["status"])
        resp = self._post(note, DeliveryNote.Status.DELIVERING)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], DeliveryNote.Status.DELIVERING)
        self.assertEqual(body["assigned_to"], self.nv_giao.pk)
        self.assertIsNone(body["completed_at"])

    def test_ac_completed_returns_full_note_json_with_completed_at(self):
        """DELIVERING -> COMPLETED — completed_at phải có giá trị, assigned_to giữ nguyên."""
        _, _, note = make_order_with_note("SO-R3", "0900000103", assigned_to=self.nv_giao)
        note.status = DeliveryNote.Status.DELIVERING
        note.save(update_fields=["status"])
        resp = self._post(note, DeliveryNote.Status.COMPLETED)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], DeliveryNote.Status.COMPLETED)
        self.assertEqual(body["assigned_to"], self.nv_giao.pk)
        self.assertIsNotNone(body["completed_at"])

    def test_ac_failed_returns_full_note_json_not_broken(self):
        """Tái hiện bug B-DELIVERY-MARKFAILED: to_status=FAILED không được hỏng
        assigned_to/completed_at do gán nguyên tuple (note, needs_decision) vào serializer."""
        _, _, note = make_order_with_note("SO-R4", "0900000104", assigned_to=self.nv_giao)
        note.status = DeliveryNote.Status.DELIVERING
        note.save(update_fields=["status"])
        resp = self._post(note, DeliveryNote.Status.FAILED)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], DeliveryNote.Status.FAILED)
        self.assertEqual(body["assigned_to"], self.nv_giao.pk)  # trước đây bị None sai
        self.assertEqual(body["failed_attempts"], 1)

    def test_ac_failed_adds_needs_decision_key_after_threshold(self):
        """Vượt ngưỡng thất bại -> thêm khoá `needs_decision` (BR-GH-04), không đổi
        các khoá khác của contract hiện có."""
        with self.settings(DELIVERY_MAX_FAILED_ATTEMPTS=2):
            _, _, note = make_order_with_note("SO-R5", "0900000105", assigned_to=self.nv_giao)
            note.status = DeliveryNote.Status.DELIVERING
            note.save(update_fields=["status"])
            self._post(note, DeliveryNote.Status.FAILED)
            note.status = DeliveryNote.Status.DELIVERING
            note.save(update_fields=["status"])
            resp = self._post(note, DeliveryNote.Status.FAILED)
            self.assertEqual(resp.status_code, 200, resp.content)
            body = resp.json()
            self.assertEqual(body["failed_attempts"], 2)
            self.assertIn("needs_decision", body)
            self.assertTrue(body["needs_decision"])

    def test_ac_failed_needs_decision_false_below_threshold(self):
        with self.settings(DELIVERY_MAX_FAILED_ATTEMPTS=2):
            _, _, note = make_order_with_note("SO-R6", "0900000106", assigned_to=self.nv_giao)
            note.status = DeliveryNote.Status.DELIVERING
            note.save(update_fields=["status"])
            resp = self._post(note, DeliveryNote.Status.FAILED)
            body = resp.json()
            self.assertIn("needs_decision", body)
            self.assertFalse(body["needs_decision"])

    def test_ac_invalid_transition_returns_400(self):
        """PREPARING -> COMPLETED không hợp lệ -> 400 BusinessError."""
        _, _, note = make_order_with_note("SO-R7", "0900000107", assigned_to=self.nv_giao)
        resp = self._post(note, DeliveryNote.Status.COMPLETED)
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_ac_perm_unauthenticated_returns_401(self):
        _, _, note = make_order_with_note("SO-R8", "0900000108", assigned_to=self.nv_giao)
        client = APIClient()
        resp = client.post(self._url(note), {"to_status": DeliveryNote.Status.READY}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_ac_perm_other_nv_giao_gets_404_not_403(self):
        """BR-GH-06/BR-PQ-12: nv_giao khác không thấy phiếu (scope dòng) -> 404, không rò trạng thái."""
        _, _, note = make_order_with_note("SO-R9", "0900000109", assigned_to=self.nv_giao)
        client = APIClient()
        client.force_authenticate(self.nv_giao2)
        resp = client.post(
            f"/api/delivery/notes/{note.pk}/status/",
            {"to_status": DeliveryNote.Status.READY},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)
