"""FISH-66 S3: tải danh sách mặt hàng ra Excel (BR-DM-27, BR-DM-28). Dữ liệu giả."""
import datetime
from decimal import Decimal

from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.items.tests.api_base import COST_SENTINEL, today
from apps.catalog.models import Item, ItemImage, ItemPrice

from .base import (
    EXPORT_URL, HEADERS_FULL, HEADERS_NO_PRICE, SELL_PRICE, ItemFilesBase, open_xlsx, sheet_rows,
)


class ExportContentTests(ItemFilesBase):
    def test_s3_ac1_owner_gets_17_columns_in_order_with_current_price(self):
        resp = self.get(self.owner)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        rows = sheet_rows(resp)
        self.assertEqual(rows[0], HEADERS_FULL)
        self.assertEqual(len(rows), 4)  # tiêu đề + 3 món
        self.assertEqual([r[0] for r in rows[1:]], ["CA01", "CB01", "TOM01"])  # sắp theo mã
        ca = rows[1]
        self.assertEqual(ca[1], "Cá thu")
        self.assertEqual(ca[2], "Cá")
        self.assertEqual(ca[3], "Mặt hàng thường")
        self.assertEqual(rows[2][3], "Combo")
        self.assertEqual(ca[4], "Kg")
        self.assertEqual(ca[14], 278000)
        self.assertIsNone(ca[15])
        self.assertIsNone(ca[16])
        self.assertEqual(resp["X-Row-Count"], "3")
        self.assertEqual(resp["Cache-Control"], "no-store")

    def test_s3_ac1_filename_uses_vietnam_time(self):
        resp = self.get(self.owner)
        disposition = resp["Content-Disposition"]
        self.assertRegex(disposition, r'^attachment; filename="hang-ban-\d{8}-\d{4}\.xlsx"$')
        stamp = disposition.split("hang-ban-")[1][:8]
        self.assertEqual(stamp, timezone.localtime().strftime("%Y%m%d"))

    def test_s3_ac2_manager_gets_full_columns(self):
        rows = sheet_rows(self.get(self.manager))
        self.assertEqual(rows[0], HEADERS_FULL)
        self.assertEqual(rows[1][14], 278000)

    def test_s3_ac3_warehouse_staff_has_no_price_columns(self):
        resp = self.get(self.warehouse_staff)
        self.assertEqual(resp.status_code, 200)
        rows = sheet_rows(resp)
        self.assertEqual(rows[0], HEADERS_NO_PRICE)
        for row in rows:
            self.assertEqual(len(row), 14)
            self.assertNotIn(int(SELL_PRICE), row)
            self.assertNotIn("278000", [str(c) for c in row])

    def test_s3_ac5_no_cost_in_any_cell_for_any_role(self):
        allowed = {"owner": HEADERS_FULL, "manager": HEADERS_FULL, "warehouse_staff": HEADERS_NO_PRICE}
        users = {"owner": self.owner, "manager": self.manager, "warehouse_staff": self.warehouse_staff}
        for role, user in users.items():
            with self.subTest(role=role):
                wb = open_xlsx(self.get(user))
                self.assertEqual(len(wb.sheetnames), 2)
                for ws in wb.worksheets:
                    for row in ws.iter_rows(values_only=True):
                        for cell in row:
                            self.assertNotEqual(str(cell), COST_SENTINEL)
                            text = str(cell or "").lower()
                            for bad in ("giá vốn", "giá mua", "landed", "purchase", "nhà cung cấp", "đầu mối giả"):
                                self.assertNotIn(bad, text)
                header = [c.value for c in wb["Hàng bán"][1]]
                self.assertEqual(header, allowed[role])  # so khớp tuyệt đối

    def test_s3_ac11_types_and_flags(self):
        rows = sheet_rows(self.get(self.owner))
        ca = rows[1]
        self.assertIsInstance(ca[14], int)
        self.assertIsInstance(ca[6], int)
        self.assertEqual(ca[6], 365)
        self.assertEqual(ca[5], "Có")
        self.assertEqual(rows[3][5], "Không")  # TOM01 is_active=False
        ws = open_xlsx(self.get(self.owner))["Hàng bán"]
        self.assertEqual(ws["Q2"].number_format, "dd/mm/yyyy")
        self.assertEqual(ws["O2"].number_format, "#,##0")

    def test_s3_ac1_current_price_is_the_one_in_effect_today(self):
        ItemPrice.objects.filter(item=self.item_a).update(valid_upto=today() - datetime.timedelta(days=1))
        ItemPrice.objects.create(
            item=self.item_a, price_list=self.price_list, rate=Decimal("300000"), valid_from=today()
        )
        ItemPrice.objects.create(
            item=self.item_a, price_list=self.price_list, rate=Decimal("999000"),
            valid_from=today() + datetime.timedelta(days=5),
        )
        self.assertEqual(sheet_rows(self.get(self.owner))[1][14], 300000)

    def test_s3_ac1_item_without_price_has_empty_price_cell(self):
        self.assertIsNone(sheet_rows(self.get(self.owner))[3][14])

    def test_workbook_metadata_has_no_user_name(self):
        wb = open_xlsx(self.get(self.owner))
        self.assertEqual(wb.properties.creator, "Cá Về")
        self.assertNotIn("u_owner", str(wb.properties.lastModifiedBy or ""))
        self.assertEqual(wb.sheetnames, ["Hàng bán", "Hướng dẫn"])
        self.assertEqual(wb["Hàng bán"].freeze_panes, "A2")

    def test_read_only_columns_are_grey(self):
        ws = open_xlsx(self.get(self.owner))["Hàng bán"]
        for col in ("D", "E", "O"):
            self.assertEqual(ws[f"{col}2"].fill.fill_type, "solid", col)
        self.assertNotEqual(ws["B2"].fill.fill_type, "solid")


