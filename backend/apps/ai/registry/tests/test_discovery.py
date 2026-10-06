"""
Test khám phá lệnh và luật chặn tất định (DW-07-AC1, DW-07-AC3, DW-07-AC7).
"""
import json
import os
from django.conf import settings
from django.test import TestCase

from apps.ai.policy.rules import (
    FORBIDDEN_METHODS,
    FORBIDDEN_PERMS_T2,
    FORBIDDEN_PREFIXES,
    FORBIDDEN_RESOURCES,
    FORBIDDEN_SUFFIXES,
    RED_ZONE_PERMS,
)
from apps.ai.registry.discovery import get_registry
from apps.ai import command_groups


class CommandDiscoveryTestCase(TestCase):
    def setUp(self):
        self.registry = get_registry()
        self.specs = self.registry.get_specs()

    def test_dw07_ac1_snapshot_khop_file(self):
        """DW-07-AC1: Danh sách id lệnh đúng quy tắc và khớp file snapshot."""
        snapshot_path = os.path.join(
            settings.BASE_DIR, "apps/ai/registry/tests/snapshots/commands_index_snapshot.json"
        )
        self.assertTrue(os.path.exists(snapshot_path), "File snapshot phải tồn tại.")
        with open(snapshot_path, "r", encoding="utf-8") as f:
            expected_ids = json.load(f)

        actual_ids = [s.id for s in self.specs]
        self.assertEqual(actual_ids, expected_ids, "Danh sách ID lệnh trong registry phải khớp với snapshot.")

        # Kiểm tra cấu trúc id: <app>.<model|view>.<action> hoặc <app>.<view>
        for s in self.specs:
            parts = s.id.split(".")
            self.assertIn(len(parts), (2, 3), f"ID lệnh không đúng format: {s.id}")
            self.assertIn(s.group, (command_groups.PURCHASING, command_groups.SALES, command_groups.CUSTOMER_SERVICE), f"Group không hợp lệ: {s.group} của {s.id}")
            self.assertIn(s.kind, ("read", "write"))

    def test_cs17_lookup_label_forbidden_for_ai(self):
        """CS-17 (02b §4.1): tra mã tem bị cấm với AI và không có trong registry."""
        from apps.ai.policy.rules import is_url_forbidden

        self.assertTrue(is_url_forbidden("/api/delivery/notes/lookup/"))
        self.assertNotIn("delivery.deliverynote.lookup", [s.id for s in self.specs])

    def test_dw07_ac3_hard_blocklist(self):
        """DW-07-AC3: Không lệnh nào vi phạm danh sách cấm tất định."""
        for s in self.specs:
            # 1. Không prefix cấm
            for prefix in FORBIDDEN_PREFIXES:
                self.assertFalse(
                    s.path.startswith(prefix) or s.path.startswith(prefix.rstrip("/")),
                    f"Lệnh {s.id} vi phạm prefix cấm: {prefix}",
                )

            # 2. Không suffix cấm (tem nhãn)
            for suffix in FORBIDDEN_SUFFIXES:
                self.assertFalse(
                    s.path.rstrip("/").endswith(suffix.rstrip("/")),
                    f"Lệnh {s.id} vi phạm suffix cấm: {suffix}",
                )

            # 3. Không method DELETE/PUT
            self.assertNotIn(s.method, FORBIDDEN_METHODS, f"Lệnh {s.id} dùng method bị cấm: {s.method}")

            # 4. Không upload ảnh
            self.assertNotIn("image", s.path, f"Lệnh {s.id} là endpoint ảnh: {s.path}")

            # 5. Không quyền cấm trong required_perms
            for perm in s.required_perms:
                self.assertFalse(perm.startswith("auth."), f"Lệnh {s.id} có quyền auth.*: {perm}")
                self.assertNotIn(perm, FORBIDDEN_PERMS_T2, f"Lệnh {s.id} có quyền cấm: {perm}")

            # 6. Không CRUD ghi trên SalesOrder và SalesInvoice
            if s.id.startswith("sales.salesorder."):
                self.assertNotIn(s.action, ("create", "update", "partial_update", "destroy"))
            if s.id.startswith("sales.salesinvoice."):
                self.assertNotIn(s.action, ("create", "update", "partial_update", "destroy"))

            # 7. Không resource customer
            self.assertNotIn("customer", s.id.lower(), f"Lệnh {s.id} đụng resource customer.")

    def test_dw07_ac3_red_zone_dung_bang_3_quyen(self):
        """DW-07-AC3: Tập red_zone=true đúng bằng các action có close_batch/confirm_refund/confirm_payment_manual."""
        expected_red_zone_ids = {
            "inventory.batch.close",
            "sales.paymenttransaction.record_late",
            "sales.paymenttransaction.resolve",
            "sales.refund.confirm",
            "sales.refund.mark_failed",
            "sales.refund.retry",
            "sales.salesorder.confirm_payment",
        }
        actual_red_zone_ids = {s.id for s in self.specs if s.red_zone}
        self.assertEqual(
            actual_red_zone_ids,
            expected_red_zone_ids,
            f"Tập red_zone phải đúng bằng 7 action có 3 quyền đỏ. Lệch: {actual_red_zone_ids ^ expected_red_zone_ids}",
        )

        for s in self.specs:
            has_red_perm = bool(set(s.required_perms) & RED_ZONE_PERMS)
            self.assertEqual(s.red_zone, has_red_perm, f"Lệnh {s.id} red_zone không khớp required_perms")

    def test_dw07_ac7_schema_budget(self):
        """DW-07-AC7: Mô tả <= 80 ký tự, enum > 20 đổi thành string, tokens > 450 -> form_only."""
        for s in self.specs:
            if s.input_schema and "properties" in s.input_schema:
                for prop_name, prop_data in s.input_schema["properties"].items():
                    if "description" in prop_data:
                        self.assertLessEqual(
                            len(prop_data["description"]),
                            80,
                            f"Lệnh {s.id} prop {prop_name} có mô tả dài quá 80 ký tự",
                        )
                    if "enum" in prop_data:
                        self.assertLessEqual(
                            len(prop_data["enum"]),
                            20,
                            f"Lệnh {s.id} prop {prop_name} enum > 20 giá trị phải đổi thành string",
                        )

            if s.schema_tokens_est > getattr(settings, "AI_SCHEMA_MAX_TOKENS", 450):
                self.assertTrue(s.form_only, f"Lệnh {s.id} vượt token trần mà form_only=False")
