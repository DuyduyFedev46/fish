"""
B6 (ED-16, BR-GH-23, ERP theo design Lô 4): giao / đổi người giao cho phiếu giao.

- `POST /api/delivery/notes/{id}/assign/` và `GET /api/delivery/deliverers/`.
- Quyền Tầng 2 `delivery.assign_deliverynote`: chỉ owner, manager (data migration 0006).
- T6: chỉ phiếu CONFIRMING / PREPARING / READY. T7: số `DELIVERING` + `READY` mỗi người.
Dữ liệu giả (SĐT 0900000xxx, tên "Khách …").
"""
import json

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase, override_settings

from apps.accounts import roles
from apps.accounts.models import AuditLog, StaffProfile
from apps.common.tests.fixtures import client_for, make_order_with_note, make_user
from apps.delivery import services
from apps.delivery.models import DeliveryNote

ASSIGN_PERM = "delivery.assign_deliverynote"


def _staff(username, display_name, *group_names, active=True):
    user = make_user(username, *group_names)
    StaffProfile.objects.create(user=user, phone="0900000999", display_name=display_name)
    if not active:
        user.is_active = False
        user.save(update_fields=["is_active"])
    return user


class AssignTestBase(TestCase):
    def setUp(self):
        self.owner = _staff("chu_t", "Chủ Thử", roles.OWNER)
        self.manager = _staff("ql_t", "Quản Lý Thử", roles.MANAGER)
        self.warehouse = _staff("kho_t", "Kho Thử", roles.WAREHOUSE_STAFF)
        self.service = _staff("cs_t", "CSKH Thử", roles.CUSTOMER_SERVICE)
        self.phuc = _staff("giao_phuc", "Anh Phúc", roles.DELIVERY_STAFF)
        self.lam = _staff("giao_lam", "Anh Lâm", roles.DELIVERY_STAFF)

    def _note(self, code="SO-A1", phone="0900000201", status=DeliveryNote.Status.PREPARING, assigned_to=None):
        _, _, note = make_order_with_note(code, phone, assigned_to=assigned_to)
        note.status = status
        note.save(update_fields=["status"])
        return note

    def _assign(self, user, note, assigned_to, **extra):
        body = {"assigned_to": assigned_to, **extra}
        return client_for(user).post(f"/api/delivery/notes/{note.pk}/assign/", body, format="json")


class PermissionGrantTests(AssignTestBase):
    def test_b6_permission_exists_and_only_owner_manager_have_it(self):
        perm = Permission.objects.get(content_type__app_label="delivery", codename="assign_deliverynote")
        holders = set(Group.objects.filter(permissions=perm).values_list("name", flat=True))
        self.assertEqual(holders, {roles.OWNER, roles.MANAGER})


