"""
Test suite cho Story DW-18: Huỷ phiếu nhập bằng trạng thái (BR-MH-07, V-DW2).
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, StockLedgerEntry, Warehouse
from apps.purchasing.models import (
    PurchaseCost,
    PurchaseCostAllocation,
    PurchaseInvoice,
    PurchaseReceipt,
    Supplier,
)
from apps.purchasing.receipts import services

User = get_user_model()


class CancelReceiptTests(APITestCase):
    def setUp(self):
        self.g = ItemGroup.objects.create(name="Cá")
        self.item1 = Item.objects.create(code="CA01", name="Cá nục", item_group=self.g, shelf_life_in_days=60, is_active=True)
        self.item2 = Item.objects.create(code="CA02", name="Cá thu", item_group=self.g, shelf_life_in_days=90, is_active=True)

        self.sup = Supplier.objects.create(name="Cảng cá Phan Thiết", is_active=True)
        self.wh = Warehouse.objects.create(name="Kho chính")

        self.u_chu = make_user("chu1", "chu")
        self.u_quan_ly = make_user("quanly1", "quan_ly")
        self.u_kho1 = make_user("kho1", "nv_kho")
        self.u_kho2 = make_user("kho2", "nv_kho")
        self.u_giao = make_user("giao1", "nv_giao")

        self.client_chu = client_for(self.u_chu)
        self.client_quan_ly = client_for(self.u_quan_ly)
        self.client_kho1 = client_for(self.u_kho1)
        self.client_kho2 = client_for(self.u_kho2)
        self.client_giao = client_for(self.u_giao)

    def _create_receipt(self, actor=None):
        import datetime
        actor = actor or self.u_kho1
        receipt, batches = services.create_and_submit_receipt(
            supplier=self.sup,
            received_date=datetime.date(2026, 9, 28),
            warehouse=self.wh,
            lines=[
                {"item_code": self.item1, "qty": Decimal("50.000"), "rate": Decimal("80000.00")},
                {"item_code": self.item2, "qty": Decimal("30.000"), "rate": Decimal("120000.00")},
            ],
            actor=actor,
        )
        return receipt, batches

    def test_dw18_ac1_nguoi_tao_phieu_huy_thanh_cong(self):
        """DW-18-AC1: Phiếu SUBMITTED, 2 lô DRAFT chưa xuất -> người tạo huỷ -> CANCELLED, bút toán đảo sổ kho, AuditLog."""
        receipt, batches = self._create_receipt(actor=self.u_kho1)
        self.assertEqual(receipt.status, PurchaseReceipt.Status.SUBMITTED)
        self.assertEqual(len(batches), 2)
        for b in batches:
            self.assertEqual(b.status, Batch.Status.DRAFT)
            self.assertGreater(b.qty_available, 0)

        url = f"/api/purchasing/receipts/{receipt.pk}/cancel/"
        res = self.client_kho1.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["status"], "CANCELLED")

        receipt.refresh_from_db()
        self.assertEqual(receipt.status, PurchaseReceipt.Status.CANCELLED)

        # 2 lô phải CANCELLED và tồn kho khả dụng về 0
        for b in batches:
            b.refresh_from_db()
            self.assertEqual(b.status, Batch.Status.CANCELLED)
            self.assertEqual(b.qty_available, Decimal("0"))
            # Sổ kho có bút toán WRITE_OFF
            write_offs = StockLedgerEntry.objects.filter(
                batch=b,
                movement_type=StockLedgerEntry.MovementType.WRITE_OFF,
            )
            self.assertTrue(write_offs.exists())
            self.assertEqual(write_offs.first().qty_change, -b.qty_received)

        # AuditLog ghi nhận
        audit = AuditLog.objects.filter(action="cancel_purchase_receipt", object_id=str(receipt.pk)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.u_kho1)

    def test_dw18_ac2_loi_khi_lo_da_publish_hoac_co_invoice_cost(self):
        """DW-18-AC2: Một lô đã publish (SELLING), hoặc có Purchase Cost / Invoice -> 400 BR-MH-07, không đổi."""
        # 1. Lô đã publish
        receipt1, batches1 = self._create_receipt()
        b1 = batches1[0]
        b1.status = Batch.Status.SELLING
        b1.save(update_fields=["status"])

        res1 = self.client_kho1.post(f"/api/purchasing/receipts/{receipt1.pk}/cancel/", {}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res1.json().get("code"), "BR-MH-07")

        receipt1.refresh_from_db()
        self.assertEqual(receipt1.status, PurchaseReceipt.Status.SUBMITTED)

        # 2. Đã có PurchaseInvoice
        receipt2, batches2 = self._create_receipt()
        PurchaseInvoice.objects.create(
            supplier=self.sup,
            receipt=receipt2,
            amount=Decimal("5000000"),
            invoice_date="2026-09-28",
            created_by=self.u_chu,
        )
        res2 = self.client_kho1.post(f"/api/purchasing/receipts/{receipt2.pk}/cancel/", {}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res2.json().get("code"), "BR-MH-07")

        # 3. Đã có PurchaseCost phân bổ vào lô
        receipt3, batches3 = self._create_receipt()
        cost = PurchaseCost.objects.create(
            cost_type=PurchaseCost.CostType.TRANSPORT,
            amount=Decimal("200000"),
            incurred_date="2026-09-28",
            created_by=self.u_chu,
        )
        PurchaseCostAllocation.objects.create(
            purchase_cost=cost,
            batch=batches3[0],
            allocated_amount=Decimal("200000"),
        )
        res3 = self.client_kho1.post(f"/api/purchasing/receipts/{receipt3.pk}/cancel/", {}, format="json")
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res3.json().get("code"), "BR-MH-07")

    def test_dw18_ac3_phan_quyen_v_dw2(self):
        """DW-18-AC3: nv_kho khác người tạo -> 403; nv_giao -> 403; quan_ly và chu -> 200."""
        receipt, _ = self._create_receipt(actor=self.u_kho1)

        # nv_kho khác người tạo (kho2)
        res_kho2 = self.client_kho2.post(f"/api/purchasing/receipts/{receipt.pk}/cancel/", {}, format="json")
        self.assertEqual(res_kho2.status_code, status.HTTP_403_FORBIDDEN)

        # nv_giao
        res_giao = self.client_giao.post(f"/api/purchasing/receipts/{receipt.pk}/cancel/", {}, format="json")
        self.assertEqual(res_giao.status_code, status.HTTP_403_FORBIDDEN)

        # quan_ly huỷ được phiếu của người khác
        res_ql = self.client_quan_ly.post(f"/api/purchasing/receipts/{receipt.pk}/cancel/", {}, format="json")
        self.assertEqual(res_ql.status_code, status.HTTP_200_OK)

        # chu huỷ được phiếu khác
        receipt2, _ = self._create_receipt(actor=self.u_kho1)
        res_chu = self.client_chu.post(f"/api/purchasing/receipts/{receipt2.pk}/cancel/", {}, format="json")
        self.assertEqual(res_chu.status_code, status.HTTP_200_OK)

    def test_dw18_ac4_hai_lan_huy_lien_tiep(self):
        """DW-18-AC4: Gọi huỷ 2 lần -> lần 2 bị từ chối 400 BR-MH-07 vì đã CANCELLED."""
        receipt, _ = self._create_receipt(actor=self.u_kho1)
        res1 = self.client_kho1.post(f"/api/purchasing/receipts/{receipt.pk}/cancel/", {}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        res2 = self.client_kho1.post(f"/api/purchasing/receipts/{receipt.pk}/cancel/", {}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res2.json().get("code"), "BR-MH-07")

    def test_dw18_ac5_quan_ly_xem_phieu_huy_khong_ro_rate(self):
        """DW-18-AC5: quan_ly xem chi tiết phiếu đã huỷ -> không có trường rate (Bất biến 1)."""
        receipt, _ = self._create_receipt(actor=self.u_kho1)
        self.client_kho1.post(f"/api/purchasing/receipts/{receipt.pk}/cancel/", {}, format="json")

        res = self.client_quan_ly.get(f"/api/purchasing/receipts/{receipt.pk}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        lines = res.json().get("lines", [])
        self.assertGreater(len(lines), 0)
        for line in lines:
            self.assertNotIn("rate", line)

    @override_settings(AI_ENABLED=True)
    def test_dw18_ac6_descriptor_nhap_lo_max_level_b_va_het_ai_undo_missing(self):
        """DW-18-AC6: Sau khi action cancel có -> descriptor nhap_lo max_level=B, locked_reason không còn AI_UNDO_MISSING."""
        from apps.ai.registry.discovery import get_registry
        spec = get_registry().get("purchasing.purchasereceipt.nhap_lo")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.max_level, "B")
        self.assertFalse(spec.undo_missing)

        # Kiểm tra chi tiết descriptor qua API
        res = self.client_kho1.get("/api/ai/commands/purchasing.purchasereceipt.nhap_lo/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json().get("max_level"), "B")

        # Kiểm tra my-config
        res_cfg = self.client_kho1.get("/api/ai/my-config/")
        self.assertEqual(res_cfg.status_code, status.HTTP_200_OK)
        groups = res_cfg.json()["groups"]
        thu_mua = next(g for g in groups if g["group"] == "thu_mua")
        cfg_cmd = next(c for c in thu_mua["commands"] if c["id"] == "purchasing.purchasereceipt.nhap_lo")
        self.assertIsNone(cfg_cmd.get("locked_reason"))

    @override_settings(AI_ENABLED=False)
    def test_dw18_ac7_ai_tat_huy_phieu_van_chay_binh_thuong(self):
        """DW-18-AC7: AI_ENABLED=False -> huỷ phiếu bằng tay vẫn chạy bình thường."""
        receipt, _ = self._create_receipt(actor=self.u_kho1)
        res = self.client_kho1.post(f"/api/purchasing/receipts/{receipt.pk}/cancel/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, PurchaseReceipt.Status.CANCELLED)
