"""PV-02-AC2 — danh mục phạm vi D1..D8 (S-8: lựa chọn do dự án định nghĩa, Chủ không gõ luật)."""
from django.test import SimpleTestCase

from apps.accounts import roles
from apps.accounts.data_scopes import catalog

EDITABLE_ORDER = ("orders", "deliveries", "confirmation", "returns", "receipts", "customers")


class CatalogShapeTests(SimpleTestCase):
    def test_pv02_ac2_eight_objects_in_contract_order(self):
        self.assertEqual(
            [o.key for o in catalog.OBJECTS],
            ["orders", "invoices", "deliveries", "confirmation", "returns", "receipts", "customers", "audit_log"],
        )
        self.assertEqual(len({o.key for o in catalog.OBJECTS}), 8)

    def test_pv02_ac2_each_object_has_exactly_one_rank_zero_and_unique_ranks(self):
        for obj in catalog.OBJECTS:
            ranks = [option.rank for option in catalog.ranked_options(obj)]
            self.assertEqual(ranks.count(0), 1, obj.key)
            self.assertEqual(len(ranks), len(set(ranks)), obj.key)
            self.assertEqual(sorted(ranks), list(range(len(ranks))), obj.key)  # rank liên tục 0..n-1

    def test_pv02_ac2_option_values_are_unique_within_object(self):
        for obj in catalog.OBJECTS:
            values = [option.value for option in catalog.ranked_options(obj)]
            self.assertEqual(len(values), len(set(values)), obj.key)

    def test_pv02_ac2_defaults_are_valid_options_for_every_stored_group(self):
        for obj in catalog.stored_objects():
            valid = {option.value for option in obj.options}
            self.assertEqual(set(obj.defaults), set(catalog.DEFAULT_GROUPS), obj.key)
            for group, value in obj.defaults.items():
                self.assertIn(value, valid, f"{obj.key}/{group}")

    def test_pv02_ac2_only_six_objects_are_editable_and_stored(self):
        self.assertEqual([o.key for o in catalog.stored_objects()], list(EDITABLE_ORDER))
        read_only = {o.key for o in catalog.OBJECTS if o.read_only}
        self.assertEqual(read_only, {"invoices", "audit_log"})
        self.assertEqual(catalog.BY_KEY["invoices"].derived_from, "orders")

    def test_pv02_ac2_customer_data_flags(self):
        flags = {o.key: o.customer_data for o in catalog.OBJECTS}
        self.assertEqual(
            flags,
            {"orders": True, "invoices": True, "deliveries": True, "confirmation": True, "returns": True,
             "receipts": False, "customers": True, "audit_log": False},
        )

    def test_pv02_ac2_gate_permissions_follow_design(self):
        self.assertEqual(catalog.BY_KEY["orders"].gate_perms, ("sales.view_salesorder",))
        self.assertEqual(catalog.BY_KEY["invoices"].gate_perms, ("sales.view_salesinvoice",))
        self.assertEqual(catalog.BY_KEY["deliveries"].gate_perms, ("delivery.view_deliverynote",))
        self.assertEqual(catalog.BY_KEY["confirmation"].gate_perms, ("delivery.confirm_with_customer",))
        self.assertEqual(catalog.BY_KEY["returns"].gate_perms, ("inventory.view_returntostock",))
        self.assertEqual(
            catalog.BY_KEY["receipts"].gate_perms, ("purchasing.view_purchasereceipt", "purchasing.add_purchasereceipt"),
        )
        self.assertEqual(catalog.BY_KEY["customers"].gate_perms, ("sales.view_customer_list", "sales.view_customer"))
        self.assertEqual(catalog.BY_KEY["audit_log"].gate_perms, ("accounts.view_auditlog",))

    def test_pv02_ac2_option_values_match_contract(self):
        values = {o.key: [opt.value for opt in sorted(o.options, key=lambda x: x.rank)] for o in catalog.stored_objects()}
        self.assertEqual(values["orders"], ["assigned_deliveries", "assigned_or_confirmation", "all"])
        self.assertEqual(values["deliveries"], ["assigned", "all"])
        self.assertEqual(values["confirmation"], ["pending_or_called_recently", "all_pending"])
        self.assertEqual(values["returns"], ["assigned_deliveries", "all"])
        self.assertEqual(values["receipts"], ["created_by_me_today", "created_by_me", "all"])
        self.assertEqual(values["customers"], ["none", "assigned_deliveries", "all"])

    def test_pv02_ac1_defaults_match_contract_table(self):
        expected = {
            # nhóm: orders, deliveries, confirmation, returns, receipts, customers
            roles.MANAGER: ("all", "all", "all_pending", "all", "all", "all"),
            roles.WAREHOUSE_STAFF: ("all", "all", "all_pending", "all", "all", "none"),
            roles.DELIVERY_STAFF: ("assigned_deliveries", "assigned", "pending_or_called_recently",
                                   "assigned_deliveries", "all", "assigned_deliveries"),
            roles.CUSTOMER_SERVICE: ("assigned_or_confirmation", "assigned", "pending_or_called_recently",
                                     "assigned_deliveries", "all", "none"),
        }
        for group, row in expected.items():
            actual = tuple(catalog.BY_KEY[key].defaults[group] for key in EDITABLE_ORDER)
            self.assertEqual(actual, row, group)

    def test_pv02_catalog_does_not_import_models(self):
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(catalog))
        modules = [
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        ] + [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        for module in modules:
            self.assertNotIn("models", module)  # catalog thuần dữ liệu, không import model (02b §1.2)
            self.assertFalse(module.startswith("django.db"), module)
