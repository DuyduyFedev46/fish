"""
B5 (ED-18, BR-GH-22, BR-GH-04, ERP theo design Lô 4): báo giao thất bại phải có lý do.

`POST /api/delivery/notes/{id}/status/` với `to_status=FAILED` đòi `failure_reason` thuộc
NOT_MET / REFUSED / WRONG_ADDRESS / DAMAGED / OTHER; OTHER đòi `failure_note`. `failure_note` là chữ tự do,
có thể chứa dữ liệu cá nhân của khách (bất biến 9): không vào AuditLog, nhãn dòng thời gian, danh sách. Dữ liệu giả.
"""
import json

from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.ai.policy import rules as ai_rules
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import client_for, make_order_with_note, make_user
from apps.delivery import services
from apps.delivery.models import DeliveryNote

FREE_NOTE = "Khách Thử A hẹn lại, nhà số 12 hẻm Thử, gọi số phụ 0900-0099"
SECRET_PARTS = ("Khách Thử A hẹn lại", "nhà số 12 hẻm Thử", "0900-0099", "0900 0099")


class FailureReasonBase(TestCase):
    def setUp(self):
        self.courier = make_user("giao_a", roles.DELIVERY_STAFF)
        self.other = make_user("giao_b", roles.DELIVERY_STAFF)
        self.owner = make_user("chu_t", roles.OWNER)
        self.manager = make_user("ql_t", roles.MANAGER)
        self.warehouse = make_user("kho_t", roles.WAREHOUSE_STAFF)
        self.order, _, self.note = make_order_with_note("SO-F1", "0900000301", assigned_to=self.courier)
        self._delivering(self.note)

    def _delivering(self, note):
        note.status = DeliveryNote.Status.DELIVERING
        note.save(update_fields=["status"])

    def _fail(self, user=None, note=None, **fields):
        note = note or self.note
        body = {"to_status": "FAILED", "from_status": "DELIVERING", **fields}
        return client_for(user or self.courier).post(
            f"/api/delivery/notes/{note.pk}/status/", body, format="json"
        )

    def _assert_untouched(self):
        self.note.refresh_from_db()
        self.assertEqual(self.note.status, DeliveryNote.Status.DELIVERING)
        self.assertEqual(self.note.failed_attempts, 0)
        self.assertEqual(self.note.failure_reason, "")
        self.assertFalse(AuditLog.objects.filter(action="delivery_mark_failed").exists())


