"""FISH-66 S5, S6: xem trước thay đổi khi nhập Excel (plan.py, services.preview_import, 02b §3.5, §4.2, §4.3, §9). Dữ liệu giả."""
import datetime
from decimal import Decimal
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import AuditLog
from apps.catalog.items.tests.api_base import COST_SENTINEL, find_cost_keys, today
from apps.catalog.models import Item, ItemPrice
from apps.sales.models import Customer, SalesOrder, SalesOrderLine

from .base import EXPORT_URL, HEADERS_FULL, TEMPLATE_URL, ItemFilesBase
from .test_reader import _workbook_bytes


class PreviewPlanTests(ItemFilesBase):
    def test_s5_ac4_and_s6_ac13_reimporting_exported_file_unchanged_has_no_changes_even_with_control_chars(self):
        # Giả lập DB có ký tự điều khiển cũ để kiểm chuẩn hoá round-trip (02b §13.2).
        Item.objects.filter(pk=self.item_a.pk).update(description="Cá thu tươi\x07ngon")
        exported = self.get(self.owner, EXPORT_URL)
        self.assertEqual(exported.status_code, 200)

        audit_before = AuditLog.objects.count()
        resp = self.post_preview(self.owner, SimpleUploadedFile("unchanged.xlsx", exported.content))
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertFalse(body["has_changes"])
        self.assertIsNone(body["preview_token"])
        self.assertIsNone(body["expires_at"])
        self.assertEqual(body["rows"], [])
        self.assertEqual(body["summary"]["unchanged"], 3)
        self.assertEqual(body["summary"]["created"], 0)
        self.assertEqual(body["summary"]["updated"], 0)
        self.assertEqual(body["summary"]["price_changed"], 0)
        self.assertEqual(AuditLog.objects.count(), audit_before)

    def test_s4_ac2_uploading_unmodified_template_rejects_vd_001_example_row(self):
        tpl = self.get(self.owner, TEMPLATE_URL)
        resp = self.post_preview(self.owner, SimpleUploadedFile("mau-hang-ban.xlsx", tpl.content))
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["code"], "IMPORT_INVALID_ROWS")
        self.assertEqual(body["errors"][0]["code"], "VD-001")
        self.assertEqual(body["errors"][0]["message"], "Đây là dòng ví dụ, hãy xoá hoặc đổi mã.")

    def test_s5_ac1_ac2_ac3_ac14_full_preview_with_new_item_update_visibility_price_flags_and_warnings(self):
        # Thêm giá hiện hành cho CB01 (240.000) để thử large_change + backdated, và CA01 (278.000) thử check_zeros (27.800).
        ItemPrice.objects.create(
            item=self.combo,
            price_list=self.price_list,
            rate=Decimal("240000"),
            valid_from=today() - datetime.timedelta(days=10),
        )
        backdated_day = today() - datetime.timedelta(days=2)
        tomorrow = today() + datetime.timedelta(days=1)

        rows = [
            # Dòng 2: CA01 sửa tên + sửa nhầm cột chỉ đọc Giá bán hiện hành (999999) + giá mới dính check_zeros & large_change
            {
                "code": "CA01",
                "name": "Cá thu một nắng",
                "item_group": "Cá",
                "item_type": "Mặt hàng thường",
                "stock_uom": "Kg",
                "is_active": True,
                "shelf_life_in_days": 365,
                "has_batch_no": True,
                "has_expiry_date": True,
                "short_note": "Cắt khúc dày",
                "current_price": 999999,
                "new_price": 27800,
                "new_price_from": today(),
            },
            # Dòng 3: CB01 chỉ đổi giá +37.5% (large_change) và lùi ngày (backdated), giữ nguyên các cột mặt hàng
            {
                "code": "CB01",
                "name": "Combo thử",
                "item_group": "Cá",
                "item_type": "Combo",
                "stock_uom": "Kg",
                "is_active": True,
                "shelf_life_in_days": 365,
                "has_batch_no": True,
                "has_expiry_date": True,
                "current_price": 240000,
                "new_price": 330000,
                "new_price_from": backdated_day,
            },
            # Dòng 4: TOM01 đang ẩn -> bật Đang kinh doanh (visibility_changed: will_show), giữ nguyên hạn dùng 365
            {
                "code": "TOM01",
                "name": "Tôm sú",
                "item_group": "Tôm",
                "item_type": "Mặt hàng thường",
                "stock_uom": "Kg",
                "is_active": True,
                "shelf_life_in_days": 365,
                "has_batch_no": True,
                "has_expiry_date": True,
            },
            # Dòng 5: Món mới MUC01 kèm giá mới (S5-AC2: will_show)
            {
                "code": "MUC01",
                "name": "Mực ống tươi",
                "item_group": "Tôm",
                "item_type": "Mặt hàng thường",
                "stock_uom": "Kg",
                "is_active": True,
                "shelf_life_in_days": 90,
                "has_batch_no": True,
                "has_expiry_date": True,
                "new_price": 195000,
                "new_price_from": tomorrow,
            },
        ]

        items_before = Item.objects.count()
        prices_before = ItemPrice.objects.count()
        audits_before = AuditLog.objects.count()

        resp = self.post_preview(self.owner, self.make_xlsx_file(rows))
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()

        # Preview tuyệt đối không ghi DB hay AuditLog (S5-AC1, S5-AC15)
        self.assertEqual(Item.objects.count(), items_before)
        self.assertEqual(ItemPrice.objects.count(), prices_before)
        self.assertEqual(AuditLog.objects.count(), audits_before)

        # S5-AC14: Không rò giá vốn trong JSON xem trước
        self.assertEqual(find_cost_keys(body), set())
        self.assertNotIn(COST_SENTINEL, json.dumps(body, ensure_ascii=False))

        self.assertTrue(body["has_changes"])
        self.assertTrue(body["preview_token"])
        self.assertTrue(body["expires_at"])

        summary = body["summary"]
        self.assertEqual(summary["total_rows"], 4)
        self.assertEqual(summary["created"], 1)
        self.assertEqual(summary["updated"], 1)
        self.assertEqual(summary["visibility_changed"], 1)
        self.assertEqual(summary["price_changed"], 3)
        self.assertEqual(summary["unchanged"], 0)
        # M2: MUC01 có giá từ ngày mai, TOM01 bật lại nhưng chưa có giá → chưa món nào hiện thật trên Shop
        self.assertEqual(summary["will_show_on_shop"], 0)

        rows_by_code = {r["code"]: r for r in body["rows"]}
        self.assertEqual(rows_by_code["CA01"]["price"]["flags"], ["check_zeros", "large_change"])
        self.assertEqual(rows_by_code["CA01"]["price"]["change_percent"], "-90.0")
        self.assertEqual(set(rows_by_code["CB01"]["price"]["flags"]), {"large_change", "backdated"})
        self.assertEqual(rows_by_code["CB01"]["price"]["change_percent"], "37.5")
        self.assertEqual(rows_by_code["MUC01"]["action"], "create")
        self.assertEqual(rows_by_code["MUC01"]["shop_state"], "hidden")
        self.assertEqual(rows_by_code["TOM01"]["changes"][0]["field"], "is_active")
        self.assertEqual(rows_by_code["TOM01"]["changes"][0]["old"], "Không")
        self.assertEqual(rows_by_code["TOM01"]["changes"][0]["new"], "Có")

        # Cảnh báo sửa cột chỉ đọc Giá bán hiện hành ở dòng 2
        self.assertEqual(len(body["warnings"]), 1)
        self.assertEqual(body["warnings"][0]["column"], "Giá bán hiện hành")
        self.assertEqual(body["warnings"][0]["row"], 2)

    @override_settings(ITEM_IMPORT_PRICE_ZERO_FACTOR=4, ITEM_IMPORT_PRICE_ALERT_PERCENT=25)
    def test_price_flag_thresholds_read_from_settings(self):
        # Giá hiện hành của CA01 là 278.000; đặt giá mới 69.500 (đúng 1/4 = check_zeros khi factor=4)
        rows = [
            {
                "code": "CA01",
                "name": "Cá thu",
                "item_group": "Cá",
                "is_active": True,
                "new_price": 69500,
            }
        ]
        resp = self.post_preview(self.owner, self.make_xlsx_file(rows))
        self.assertEqual(resp.status_code, 200)
        flags = resp.json()["rows"][0]["price"]["flags"]
        self.assertIn("check_zeros", flags)
        self.assertIn("large_change", flags)

    def test_s5_ac17_blank_optional_text_keeps_existing_db_value_and_same_price_is_ignored(self):
        Item.objects.filter(pk=self.item_a.pk).update(
            short_note="Ghi chú cũ giữ nguyên",
            description="Mô tả cũ giữ nguyên",
        )
        rows = [
            {
                "code": "CA01",
                "name": "Cá thu",
                "item_group": "Cá",
                "item_type": "Mặt hàng thường",
                "stock_uom": "Kg",
                "is_active": True,
                "shelf_life_in_days": 365,
                "has_batch_no": True,
                "has_expiry_date": True,
                "short_note": "",
                "description": "",
                "new_price": 278000,  # trùng đúng giá hiện hành
            }
        ]
        resp = self.post_preview(self.owner, self.make_xlsx_file(rows))
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertFalse(body["has_changes"])
        self.assertEqual(body["summary"]["unchanged"], 1)

    def test_s5_ac11_accepts_dot_thousands_price_vn_date_and_case_insensitive_flags(self):
        future_str = (today() + datetime.timedelta(days=5)).strftime("%d/%m/%Y")
        raw_row = [
            "CA01", "Cá thu", "Cá", "Mặt hàng thường", "Kg", "có", 365, "CÓ", "không",
            "", "", "", "", "", "278.000", "295.000", future_str,
        ]
        wb_bytes = _workbook_bytes(HEADERS_FULL, [raw_row])
        resp = self.post_preview(self.owner, SimpleUploadedFile("dot.xlsx", wb_bytes))
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertTrue(body["has_changes"])
        self.assertEqual(body["rows"][0]["price"]["new"], "295000")
        self.assertEqual(body["rows"][0]["changes"][0]["field"], "has_expiry_date")

    def test_s5_ac6_ac7_ac8_collects_all_row_errors_across_entire_file_without_stopping_early(self):
        from django.utils import timezone

        # Tạo đơn hàng ở ngày hôm qua cho CA01 để kiểm BR-DM-02 (chặn lùi ngày đè lên đơn đã có)
        customer = Customer.objects.create(name="Khách giả", phone="0900000001")
        order = SalesOrder.objects.create(
            code="SO261114-TEST01",
            customer=customer,
            status=SalesOrder.Status.PAID,
            delivery_address="Địa chỉ giả",
            phone="0900000001",
        )
        SalesOrder.objects.filter(pk=order.pk).update(created_at=timezone.now() - datetime.timedelta(days=1))
        SalesOrderLine.objects.create(
            order=order,
            item=self.item_a,
            qty=Decimal("1.0"),
            rate=Decimal("278000"),
            amount=Decimal("278000"),
        )

        # Tạo giá tương lai cho TOM01 ở +10 ngày để kiểm BR-DM-03 (chồng lấn khoảng hiệu lực)
        future_10 = today() + datetime.timedelta(days=10)
        ItemPrice.objects.create(
            item=self.item_b,
            price_list=self.price_list,
            rate=Decimal("310000"),
            valid_from=future_10,
        )

        bad_rows = [
            # Dòng 2: Trùng mã DUP01 (lần 1) + nhóm chưa có + giá âm
            ["DUP01", "Món lặp 1", "Nhóm Ma", "Mặt hàng thường", "Kg", "Có", 365, "Có", "Có", "", "", "", "", "", None, -5000, None],
            # Dòng 3: Trùng mã dup01 (lần 2, khác hoa/thường) + có ngày áp dụng nhưng không có giá mới
            ["dup01", "Món lặp 2", "Cá", "Mặt hàng thường", "Kg", "Có", 365, "Có", "Có", "", "", "", "", "", None, None, "20/12/2026"],
            # Dòng 4: Mã mới ca01 trùng chữ hoa/thường với CA01 đã có + Q-TL-2 Tên chứa SĐT/giá
            ["ca01", "Cá thu 0912345678", "Cá", "Mặt hàng thường", "Kg", "Có", 365, "Có", "Có", "", "", "", "", "", None, None, None],
            # Dòng 5: Tạo mới Combo qua Excel bị chặn (S5-AC8)
            ["CB_NEW", "Combo mới", "Cá", "Combo", "Kg", "Có", 365, "Không", "Không", "", "", "", "", "", None, 200000, None],
            # Dòng 6: CA01 đặt giá lùi về trước ngày có đơn hàng (BR-DM-02, S5-AC7)
            ["CA01", "Cá thu", "Cá", "Mặt hàng thường", "Kg", "Có", 365, "Có", "Có", "", "", "", "", "", 278000, 260000, (today() - datetime.timedelta(days=2)).strftime("%d/%m/%Y")],
            # Dòng 7: TOM01 đặt giá chồng lấn giá tương lai đã có (BR-DM-03, S5-AC7)
            ["TOM01", "Tôm sú", "Tôm", "Mặt hàng thường", "Kg", "Không", 365, "Có", "Có", "", "", "", "", "", None, 300000, (today() + datetime.timedelta(days=5)).strftime("%d/%m/%Y")],
            # Dòng 8: Cột chữ công khai chứa thông tin nhà cung cấp / lô + giá dấu phẩy 278,000
            ["MUC02", "Mực lá", "Cá", "Mặt hàng thường", "Kg", "Có", 365, "Có", "Có", "Nhà cung cấp Hùng", "", "", "", "", None, "278,000", None],
            # Dòng 9: Combo CB01 sửa Nhóm hàng bị chặn (BR-DM-33)
            ["CB01", "Combo thử", "Tôm", "Combo", "Kg", "Có", 365, "Có", "Có", "", "", "", "", "", None, None, None],
        ]
        wb_bytes = _workbook_bytes(HEADERS_FULL, bad_rows)
        resp = self.post_preview(self.owner, SimpleUploadedFile("bad.xlsx", wb_bytes))
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["code"], "IMPORT_INVALID_ROWS")
        self.assertEqual(body["error_row_count"], 8)
        self.assertGreaterEqual(body["error_count"], 10)

        by_row_col = {(e["row"], e["column"]): e["message"] for e in body["errors"]}
        self.assertIn("lặp ở dòng 2 và 3", by_row_col[(2, "Mã hàng")])
        self.assertIn("Nhóm Ma", by_row_col[(2, "Nhóm hàng")])
        self.assertIn("số nguyên đồng", by_row_col[(2, "Giá mới")])
        self.assertIn("chưa có giá mới", by_row_col[(3, "Ngày áp dụng giá mới")])
        self.assertIn("gần trùng mã CA01", by_row_col[(4, "Mã hàng")])
        self.assertTrue(by_row_col[(4, "Tên")])
        self.assertIn("combo", by_row_col[(5, "Loại")].lower())
        self.assertIn("đơn hàng", by_row_col[(6, "Ngày áp dụng giá mới")].lower())
        self.assertIn("chồng", by_row_col[(7, "Ngày áp dụng giá mới")].lower())
        self.assertTrue(by_row_col[(8, "Ghi chú ngắn")])
        self.assertIn("số nguyên đồng", by_row_col[(8, "Giá mới")])
        self.assertIn("Combo chỉ sửa", by_row_col[(9, "Nhóm hàng")])

    def test_s5_ac16_query_count_is_constant_regardless_of_row_count(self):
        small_rows = [
            {"code": f"NEW{i:03d}", "name": f"Cá mới {i}", "item_group": "Cá", "is_active": True, "new_price": 150000 + i * 1000}
            for i in range(5)
        ]
        large_rows = [
            {"code": f"BIG{i:03d}", "name": f"Cá lớn {i}", "item_group": "Cá", "is_active": True, "new_price": 150000 + i * 1000}
            for i in range(60)
        ]
        f_small = self.make_xlsx_file(small_rows)
        f_large = self.make_xlsx_file(large_rows)

        # Làm nóng bộ nhớ đệm quyền của user trước khi đếm số câu SQL
        self.post_preview(self.owner, f_small)

        with CaptureQueriesContext(connection) as q_small:
            r1 = self.post_preview(self.owner, f_small)
        self.assertEqual(r1.status_code, 200)

        with CaptureQueriesContext(connection) as q_large:
            r2 = self.post_preview(self.owner, f_large)
        self.assertEqual(r2.status_code, 200)

        self.assertEqual(len(q_small), len(q_large))
        self.assertLessEqual(len(q_large), 10)