class AssignHappyPathTests(AssignTestBase):
    def test_ed16_ac1_manager_assigns_and_courier_sees_note(self):
        """ED-16-AC1: Quản lý giao phiếu CONFIRMING/PREPARING/READY; người giao thấy phiếu; AuditLog ghi ID."""
        for i, st in enumerate(
            (DeliveryNote.Status.CONFIRMING, DeliveryNote.Status.PREPARING, DeliveryNote.Status.READY)
        ):
            note = self._note(f"SO-H{i}", f"090000030{i}", status=st)
            resp = self._assign(self.manager, note, self.phuc.pk)
            self.assertEqual(resp.status_code, 200, resp.content)
            body = resp.json()
            self.assertEqual(body["assigned_to"], self.phuc.pk)
            self.assertEqual(body["assigned_to_name"], "Anh Phúc")
            self.assertFalse(body["already"])
            note.refresh_from_db()
            self.assertEqual(note.assigned_to_id, self.phuc.pk)
            self.assertEqual(note.status, st)  # giao người không đổi trạng thái
            seen = client_for(self.phuc).get(f"/api/delivery/notes/{note.pk}/")
            self.assertEqual(seen.status_code, 200)

    def test_ed16_ac1_owner_can_assign(self):
        note = self._note()
        self.assertEqual(self._assign(self.owner, note, self.lam.pk).status_code, 200)

    def test_ed16_ac1_audit_has_ids_only(self):
        note = self._note("SO-AU", "0900000211")
        self._assign(self.manager, note, self.phuc.pk)
        row = AuditLog.objects.get(action="assign_deliverynote", object_id=str(note.pk))
        self.assertEqual(row.actor_id, self.manager.pk)
        self.assertEqual(row.changes, {"assigned_to": {"from": None, "to": self.phuc.pk}})
        dumped = json.dumps(row.changes) + row.note + row.object_repr
        for secret in ("Anh Phúc", "Khách SO-AU", "0900000211", "1 Cảng"):
            self.assertNotIn(secret, dumped)

    def test_ed16_ac2_reassign_moves_note_between_couriers(self):
        """ED-16-AC2: đổi từ Lâm sang Phúc; Lâm nhận 404, Phúc thấy phiếu (BR-PQ-12)."""
        note = self._note("SO-RE", "0900000212", assigned_to=self.lam)
        resp = self._assign(self.manager, note, self.phuc.pk, expected_assigned_to=self.lam.pk)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(client_for(self.lam).get(f"/api/delivery/notes/{note.pk}/").status_code, 404)
        self.assertEqual(client_for(self.phuc).get(f"/api/delivery/notes/{note.pk}/").status_code, 200)
        row = AuditLog.objects.get(action="assign_deliverynote", object_id=str(note.pk))
        self.assertEqual(row.changes, {"assigned_to": {"from": self.lam.pk, "to": self.phuc.pk}})

    def test_b6_same_assignee_is_idempotent_no_second_audit(self):
        note = self._note("SO-ID", "0900000213", assigned_to=self.phuc)
        resp = self._assign(self.manager, note, self.phuc.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["already"])
        self.assertFalse(AuditLog.objects.filter(action="assign_deliverynote").exists())

    def test_b6_available_actions_has_assign_only_for_holder_and_valid_status(self):
        prep = self._note("SO-AA1", "0900000214")
        body = client_for(self.manager).get(f"/api/delivery/notes/{prep.pk}/").json()
        self.assertIn("assign", body["available_actions"])
        body = client_for(self.warehouse).get(f"/api/delivery/notes/{prep.pk}/").json()
        self.assertNotIn("assign", body["available_actions"])
        busy = self._note("SO-AA2", "0900000215", status=DeliveryNote.Status.DELIVERING)
        body = client_for(self.manager).get(f"/api/delivery/notes/{busy.pk}/").json()
        self.assertNotIn("assign", body["available_actions"])
        confirming = self._note("SO-AA3", "0900000216", status=DeliveryNote.Status.CONFIRMING)
        body = client_for(self.manager).get(f"/api/delivery/notes/{confirming.pk}/").json()
        self.assertIn("assign", body["available_actions"])