class ExportFilterTests(ItemFilesBase):
    def codes(self, **params):
        return [r[0] for r in sheet_rows(self.get(self.owner, **params))[1:]]

    def test_s3_ac6_filters_match_list_filters(self):
        self.assertEqual(self.codes(item_group=self.group_fish.pk), ["CA01", "CB01"])
        self.assertEqual(self.codes(is_active="1"), ["CA01", "CB01"])
        self.assertEqual(self.codes(is_active="0"), ["TOM01"])
        self.assertEqual(self.codes(item_type="BUNDLE"), ["CB01"])
        self.assertEqual(self.codes(item_group=self.group_fish.pk, is_active="1", item_type="SIMPLE"), ["CA01"])

    def test_s3_ac6_has_image_filter(self):
        self.assertEqual(self.codes(has_image="1"), [])
        self.assertEqual(self.codes(has_image="0"), ["CA01", "CB01", "TOM01"])
        ItemImage.objects.create(item=self.item_a, **_image_kwargs())
        self.assertEqual(self.codes(has_image="1"), ["CA01"])
        self.assertEqual(self.codes(has_image="0"), ["CB01", "TOM01"])

    def test_s3_ac7_empty_result_still_returns_header_only_file(self):
        resp = self.get(self.owner, item_group=999999)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(sheet_rows(resp), [HEADERS_FULL])
        self.assertEqual(resp["X-Row-Count"], "0")

    def test_s3_ac8_invalid_filter_is_400(self):
        for params in ({"item_type": "abc"}, {"is_active": "maybe"}, {"item_group": "x"}, {"has_image": "zz"}):
            with self.subTest(params=params):
                resp = self.get(self.owner, **params)
                self.assertEqual(resp.status_code, 400)
                self.assertEqual(resp.json()["code"], "INVALID_FILTER")

    def test_s3_ac8_item_type_value_from_story_draft_is_rejected(self):
        self.assertEqual(self.get(self.owner, item_type="item").status_code, 400)


