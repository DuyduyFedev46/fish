"""
R4 (ERP theo design Lô 4, 02b §3.7, §3.8, bất biến 9 và 1): phiếu giao chi tiết có SĐT đủ cho người trong phạm vi,
tem giữ che; lọc `assigned_to=me|<id>`, `order=<id>`; `assigned_to_name`. Dữ liệu giả.
"""
import datetime

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.models import StaffProfile
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_order_with_note, make_user
from apps.delivery.models import DeliveryNote


def _walk_keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk_keys(v)


class NoteScopeBase(TestCase):
    def setUp(self):
        self.owner = make_user("chu_t", roles.OWNER)
        self.manager = make_user("ql_t", roles.MANAGER)
        self.warehouse = make_user("kho_t", roles.WAREHOUSE_STAFF)
        self.phuc = make_user("giao_phuc", roles.DELIVERY_STAFF)
        self.lam = make_user("giao_lam", roles.DELIVERY_STAFF)
        StaffProfile.objects.create(user=self.phuc, phone="0900000998", display_name="Anh Phúc")
        StaffProfile.objects.create(user=self.lam, phone="0900000997", display_name="Anh Lâm")
        self.order_p, _, self.note_p = make_order_with_note("SO-R1", "0900000401", assigned_to=self.phuc)
        self.order_l, _, self.note_l = make_order_with_note("SO-R2", "0900000402", assigned_to=self.lam)
        self.order_n, _, self.note_n = make_order_with_note("SO-R3", "0900000403")  # chưa giao cho ai

    def _get(self, user, path):
        return client_for(user).get(path)


