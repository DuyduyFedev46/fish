"""
S01 — Bất biến của command registry (PA G4/V4: registry là code, không bảng DB).

Nguồn: 02b-tech-design mục 2.1 + Phụ lục B (14 lệnh khởi đầu); 02-stories S01-AC1/AC4/AC6;
lệch D6 (field `description` tiếng Việt) và D8 (`xac_nhan_hoan`/`xac_nhan_thanh_toan_tay`
nhãn `local`, vẫn `forbidden_channel="ai"`).
"""
import jsonschema
from django.contrib.auth.models import Permission
from django.test import SimpleTestCase, TestCase

from apps.ai.commands.registry import COMMANDS, PII_FORBIDDEN_KEYS

# 6 trường ADR 2.5 bắt buộc cho mọi lệnh (S01-AC1).
ADR_FIELDS = ("name", "channel", "sensitivity", "min_permissions", "input_schema", "output_schema")

ACTIVE = {
    "nhap_lo", "tra_ton", "tra_lo", "tra_hang", "tra_don",
    "bao_cao_ton_kho", "bao_cao_lo", "bao_cao_ky",
    "chot_lo", "tao_phieu_hoan", "xac_nhan_hoan", "xac_nhan_thanh_toan_tay",
}
DRAFT = {"kiem_ke", "cap_nhat_giao"}
# S01-AC4 (BR-AI-07): đúng 3 lệnh cấm kênh AI, không lệnh nào khác.
FORBIDDEN_AI = {"chot_lo", "xac_nhan_hoan", "xac_nhan_thanh_toan_tay"}


class RegistryInvariantTests(SimpleTestCase):
    """Bất biến registry — không cần DB (registry là code thuần)."""

    def test_s01_du_14_lenh_khoi_dau(self):
        self.assertEqual(set(COMMANDS), ACTIVE | DRAFT)

    def test_s01_ac1_moi_lenh_du_6_truong_adr(self):
        for spec in COMMANDS.values():
            for field in ADR_FIELDS:
                value = getattr(spec, field)
                self.assertIsNotNone(value, f"{spec.name}: thiếu {field}")
                self.assertTrue(value, f"{spec.name}: {field} rỗng")

    def test_s01_ac1_input_output_schema_la_json_schema_hop_le(self):
        for spec in COMMANDS.values():
            jsonschema.Draft7Validator.check_schema(spec.input_schema)
            jsonschema.Draft7Validator.check_schema(spec.output_schema)

    def test_s01_ten_lenh_duy_nhat(self):
        names = [spec.name for spec in COMMANDS.values()]
        self.assertEqual(len(names), len(set(names)), "tên lệnh trùng")

    def test_s01_status_active_draft_dung_theo_story(self):
        for spec in COMMANDS.values():
            if spec.name in ACTIVE:
                self.assertEqual(spec.status, "active", spec.name)
            if spec.name in DRAFT:
                self.assertEqual(spec.status, "draft", spec.name)

    def test_s01_ac4_forbidden_channel_dung_3_lenh(self):
        for spec in COMMANDS.values():
            if spec.name in FORBIDDEN_AI:
                self.assertEqual(spec.forbidden_channel, "ai", spec.name)
            else:
                self.assertIsNone(spec.forbidden_channel, spec.name)

    def test_s01_ac6_nhan_dung_theo_bang_da_chot(self):
        labels = {
            "nhap_lo": ("local", "cao"),
            "tra_ton": ("local", "trung_binh"),
            "tra_don": ("local", "trung_binh"),
            "bao_cao_ton_kho": ("cloud", "thap"),
            "bao_cao_lo": ("cloud", "cao"),
            "bao_cao_ky": ("cloud", "cao"),
        }
        for name, (channel, sensitivity) in labels.items():
            spec = COMMANDS[name]
            self.assertEqual(spec.channel, channel, name)
            self.assertEqual(spec.sensitivity, sensitivity, name)

    def test_s01_d8_xac_nhan_hoan_va_thanh_toan_tay_nhan_local(self):
        for name in ("xac_nhan_hoan", "xac_nhan_thanh_toan_tay"):
            spec = COMMANDS[name]
            self.assertEqual(spec.channel, "local", name)
            self.assertEqual(spec.forbidden_channel, "ai", name)  # vẫn cấm kênh AI

    def test_s01_context_fields_khong_chua_khoa_pii(self):
        # Bất biến 9 / BR-AI-09: allowlist context không bao giờ chứa khoá dữ liệu cá nhân.
        for spec in COMMANDS.values():
            for group_fields in (spec.context_fields or {}).values():
                for key in group_fields:
                    self.assertNotIn(key, PII_FORBIDDEN_KEYS, f"{spec.name}: {key} là khoá PII")

    def test_s01_d6_moi_lenh_co_description_tieng_viet(self):
        for spec in COMMANDS.values():
            self.assertTrue(spec.description.strip(), f"{spec.name}: thiếu description")


class RegistryPermissionExistsTests(TestCase):
    """Mọi min_permissions khai trong registry phải là permission có thật (chống gõ nhầm)."""

    def test_s01_min_permissions_ton_tai_thuc(self):
        existing = set(Permission.objects.values_list("content_type__app_label", "codename"))
        for spec in COMMANDS.values():
            self.assertTrue(spec.min_permissions, f"{spec.name}: min_permissions rỗng")
            for perm in spec.min_permissions:
                app_label, codename = perm.split(".", 1)
                self.assertIn(
                    (app_label, codename), existing,
                    f"{spec.name}: perm {perm} không tồn tại trong DB",
                )
