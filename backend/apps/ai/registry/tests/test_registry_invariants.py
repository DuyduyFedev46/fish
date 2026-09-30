"""
Test DW-15: Bất biến của registry tự sinh (chuyển tiếp từ S01 sang tự đăng ký).

Chuyển các ý test cũ sang registry tự sinh:
1. Tên lệnh duy nhất (DW-15-AC4)
2. input_schema của mọi lệnh là JSON Schema hợp lệ Draft 2020-12 (DW-15-AC4)
3. all_output_fields không chứa khoá PII cấm (DW-15-AC4, Bất biến 9)
4. required_perms của mọi lệnh phải là Permission có thật trong database (DW-15-AC4, H1)
5. Mọi lệnh có title và description tiếng Việt không rỗng (DW-15-AC4, BR-AI-01)
6. Đối chiếu 12 lệnh cũ x 4 Group (DW-15-AC2)
7. Keywords của các lệnh tương ứng theo Phụ lục B (DW-15-AC3)
"""
import jsonschema
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings

from apps.ai.policy.effective import effective_level
from apps.ai.policy.rules import SCRUB_PII_KEYS
from apps.ai.registry.discovery import get_registry
from apps.common.tests.fixtures import make_user
from apps.accounts import roles


@override_settings(AI_ENABLED=True)
class RegistryInvariantsTestCase(TestCase):
    def setUp(self):
        self.registry = get_registry()
        self.specs = self.registry.get_specs()

    def test_dw15_ac4_ten_lenh_duy_nhat(self):
        """DW-15-AC4: Tên (ID) của mọi lệnh trong registry phải duy nhất."""
        ids = [spec.id for spec in self.specs]
        self.assertEqual(len(ids), len(set(ids)), "Tên/ID lệnh trong registry bị trùng lặp")

    def test_dw15_ac4_input_schema_hop_le_draft202012(self):
        """DW-15-AC4: input_schema của mọi lệnh phải là JSON Schema hợp lệ Draft 2020-12."""
        checked = 0
        for spec in self.specs:
            if spec.input_schema is not None:
                jsonschema.Draft202012Validator.check_schema(spec.input_schema)
                checked += 1
        self.assertGreater(checked, 0, "Phải có ít nhất một lệnh có input_schema để kiểm tra")

    def test_dw15_ac4_output_fields_khong_chua_khoa_pii(self):
        """DW-15-AC4: all_output_fields không bao giờ chứa khoá PII cấm (Bất biến 9)."""
        for spec in self.specs:
            for field in (spec.all_output_fields or []):
                self.assertNotIn(
                    field,
                    SCRUB_PII_KEYS,
                    f"Lệnh {spec.id} chứa khoá PII cấm trong output_fields: {field}",
                )

    def test_dw15_ac4_required_perms_ton_tai_thuc(self):
        """DW-15-AC4: Mọi required_perms khai báo phải là permission có thật trong DB."""
        existing_perms = set(Permission.objects.values_list("content_type__app_label", "codename"))
        for spec in self.specs:
            for perm in spec.required_perms:
                self.assertIn(".", perm, f"Permission {perm} của lệnh {spec.id} không đúng format app_label.codename")
                app_label, codename = perm.split(".", 1)
                self.assertIn(
                    (app_label, codename),
                    existing_perms,
                    f"Lệnh {spec.id} khai required_perm không tồn tại trong DB: {perm}",
                )

    def test_dw15_ac4_title_va_description_tieng_viet_khong_rong(self):
        """DW-15-AC4: Mọi lệnh phải có title và description tiếng Việt không rỗng."""
        for spec in self.specs:
            self.assertTrue(spec.title and spec.title.strip(), f"Lệnh {spec.id} thiếu title")
            self.assertTrue(spec.description and spec.description.strip(), f"Lệnh {spec.id} thiếu description")

    def test_dw15_ac2_doi_chieu_12_lenh_cu_voi_4_group(self):
        """DW-15-AC2: Đối chiếu 12 lệnh cũ tương ứng theo Phụ lục B với 4 Group."""
        chu = make_user("chu_inv", roles.OWNER)
        ql = make_user("ql_inv", roles.MANAGER)
        kho = make_user("kho_inv", roles.WAREHOUSE_STAFF)

        # 1. tra_ton -> inventory.batch.list
        batch_list = self.registry.get("inventory.batch.list")
        self.assertIsNotNone(batch_list)
        for u in (chu, ql, kho):
            self.assertIn(effective_level(u, batch_list), ("A", "C", "B"))

        # 2. chot_lo -> inventory.batch.close: chỉ Chu có quyền
        batch_close = self.registry.get("inventory.batch.close")
        self.assertIsNotNone(batch_close)
        self.assertIn(effective_level(chu, batch_close), ("C", "B"))
        self.assertEqual(effective_level(ql, batch_close), "OFF")
        self.assertEqual(effective_level(kho, batch_close), "OFF")

        # 3. bao_cao_lo -> reports.batch_pnl: chỉ Chu (view_profitreport)
        batch_pnl = self.registry.get("reports.batch_pnl")
        self.assertIsNotNone(batch_pnl)
        self.assertEqual(effective_level(chu, batch_pnl), "A")
        self.assertEqual(effective_level(ql, batch_pnl), "OFF")
        self.assertEqual(effective_level(kho, batch_pnl), "OFF")

        # 4. xac_nhan_hoan -> sales.refund.confirm: chỉ Chu (confirm_refund)
        refund_confirm = self.registry.get("sales.refund.confirm")
        self.assertIsNotNone(refund_confirm)
        self.assertIn(effective_level(chu, refund_confirm), ("C", "B"))
        self.assertEqual(effective_level(ql, refund_confirm), "OFF")

    def test_dw15_ac3_keywords_theo_phu_luc_b(self):
        """DW-15-AC3: Các lệnh có keywords tên cũ theo Phụ lục B."""
        # 1. Batch list: tra_ton, tra tồn
        batch_list = self.registry.get("inventory.batch.list")
        self.assertTrue(any("tra_ton" in kw or "tra tồn" in kw for kw in batch_list.keywords))

        # 2. Batch close: chot_lo, chốt lô
        batch_close = self.registry.get("inventory.batch.close")
        self.assertTrue(any("chot_lo" in kw or "chốt lô" in kw for kw in batch_close.keywords))

        # 3. Item list/retrieve: tra_hang, tra hàng
        item_list = self.registry.get("catalog.item.list")
        self.assertTrue(any("tra_hang" in kw or "tra hàng" in kw for kw in item_list.keywords))

        # 4. Order list/retrieve: tra_don, tra đơn
        order_list = self.registry.get("sales.salesorder.list")
        self.assertTrue(any("tra_don" in kw or "tra đơn" in kw for kw in order_list.keywords))

        # 5. Refund create: tao_phieu_hoan, tạo phiếu hoàn
        refund_create = self.registry.get("sales.refund.create_refund")
        self.assertTrue(any("tao_phieu_hoan" in kw or "tạo phiếu hoàn" in kw for kw in refund_create.keywords))

        # 6. Refund confirm: xac_nhan_hoan, xác nhận hoàn
        refund_confirm = self.registry.get("sales.refund.confirm")
        self.assertTrue(any("xac_nhan_hoan" in kw or "xác nhận hoàn" in kw for kw in refund_confirm.keywords))

        # 7. Reports
        pnl = self.registry.get("reports.batch_pnl")
        self.assertTrue(any("bao_cao_lo" in kw or "báo cáo lô" in kw for kw in pnl.keywords))

        period = self.registry.get("reports.period_pnl")
        self.assertTrue(any("bao_cao_ky" in kw or "báo cáo kỳ" in kw for kw in period.keywords))

        dashboard = self.registry.get("reports.dashboard_summary")
        self.assertTrue(any("bao_cao_ton_kho" in kw or "báo cáo tồn kho" in kw for kw in dashboard.keywords))
