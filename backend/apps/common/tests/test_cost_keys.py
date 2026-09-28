"""
Test unit cho apps/common/cost_keys.py (S01 / L-3 / AC5).
"""
import copy
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase

from apps.common.cost_keys import COST_KEYS, can_view_cost, redact_cost


class CostKeysUnitTests(TestCase):
    def test_cost_keys_contains_required_fields(self):
        expected = {
            "purchase_rate", "landed_unit_cost", "unit_cost", "rate",
            "allocated_amount", "purchase_cost", "allocated_cost", "total_cost",
            "shrinkage_cost", "damage_cost", "cogs", "profit",
        }
        self.assertTrue(expected.issubset(COST_KEYS))

    def test_redact_cost_removes_keys_flat(self):
        data = {
            "status": "CLOSED",
            "purchase_rate": "80000.00",
            "landed_unit_cost": "85000.00",
            "note": "ok",
        }
        result = redact_cost(data)
        self.assertEqual(result, {"status": "CLOSED", "note": "ok"})

    def test_redact_cost_nested_dicts_and_lists(self):
        data = {
            "level1": {
                "unit_cost": "100.00",
                "normal": "value",
                "level2": {
                    "profit": "500.00",
                    "items": [
                        {"rate": "10.00", "qty": 5},
                        {"name": "Ca thu", "cogs": "20.00"},
                    ],
                },
            },
            "total_cost": "999.00",
        }
        result = redact_cost(data)
        expected = {
            "level1": {
                "normal": "value",
                "level2": {
                    "items": [
                        {"qty": 5},
                        {"name": "Ca thu"},
                    ],
                },
            },
        }
        self.assertEqual(result, expected)

    def test_redact_cost_immutable_does_not_modify_input(self):
        original = {
            "purchase_rate": "80000",
            "items": [{"rate": "50", "qty": 1}],
        }
        original_copy = copy.deepcopy(original)
        result = redact_cost(original)
        self.assertEqual(original, original_copy)
        self.assertNotIn("purchase_rate", result)
        self.assertNotIn("rate", result["items"][0])

    def test_redact_cost_primitives(self):
        self.assertEqual(redact_cost("abc"), "abc")
        self.assertEqual(redact_cost(123), 123)
        self.assertIsNone(redact_cost(None))

    def test_can_view_cost_permission_check(self):
        user = User.objects.create_user("test_user", password="x")
        self.assertFalse(can_view_cost(user))
        self.assertFalse(can_view_cost(None))

        perm = Permission.objects.get(
            content_type__app_label="inventory", codename="view_costprice"
        )
        user.user_permissions.add(perm)
        user = User.objects.get(pk=user.pk)
        self.assertTrue(can_view_cost(user))