class PhoneInDetailTests(NoteScopeBase):
    def test_r4_detail_has_full_phone_for_people_in_scope(self):
        for user in (self.owner, self.manager, self.warehouse):
            resp = self._get(user, f"/api/delivery/notes/{self.note_p.pk}/")
            self.assertEqual(resp.status_code, 200, user.username)
            self.assertEqual(resp.json()["phone"], "0900000401", user.username)

    def test_r4_assigned_courier_sees_full_phone_of_own_note(self):
        resp = self._get(self.phuc, f"/api/delivery/notes/{self.note_p.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["phone"], "0900000401")

    def test_r4_recipient_phone_wins_over_order_phone(self):
        self.note_p.recipient_phone = "0900000555"
        self.note_p.save(update_fields=["recipient_phone"])
        resp = self._get(self.manager, f"/api/delivery/notes/{self.note_p.pk}/")
        self.assertEqual(resp.json()["phone"], "0900000555")

    def test_r4_other_courier_gets_404_not_the_phone(self):
        resp = self._get(self.lam, f"/api/delivery/notes/{self.note_p.pk}/")
        self.assertEqual(resp.status_code, 404)
        self.assertNotIn("0900000401", resp.content.decode())

    def test_r4_courier_past_pii_window_gets_null_phone_and_note(self):
        """SR-PII-02: phiếu đã kết thúc quá cửa sổ thì `phone`, `failure_note` ẩn bằng null, khoá JSON còn."""
        old = timezone.now() - datetime.timedelta(days=30)
        DeliveryNote.objects.filter(pk=self.note_p.pk).update(
            status=DeliveryNote.Status.COMPLETED, completed_at=old, failure_note="Ghi chú cũ"
        )
        body = self._get(self.phuc, f"/api/delivery/notes/{self.note_p.pk}/").json()
        self.assertIn("phone", body)
        self.assertIsNone(body["phone"])
        self.assertIsNone(body["failure_note"])
        self.assertIsNone(body["customer_name"])
        # người full scope vẫn thấy
        self.assertEqual(self._get(self.manager, f"/api/delivery/notes/{self.note_p.pk}/").json()["phone"], "0900000401")

    def test_r4_list_does_not_carry_phone(self):
        rows = self._get(self.manager, "/api/delivery/notes/").json()["results"]
        self.assertTrue(rows)
        for row in rows:
            self.assertNotIn("phone", row)
            self.assertNotIn("recipient_phone", row)

    def test_r4_label_still_masks_phone(self):
        DeliveryNote.objects.filter(pk=self.note_p.pk).update(status=DeliveryNote.Status.PREPARING)
        resp = self._get(self.warehouse, f"/api/delivery/notes/{self.note_p.pk}/label/")
        self.assertEqual(resp.status_code, 200, resp.content)
        raw = resp.content.decode()
        self.assertNotIn("0900000401", raw)
        self.assertIn("09xx xxx 401", raw)

    def test_r4_detail_is_no_store(self):
        resp = self._get(self.manager, f"/api/delivery/notes/{self.note_p.pk}/")
        self.assertIn("no-store", resp.headers.get("Cache-Control", ""))

    def test_r4_unauthenticated_gets_401(self):
        self.assertEqual(self._get(None, f"/api/delivery/notes/{self.note_p.pk}/").status_code, 401)

    def test_r4_no_cost_keys_for_warehouse_and_manager(self):
        for user in (self.warehouse, self.manager):
            for path in (f"/api/delivery/notes/{self.note_p.pk}/", "/api/delivery/notes/"):
                payload = self._get(user, path).json()
                leaked = set(_walk_keys(payload)) & COST_KEYS
                self.assertEqual(leaked, set(), f"{user.username} {path}: {leaked}")

    def test_r4_delete_is_not_allowed(self):
        resp = client_for(self.owner).delete(f"/api/delivery/notes/{self.note_p.pk}/")
        self.assertEqual(resp.status_code, 405)


class ListFilterTests(NoteScopeBase):
    def _ids(self, user, query):
        resp = self._get(user, f"/api/delivery/notes/?{query}")
        self.assertEqual(resp.status_code, 200, resp.content)
        return {r["id"] for r in resp.json()["results"]}

    def test_r4_assigned_to_me_for_courier_and_manager(self):
        self.assertEqual(self._ids(self.phuc, "assigned_to=me"), {self.note_p.pk})
        self.note_n.assigned_to = self.manager
        self.note_n.save(update_fields=["assigned_to"])
        self.assertEqual(self._ids(self.manager, "assigned_to=me"), {self.note_n.pk})

    def test_r4_assigned_to_id_for_full_scope(self):
        self.assertEqual(self._ids(self.manager, f"assigned_to={self.lam.pk}"), {self.note_l.pk})
        self.assertEqual(self._ids(self.warehouse, f"assigned_to={self.phuc.pk}"), {self.note_p.pk})

    def test_r4_courier_can_pass_own_id_but_not_someone_elses(self):
        self.assertEqual(self._ids(self.phuc, f"assigned_to={self.phuc.pk}"), {self.note_p.pk})
        resp = self._get(self.phuc, f"/api/delivery/notes/?assigned_to={self.lam.pk}")
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn("0900000402", resp.content.decode())

    def test_r4_invalid_filters_get_400(self):
        oversized = "9223372036854775808"  # int64 max + 1
        for query in (
            "assigned_to=abc", "assigned_to=0", "assigned_to=-3", "order=abc", "order=0",
            "assigned_to=%2B5", f"order={oversized}", f"assigned_to={oversized}",
            "assigned_to=99999999999999999999999",
            "order=" + "1" * 5000, "assigned_to=" + "1" * 5000,   # quá giới hạn chuyển chuỗi sang số
            "order=%EF%BC%91%EF%BC%92", "assigned_to=%EF%BC%91%EF%BC%92",  # chữ số toàn độ rộng
        ):
            resp = self._get(self.manager, f"/api/delivery/notes/?{query}")
            self.assertEqual(resp.status_code, 400, f"{query}: {resp.content}")
            self.assertEqual(resp.json()["code"], "INVALID_FILTER")

    def test_r4_empty_filter_value_means_no_filter(self):
        self.assertEqual(len(self._ids(self.manager, "assigned_to=&order=")), 3)

    def test_r4_filter_by_order(self):
        self.assertEqual(self._ids(self.manager, f"order={self.order_l.pk}"), {self.note_l.pk})
        self.assertEqual(self._ids(self.manager, "order=999999"), set())

    def test_r4_filter_by_order_respects_courier_scope(self):
        self.assertEqual(self._ids(self.phuc, f"order={self.order_l.pk}"), set())

    def test_r4_filters_combine_with_status(self):
        DeliveryNote.objects.filter(pk=self.note_p.pk).update(status=DeliveryNote.Status.DELIVERING)
        self.assertEqual(self._ids(self.manager, f"assigned_to={self.phuc.pk}&status=DELIVERING"), {self.note_p.pk})
        self.assertEqual(self._ids(self.manager, f"assigned_to={self.phuc.pk}&status=READY"), set())


class AssignedNameTests(NoteScopeBase):
    def test_r4_list_and_detail_have_assigned_to_name(self):
        rows = {r["id"]: r for r in self._get(self.manager, "/api/delivery/notes/").json()["results"]}
        self.assertEqual(rows[self.note_p.pk]["assigned_to_name"], "Anh Phúc")
        self.assertEqual(rows[self.note_l.pk]["assigned_to_name"], "Anh Lâm")
        self.assertIsNone(rows[self.note_n.pk]["assigned_to_name"])
        detail = self._get(self.manager, f"/api/delivery/notes/{self.note_l.pk}/").json()
        self.assertEqual(detail["assigned_to_name"], "Anh Lâm")

    def test_r4_name_falls_back_to_username_when_no_profile(self):
        bare = make_user("giao_tran", roles.DELIVERY_STAFF)
        self.note_n.assigned_to = bare
        self.note_n.save(update_fields=["assigned_to"])
        detail = self._get(self.manager, f"/api/delivery/notes/{self.note_n.pk}/").json()
        self.assertEqual(detail["assigned_to_name"], "giao_tran")

    def test_r4_list_query_count_does_not_grow_with_notes(self):
        def count():
            client = client_for(self.manager)
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(client.get("/api/delivery/notes/").status_code, 200)
            return len(ctx)

        count()  # lượt làm nóng: cache quyền, ContentType
        before = count()
        for i in range(4):
            user = make_user(f"giao_x{i}", roles.DELIVERY_STAFF)
            StaffProfile.objects.create(user=user, phone="0900000996", display_name=f"Anh X{i}")
            make_order_with_note(f"SO-X{i}", f"090000050{i}", assigned_to=user)
        self.assertEqual(count(), before)