class FailureReasonContractTests(FailureReasonBase):
    def test_ed18_ac1_reason_and_note_are_saved(self):
        resp = self._fail(failure_reason="NOT_MET", failure_note="Gọi 3 lần không nghe máy")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], "FAILED")
        self.assertEqual(body["failed_attempts"], 1)
        self.assertEqual(body["failure_reason"], "NOT_MET")
        self.assertEqual(body["failure_reason_label"], "Không gặp khách")
        self.assertIn("needs_decision", body)
        self.note.refresh_from_db()
        self.assertEqual(self.note.failure_reason, "NOT_MET")
        self.assertEqual(self.note.failure_note, "Gọi 3 lần không nghe máy")

    def test_ed18_enum_codes_and_labels(self):
        expected = {
            "NOT_MET": "Không gặp khách",
            "REFUSED": "Khách từ chối nhận",
            "WRONG_ADDRESS": "Sai địa chỉ",
            "DAMAGED": "Hàng hư khi giao",
            "OTHER": "Khác",
        }
        self.assertEqual(dict(DeliveryNote.FailureReason.choices), expected)

    def test_ed18_each_reason_accepted(self):
        for code in ("NOT_MET", "REFUSED", "WRONG_ADDRESS", "DAMAGED"):
            self._delivering(self.note)
            resp = self._fail(failure_reason=code)
            self.assertEqual(resp.status_code, 200, f"{code}: {resp.content}")
            self.assertEqual(resp.json()["failure_reason"], code)

    def test_ed18_ac2_missing_reason_gets_400_and_nothing_changes(self):
        for fields in ({}, {"failure_reason": ""}, {"failure_reason": None}, {"failure_note": "Gọi không được"}):
            resp = self._fail(**fields)
            self.assertEqual(resp.status_code, 400, f"{fields}: {resp.content}")
            self.assertEqual(resp.json()["code"], "DELIVERY_FAILURE_REASON_REQUIRED")
        self._assert_untouched()

    def test_ed18_ac2_unknown_reason_gets_400(self):
        for value in ("CUSTOMER_ABSENT", "not_met", "XYZ", 5, ["NOT_MET"]):
            resp = self._fail(failure_reason=value)
            self.assertEqual(resp.status_code, 400, f"{value!r}: {resp.content}")
            self.assertEqual(resp.json()["code"], "DELIVERY_FAILURE_REASON_REQUIRED")
        self._assert_untouched()

    def test_ed18_other_requires_note(self):
        for note in (None, "", "   "):
            fields = {"failure_reason": "OTHER"}
            if note is not None:
                fields["failure_note"] = note
            resp = self._fail(**fields)
            self.assertEqual(resp.status_code, 400, f"{note!r}: {resp.content}")
            self.assertEqual(resp.json()["code"], "DELIVERY_FAILURE_NOTE_REQUIRED")
        self._assert_untouched()

    def test_ed18_other_with_note_is_accepted(self):
        resp = self._fail(failure_reason="OTHER", failure_note="Đường ngập, xe không vào được")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["failure_reason_label"], "Khác")

    def test_ed18_ac5_note_with_long_digit_run_is_rejected(self):
        """Dãy từ 9 chữ số (SĐT, số tài khoản) bị chặn như BR-GH-19, kể cả khi bị ngăn cách."""
        for note in ("Gọi 0900000123 không nghe", "gọi 0900 000 123", "0900.000.123", "090-000-0123"):
            resp = self._fail(failure_reason="NOT_MET", failure_note=note)
            self.assertEqual(resp.status_code, 400, f"{note!r}: {resp.content}")
            self.assertEqual(resp.json()["code"], "DELIVERY_FAILURE_NOTE_PII")
            self.assertNotIn("0900000123", resp.content.decode())  # không lặp lại nội dung đã gửi
        self._assert_untouched()

    def test_ed18_note_longer_than_200_or_not_text_is_rejected(self):
        for note in ("x" * 201, 12345, ["a"]):
            resp = self._fail(failure_reason="NOT_MET", failure_note=note)
            self.assertEqual(resp.status_code, 400, f"{note!r}: {resp.content}")
            self.assertEqual(resp.json()["code"], "DELIVERY_FAILURE_NOTE_INVALID")
        self._assert_untouched()

    def test_ed18_ac6_old_client_without_reason_still_gets_400(self):
        resp = client_for(self.courier).post(
            f"/api/delivery/notes/{self.note.pk}/status/", {"to_status": "FAILED"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self._assert_untouched()

    def test_ed18_ac3_second_failure_keeps_latest_reason_and_audit_has_every_attempt(self):
        self.assertEqual(self._fail(failure_reason="NOT_MET").status_code, 200)
        self._delivering(self.note)  # giao lại: lý do lần trước còn đó tới khi có lần mới
        self.note.refresh_from_db()
        self.assertEqual(self.note.failure_reason, "NOT_MET")
        resp = self._fail(failure_reason="REFUSED", failure_note="Khách bảo không đặt")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["failed_attempts"], 2)
        self.assertEqual(body["failure_reason"], "REFUSED")
        rows = AuditLog.objects.filter(action="delivery_mark_failed", object_id=str(self.note.pk)).order_by("id")
        self.assertEqual(
            [r.changes["failure_reason"] for r in rows],
            [{"to": "NOT_MET"}, {"to": "REFUSED"}],
        )
        self.assertEqual([r.changes["failed_attempts"] for r in rows], [{"to": 1}, {"to": 2}])

    def test_ed18_fields_are_locked_against_patch(self):
        for field in ("failure_reason", "failure_note"):
            resp = client_for(self.owner).patch(
                f"/api/delivery/notes/{self.note.pk}/", {field: "OTHER"}, format="json"
            )
            self.assertEqual(resp.status_code, 400, f"{field}: {resp.content}")
        self._assert_untouched()

    def test_ed18_ac4_other_courier_gets_404_and_nothing_changes(self):
        resp = self._fail(user=self.other, failure_reason="NOT_MET")
        self.assertEqual(resp.status_code, 404)
        self._assert_untouched()

    def test_ed18_unauthenticated_gets_401_and_no_permission_user_gets_403(self):
        resp = client_for(None).post(
            f"/api/delivery/notes/{self.note.pk}/status/",
            {"to_status": "FAILED", "failure_reason": "NOT_MET"}, format="json",
        )
        self.assertEqual(resp.status_code, 401)
        nobody = User.objects.create_user("khong_quyen", password="x")
        resp = self._fail(user=nobody, failure_reason="NOT_MET")
        self.assertEqual(resp.status_code, 403)
        self._assert_untouched()

    def test_ed18_list_and_detail_expose_reason_but_only_detail_has_note(self):
        self._fail(failure_reason="WRONG_ADDRESS", failure_note="Không thấy số nhà")
        listing = client_for(self.manager).get("/api/delivery/notes/?status=FAILED").json()
        row = listing["results"][0]
        self.assertEqual(row["failure_reason"], "WRONG_ADDRESS")
        self.assertEqual(row["failure_reason_label"], "Sai địa chỉ")
        self.assertNotIn("failure_note", row)
        detail = client_for(self.manager).get(f"/api/delivery/notes/{self.note.pk}/").json()
        self.assertEqual(detail["failure_note"], "Không thấy số nhà")
        fresh = make_order_with_note("SO-F9", "0900000399")[2]
        fresh_row = client_for(self.manager).get(f"/api/delivery/notes/{fresh.pk}/").json()
        self.assertEqual(fresh_row["failure_reason"], "")
        self.assertEqual(fresh_row["failure_reason_label"], "")

    def test_ed18_service_rejects_empty_reason_when_given_explicitly(self):
        with self.assertRaises(BusinessError) as ctx:
            services.mark_failed(note=self.note, actor=self.courier, reason="")
        self.assertEqual(ctx.exception.code, "DELIVERY_FAILURE_REASON_REQUIRED")

    def test_ed18_service_rereads_note_under_lock(self):
        """Phiếu đã bị đổi trạng thái sau khi đọc: dùng trạng thái mới trong khoá, không ghi đè."""
        stale = DeliveryNote.objects.get(pk=self.note.pk)
        DeliveryNote.objects.filter(pk=self.note.pk).update(status=DeliveryNote.Status.COMPLETED)
        with self.assertRaises(BusinessError):
            services.mark_failed(note=stale, actor=self.courier, reason="NOT_MET")
        self.note.refresh_from_db()
        self.assertEqual(self.note.status, DeliveryNote.Status.COMPLETED)
        self.assertEqual(self.note.failed_attempts, 0)


class FailureNotePrivacyTests(FailureReasonBase):
    """ED-18-AC5, bất biến 9: chữ tự do không đi vào AuditLog, dòng thời gian, danh sách đơn, AI."""

    def setUp(self):
        super().setUp()
        resp = self._fail(failure_reason="OTHER", failure_note=FREE_NOTE)
        self.assertEqual(resp.status_code, 200, resp.content)

    def _assert_clean(self, text, where):
        for part in SECRET_PARTS:
            self.assertNotIn(part, text, f"{where} rò: {part}")

    def test_ed18_ac5_audit_log_has_reason_code_but_not_the_note(self):
        rows = AuditLog.objects.filter(model_name="delivery.DeliveryNote", object_id=str(self.note.pk))
        self.assertTrue(rows.exists())
        for row in rows:
            dumped = json.dumps(row.changes, ensure_ascii=False) + row.note + row.object_repr
            self._assert_clean(dumped, f"AuditLog {row.action}")
        mark = rows.get(action="delivery_mark_failed")
        self.assertEqual(mark.changes["failure_reason"], {"to": "OTHER"})
        self.assertNotIn("failure_note", mark.changes)

    def test_ed18_ac5_delivery_guidance_timeline_is_clean(self):
        resp = client_for(self.owner).get(f"/api/guidance/delivery/{self.note.pk}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self._assert_clean(resp.content.decode(), "guidance delivery")

    def test_ed18_ac5_order_detail_timeline_guidance_and_list_are_clean(self):
        for path in (
            f"/api/sales/orders/{self.order.pk}/",
            f"/api/guidance/order/{self.order.pk}/",
            "/api/sales/orders/",
        ):
            resp = client_for(self.owner).get(path)
            self.assertEqual(resp.status_code, 200, f"{path}: {resp.content}")
            self._assert_clean(resp.content.decode(), path)

    def test_ed18_order_list_reason_uses_fixed_label_from_failure_reason(self):
        """Lô 3 đọc `failure_reason` của phiếu FAILED mới nhất: mã và nhãn khớp bộ enum của B5."""
        self._delivering(self.note)
        self.assertEqual(self._fail(failure_reason="DAMAGED").status_code, 200)
        rows = client_for(self.owner).get("/api/sales/orders/").json()["results"]
        row = next(r for r in rows if r["code"] == self.order.code)
        self.assertEqual(row["reason"], {"code": "DAMAGED", "label": "Hàng hư khi giao"})

    def test_ed18_ai_scrub_covers_failure_note(self):
        self.assertIn("failure_note", ai_rules.SCRUB_FREE_TEXT_KEYS)
        self.assertIn("failure_reason", ai_rules.SCRUB_FREE_TEXT_KEYS)

    def test_ed18_failure_note_not_logged(self):
        import logging

        records = []

        class Collect(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        handler = Collect(level=logging.DEBUG)
        root = logging.getLogger()
        old_level = root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            self._delivering(self.note)
            self.assertEqual(self._fail(failure_reason="OTHER", failure_note=FREE_NOTE).status_code, 200)
            self._delivering(self.note)
            self._fail(failure_reason="OTHER", failure_note="Gọi 0900000123 không nghe")  # bị chặn 400
        finally:
            root.removeHandler(handler)
            root.setLevel(old_level)
        self._assert_clean("\n".join(records), "log")
        self.assertNotIn("0900000123", "\n".join(records))
