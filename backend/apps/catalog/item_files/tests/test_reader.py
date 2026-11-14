"""FISH-66 S5, S6: kiểm đọc file .xlsx an toàn (reader.py, 02b §3.5, §6.1, §9). Dữ liệu giả."""
import io
import socket
from unittest import mock
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from openpyxl import Workbook
import openpyxl.xml

from .base import HEADERS_FULL, ItemFilesBase


def _workbook_bytes(headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Hàng bán"
    ws.append(list(headers))
    for r in rows:
        ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class ReaderSecurityAndStructureTests(ItemFilesBase):
    def test_l5_openpyxl_uses_defusedxml_and_not_lxml(self):
        self.assertTrue(openpyxl.xml.DEFUSEDXML)
        self.assertFalse(openpyxl.xml.LXML)

    def test_s5_ac9_rejects_csv_xls_fake_xlsx_and_corrupt_files(self):
        cases = [
            ("bang-gia.csv", b"Ma hang,Ten\nCA01,Ca thu\n", "not_xlsx"),
            ("bang-gia.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1fake-ole2", "not_xlsx"),
            ("gia-doi-duoi.xlsx", b"Ma hang,Ten\nCA01,Ca thu\n", "not_xlsx"),
            ("rong.xlsx", b"", "unreadable"),
            ("hong.xlsx", b"PK\x03\x04truncated-zip-bytes", "unreadable"),
        ]
        for filename, content, expected_reason in cases:
            with self.subTest(filename=filename):
                up = SimpleUploadedFile(filename, content)
                resp = self.post_preview(self.owner, up)
                self.assertEqual(resp.status_code, 400)
                body = resp.json()
                self.assertEqual(body["code"], "IMPORT_INVALID_FILE")
                self.assertEqual(body["reason"], expected_reason)
                self.assertIn("limits", body)

    def test_s5_ac9_and_ac12_rejects_xlsm_macro_and_never_connects_network(self):
        sample_row = ["CA01", "Cá thu", "Cá", "Mặt hàng thường", "Kg", "Có", 365, "Có", "Có", "", "", "", "", "", None, None, None]
        valid_bytes = _workbook_bytes(HEADERS_FULL, [sample_row])
        resp_ext = self.post_preview(self.owner, SimpleUploadedFile("macro.xlsm", valid_bytes))
        self.assertEqual(resp_ext.status_code, 400)
        self.assertEqual(resp_ext.json()["code"], "IMPORT_INVALID_FILE")
        self.assertEqual(resp_ext.json()["reason"], "not_xlsx")

        # File .xlsx nhưng bên trong có vbaProject.bin
        macro_buf = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(valid_bytes), "r") as zin, zipfile.ZipFile(macro_buf, "w") as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
            zout.writestr("xl/vbaProject.bin", b"fake-vba")
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("Không được gọi mạng")):
            resp_vba = self.post_preview(self.owner, SimpleUploadedFile("co-vba.xlsx", macro_buf.getvalue()))
        self.assertEqual(resp_vba.status_code, 400)
        self.assertEqual(resp_vba.json()["code"], "IMPORT_INVALID_FILE")
        self.assertEqual(resp_vba.json()["reason"], "not_xlsx")

    @override_settings(ITEM_IMPORT_MAX_BYTES=1024)
    def test_s5_ac9_rejects_file_exceeding_max_bytes(self):
        big = SimpleUploadedFile("qua-lon.xlsx", b"PK\x03\x04" + b"0" * 2048)
        resp = self.post_preview(self.owner, big)
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["code"], "IMPORT_INVALID_FILE")
        self.assertEqual(body["reason"], "too_large")
        self.assertEqual(body["limits"]["max_bytes"], 1024)

    @override_settings(ITEM_IMPORT_MAX_UNPACKED_BYTES=2000)
    def test_s5_ac9_rejects_zip_bomb_exceeding_unpacked_limit(self):
        sample_row = ["CA01", "Cá thu", "Cá", "Mặt hàng thường", "Kg", "Có", 365, "Có", "Có", "", "", "", "", "", None, None, None]
        valid_bytes = _workbook_bytes(HEADERS_FULL, [sample_row])
        resp = self.post_preview(self.owner, SimpleUploadedFile("bomb.xlsx", valid_bytes))
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["code"], "IMPORT_INVALID_FILE")
        self.assertEqual(body["reason"], "unreadable")

    @override_settings(ITEM_IMPORT_MAX_ROWS=3)
    def test_s5_ac9_rejects_more_than_max_rows_and_ignores_blank_rows(self):
        base_row = ["CA01", "Cá thu", "Cá", "Mặt hàng thường", "Kg", "Có", 365, "Có", "Có", "", "", "", "", "", None, None, None]
        four_rows = [
            ["CA01", *base_row[1:]],
            ["CA02", *base_row[1:]],
            ["CA03", *base_row[1:]],
            ["CA04", *base_row[1:]],
        ]
        resp = self.post_preview(self.owner, SimpleUploadedFile("4dong.xlsx", _workbook_bytes(HEADERS_FULL, four_rows)))
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["code"], "IMPORT_INVALID_FILE")
        self.assertEqual(body["reason"], "too_many_rows")
        self.assertEqual(body["limits"]["max_rows"], 3)

        # 3 dòng có chữ + 5 dòng trống hoàn toàn → vẫn được nhận
        three_plus_blanks = four_rows[:3] + [[None] * len(HEADERS_FULL) for _ in range(5)]
        resp_ok = self.post_preview(
            self.owner, SimpleUploadedFile("3dong.xlsx", _workbook_bytes(HEADERS_FULL, three_plus_blanks))
        )
        self.assertEqual(resp_ok.status_code, 200, resp_ok.content)

    def test_s5_ac10_missing_unknown_and_duplicate_columns(self):
        sample_row = ["CA01", "Cá thu", "Cá", "Mặt hàng thường", "Kg", "Có", 365, "Có", "Có", "", "", "", "", ""]
        # Thiếu cột bắt buộc Nhóm hàng
        missing_headers = [h for h in HEADERS_FULL if h != "Nhóm hàng"]
        resp_missing = self.post_preview(
            self.owner, SimpleUploadedFile("thieu.xlsx", _workbook_bytes(missing_headers, [sample_row]))
        )
        self.assertEqual(resp_missing.status_code, 400)
        body_missing = resp_missing.json()
        self.assertEqual(body_missing["code"], "IMPORT_INVALID_FILE")
        self.assertEqual(body_missing["reason"], "missing_columns")
        self.assertEqual(body_missing["columns"], ["Nhóm hàng"])
        self.assertIn("Nhóm hàng", body_missing["detail"])

        # Có Ngày áp dụng giá mới nhưng thiếu Giá mới
        no_new_price_headers = [h for h in HEADERS_FULL if h != "Giá mới"]
        resp_no_price = self.post_preview(
            self.owner, SimpleUploadedFile("thieu-gia.xlsx", _workbook_bytes(no_new_price_headers, [sample_row]))
        )
        self.assertEqual(resp_no_price.status_code, 400)
        self.assertEqual(resp_no_price.json()["reason"], "missing_columns")
        self.assertEqual(resp_no_price.json()["columns"], ["Giá mới"])

        # Cột lạ (vd Gia moi hoặc Giá mua)
        unknown_headers = [*(h for h in HEADERS_FULL if h != "Giá mới"), "Gia moi"]
        resp_unknown = self.post_preview(
            self.owner, SimpleUploadedFile("la.xlsx", _workbook_bytes(unknown_headers, [sample_row]))
        )
        self.assertEqual(resp_unknown.status_code, 400)
        body_unknown = resp_unknown.json()
        self.assertEqual(body_unknown["code"], "IMPORT_INVALID_FILE")
        self.assertEqual(body_unknown["reason"], "unknown_columns")
        self.assertIn("Gia moi", body_unknown["columns"])

        # Cột trùng tên
        dup_headers = [*HEADERS_FULL, "Giá mới"]
        resp_dup = self.post_preview(
            self.owner, SimpleUploadedFile("trung.xlsx", _workbook_bytes(dup_headers, [sample_row]))
        )
        self.assertEqual(resp_dup.status_code, 400)
        body_dup = resp_dup.json()
        self.assertEqual(body_dup["code"], "IMPORT_INVALID_FILE")
        self.assertEqual(body_dup["reason"], "duplicate_columns")
        self.assertEqual(body_dup["columns"], ["Giá mới"])

    def test_empty_rows_file_returns_import_invalid_file_empty(self):
        wb_bytes = _workbook_bytes(HEADERS_FULL, [])
        resp = self.post_preview(self.owner, SimpleUploadedFile("empty.xlsx", wb_bytes))
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["code"], "IMPORT_INVALID_FILE")
        self.assertEqual(body["reason"], "empty")

    def test_s5_ac12_uncached_formula_rejected_with_row_error_and_cached_formula_uses_cached_value(self):
        row_uncached = [
            "CA01", "Cá thu", "Cá", "Mặt hàng thường", "Kg", "Có", 365, "Có", "Có",
            "", "", "", "", "=1+1", 278000, "=100000+50000", None,
        ]
        wb_bytes = _workbook_bytes(HEADERS_FULL, [row_uncached])
        resp = self.post_preview(self.owner, SimpleUploadedFile("formula.xlsx", wb_bytes))
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["code"], "IMPORT_INVALID_ROWS")
        self.assertEqual(body["error_row_count"], 1)
        cols = {e["column"]: e["message"] for e in body["errors"]}
        self.assertEqual(cols["Mô tả"], "Ô có công thức, hãy dán giá trị.")
        self.assertEqual(cols["Giá mới"], "Ô có công thức, hãy dán giá trị.")
