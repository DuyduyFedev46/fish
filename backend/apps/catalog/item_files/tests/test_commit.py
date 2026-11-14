"""FISH-66 S6: xác nhận nhập mặt hàng từ Excel trong một giao dịch nguyên tử (02b §3.6, §5.3, §7, §9). Dữ liệu giả."""
import datetime
from decimal import Decimal
import json
import time
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import AuditLog
from apps.catalog.item_files import services
from apps.catalog.items.tests.api_base import COST_SENTINEL, find_cost_keys, today
from apps.catalog.models import Item, ItemPrice
from apps.inventory.models import Batch, StockLedgerEntry
from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine
from apps.sales.models import SalesOrder, SalesOrderLine

from .base import COMMIT_URL, EXPORT_URL, ItemFilesBase


class CommitImportTests(ItemFilesBase):
    def _sample_rows(self):
        return [
            # Sửa CA01 (tên, hạn dùng, ghi chú, mô tả) + đổi giá 278000 -> 290000 từ hôm nay
            {
                "code": "CA01",
                "name": "Cá thu cắt khúc",
                "item_group": "Cá",
                "is_active": True,
                "shelf_life_in_days": 180,
                "has_batch_no": True,
                "has_expiry_date": True,
                "short_note": "Khúc giữa dày",
                "description": "Mô tả an toàn cho khách",
                "new_price": 290000,
                "new_price_from": today(),
            },
            # Tạo mới MUC01 + đặt giá 195000 từ hôm nay
            {
                "code": "MUC01",
                "name": "Mực ống câu",
                "item_group": "Tôm",
                "is_active": True,
                "shelf_life_in_days": 90,
                "has_batch_no": True,
                "has_expiry_date": True,
                "spec": "Con 400-500 g",
                "new_price": 195000,
                "new_price_from": today(),
            },
        ]

    def test_s6_ac1_ac2_ac3_ac11_ac12_ac13_commit_applies_all_changes_writes_safe_audit_and_leaves_inventory_untouched(self):
        batches_before = list(
            Batch.objects.values_list("id", "qty_received", "qty_available", "qty_reserved", "purchase_rate", "landed_unit_cost")
        )
        sle_before = StockLedgerEntry.objects.count()
        pr_before = PurchaseReceipt.objects.count()
        prl_before = PurchaseReceiptLine.objects.count()
        so_before = SalesOrder.objects.count()
        sol_before = SalesOrderLine.objects.count()

        xlsx_file = self.make_xlsx_file(self._sample_rows())
        prev_resp = self.post_preview(self.owner, xlsx_file)
        self.assertEqual(prev_resp.status_code, 200, prev_resp.content)
        token = prev_resp.json()["preview_token"]

        commit_resp = self.post_commit(self.owner, xlsx_file, token)
        self.assertEqual(commit_resp.status_code, 200, commit_resp.content)
        body = commit_resp.json()

        self.assertEqual(body["created"], 1)
        self.assertEqual(body["updated"], 1)
        self.assertEqual(body["price_changed"], 2)
        self.assertEqual(body["visibility_changed"], 0)
        self.assertEqual(body["codes"], ["CA01", "MUC01"])
        self.assertEqual(find_cost_keys(body), set())
        self.assertNotIn(COST_SENTINEL, json.dumps(body, ensure_ascii=False))

        # Kiểm DB sau commit
        self.item_a.refresh_from_db()
        self.assertEqual(self.item_a.name, "Cá thu cắt khúc")
        self.assertEqual(self.item_a.shelf_life_in_days, 180)
        self.assertEqual(self.item_a.short_note, "Khúc giữa dày")
        self.assertEqual(self.item_a.description, "Mô tả an toàn cho khách")

        muc = Item.objects.get(code="MUC01")
        self.assertEqual(muc.name, "Mực ống câu")
        self.assertEqual(muc.item_group, self.group_shrimp)
        self.assertEqual(muc.spec, "Con 400-500 g")

        # Giá cũ của CA01 đã tự đóng ở ngày hôm qua, giá mới 290000 có hiệu lực từ hôm nay
        ca_prices = list(ItemPrice.objects.filter(item=self.item_a, price_list=self.price_list).order_by("valid_from"))
        self.assertEqual(len(ca_prices), 2)
        self.assertEqual(ca_prices[0].valid_upto, today() - datetime.timedelta(days=1))
        self.assertEqual(ca_prices[1].rate, Decimal("290000"))
        self.assertIsNone(ca_prices[1].valid_upto)

        muc_price = ItemPrice.objects.get(item=muc, price_list=self.price_list)
        self.assertEqual(muc_price.rate, Decimal("195000"))

        # Không đụng kho/lô/phiếu nhập/đơn bán (S6-AC3, BR-DM-32)
        self.assertEqual(
            list(
                Batch.objects.values_list("id", "qty_received", "qty_available", "qty_reserved", "purchase_rate", "landed_unit_cost")
            ),
            batches_before,
        )
        self.assertEqual(StockLedgerEntry.objects.count(), sle_before)
        self.assertEqual(PurchaseReceipt.objects.count(), pr_before)
        self.assertEqual(PurchaseReceiptLine.objects.count(), prl_before)
        self.assertEqual(SalesOrder.objects.count(), so_before)
        self.assertEqual(SalesOrderLine.objects.count(), sol_before)

        # Kiểm AuditLog (S6-AC2): có create_item, update_item, create_itemprice, import_items; không lộ chữ tự do hay giá vốn
        create_log = AuditLog.objects.get(action="create_item", object_id=str(muc.pk))
        self.assertEqual(create_log.note, "Nhập từ file Excel")
        self.assertIn("spec", create_log.changes["fields"])

        update_log = AuditLog.objects.get(action="update_item", object_id=str(self.item_a.pk))
        self.assertEqual(update_log.note, "Nhập từ file Excel")
        self.assertEqual(
            update_log.changes,
            {"fields": ["description", "name", "shelf_life_in_days", "short_note"]},
        )
        summary_log = AuditLog.objects.get(action="import_items")
        self.assertEqual(summary_log.changes["created"], 1)
        self.assertEqual(summary_log.changes["updated"], 1)
        self.assertEqual(summary_log.changes["price_changed"], 2)
        self.assertEqual(summary_log.changes["visibility_changed"], 0)
        self.assertTrue(summary_log.changes["import_ref"])

        for log in AuditLog.objects.all():
            blob = json.dumps(log.changes, ensure_ascii=False) + (log.note or "")
            self.assertNotIn("Mô tả an toàn cho khách", blob)
            self.assertNotIn("Khúc giữa dày", blob)
            self.assertNotIn("Con 400-500 g", blob)
            self.assertNotIn(COST_SENTINEL, blob)
            self.assertEqual(find_cost_keys(log.changes), set())

        # S6-AC11: Shop catalog hiện MUC01 với trạng thái hết hàng (chưa có lô)
        shop_resp = self.client.get("/api/shop/catalog/")
        self.assertEqual(shop_resp.status_code, 200)
        shop_items = {it["item_code"]: it for it in shop_resp.json()["items"]}
        self.assertIn("MUC01", shop_items)
        self.assertEqual(shop_items["MUC01"]["stock_level"], "out")

        # S6-AC13: Tải lại file sau khi nhập rồi xem trước → "File không có gì mới"
        exported_after = self.get(self.owner, EXPORT_URL)
        roundtrip_resp = self.post_preview(self.owner, SimpleUploadedFile("after.xlsx", exported_after.content))
        self.assertEqual(roundtrip_resp.status_code, 200)
        self.assertFalse(roundtrip_resp.json()["has_changes"])

    def test_s6_ac7_duplicate_commit_returns_409_import_already_applied_with_counts(self):
        xlsx_file = self.make_xlsx_file(self._sample_rows())
        prev = self.post_preview(self.owner, xlsx_file)
        token = prev.json()["preview_token"]

        first = self.post_commit(self.owner, xlsx_file, token)
        self.assertEqual(first.status_code, 200)

        items_count = Item.objects.count()
        prices_count = ItemPrice.objects.count()
        audits_count = AuditLog.objects.count()

        second = self.post_commit(self.owner, xlsx_file, token)
        self.assertEqual(second.status_code, 409)
        body = second.json()
        self.assertEqual(body["code"], "IMPORT_ALREADY_APPLIED")
        self.assertEqual(body["created"], 1)
        self.assertEqual(body["updated"], 1)
        self.assertEqual(body["price_changed"], 2)
        self.assertEqual(body["visibility_changed"], 0)

        # Không tạo thêm bất kỳ dòng nào
        self.assertEqual(Item.objects.count(), items_count)
        self.assertEqual(ItemPrice.objects.count(), prices_count)
        self.assertEqual(AuditLog.objects.count(), audits_count)

    def test_s6_ac5_error_mid_commit_rolls_back_all_items_prices_and_audit_logs(self):
        xlsx_file = self.make_xlsx_file(self._sample_rows())
        prev = self.post_preview(self.owner, xlsx_file)
        token = prev.json()["preview_token"]

        items_before = Item.objects.count()
        prices_before = ItemPrice.objects.count()
        audits_before = AuditLog.objects.count()

        with mock.patch("apps.catalog.item_files.services.set_item_price", side_effect=RuntimeError("Boom at line")):
            with self.assertRaises(RuntimeError):
                services.commit_import(user=self.owner, uploaded_file=xlsx_file, preview_token=token)

        self.assertEqual(Item.objects.count(), items_before)
        self.assertEqual(ItemPrice.objects.count(), prices_before)
        self.assertEqual(AuditLog.objects.count(), audits_before)

    def test_s6_ac6_data_changed_after_preview_returns_409_and_rolls_back(self):
        xlsx_file = self.make_xlsx_file(self._sample_rows())
        prev = self.post_preview(self.owner, xlsx_file)
        token = prev.json()["preview_token"]

        # Người khác sửa tên CA01 sau lúc preview
        self.item_a.name = "Cá thu vừa bị sửa"
        self.item_a.save(update_fields=["name"])

        resp = self.post_commit(self.owner, xlsx_file, token)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["code"], "IMPORT_DATA_CHANGED")
        self.assertFalse(Item.objects.filter(code="MUC01").exists())
        self.assertFalse(AuditLog.objects.filter(action="import_items").exists())

    def test_s6_ac6_new_code_created_between_preview_and_commit_returns_409(self):
        xlsx_file = self.make_xlsx_file(self._sample_rows())
        prev = self.post_preview(self.owner, xlsx_file)
        token = prev.json()["preview_token"]

        Item.objects.create(code="MUC01", name="Mực đã tạo tay", item_group=self.group_shrimp)

        resp = self.post_commit(self.owner, xlsx_file, token)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["code"], "IMPORT_DATA_CHANGED")

    def test_expired_preview_token_returns_410_import_preview_expired(self):
        xlsx_file = self.make_xlsx_file(self._sample_rows())
        prev = self.post_preview(self.owner, xlsx_file)
        token = prev.json()["preview_token"]

        future_ts = int(time.time()) + 31 * 60
        with self.assertRaises(Exception) as ctx:
            services.commit_import(user=self.owner, uploaded_file=xlsx_file, preview_token=token, now=future_ts)
        self.assertEqual(getattr(ctx.exception, "code", None), "IMPORT_PREVIEW_EXPIRED")
        self.assertEqual(getattr(ctx.exception, "http_status", None), 410)

    def test_invalid_token_different_file_or_other_users_token_returns_400_import_preview_invalid(self):
        xlsx_file = self.make_xlsx_file(self._sample_rows())
        prev = self.post_preview(self.owner, xlsx_file)
        token = prev.json()["preview_token"]

        for bad in ("", "not-a-valid-token", token + "tampered"):
            resp = self.post_commit(self.owner, xlsx_file, bad)
            self.assertEqual(resp.status_code, 400, bad)
            self.assertEqual(resp.json()["code"], "IMPORT_PREVIEW_INVALID")

        # File khác với file đã xem trước → 400 IMPORT_PREVIEW_INVALID
        other_file = self.make_xlsx_file([
            {"code": "CA01", "name": "Tên khác", "item_group": "Cá", "is_active": True}
        ])
        resp_diff_file = self.post_commit(self.owner, other_file, token)
        self.assertEqual(resp_diff_file.status_code, 400)
        self.assertEqual(resp_diff_file.json()["code"], "IMPORT_PREVIEW_INVALID")

        # Token của owner không dùng được cho user khác kể cả khi user đó được cấp đủ 4 quyền
        from django.contrib.auth.models import Permission
        from apps.catalog.item_files.columns import IMPORT_PERMS

        for perm_str in IMPORT_PERMS:
            _, codename = perm_str.split(".")
            self.manager.user_permissions.add(
                Permission.objects.get(content_type__app_label="catalog", codename=codename)
            )
        resp_other = self.post_commit(self.manager, xlsx_file, token)
        self.assertEqual(resp_other.status_code, 400)
        self.assertEqual(resp_other.json()["code"], "IMPORT_PREVIEW_INVALID")
        self.assertEqual(self.client_as(self.owner).get(COMMIT_URL).status_code, 405)