def _image_kwargs():
    """Điền các field bắt buộc của ItemImage theo model thật (không đoán tên)."""
    kwargs = {}
    for field in ItemImage._meta.get_fields():
        if getattr(field, "concrete", False) and not field.is_relation and not field.primary_key \
                and not getattr(field, "null", False) and not field.has_default() \
                and not getattr(field, "auto_now_add", False) and not getattr(field, "auto_now", False):
            internal = field.get_internal_type()
            if internal in ("CharField", "TextField", "SlugField"):
                kwargs[field.name] = "x" * min(8, getattr(field, "max_length", None) or 8)
            elif internal in ("PositiveIntegerField", "IntegerField", "PositiveSmallIntegerField", "BigIntegerField"):
                kwargs[field.name] = 1
    return kwargs


class ExportPermissionTests(ItemFilesBase):
    def test_s3_ac4_delivery_and_customer_service_get_403(self):
        for user in (self.courier, self.customer_service, self.no_group):
            with self.subTest(user=user.username):
                resp = self.get(user)
                self.assertEqual(resp.status_code, 403)
                self.assertNotIn("openxml", resp.get("Content-Type", ""))
        self.assertFalse(AuditLog.objects.filter(action="export_items").exists())

    def test_s3_ac4_anonymous_gets_401(self):
        self.assertEqual(self.get(None).status_code, 401)

    def test_s3_ac4_only_get_is_allowed(self):
        self.assertEqual(self.client_as(self.owner).post(EXPORT_URL, {}).status_code, 405)


class ExportFormulaInjectionTests(ItemFilesBase):
    def test_s3_ac10_dangerous_cells_are_text_with_quote_prefix(self):
        payloads = {
            "description": '=HYPERLINK("http://x","y")',
            "short_note": "+cmd",
            "spec": "-1+1",
            "storage": "@SUM(1)",
            "origin": "\tabc",
        }
        Item.objects.filter(pk=self.item_a.pk).update(**payloads)
        Item.objects.filter(pk=self.item_b.pk).update(description="\nxuống dòng đầu", short_note="\rcr", name="=1+1")
        ws = open_xlsx(self.get(self.owner))["Hàng bán"]
        for row in ws.iter_rows():
            for cell in row:
                self.assertNotEqual(cell.data_type, "f", cell.coordinate)
        by_header = {c.value: i for i, c in enumerate(ws[1])}
        ca = list(ws[2])
        for field, label in (("description", "Mô tả"), ("short_note", "Ghi chú ngắn"), ("spec", "Quy cách"),
                             ("storage", "Bảo quản"), ("origin", "Nguồn hàng")):
            cell = ca[by_header[label]]
            self.assertEqual(cell.value, payloads[field], field)  # nguyên chữ, không thêm dấu '
            self.assertEqual(cell.data_type, "s")
            self.assertTrue(cell.quotePrefix, field)
        tom = list(ws[4])
        self.assertEqual(tom[by_header["Mô tả"]].value, "\nxuống dòng đầu")
        self.assertTrue(tom[by_header["Mô tả"]].quotePrefix)
        self.assertTrue(tom[by_header["Ghi chú ngắn"]].quotePrefix)
        self.assertEqual(tom[by_header["Tên"]].value, "=1+1")
        self.assertTrue(tom[by_header["Tên"]].quotePrefix)

    def test_s3_ac10_safe_text_has_no_quote_prefix(self):
        ws = open_xlsx(self.get(self.owner))["Hàng bán"]
        self.assertFalse(ws["B2"].quotePrefix)

    def test_s3_ac10_group_name_and_code_are_also_protected(self):
        self.group_fish.name = "=evil"
        self.group_fish.save()
        Item.objects.filter(pk=self.item_a.pk).update(code="@x")
        ws = open_xlsx(self.get(self.owner))["Hàng bán"]
        for row in ws.iter_rows():
            for cell in row:
                self.assertNotEqual(cell.data_type, "f")
        found = [c for row in ws.iter_rows() for c in row if c.value in ("=evil", "@x")]
        self.assertEqual(len(found), 3)  # =evil ở CA01 và CB01, @x
        self.assertTrue(all(c.quotePrefix for c in found))