class AssignRejectedTests(AssignTestBase):
    def test_ed16_ac6_roles_without_permission_get_403_and_data_unchanged(self):
        note = self._note("SO-P1", "0900000221")
        for user in (self.phuc, self.warehouse, self.service):
            resp = self._assign(user, note, self.lam.pk)
            self.assertEqual(resp.status_code, 403, f"{user.username}: {resp.content}")
        note.refresh_from_db()
        self.assertIsNone(note.assigned_to_id)
        self.assertFalse(AuditLog.objects.filter(action="assign_deliverynote").exists())

    def test_ed16_ac6_courier_assigned_to_note_still_403(self):
        note = self._note("SO-P2", "0900000222", assigned_to=self.phuc)
        self.assertEqual(self._assign(self.phuc, note, self.lam.pk).status_code, 403)

    def test_ed16_ac6_unauthenticated_gets_401(self):
        note = self._note("SO-P3", "0900000223")
        resp = client_for(None).post(
            f"/api/delivery/notes/{note.pk}/assign/", {"assigned_to": self.phuc.pk}, format="json"
        )
        self.assertEqual(resp.status_code, 401)

    def test_ed16_ac3_delivering_failed_completed_cancelled_get_400(self):
        for i, st in enumerate((
            DeliveryNote.Status.DELIVERING, DeliveryNote.Status.FAILED,
            DeliveryNote.Status.COMPLETED, DeliveryNote.Status.CANCELLED,
        )):
            note = self._note(f"SO-S{i}", f"090000023{i}", status=st, assigned_to=self.lam)
            resp = self._assign(self.manager, note, self.phuc.pk)
            self.assertEqual(resp.status_code, 400, f"{st}: {resp.content}")
            self.assertEqual(resp.json()["code"], "DELIVERY_ASSIGN_STATE")
            note.refresh_from_db()
            self.assertEqual(note.assigned_to_id, self.lam.pk)

    def test_ed16_ac4_assignee_not_in_delivery_staff_group_gets_400(self):
        note = self._note("SO-G1", "0900000241")
        for user in (self.warehouse, self.manager, self.service):
            resp = self._assign(self.manager, note, user.pk)
            self.assertEqual(resp.status_code, 400, f"{user.username}: {resp.content}")
            self.assertEqual(resp.json()["code"], "DELIVERY_ASSIGNEE_INVALID")
        note.refresh_from_db()
        self.assertIsNone(note.assigned_to_id)

    def test_ed16_ac4_inactive_assignee_gets_400(self):
        gone = _staff("giao_nghi", "Anh Nghỉ", roles.DELIVERY_STAFF, active=False)
        note = self._note("SO-G2", "0900000242")
        resp = self._assign(self.manager, note, gone.pk)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "DELIVERY_ASSIGNEE_INVALID")

    def test_ed16_ac4_missing_or_unknown_assignee_gets_400(self):
        note = self._note("SO-G3", "0900000243")
        for value in (None, 999999, "abc", True):
            resp = self._assign(self.manager, note, value)
            self.assertEqual(resp.status_code, 400, f"{value!r}: {resp.content}")
            self.assertEqual(resp.json()["code"], "DELIVERY_ASSIGNEE_INVALID")
        resp = client_for(self.manager).post(f"/api/delivery/notes/{note.pk}/assign/", {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_b6_unknown_note_gets_404(self):
        resp = client_for(self.manager).post(
            "/api/delivery/notes/987654/assign/", {"assigned_to": self.phuc.pk}, format="json"
        )
        self.assertEqual(resp.status_code, 404)


class AssignConcurrencyTests(AssignTestBase):
    def test_b6_stale_expected_assignee_gets_409_and_first_writer_wins(self):
        """Hai người cùng giao phiếu chưa có người giao (expected null): chỉ người đến trước thành công."""
        note = self._note("SO-C1", "0900000251")
        first = self._assign(self.manager, note, self.phuc.pk, expected_assigned_to=None)
        second = self._assign(self.owner, note, self.lam.pk, expected_assigned_to=None)
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.status_code, 409, second.content)
        self.assertEqual(second.json()["code"], "STALE_STATE")
        note.refresh_from_db()
        self.assertEqual(note.assigned_to_id, self.phuc.pk)
        self.assertEqual(AuditLog.objects.filter(action="assign_deliverynote").count(), 1)

    def test_b6_expected_matches_current_allows_change(self):
        note = self._note("SO-C2", "0900000252", assigned_to=self.lam)
        resp = self._assign(self.manager, note, self.phuc.pk, expected_assigned_to=self.lam.pk)
        self.assertEqual(resp.status_code, 200)

    def test_b6_expected_assigned_to_wrong_type_gets_400_not_409(self):
        """Chuỗi, số âm, 0, bool, số quá int64, danh sách: 400, không rơi xuống nhánh 409."""
        note = self._note("SO-C5", "0900000256", assigned_to=self.lam)
        for bad in (str(self.lam.pk), "abc", "", 0, -1, True, 1.5, [self.lam.pk], 2**63):
            resp = self._assign(self.manager, note, self.phuc.pk, expected_assigned_to=bad)
            self.assertEqual(resp.status_code, 400, f"{bad!r}: {resp.content}")
            self.assertEqual(resp.json()["code"], "DELIVERY_ASSIGNEE_INVALID", repr(bad))
        note.refresh_from_db()
        self.assertEqual(note.assigned_to_id, self.lam.pk)
        self.assertFalse(AuditLog.objects.filter(action="assign_deliverynote").exists())

    def test_b6_assigned_to_beyond_int64_gets_400(self):
        note = self._note("SO-C6", "0900000257")
        resp = self._assign(self.manager, note, 2**63)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "DELIVERY_ASSIGNEE_INVALID")

    def test_b6_omitting_expected_skips_the_check(self):
        note = self._note("SO-C3", "0900000253", assigned_to=self.lam)
        self.assertEqual(self._assign(self.manager, note, self.phuc.pk).status_code, 200)

    def test_b6_service_rereads_note_under_lock_stale_object_cannot_overwrite(self):
        """Service đọc lại phiếu có khoá: đối tượng cũ (status/assigned_to lỗi thời) không ghi đè được."""
        note = self._note("SO-C4", "0900000254")
        stale = DeliveryNote.objects.get(pk=note.pk)
        DeliveryNote.objects.filter(pk=note.pk).update(status=DeliveryNote.Status.DELIVERING)
        from apps.common.exceptions import BusinessError

        with self.assertRaises(BusinessError) as ctx:
            services.assign_deliverer(
                note=stale, assignee=self.phuc, expected_assignee_id=None, actor=self.manager
            )
        self.assertEqual(ctx.exception.code, "DELIVERY_ASSIGN_STATE")


