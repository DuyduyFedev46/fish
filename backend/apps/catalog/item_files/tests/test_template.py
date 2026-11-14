"""FISH-66 S4: tải file mẫu thêm món mới (BR-DM-27, BR-DM-28). Dữ liệu giả."""
import datetime

from django.utils import timezone

from apps.accounts.models import AuditLog

from .base import HEADERS_FULL, HEADERS_NO_PRICE, TEMPLATE_URL, ItemFilesBase, open_xlsx, sheet_rows


class TemplateTests(ItemFilesBase):
    def test_s4_ac1_owner_gets_17_columns_and_one_fake_example_row(self):
        resp = self.get(self.owner, TEMPLATE_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Disposition"], 'attachment; filename="mau-hang-ban.xlsx"')
        self.assertEqual(resp["X-Row-Count"], "1")
        self.assertEqual(resp["Cache-Control"], "no-store")
        rows = sheet_rows(resp)
        self.assertEqual(rows[0], HEADERS_FULL)
        self.assertEqual(len(rows), 2)
        example = dict(zip(HEADERS_FULL, rows[1]))
        self.assertEqual(example["Mã hàng"], "VD-001")
        self.assertEqual(example["Tên"], "Cá ví dụ")
        self.assertEqual(example["Nhóm hàng"], "Nhóm ví dụ")
        self.assertEqual(example["Loại"], "Mặt hàng thường")
        self.assertEqual(example["Đơn vị"], "Kg")
        self.assertEqual(example["Đang kinh doanh"], "Có")
        self.assertEqual(example["Hạn dùng mặc định (ngày)"], 365)
        self.assertEqual(example["Quản lý theo lô"], "Có")
        self.assertEqual(example["Có hạn dùng"], "Có")
        self.assertIsNone(example["Giá bán hiện hành"])
        self.assertEqual(example["Giá mới"], 150000)
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        value = example["Ngày áp dụng giá mới"]
        self.assertEqual(value.date() if hasattr(value, "date") else value, tomorrow)

    def test_s4_example_has_no_data_from_the_database(self):
        wb = open_xlsx(self.get(self.owner, TEMPLATE_URL))
        text = " ".join(str(c) for ws in wb.worksheets for row in ws.iter_rows(values_only=True) for c in row if c)
        self.assertNotIn("Cá thu", text)
        self.assertNotIn("CA01", text)

    def test_s4_ac3_manager_full_and_warehouse_staff_has_14_columns(self):
        self.assertEqual(sheet_rows(self.get(self.manager, TEMPLATE_URL))[0], HEADERS_FULL)
        rows = sheet_rows(self.get(self.warehouse_staff, TEMPLATE_URL))
        self.assertEqual(rows[0], HEADERS_NO_PRICE)
        self.assertEqual(len(rows[1]), 14)
        self.assertNotIn(150000, rows[1])

    def test_s4_ac4_delivery_cs_and_anonymous_are_rejected(self):
        for user in (self.courier, self.customer_service, self.no_group):
            self.assertEqual(self.get(user, TEMPLATE_URL).status_code, 403)
        self.assertEqual(self.get(None, TEMPLATE_URL).status_code, 401)

    def test_s4_template_writes_no_audit(self):
        self.get(self.owner, TEMPLATE_URL)
        self.assertFalse(AuditLog.objects.filter(action="export_items").exists())

    def test_s4_no_cost_columns(self):
        for user in (self.owner, self.manager, self.warehouse_staff):
            header = " ".join(sheet_rows(self.get(user, TEMPLATE_URL))[0]).lower()
            for bad in ("giá vốn", "giá mua", "nhà cung cấp", "mã lô", "tồn", "lãi"):
                self.assertNotIn(bad, header)

    def test_s4_template_cells_are_never_formulas(self):
        ws = open_xlsx(self.get(self.owner, TEMPLATE_URL))["Hàng bán"]
        for row in ws.iter_rows():
            for cell in row:
                self.assertNotEqual(cell.data_type, "f")