class ExportAuditTests(ItemFilesBase):
    def test_s3_ac12_audit_row_has_counts_only(self):
        self.get(self.owner)
        log = AuditLog.objects.get(action="export_items")
        self.assertEqual(log.actor, self.owner)
        self.assertEqual(log.changes, {"rows": 3, "with_prices": True})
        self.assertEqual(log.note, "")
        blob = f"{log.changes}{log.note}{log.object_repr}"
        for text in ("Cá thu", "Tôm sú", "CA01"):
            self.assertNotIn(text, blob)

    def test_s3_ac12_warehouse_export_audit_says_no_prices(self):
        self.get(self.warehouse_staff, item_type="SIMPLE")
        log = AuditLog.objects.get(action="export_items")
        self.assertEqual(log.changes, {"rows": 2, "with_prices": False})

    def test_s3_ac12_filter_text_not_in_audit(self):
        self.get(self.owner, item_group=self.group_fish.pk)
        log = AuditLog.objects.get(action="export_items")
        self.assertEqual(set(log.changes), {"rows", "with_prices"})

    def test_failed_export_writes_no_audit(self):
        self.get(self.owner, item_type="abc")
        self.get(self.courier)
        self.assertFalse(AuditLog.objects.filter(action="export_items").exists())


class ExportQueryCountTests(ItemFilesBase):
    def _count(self, user):
        self.get(user)  # làm nóng bộ nhớ đệm quyền, để chỉ đếm truy vấn phụ thuộc số món
        with CaptureQueriesContext(connection) as ctx:
            self.get(user)
        return len(ctx)

    def test_s3_ac13_query_count_does_not_grow_with_items(self):
        base = self._count(self.owner)
        for i in range(50):
            item = Item.objects.create(code=f"BULK{i:03d}", name=f"Món {i}", item_group=self.group_fish)
            ItemPrice.objects.create(item=item, price_list=self.price_list, rate=Decimal("10000"), valid_from=today())
        self.assertEqual(self._count(self.owner), base)
        self.assertLessEqual(base, 12)

    def test_s3_ac13_query_count_for_warehouse_staff_is_constant_too(self):
        base = self._count(self.warehouse_staff)
        for i in range(50):
            Item.objects.create(code=f"BULK{i:03d}", name=f"Món {i}", item_group=self.group_shrimp)
        self.assertEqual(self._count(self.warehouse_staff), base)


class ExportCorsTests(ItemFilesBase):
    @override_settings(CORS_ALLOWED_ORIGINS=["https://erp.example.test"])
    def test_expose_headers_are_listed_for_allowed_origin(self):
        resp = self.client_as(self.owner).get(EXPORT_URL, HTTP_ORIGIN="https://erp.example.test")
        exposed = [h.strip().lower() for h in resp["Access-Control-Expose-Headers"].split(",")]
        self.assertIn("content-disposition", exposed)
        self.assertIn("x-row-count", exposed)

    def test_settings_declare_expose_headers(self):
        from django.conf import settings
        self.assertEqual(set(settings.CORS_EXPOSE_HEADERS), {"Content-Disposition", "X-Row-Count"})


class ExportSettingsTests(ItemFilesBase):
    def test_import_parameters_exist_with_defaults(self):
        from django.conf import settings
        self.assertEqual(settings.ITEM_IMPORT_MAX_ROWS, 1000)
        self.assertEqual(settings.ITEM_IMPORT_MAX_BYTES, 2097152)
        self.assertEqual(settings.ITEM_IMPORT_MAX_UNPACKED_BYTES, 26214400)
        self.assertEqual(settings.ITEM_IMPORT_PREVIEW_TTL_MINUTES, 30)
        self.assertEqual(settings.ITEM_IMPORT_PRICE_ALERT_PERCENT, 30)
        self.assertEqual(settings.ITEM_IMPORT_PRICE_ZERO_FACTOR, 5)

    def test_openpyxl_uses_defusedxml(self):
        import openpyxl.xml
        self.assertTrue(openpyxl.xml.DEFUSEDXML)
