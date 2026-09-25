"""
S4 — Người tạo / người duyệt do hệ thống ghi theo người đăng nhập (BR-PQ-16).

Áp dụng khi tạo: phiếu kiểm kê, hàng hoàn, phiếu nhập, chi phí mua, phiếu hoàn,
hoá đơn mua. Client gửi `created_by` → 400 BR-PQ-16, không tạo (S4-AC2).
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.inventory.models import ReturnToStock, StockEntry, StockReconciliation
from apps.purchasing.models import PurchaseCost, PurchaseInvoice, PurchaseReceipt
from apps.sales.models import Refund

from .fixtures import client_for, make_batch, make_master, make_order_with_note, make_user


class S4ReconciliationTests(TestCase):
    def setUp(self):
        self.kho1 = make_user("kho1", "nv_kho")
        self.ql1 = make_user("ql1", "quan_ly")
        self.url = "/api/inventory/reconciliations/"
        self.payload = {"count_date": str(timezone.localdate()), "note": "kiểm cuối ngày"}

    def test_s4_ac1_created_by_la_nguoi_dang_nhap(self):
        resp = client_for(self.kho1).post(self.url, self.payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["created_by"], self.kho1.pk)
        self.assertEqual(StockReconciliation.objects.get().created_by, self.kho1)

    def test_s4_ac2_gui_created_by_bi_chan_400_br_pq_16(self):
        resp = client_for(self.kho1).post(
            self.url, {**self.payload, "created_by": self.ql1.pk}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-16")
        self.assertIn("created_by", resp.json()["detail"])
        self.assertFalse(StockReconciliation.objects.exists())

    def test_s4_ac2_gui_created_by_bang_chinh_minh_cung_bi_chan(self):
        resp = client_for(self.kho1).post(
            self.url, {**self.payload, "created_by": self.kho1.pk}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-16")

    def test_s4_ac2_patch_doi_created_by_bi_chan(self):
        rec = StockReconciliation.objects.create(count_date=timezone.localdate(), created_by=self.ql1)
        resp = client_for(self.ql1).patch(
            f"{self.url}{rec.pk}/", {"created_by": self.kho1.pk}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-16")
        rec.refresh_from_db()
        self.assertEqual(rec.created_by, self.ql1)

    def test_s4_ac3_ql_tu_tao_roi_tu_duyet_bi_chan_br_kk_02(self):
        resp = client_for(self.ql1).post(self.url, self.payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        rec_id = resp.json()["id"]
        resp = client_for(self.ql1).post(f"{self.url}{rec_id}/approve/")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-KK-02")
        self.assertEqual(StockReconciliation.objects.get(pk=rec_id).status, "DRAFT")

    def test_s4_ac3_nguoi_khac_duyet_duoc(self):
        resp = client_for(self.kho1).post(self.url, self.payload, format="json")
        rec_id = resp.json()["id"]
        resp = client_for(self.ql1).post(f"{self.url}{rec_id}/approve/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["approved_by"], self.ql1.pk)

    def test_s4_ac4_nv_giao_tao_kiem_ke_403(self):
        giao = make_user("giao1", "nv_giao")
        resp = client_for(giao).post(self.url, self.payload, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(StockReconciliation.objects.exists())

    def test_s4_ac4_chua_dang_nhap_401(self):
        self.assertEqual(client_for(None).post(self.url, self.payload, format="json").status_code, 401)


class S4OtherDocumentsTests(TestCase):
    """BR-PQ-16 trên hàng hoàn, phiếu nhập, hoá đơn mua, chi phí mua, phiếu hoàn."""

    def setUp(self):
        self.item, self.sup, self.wh = make_master()
        self.batch = make_batch(self.item, self.sup, self.wh)
        self.chu = make_user("chu1", "chu")
        self.ql1 = make_user("ql1", "quan_ly")
        self.kho1 = make_user("kho1", "nv_kho")
        self.giao1 = make_user("giao1", "nv_giao")

    def _assert_actor(self, user, url, payload, model):
        resp = client_for(user).post(url, {**payload, "created_by": self.ql1.pk}, format="json")
        self.assertEqual(resp.status_code, 400, (url, resp.content))
        self.assertEqual(resp.json()["code"], "BR-PQ-16")
        self.assertEqual(model.objects.count(), 0, url)
        resp = client_for(user).post(url, payload, format="json")
        self.assertEqual(resp.status_code, 201, (url, resp.content))
        self.assertEqual(model.objects.get().created_by, user, url)
        return resp

    def test_s4_hang_hoan_created_by_la_nv_giao(self):
        resp = self._assert_actor(
            self.giao1, "/api/inventory/returns/", {"batch": self.batch.pk, "qty": "1.5"}, ReturnToStock,
        )
        self.assertEqual(resp.json()["created_by"], self.giao1.pk)
        rt = ReturnToStock.objects.get()
        self.assertEqual((rt.status, rt.decision), ("DRAFT", "PENDING"))

    def test_s4_phieu_nhap_created_by_la_nv_kho(self):
        self._assert_actor(
            self.kho1, "/api/purchasing/receipts/",
            {"supplier": self.sup.pk, "warehouse": self.wh.pk, "received_date": str(timezone.localdate())},
            PurchaseReceipt,
        )

    def test_s4_hoa_don_mua_created_by_la_chu(self):
        self._assert_actor(
            self.chu, "/api/purchasing/invoices/",
            {"supplier": self.sup.pk, "amount": "1000000", "invoice_date": str(timezone.localdate())},
            PurchaseInvoice,
        )

    def test_s4_hoa_don_mua_khong_ro_so_tien_cho_ql(self):
        """Hoá đơn mua: quan_ly chỉ có quyền xem; không được tạo (403)."""
        resp = client_for(self.ql1).post(
            "/api/purchasing/invoices/",
            {"supplier": self.sup.pk, "amount": "1", "invoice_date": str(timezone.localdate())},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_s4_chi_phi_mua_created_by_la_chu(self):
        self._assert_actor(
            self.chu, "/api/purchasing/costs/",
            {
                "cost_type": "ICE", "amount": "100000", "incurred_date": str(timezone.localdate()),
                "allocations": [{"batch": self.batch.pk}],
            },
            PurchaseCost,
        )

    def test_s4_chi_phi_mua_nv_kho_403(self):
        resp = client_for(self.kho1).post(
            "/api/purchasing/costs/",
            {"cost_type": "ICE", "amount": "1", "incurred_date": str(timezone.localdate()),
             "allocations": [{"batch": self.batch.pk}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(PurchaseCost.objects.exists())

    def test_s4_phieu_hoan_created_by_la_nguoi_dang_nhap(self):
        order, _, _ = make_order_with_note("SO-1", "0900000001")
        payload = {"sales_invoice": order.invoice.pk, "amount": "1000", "reason": "khách huỷ"}
        resp = client_for(self.ql1).post(
            "/api/sales/refunds/create/", {**payload, "created_by": self.chu.pk}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-16")
        self.assertFalse(Refund.objects.exists())
        resp = client_for(self.ql1).post("/api/sales/refunds/create/", payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Refund.objects.get().created_by, self.ql1)

    def test_s4_phieu_dieu_chinh_kho_created_by_la_nguoi_dang_nhap(self):
        self._assert_actor(
            self.kho1, "/api/inventory/stock-entries/",
            {"purpose": StockEntry.Purpose.choices[0][0], "batch": self.batch.pk,
             "qty_change": "-1", "reason": "hỏng"},
            StockEntry,
        )
