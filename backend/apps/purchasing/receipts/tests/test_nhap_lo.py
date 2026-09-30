"""
Unit & Integration tests cho Story DW-17 (Nhập lô mua tại cảng trên ERP).
Tiêu chuẩn AC1 đến AC8 (02-stories.md, 02b §2.5).
"""
import datetime
from decimal import Decimal
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine, Supplier
from apps.ai import command_groups
from apps.accounts import roles


class NhapLoTests(TestCase):
    def setUp(self):
        self.g = ItemGroup.objects.create(name="Cá")
        self.tom = Item.objects.create(
            code="TOM01", name="Tôm sú", item_group=self.g, shelf_life_in_days=90, stock_uom="KG"
        )
        self.muc = Item.objects.create(
            code="MUC01", name="Mực", item_group=self.g, shelf_life_in_days=60, stock_uom="KG"
        )
        self.sup = Supplier.objects.create(name="Đầu mối Phan Thiết")
        self.wh = Warehouse.objects.create(name="Kho chính")

        self.user_chu = make_user("chu_test", roles.OWNER)
        self.user_quanly = make_user("quanly_test", roles.MANAGER)
        self.user_kho = make_user("kho_test", roles.WAREHOUSE_STAFF)
        self.user_giao = make_user("giao_test", roles.DELIVERY_STAFF)

        self.client_chu = client_for(self.user_chu)
        self.client_quanly = client_for(self.user_quanly)
        self.client_kho = client_for(self.user_kho)
        self.client_giao = client_for(self.user_giao)

    def test_dw17_ac1_nhap_lo_thanh_cong(self):
        """DW-17-AC1: NV kho nhập 2 dòng hàng -> 201; 1 phiếu SUBMITTED, 2 lô DRAFT, hạn đúng, AuditLog."""
        payload = {
            "supplier": self.sup.pk,
            "received_date": "2026-09-28",
            "warehouse": self.wh.pk,
            "lines": [
                {"item_code": "TOM01", "qty": "50.000", "rate": "80000.00", "shelf_life_days": 60},
                {"item_code": "MUC01", "qty": "30.000", "rate": "120000.00"},  # không gửi shelf_life_days -> lấy mặc định 60
            ],
        }
        res = self.client_kho.post("/api/purchasing/receipts/nhap-lo/", payload, format="json")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("receipt", data)
        self.assertIn("batches", data)
        self.assertEqual(len(data["batches"]), 2)

        receipt = PurchaseReceipt.objects.get(pk=data["receipt"]["id"])
        self.assertEqual(receipt.status, PurchaseReceipt.Status.SUBMITTED)
        self.assertEqual(receipt.created_by, self.user_kho)

        batches = list(Batch.objects.filter(source_line__receipt=receipt).order_by("pk"))
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0].status, Batch.Status.DRAFT)
        self.assertEqual(batches[0].expiry_date, datetime.date(2026, 9, 28) + datetime.timedelta(days=60))
        self.assertEqual(batches[1].status, Batch.Status.DRAFT)
        self.assertEqual(batches[1].expiry_date, datetime.date(2026, 9, 28) + datetime.timedelta(days=60))

        # Kiểm tra AuditLog
        log = AuditLog.objects.filter(action="create_and_submit_receipt", object_id=str(receipt.pk)).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.user_kho)
        self.assertEqual(log.actor_kind, "user")

    def test_dw17_ac2_loi_shelf_life_va_lines_rong_atomic(self):
        """DW-17-AC2: shelf_life_days > mặc định -> 400 BR-MH-02; lines rỗng -> 400; không tạo phiếu, không lô."""
        # 1. shelf_life_days vượt mặc định
        payload_bad_expiry = {
            "supplier": self.sup.pk,
            "received_date": "2026-09-28",
            "lines": [
                {"item_code": "MUC01", "qty": "30.000", "rate": "120000.00", "shelf_life_days": 100},  # MUC01 mặc định 60
            ],
        }
        res = self.client_kho.post("/api/purchasing/receipts/nhap-lo/", payload_bad_expiry, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json().get("code"), "BR-MH-02")
        self.assertEqual(PurchaseReceipt.objects.count(), 0)
        self.assertEqual(Batch.objects.count(), 0)

        # 2. lines rỗng
        payload_empty_lines = {
            "supplier": self.sup.pk,
            "lines": [],
        }
        res2 = self.client_kho.post("/api/purchasing/receipts/nhap-lo/", payload_empty_lines, format="json")
        self.assertEqual(res2.status_code, 400)
        self.assertEqual(PurchaseReceipt.objects.count(), 0)
        self.assertEqual(Batch.objects.count(), 0)

    def test_dw17_ac3_idempotency_khong_tao_phieu_thu_hai(self):
        """DW-17-AC3: Gửi lại cùng idempotency_key -> không tạo phiếu thứ 2, trả phiếu đã tạo."""
        key = "idemp-key-001"
        payload = {
            "supplier": self.sup.pk,
            "received_date": "2026-09-28",
            "idempotency_key": key,
            "lines": [
                {"item_code": "TOM01", "qty": "50.000", "rate": "80000.00"},
            ],
        }
        res1 = self.client_kho.post("/api/purchasing/receipts/nhap-lo/", payload, format="json")
        self.assertEqual(res1.status_code, 201)
        r1_id = res1.json()["receipt"]["id"]

        # Gửi lại lần 2
        res2 = self.client_kho.post("/api/purchasing/receipts/nhap-lo/", payload, format="json")
        self.assertEqual(res2.status_code, 201)
        r2_id = res2.json()["receipt"]["id"]
        self.assertEqual(r1_id, r2_id)
        self.assertEqual(PurchaseReceipt.objects.count(), 1)
        self.assertEqual(Batch.objects.count(), 1)

    def test_dw17_ac4_nv_giao_bi_403(self):
        """DW-17-AC4: nv_giao gọi API nhập lô -> 403, DB không đổi."""
        payload = {
            "supplier": self.sup.pk,
            "lines": [{"item_code": "TOM01", "qty": "10.000", "rate": "50000.00"}],
        }
        res = self.client_giao.post("/api/purchasing/receipts/nhap-lo/", payload, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(PurchaseReceipt.objects.count(), 0)

    def test_dw17_ac5_khong_ro_gia_von_voi_kho_va_quan_ly(self):
        """DW-17-AC5: nv_kho, quan_ly không thấy rate, purchase_rate, landed_unit_cost; chu thấy."""
        payload = {
            "supplier": self.sup.pk,
            "received_date": "2026-09-28",
            "lines": [{"item_code": "TOM01", "qty": "20.000", "rate": "95000.00"}],
        }
        # 1. nv_kho
        res_kho = self.client_kho.post("/api/purchasing/receipts/nhap-lo/", payload, format="json")
        self.assertEqual(res_kho.status_code, 201)
        data_kho = res_kho.json()
        line_kho = data_kho["receipt"]["lines"][0]
        self.assertNotIn("rate", line_kho)
        batch_kho = data_kho["batches"][0]
        self.assertNotIn("purchase_rate", batch_kho)
        self.assertNotIn("landed_unit_cost", batch_kho)

        # 2. chu
        payload2 = {
            "supplier": self.sup.pk,
            "received_date": "2026-09-28",
            "lines": [{"item_code": "MUC01", "qty": "15.000", "rate": "150000.00"}],
        }
        res_chu = self.client_chu.post("/api/purchasing/receipts/nhap-lo/", payload2, format="json")
        self.assertEqual(res_chu.status_code, 201)
        data_chu = res_chu.json()
        line_chu = data_chu["receipt"]["lines"][0]
        self.assertIn("rate", line_chu)
        self.assertEqual(Decimal(str(line_chu["rate"])), Decimal("150000.00"))
        batch_chu = data_chu["batches"][0]
        self.assertIn("purchase_rate", batch_chu)
        self.assertIn("landed_unit_cost", batch_chu)

    @override_settings(AI_ENABLED=True)
    def test_dw17_ac6_lenh_ai_nhap_lo_muc_c_va_proposal(self):
        """DW-17-AC6: Lệnh AI tự sinh nhap_lo trần C, AI_UNDO_MISSING; call sinh nháp; duyệt tạo phiếu."""
        # 1. Kiểm tra index
        res_index = self.client_kho.get("/api/ai/commands/index/")
        self.assertEqual(res_index.status_code, 200)
        cmd_item = next((c for c in res_index.json()["commands"] if c["id"] == "purchasing.purchasereceipt.nhap_lo"), None)
        self.assertIsNotNone(cmd_item)
        self.assertEqual(cmd_item["level"], "C")

        # 2. Kiểm tra my-config
        res_cfg = self.client_kho.get("/api/ai/my-config/")
        self.assertEqual(res_cfg.status_code, 200)
        groups = res_cfg.json()["groups"]
        thu_mua = next(g for g in groups if g["group"] == command_groups.PURCHASING)
        cfg_cmd = next(c for c in thu_mua["commands"] if c["id"] == "purchasing.purchasereceipt.nhap_lo")
        self.assertEqual(cfg_cmd["choices"], ["OFF", "C"])
        self.assertIsNone(cfg_cmd["locked_reason"])

        # 3. Call lệnh ghi -> outcome=proposal (mức C)
        call_payload = {
            "args": {
                "supplier": self.sup.pk,
                "received_date": "2026-09-28",
                "lines": [{"item_code": "TOM01", "qty": "10.000", "rate": "70000.00"}],
            }
        }
        res_call = self.client_kho.post("/api/ai/commands/purchasing.purchasereceipt.nhap_lo/call/", call_payload, format="json")
        self.assertEqual(res_call.status_code, 200)
        call_data = res_call.json()
        self.assertEqual(call_data["outcome"], "proposal")
        self.assertEqual(call_data["level"], "C")
        action_id = call_data["action_id"]

        # Chưa có phiếu nào được tạo
        self.assertEqual(PurchaseReceipt.objects.count(), 0)

        # 4. Duyệt nháp sau khi xem chi tiết
        res_detail = self.client_kho.get(f"/api/ai/actions/{action_id}/")
        self.assertEqual(res_detail.status_code, 200)
        nonce = res_detail.json().get("confirm_nonce")

        # Giả lập viewed_at >= 3s
        action = AiAction.objects.get(pk=action_id)
        action.viewed_at = timezone.now() - datetime.timedelta(seconds=5)
        action.save(update_fields=["viewed_at"])

        res_confirm = self.client_kho.post(
            f"/api/ai/actions/{action_id}/confirm/",
            {"confirm_nonce": nonce},
            format="json",
        )
        self.assertEqual(res_confirm.status_code, 200)
        self.assertEqual(PurchaseReceipt.objects.count(), 1)
        receipt = PurchaseReceipt.objects.first()
        self.assertEqual(receipt.status, PurchaseReceipt.Status.SUBMITTED)

        # AuditLog mang proposal_ref
        log = AuditLog.objects.filter(action="create_and_submit_receipt", object_id=str(receipt.pk)).first()
        self.assertIsNotNone(log)
        self.assertEqual(str(log.proposal_ref), str(action_id))

    def test_dw17_ac7_khong_co_du_lieu_khach_pii(self):
        """DW-17-AC7: Xem phiếu nhập và lô không có dữ liệu khách hàng."""
        payload = {
            "supplier": self.sup.pk,
            "received_date": "2026-09-28",
            "lines": [{"item_code": "TOM01", "qty": "10.000", "rate": "70000.00"}],
        }
        res = self.client_kho.post("/api/purchasing/receipts/nhap-lo/", payload, format="json")
        res_text = res.content.decode("utf-8")
        self.assertNotIn("customer", res_text)
        self.assertNotIn("delivery_address", res_text)
        self.assertNotIn("phone", res_text)

    @override_settings(AI_ENABLED=False)
    def test_dw17_ac8_ai_tat_nhap_lo_van_chay_binh_thuong(self):
        """DW-17-AC8: AI_ENABLED=false -> API nhap-lo vẫn chạy bình thường 201."""
        payload = {
            "supplier": self.sup.pk,
            "received_date": "2026-09-28",
            "lines": [{"item_code": "TOM01", "qty": "10.000", "rate": "70000.00"}],
        }
        res = self.client_kho.post("/api/purchasing/receipts/nhap-lo/", payload, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(PurchaseReceipt.objects.count(), 1)