class DeliverersListTests(AssignTestBase):
    def test_ed16_ac5_counts_and_only_active_delivery_staff(self):
        _staff("giao_nghi", "Anh Nghỉ", roles.DELIVERY_STAFF, active=False)
        for i in range(2):
            self._note(f"SO-D{i}", f"090000026{i}", status=DeliveryNote.Status.DELIVERING, assigned_to=self.lam)
        self._note("SO-D2", "0900000263", status=DeliveryNote.Status.COMPLETED, assigned_to=self.lam)
        self._note("SO-D3", "0900000264", status=DeliveryNote.Status.READY, assigned_to=self.phuc)
        self._note("SO-D4", "0900000265", status=DeliveryNote.Status.PREPARING, assigned_to=self.phuc)

        resp = client_for(self.manager).get("/api/delivery/deliverers/")
        self.assertEqual(resp.status_code, 200, resp.content)
        rows = {r["display_name"]: r for r in resp.json()}
        self.assertEqual(set(rows), {"Anh Phúc", "Anh Lâm"})
        self.assertEqual(rows["Anh Lâm"]["delivering_count"], 2)
        self.assertEqual(rows["Anh Lâm"]["ready_count"], 0)
        self.assertEqual(rows["Anh Phúc"]["delivering_count"], 0)
        self.assertEqual(rows["Anh Phúc"]["ready_count"], 1)
        self.assertEqual(rows["Anh Phúc"]["id"], self.phuc.pk)

    def test_ed16_ac5_response_has_no_phone_or_username(self):
        resp = client_for(self.owner).get("/api/delivery/deliverers/")
        self.assertEqual(resp.status_code, 200)
        for row in resp.json():
            self.assertEqual(set(row), {"id", "display_name", "delivering_count", "ready_count"})
        text = resp.content.decode()
        self.assertNotIn("0900000999", text)
        self.assertNotIn("giao_phuc", text)

    def test_b6_deliverers_query_count_does_not_grow_with_people(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def count():
            client = client_for(self.manager)
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(client.get("/api/delivery/deliverers/").status_code, 200)
            return len(ctx)

        count()  # lượt làm nóng: cache quyền, ContentType
        before = count()
        for i in range(4):
            _staff(f"giao_more{i}", f"Anh Thêm {i}", roles.DELIVERY_STAFF)
        self.assertEqual(count(), before)

    def test_ed16_ac6_deliverers_forbidden_for_other_roles(self):
        for user in (self.phuc, self.warehouse, self.service):
            self.assertEqual(client_for(user).get("/api/delivery/deliverers/").status_code, 403, user.username)
        self.assertEqual(client_for(None).get("/api/delivery/deliverers/").status_code, 401)

    @override_settings(AI_ENABLED=True)
    def test_ed16_ac6_ai_command_index_lists_deliverers_only_for_holders_of_the_permission(self):
        """M1 (techlead): lệnh AI `delivery.deliverers` kế thừa `required_perms` của view."""
        def ids(user):
            resp = client_for(user).get("/api/ai/commands/index/")
            self.assertEqual(resp.status_code, 200, resp.content)
            return [c["id"] for c in resp.json()["commands"]]

        cs = make_user("cs_ai_idx", roles.CUSTOMER_SERVICE)
        for user in (self.phuc, cs):
            self.assertNotIn("delivery.deliverers", ids(user), user.username)
        for user in (self.manager, self.owner):
            self.assertIn("delivery.deliverers", ids(user), user.username)

    def test_b6_deliverers_is_read_only(self):
        self.assertEqual(client_for(self.manager).post("/api/delivery/deliverers/", {}, format="json").status_code, 405)