class ShopStateTests(ItemFilesBase):
    def _row(self, code, **extra):
        base = {
            "code": code, "name": f"Món {code}", "item_group": "Tôm", "item_type": "Mặt hàng thường",
            "stock_uom": "Kg", "is_active": True, "shelf_life_in_days": 90,
            "has_batch_no": True, "has_expiry_date": True,
        }
        base.update(extra)
        return base

    def _preview(self, rows):
        resp = self.post_preview(self.owner, self.make_xlsx_file(rows))
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def test_t8_new_item_with_future_price_is_hidden_not_will_show(self):
        body = self._preview([self._row("MUC02", new_price=195000, new_price_from=today() + datetime.timedelta(days=1))])
        self.assertEqual(body["rows"][0]["shop_state"], "hidden")
        self.assertEqual(body["summary"]["will_show_on_shop"], 0)

    def test_t8_new_item_with_price_from_today_is_will_show(self):
        body = self._preview([self._row("MUC03", new_price=195000, new_price_from=today())])
        self.assertEqual(body["rows"][0]["shop_state"], "will_show")
        self.assertEqual(body["summary"]["will_show_on_shop"], 1)

    def test_t8_reactivated_item_without_effective_price_is_hidden(self):
        # TOM01 đang ẩn và chưa có giá nào
        body = self._preview([self._row("TOM01", name="Tôm sú")])
        row = body["rows"][0]
        self.assertEqual(row["shop_state"], "hidden")
        self.assertEqual(body["summary"]["will_show_on_shop"], 0)

    def test_t8_reactivated_item_with_only_future_price_is_hidden(self):
        body = self._preview([
            self._row("TOM01", name="Tôm sú", new_price=310000, new_price_from=today() + datetime.timedelta(days=3))
        ])
        self.assertEqual(body["rows"][0]["shop_state"], "hidden")
        self.assertEqual(body["summary"]["will_show_on_shop"], 0)

    def test_t8_reactivated_item_with_effective_price_is_will_show(self):
        ItemPrice.objects.create(
            item=self.item_b, price_list=self.price_list, rate=Decimal("310000"),
            valid_from=today() - datetime.timedelta(days=5),
        )
        body = self._preview([self._row("TOM01", name="Tôm sú")])
        self.assertEqual(body["rows"][0]["shop_state"], "will_show")
        self.assertEqual(body["summary"]["will_show_on_shop"], 1)
