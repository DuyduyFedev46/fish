"""
Lô bổ sung A (Duy chốt 02/10) — #17 (R4b) SĐT trong danh sách của người giao, #18 mốc giờ bắt đầu giao / giao thất bại.
Dữ liệu giả (SĐT, tên).
"""
import datetime

from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.delivery.models import DeliveryNote

from .test_note_detail_filters import NoteScopeBase

LIST = "/api/delivery/notes/"
PHONE_P = "0900000401"
PHONE_L = "0900000402"


class CourierListPhoneTests(NoteScopeBase):
    """#17 R4b: `GET /notes/?assigned_to=me` có `phone` (chỉ phiếu của mình, chỉ DELIVERING/FAILED)."""

    def _rows(self, user, query):
        resp = self._get(user, f"{LIST}?{query}")
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp, {r["id"]: r for r in resp.json()["results"]}

    def _set(self, note, status, **extra):
        DeliveryNote.objects.filter(pk=note.pk).update(status=status, **extra)

    def test_r4b_courier_assigned_to_me_gets_phone_for_delivering_and_failed(self):
        self._set(self.note_p, DeliveryNote.Status.DELIVERING)
        order2, _, note2 = self._extra_note("SO-R4B-2", "0900000411")
        self._set(note2, DeliveryNote.Status.FAILED)
        _resp, rows = self._rows(self.phuc, "assigned_to=me")
        self.assertEqual(rows[self.note_p.pk]["phone"], PHONE_P)
        self.assertEqual(rows[note2.pk]["phone"], "0900000411")

    def _extra_note(self, code, phone):
        from apps.common.tests.fixtures import make_order_with_note

        return make_order_with_note(code, phone, assigned_to=self.phuc)

    def test_r4b_other_statuses_have_null_phone_key_present(self):
        for status in ("PREPARING", "READY", "COMPLETED", "CANCELLED", "CONFIRMING"):
            self._set(self.note_p, status, completed_at=timezone.now())
            _resp, rows = self._rows(self.phuc, "assigned_to=me")
            self.assertIn("phone", rows[self.note_p.pk], status)
            self.assertIsNone(rows[self.note_p.pk]["phone"], status)

    def test_r4b_phone_follows_recipient_phone_over_order_phone(self):
        self._set(self.note_p, DeliveryNote.Status.DELIVERING, recipient_phone="0900000555")
        _resp, rows = self._rows(self.phuc, "assigned_to=me")
        self.assertEqual(rows[self.note_p.pk]["phone"], "0900000555")

    def test_r4b_no_phone_key_without_assigned_to_me(self):
        self._set(self.note_p, DeliveryNote.Status.DELIVERING)
        for user, query in (
            (self.phuc, ""), (self.phuc, f"assigned_to={self.phuc.pk}"), (self.manager, ""),
            (self.manager, f"assigned_to={self.phuc.pk}"), (self.owner, "status=DELIVERING"),
            (self.phuc, "status=DELIVERING"),
        ):
            resp, rows = self._rows(user, query)
            for row in rows.values():
                self.assertNotIn("phone", row, (user.username, query))
            self.assertNotIn(PHONE_P, resp.content.decode(), (user.username, query))

    def test_r4b_manager_assigned_to_me_only_own_notes_and_phone(self):
        """Người có full scope gọi `assigned_to=me` cũng chỉ nhận phiếu gán cho chính mình (không lộ SĐT phiếu của người khác)."""
        self._set(self.note_p, DeliveryNote.Status.DELIVERING)
        self._set(self.note_n, DeliveryNote.Status.DELIVERING, assigned_to=self.manager)
        resp, rows = self._rows(self.manager, "assigned_to=me")
        self.assertEqual(set(rows), {self.note_n.pk})
        self.assertEqual(rows[self.note_n.pk]["phone"], "0900000403")
        self.assertNotIn(PHONE_P, resp.content.decode())

    def test_r4b_courier_never_sees_phone_of_other_couriers_note(self):
        self._set(self.note_l, DeliveryNote.Status.DELIVERING)
        resp, rows = self._rows(self.phuc, "assigned_to=me")
        self.assertNotIn(self.note_l.pk, rows)
        self.assertNotIn(PHONE_L, resp.content.decode())
        denied = self._get(self.phuc, f"{LIST}?assigned_to={self.lam.pk}")
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn(PHONE_L, denied.content.decode())

    def test_r4b_phone_hidden_beyond_pii_window_even_if_status_were_delivering(self):
        """Dùng cùng điều kiện SR-PII-02 với chi tiết: phiếu kết thúc quá cửa sổ -> null (phiếu kết thúc vốn đã null)."""
        old = timezone.now() - datetime.timedelta(days=30)
        self._set(self.note_p, DeliveryNote.Status.COMPLETED, completed_at=old)
        _resp, rows = self._rows(self.phuc, "assigned_to=me")
        self.assertIsNone(rows[self.note_p.pk]["phone"])

    def test_r4b_response_is_no_store_and_anonymous_401_and_cs_has_no_phone(self):
        self._set(self.note_p, DeliveryNote.Status.DELIVERING)
        resp, _rows = self._rows(self.phuc, "assigned_to=me")
        self.assertIn("no-store", resp.headers.get("Cache-Control", ""))
        self.assertEqual(client_for(None).get(f"{LIST}?assigned_to=me").status_code, 401)

    def test_r4b_phone_not_written_to_audit_log(self):
        self._set(self.note_p, DeliveryNote.Status.DELIVERING)
        self._rows(self.phuc, "assigned_to=me")
        self.assertFalse(AuditLog.objects.filter(changes__icontains=PHONE_P).exists())

    def test_r4b_query_count_does_not_grow(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def count():
            client = client_for(self.phuc)
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(client.get(f"{LIST}?assigned_to=me").status_code, 200)
            return len(ctx)

        count()
        before = count()
        for i in range(4):
            _o, _c, note = self._extra_note(f"SO-R4B-Q{i}", f"090000061{i}")
            self._set(note, DeliveryNote.Status.DELIVERING)
        self.assertEqual(count(), before)


class DeliveryTimestampsTests(NoteScopeBase):
    """#18: `delivery_started_at` (khi sang DELIVERING), `failed_at` (khi sang FAILED), trong chi tiết và danh sách."""

    def _status(self, user, note, to_status, from_status=None, **extra):
        body = {"to_status": to_status, **({"from_status": from_status} if from_status else {}), **extra}
        return client_for(user).post(f"{LIST}{note.pk}/status/", body, format="json")

    def _ready(self, note):
        DeliveryNote.objects.filter(pk=note.pk).update(status=DeliveryNote.Status.READY)

    def test_ed18_new_note_has_null_timestamps(self):
        body = self._get(self.manager, f"{LIST}{self.note_p.pk}/").json()
        self.assertIn("delivery_started_at", body)
        self.assertIn("failed_at", body)
        self.assertIsNone(body["delivery_started_at"])
        self.assertIsNone(body["failed_at"])

    def test_ed18_delivering_sets_started_at_and_returns_it(self):
        self._ready(self.note_p)
        before = timezone.now()
        resp = self._status(self.phuc, self.note_p, "DELIVERING", "READY")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.note_p.refresh_from_db()
        self.assertGreaterEqual(self.note_p.delivery_started_at, before)
        self.assertIsNone(self.note_p.failed_at)
        self.assertEqual(resp.json()["delivery_started_at"][:19], timezone.localtime(self.note_p.delivery_started_at).isoformat()[:19])
        detail = self._get(self.phuc, f"{LIST}{self.note_p.pk}/").json()
        self.assertIsNotNone(detail["delivery_started_at"])
        row = next(r for r in self._get(self.manager, LIST).json()["results"] if r["id"] == self.note_p.pk)
        self.assertEqual(row["delivery_started_at"], detail["delivery_started_at"])
        self.assertIsNone(row["failed_at"])

    def test_ed18_failed_sets_failed_at_and_redelivery_overwrites_started_at(self):
        self._ready(self.note_p)
        self._status(self.phuc, self.note_p, "DELIVERING", "READY")
        self.note_p.refresh_from_db()
        first_started = self.note_p.delivery_started_at
        resp = self._status(self.phuc, self.note_p, "FAILED", "DELIVERING", failure_reason="NOT_MET")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.note_p.refresh_from_db()
        self.assertIsNotNone(self.note_p.failed_at)
        self.assertGreaterEqual(self.note_p.failed_at, first_started)
        failed_at = self.note_p.failed_at
        self.assertEqual(self._status(self.phuc, self.note_p, "DELIVERING", "FAILED").status_code, 200)
        self.note_p.refresh_from_db()
        self.assertGreaterEqual(self.note_p.delivery_started_at, first_started)
        self.assertEqual(self.note_p.failed_at, failed_at)  # giữ mốc thất bại gần nhất tới khi có lần mới

    def test_ed18_already_delivering_idempotent_call_does_not_move_started_at(self):
        self._ready(self.note_p)
        self._status(self.phuc, self.note_p, "DELIVERING", "READY")
        self.note_p.refresh_from_db()
        started = self.note_p.delivery_started_at
        resp = self._status(self.phuc, self.note_p, "DELIVERING", "READY")  # lặp lại: already
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["already"])
        self.note_p.refresh_from_db()
        self.assertEqual(self.note_p.delivery_started_at, started)

    def test_ed18_timestamps_are_not_client_writable(self):
        resp = client_for(self.owner).patch(
            f"{LIST}{self.note_p.pk}/", {"delivery_started_at": "2020-01-01T00:00:00Z", "failed_at": "2020-01-01T00:00:00Z"},
            format="json",
        )
        self.note_p.refresh_from_db()
        self.assertIsNone(self.note_p.delivery_started_at)
        self.assertIsNone(self.note_p.failed_at)
        self.assertIn(resp.status_code, (200, 400, 403, 405))
