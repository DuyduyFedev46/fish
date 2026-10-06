"""
TL15-audit (Lô 17a, A3, ED-41-AC2): GET /api/audit-logs/?date_from=&date_to=&q=

- Ngày theo giờ Việt Nam: dòng 23:59 VN ngày D thuộc D, 00:00 VN ngày D+1 không thuộc D.
- Sai ngày, hoặc date_from > date_to → 400 INVALID_FILTER.
- `q` chỉ tìm theo mã chứng từ (2–40 ký tự `[0-9A-Za-z#._-]`); dãy từ 9 chữ số trở lên (có thể là SĐT) → 400;
  câu lỗi không lặp lại `q` (bất biến 9). Dữ liệu giả.
"""
import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.common.audit import record_audit
from apps.common.tests.fixtures import client_for, make_user

URL = "/api/audit-logs/"
VN = ZoneInfo("Asia/Ho_Chi_Minh")


def at(day, hour, minute):
    return datetime.datetime(2026, 10, day, hour, minute, tzinfo=VN)


@override_settings(AI_ENABLED=True)
class AuditDateAndCodeFilterTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner1", roles.OWNER)
        self.warehouse_staff = make_user("kho1", roles.WAREHOUSE_STAFF)
        self.client = client_for(self.owner)

    def make_row(self, when, *, repr_="", proposal_ref="", action="close_batch", **kwargs):
        row = AuditLog.objects.create(
            action=action, actor=self.owner, object_repr=repr_, proposal_ref=proposal_ref, **kwargs,
        )
        AuditLog.objects.filter(pk=row.pk).update(created_at=when)  # created_at là auto_now_add
        return row

    def ids(self, params):
        response = self.client.get(URL, params)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["count"], len(body["results"]))  # ít hơn 1 trang
        return {r["id"] for r in body["results"]}

    def test_tl15_audit_date_boundaries_use_vietnam_time(self):
        end_of_day = self.make_row(at(5, 23, 59))
        next_midnight = self.make_row(at(6, 0, 0))
        start_of_day = self.make_row(at(5, 0, 0))
        before = self.make_row(at(4, 23, 59))
        self.assertEqual(self.ids({"date_from": "2026-10-05", "date_to": "2026-10-05"}), {end_of_day.pk, start_of_day.pk})
        self.assertEqual(self.ids({"date_from": "2026-10-06"}), {next_midnight.pk})
        self.assertEqual(self.ids({"date_to": "2026-10-04"}), {before.pk})

    def test_tl15_audit_count_matches_filtered_rows_before_pagination(self):
        for minute in range(25):
            self.make_row(at(7, 8, minute))
        self.make_row(at(8, 8, 0))
        body = self.client.get(URL, {"date_from": "2026-10-07", "date_to": "2026-10-07"}).json()
        self.assertEqual(body["count"], 25)
        self.assertEqual(len(body["results"]), 20)

    def test_tl15_audit_invalid_dates_and_inverted_range_are_400(self):
        for params in (
            {"date_from": "05/10/2026"}, {"date_to": "2026-13-40"}, {"date_from": "abc"},
            {"date_from": "2026-10-06", "date_to": "2026-10-05"},
        ):
            response = self.client.get(URL, params)
            self.assertEqual(response.status_code, 400, params)
            self.assertEqual(response.json()["code"], "INVALID_FILTER", params)

    def test_m2_extreme_or_loose_dates_are_400_not_500(self):
        for name in ("date_from", "date_to"):
            for raw in ("9999-12-31", "0001-01-01", "1999-12-31", "2101-01-01", "20261007", "2026-W41-1", "２０２６-10-07"):
                response = self.client.get(URL, {name: raw})
                self.assertEqual(response.status_code, 400, (name, raw))
                self.assertEqual(response.json()["code"], "INVALID_FILTER", (name, raw))

    def test_m2_boundary_years_2000_and_2100_are_accepted(self):
        self.assertEqual(self.client.get(URL, {"date_from": "2000-01-01", "date_to": "2100-12-31"}).status_code, 200)

    def test_tl15_audit_q_matches_object_repr_and_proposal_ref_case_insensitive(self):
        by_repr = self.make_row(at(5, 9, 0), repr_="B-261005-01")
        by_ref = self.make_row(at(5, 9, 1), proposal_ref="AI-PROP-77")
        self.make_row(at(5, 9, 2), repr_="B-261005-02")
        self.assertEqual(self.ids({"q": "261005-01"}), {by_repr.pk})
        self.assertEqual(self.ids({"q": "ai-prop-77"}), {by_ref.pk})

    def test_tl15_audit_q_with_spaces_accents_or_bad_length_is_400(self):
        for raw in ("a b", "mã lô", "x", "a" * 41, "B-26;DROP", "<b>"):
            response = self.client.get(URL, {"q": raw})
            self.assertEqual(response.status_code, 400, raw)
            self.assertEqual(response.json()["code"], "INVALID_FILTER", raw)

    def test_tl15_audit_q_with_nine_or_more_digits_is_400_and_not_echoed(self):
        for raw in ("0900000123", "123456789", "SO-0900000123", "9" * 12):
            response = self.client.get(URL, {"q": raw})
            self.assertEqual(response.status_code, 400, raw)
            body = response.json()
            self.assertEqual(body["detail"], "Chỉ tìm theo mã chứng từ.")
            self.assertNotIn(raw, response.content.decode())

    def test_tl15_audit_q_with_up_to_eight_digits_is_allowed(self):
        row = self.make_row(at(5, 9, 0), repr_="KK-12345678")
        self.assertEqual(self.ids({"q": "12345678"}), {row.pk})

    def test_tl15_audit_filters_combine_with_existing_ones(self):
        keep = self.make_row(at(5, 9, 0), repr_="B-1", action="close_batch")
        self.make_row(at(5, 9, 1), repr_="B-1", action="publish_batch")
        self.make_row(at(6, 9, 1), repr_="B-1", action="close_batch")
        self.assertEqual(
            self.ids({"q": "B-1", "action": "close_batch", "date_from": "2026-10-05", "date_to": "2026-10-05"}),
            {keep.pk},
        )

    def test_tl15_audit_permission_403_and_401_unchanged(self):
        self.assertEqual(client_for(self.warehouse_staff).get(URL, {"q": "B-1"}).status_code, 403)
        self.assertEqual(client_for(None).get(URL, {"q": "B-1"}).status_code, 401)

    @override_settings(AI_ENABLED=False)
    def test_tl15_audit_filters_still_hide_ai_rows_when_ai_off(self):
        user_row = self.make_row(at(5, 9, 0), repr_="B-9")
        record_audit("propose_x", actor_kind="ai", ai_actor=self.owner, proposal_ref="B-9")
        AuditLog.objects.filter(actor_kind="ai").update(created_at=at(5, 9, 5), object_repr="B-9")
        self.assertEqual(self.ids({"q": "B-9", "date_from": "2026-10-05", "date_to": "2026-10-05"}), {user_row.pk})
