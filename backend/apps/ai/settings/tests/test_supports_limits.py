"""
Lô "lưu cài đặt AI", B1 (QA REJECTED): `GET /api/ai/my-config/` báo từng lệnh có hỗ trợ ngưỡng hay không
(`supports_limits`), lấy từ khai báo `limits` của AiMeta, để UI vẽ ô ngưỡng kể cả khi chưa lưu ngưỡng nào.
Không đổi khoá cũ, không trả trần của Chủ (để P9).
"""
from django.test import TestCase, override_settings

from apps.accounts import roles
from apps.ai.registry import get_registry
from apps.common.tests.fixtures import client_for, make_user

RECEIVE_BATCHES_ID = "purchasing.purchasereceipt.receive_batches"
OLD_KEYS = {"id", "title", "kind", "level", "source", "choices", "max_level", "locked_reason", "red_zone", "limits"}


def _commands(data):
    return {c["id"]: c for g in data["groups"] for c in g["commands"]}


@override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="C")
class SupportsLimitsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        get_registry().build(force=True)
        cls.owner = make_user("limits_flag_owner", roles.OWNER)
        cls.warehouse = make_user("limits_flag_kho", roles.WAREHOUSE_STAFF)
        cls.delivery = make_user("limits_flag_giao", roles.DELIVERY_STAFF)

    def _get(self, user):
        resp = client_for(user).get("/api/ai/my-config/")
        self.assertEqual(resp.status_code, 200)
        return resp

    def test_b1_receive_batches_supports_limits_true(self):
        cmds = _commands(self._get(self.owner).json())
        self.assertIn(RECEIVE_BATCHES_ID, cmds)
        self.assertIs(cmds[RECEIVE_BATCHES_ID]["supports_limits"], True)
        # Chưa lưu ngưỡng nào: limits vẫn null, cờ vẫn true
        self.assertIsNone(cmds[RECEIVE_BATCHES_ID]["limits"])

    def test_b1_read_commands_supports_limits_false(self):
        cmds = _commands(self._get(self.owner).json())
        reads = [c for c in cmds.values() if c["kind"] == "read"]
        self.assertTrue(reads)
        for c in reads:
            self.assertIs(c["supports_limits"], False, c["id"])

    def test_b1_every_command_has_boolean_flag_and_only_declared_ones_true(self):
        registry = get_registry()
        declared = {s.id for s in registry.get_specs() if s.limits}
        self.assertIn(RECEIVE_BATCHES_ID, declared)
        for user in (self.owner, self.warehouse, self.delivery):
            cmds = _commands(self._get(user).json())
            for cid, c in cmds.items():
                self.assertIsInstance(c["supports_limits"], bool)
                self.assertEqual(c["supports_limits"], cid in declared, cid)

    def test_b1_old_keys_unchanged_and_group_matrix_per_role(self):
        for user in (self.owner, self.warehouse, self.delivery):
            data = self._get(user).json()
            for c in _commands(data).values():
                self.assertEqual(set(c) - {"supports_limits"}, OLD_KEYS)
        # Ma trận Group: người không có quyền nhập lô không thấy lệnh này (cờ không mở thêm lệnh)
        self.assertNotIn(RECEIVE_BATCHES_ID, _commands(self._get(self.delivery).json()))

    def test_b1_response_has_no_cost_fields(self):
        text = self._get(self.owner).content.decode()
        for word in ("purchase_rate", "landed_unit_cost", "unit_cost", "profit"):
            self.assertNotIn(word, text)
