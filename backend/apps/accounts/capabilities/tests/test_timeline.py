"""B4 · ED-39 — dòng thời gian của nhóm (chi tiết nhóm + guidance `group`), bất biến 9 (không dữ liệu cá nhân)."""
from django.contrib.auth.models import Group
from django.test import TestCase

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user

from .base import detail_url, make_staff, put_url


class GroupTimelineTests(TestCase):
    def setUp(self):
        self.owner = make_staff("owner1", roles.OWNER, display_name="Chủ Thử")
        self.manager = make_staff("manager1", roles.MANAGER, display_name="Quản Lý Thử")
        self.warehouse = make_staff("kho1", roles.WAREHOUSE_STAFF, display_name="Kho Thử")
        self.client = client_for(self.owner)

    def change(self, code, changes):
        self.assertEqual(
            self.client.put(put_url(code), {"capabilities": changes}, format="json").status_code, 200
        )

    def timeline(self, code=roles.MANAGER):
        return self.client.get(detail_url(code)).json()["timeline"]

    def test_ed39_ac2_timeline_has_one_event_per_changed_capability(self):
        self.change(roles.MANAGER, {"view_customers": False, "publish_batch": False})
        events = self.timeline()
        labels = sorted(e["label"] for e in events)
        self.assertEqual(labels, ["Tắt việc Mở bán lô", "Tắt việc Xem khách hàng"])
        for event in events:
            self.assertEqual(event["doc"], "group")
            self.assertEqual(event["actor"], {"kind": "user", "display": "Chủ Thử"})
            self.assertTrue(event["at"])
        self.assertEqual(self.timeline(roles.WAREHOUSE_STAFF), [])

    def test_ed39_timeline_shows_on_label(self):
        self.change(roles.WAREHOUSE_STAFF, {"approve_return": True})
        self.assertEqual([e["label"] for e in self.timeline(roles.WAREHOUSE_STAFF)],
                         ["Bật việc Duyệt hàng hoàn về kho"])

    def test_ed39_timeline_includes_membership_changes_made_through_staff_api(self):
        response = self.client.put(
            f"/api/staff/{self.warehouse.pk}/groups/", {"groups": [roles.WAREHOUSE_STAFF, roles.MANAGER]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        manager_labels = [e["label"] for e in self.timeline(roles.MANAGER)]
        self.assertEqual(manager_labels, ["Thêm Kho Thử vào nhóm"])
        self.assertEqual(self.timeline(roles.WAREHOUSE_STAFF), [])  # vẫn còn trong nhóm kho
        self.client.put(f"/api/staff/{self.warehouse.pk}/groups/", {"groups": [roles.WAREHOUSE_STAFF]}, format="json")
        self.assertEqual([e["label"] for e in self.timeline(roles.MANAGER)],
                         ["Thêm Kho Thử vào nhóm", "Bớt Kho Thử khỏi nhóm"])

    def test_ed39_added_at_follows_the_membership_change(self):
        self.client.put(f"/api/staff/{self.warehouse.pk}/groups/", {"groups": [roles.WAREHOUSE_STAFF, roles.MANAGER]},
                        format="json")
        members = {m["username"]: m for m in self.client.get(detail_url(roles.MANAGER)).json()["members"]}
        event_at = self.timeline(roles.MANAGER)[0]["at"]
        self.assertEqual(members["kho1"]["added_at"], event_at)

    def test_ed39_timeline_does_not_expose_raw_changes_or_staff_phone(self):
        self.change(roles.MANAGER, {"publish_batch": False})
        text = self.client.get(detail_url(roles.MANAGER)).content.decode()
        self.assertNotIn('"from"', text)
        self.assertNotIn("changes", text)


class GroupGuidanceProviderTests(TestCase):
    def setUp(self):
        self.owner = make_staff("owner1", roles.OWNER, display_name="Chủ Thử")
        self.manager = make_staff("manager1", roles.MANAGER)
        self.client = client_for(self.owner)
        self.group = Group.objects.get(name=roles.MANAGER)

    def url(self, pk=None):
        return f"/api/guidance/group/{pk or self.group.pk}/"

    def test_r2_group_guidance_returns_timeline_only(self):
        self.client.put(put_url(roles.MANAGER), {"capabilities": {"publish_batch": False}}, format="json")
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["doc"]["type"], "group")
        self.assertEqual(body["doc"]["code"], roles.MANAGER)
        self.assertEqual(body["next_steps"], [])
        self.assertEqual(body["warnings"], [])
        self.assertEqual(len(body["timeline"]), 1)
        self.assertEqual(body["timeline"][0]["label"], "Tắt việc Mở bán lô")
        self.assertEqual(body["timeline"][0]["actor"]["display"], "Chủ Thử")

    def test_r2_group_guidance_requires_manage_staff(self):
        self.assertEqual(client_for(self.manager).get(self.url()).status_code, 403)
        self.assertEqual(client_for(make_user("kho1", roles.WAREHOUSE_STAFF)).get(self.url()).status_code, 403)
        self.assertEqual(client_for(None).get(self.url()).status_code, 401)

    def test_r2_group_guidance_unknown_id_is_404(self):
        self.assertEqual(self.client.get(self.url(999999)).status_code, 404)
        self.assertEqual(self.client.get("/api/guidance/group/abc/").status_code, 404)


class MembershipScanWindowTests(TestCase):
    """L1 (techlead Lô 14) — sự kiện thành viên quét theo ĐÚNG nhóm; nhóm ít đổi không mất sự kiện cũ khi nhóm khác
    có hàng nghìn lần đổi."""

    def setUp(self):
        from apps.accounts.models import AuditLog
        self.AuditLog = AuditLog
        self.owner = make_staff("owner1", roles.OWNER, display_name="Chủ Thử")
        self.warehouse = make_staff("kho1", roles.WAREHOUSE_STAFF, display_name="Kho Thử")
        self.client = client_for(self.owner)

    def test_ed39_old_membership_event_survives_thousands_of_other_group_changes(self):
        from django.contrib.auth.models import User
        response = self.client.put(
            f"/api/staff/{self.warehouse.pk}/groups/", {"groups": [roles.WAREHOUSE_STAFF, roles.MANAGER]},
            format="json")
        self.assertEqual(response.status_code, 200)
        other = make_staff("giao1", roles.DELIVERY_STAFF, display_name="Giao Thử")
        noise = [
            self.AuditLog(
                action="staff_groups_change", actor=self.owner, model_name=User._meta.label,
                object_id=str(other.pk), object_repr="giao1",
                changes={"groups": {"from": [roles.DELIVERY_STAFF], "to": [roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE]}
                         if i % 2 == 0 else
                         {"from": [roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE], "to": [roles.DELIVERY_STAFF]}},
            )
            for i in range(1100)
        ]
        self.AuditLog.objects.bulk_create(noise)
        labels = [e["label"] for e in self.client.get(detail_url(roles.MANAGER)).json()["timeline"]]
        self.assertEqual(labels, ["Thêm Kho Thử vào nhóm"])
        # nhóm bị nhiễu vẫn đọc được, tối đa 200 dòng
        noisy = self.client.get(detail_url(roles.CUSTOMER_SERVICE)).json()["timeline"]
        self.assertEqual(len(noisy), 200)

    def test_ed39_membership_scan_query_count_does_not_grow_with_events(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.client.get(detail_url(roles.MANAGER)).status_code, 200)
            return len(ctx)
        def flip(times):
            for i in range(times):
                groups = [roles.WAREHOUSE_STAFF, roles.MANAGER] if i % 2 == 0 else [roles.WAREHOUSE_STAFF]
                self.client.put(f"/api/staff/{self.warehouse.pk}/groups/", {"groups": groups}, format="json")
        flip(2)
        base = count()
        flip(6)  # tổng 8 lần đổi (cũ -> mới: thêm/bớt xen kẽ)
        self.assertEqual(count(), base)
