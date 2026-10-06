"""Lô dọn chữ AI (A1, 02b 2.2) — ma trận phân quyền bỏ việc `ai_policy` khi AI tắt. Dữ liệu giả."""
from django.test import TestCase, override_settings

from apps.accounts import roles
from apps.accounts.capabilities import registry
from apps.accounts.models import AuditLog
from apps.common.audit import record_audit
from apps.common.tests.fixtures import client_for

from .base import LIST_URL, detail_url, group_perms, make_staff, put_url

NON_AI_KEYS = {c.key for c in registry.CAPABILITIES} - registry.AI_CAPABILITY_KEYS


class MatrixAiFlagTests(TestCase):
    def setUp(self):
        self.owner = make_staff("owner1", roles.OWNER)
        self.manager = make_staff("manager1", roles.MANAGER)
        self.client = client_for(self.owner)

    @override_settings(AI_ENABLED=False)
    def test_off_list_and_detail_have_no_ai_policy(self):
        for row in self.client.get(LIST_URL).json():
            self.assertEqual(set(row["capabilities"]), NON_AI_KEYS)
        body = self.client.get(detail_url(roles.MANAGER)).json()
        self.assertEqual(set(body["capabilities"]), NON_AI_KEYS)
        self.assertEqual({r["key"] for r in body["registry"]}, NON_AI_KEYS)
        self.assertNotIn("AI", str(body["registry"]))

    @override_settings(AI_ENABLED=True)
    def test_on_keeps_ai_policy(self):
        body = self.client.get(detail_url(roles.MANAGER)).json()
        self.assertIn("ai_policy", body["capabilities"])
        self.assertIn("ai_policy", {r["key"] for r in body["registry"]})

    @override_settings(AI_ENABLED=False)
    def test_off_put_ai_policy_is_400_and_data_unchanged(self):
        before = group_perms(roles.MANAGER)
        response = self.client.put(put_url(roles.MANAGER), {"capabilities": {"ai_policy": False}}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INPUT_NOT_ALLOWED")
        self.assertEqual(group_perms(roles.MANAGER), before)
        self.assertFalse(AuditLog.objects.filter(action="change_group_capabilities").exists())

    @override_settings(AI_ENABLED=False)
    def test_off_put_other_keys_still_works(self):
        response = self.client.put(put_url(roles.MANAGER), {"capabilities": {"publish_batch": False}}, format="json")
        self.assertEqual(response.status_code, 200)

    @override_settings(AI_ENABLED=True)
    def test_on_put_ai_policy_off_still_accepted(self):
        response = self.client.put(put_url(roles.MANAGER), {"capabilities": {"ai_policy": False}}, format="json")
        self.assertEqual(response.status_code, 200)

    @override_settings(AI_ENABLED=False)
    def test_manager_still_403(self):
        client = client_for(self.manager)
        self.assertEqual(client.get(LIST_URL).status_code, 403)
        self.assertEqual(client.put(put_url(roles.MANAGER), {"capabilities": {"ai_policy": False}},
                                    format="json").status_code, 403)

    def _seed_events(self):
        from django.contrib.auth.models import Group

        group = Group.objects.get(name=roles.MANAGER)
        record_audit("change_group_capabilities", actor=self.owner, obj=group,
                     changes={"ai_policy": {"from": "on", "to": "off"}})
        record_audit("change_group_capabilities", actor=self.owner, obj=group,
                     changes={"ai_policy": {"from": "off", "to": "on"}, "publish_batch": {"from": "on", "to": "off"}})
        return group

    @override_settings(AI_ENABLED=False)
    def test_off_timeline_drops_ai_only_event_and_labels_mixed_without_ai(self):
        self._seed_events()
        labels = [e["label"] for e in self.client.get(detail_url(roles.MANAGER)).json()["timeline"]
                  if e["kind"] == "change_group_capabilities"]
        self.assertEqual(labels, ["Tắt việc Mở bán lô"])
        self.assertFalse([x for x in labels if "AI" in x])

    @override_settings(AI_ENABLED=True)
    def test_on_timeline_keeps_both_events(self):
        self._seed_events()
        labels = [e["label"] for e in self.client.get(detail_url(roles.MANAGER)).json()["timeline"]
                  if e["kind"] == "change_group_capabilities"]
        self.assertEqual(len(labels), 3)  # 1 + 2 khoá
        self.assertTrue([x for x in labels if "AI" in x])

    @override_settings(AI_ENABLED=False)
    def test_off_capability_change_label_for_guidance(self):
        from apps.accounts.capabilities import services

        self._seed_events()
        rows = list(AuditLog.objects.filter(action="change_group_capabilities").order_by("id"))
        self.assertEqual(services.capability_change_label(rows[1]), "Tắt việc Mở bán lô")

    @override_settings(AI_ENABLED=False)
    def test_off_guidance_group_drops_ai_only_event_without_zero_count_label(self):
        """N1: sự kiện chỉ có khoá AI không hiện "Đổi quyền của nhóm (0 việc)" ở guidance của nhóm."""
        group = self._seed_events()
        timeline = self.client.get(f"/api/guidance/group/{group.pk}/").json()["timeline"]
        labels = [e["label"] for e in timeline if e["kind"] == "change_group_capabilities"]
        self.assertEqual(labels, ["Tắt việc Mở bán lô"])
        self.assertNotIn("0 việc", str(timeline))
