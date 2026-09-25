"""
S3 — Khoá sửa chung vượt state machine (BR-PQ-14) + mã lỗi `code` (quy ước chung).

Field trạng thái / tồn / giá vốn / người phụ trách chỉ đổi qua action nghiệp vụ.
`PATCH`/`PUT`/`POST` có gửi field khoá → 400 {"detail", "code": "BR-PQ-14"}, DB không đổi.
Chứng từ không xoá được (BR-PQ-10) → `DELETE` = 405.
"""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.exceptions import BusinessError
from apps.delivery.models import DeliveryNote
from apps.inventory.models import Batch, ReturnToStock, StockReconciliation
from apps.purchasing.models import PurchaseCost, PurchaseInvoice, PurchaseReceipt
from apps.sales.models import Refund

from .fixtures import client_for, make_batch, make_master, make_order_with_note, make_user


class S3BatchLockTests(TestCase):
    def setUp(self):
        self.item, self.sup, self.wh = make_master()
        self.batch = make_batch(self.item, self.sup, self.wh)
        # Given S3-AC1: "Quản lý có change_batch" (seed hiện chỉ cấp r cho quan_ly).
        self.ql = make_user("ql1", "quan_ly", perms=["inventory.change_batch"])
        self.chu = make_user("chu1", "chu")

    def _snapshot(self):
        return Batch.objects.values().get(pk=self.batch.pk)

    def test_s3_ac1_patch_landed_unit_cost_bi_chan_400_br_pq_14(self):
        before = self._snapshot()
        resp = client_for(self.ql).patch(
            f"/api/inventory/batches/{self.batch.pk}/", {"landed_unit_cost": "1"}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "BR-PQ-14")
        self.assertIn("landed_unit_cost", body["detail"])
        self.assertEqual(self._snapshot(), before)

    def test_s3_ac1_moi_field_khoa_cua_lo_deu_bi_chan_ke_ca_chu(self):
        other = make_user("other")
        locked = {
            "status": "EXPIRED", "qty_received": "999", "qty_available": "999",
            "qty_reserved": "1", "purchase_rate": "1", "landed_unit_cost": "1",
            "expiry_date": "2030-01-01", "closed_at": "2026-09-01T00:00:00Z",
            "closed_by": other.pk,
        }
        before = self._snapshot()
        for field, value in locked.items():
            resp = client_for(self.chu).patch(
                f"/api/inventory/batches/{self.batch.pk}/", {field: value}, format="json"
            )
            self.assertEqual(resp.status_code, 400, (field, resp.content))
            self.assertEqual(resp.json()["code"], "BR-PQ-14")
            self.assertIn(field, resp.json()["detail"])
        self.assertEqual(self._snapshot(), before)

    def test_s3_ac1_liet_ke_du_cac_field_khoa_trong_detail(self):
        resp = client_for(self.chu).patch(
            f"/api/inventory/batches/{self.batch.pk}/",
            {"status": "SELLING", "qty_available": "1", "received_date": "2026-09-02"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        detail = resp.json()["detail"]
        self.assertIn("status", detail)
        self.assertIn("qty_available", detail)
        self.assertNotIn("received_date", detail)

    def test_s3_ac1_put_cung_bi_chan(self):
        before = self._snapshot()
        resp = client_for(self.chu).put(
            f"/api/inventory/batches/{self.batch.pk}/",
            {
                "item": self.item.pk, "supplier": self.sup.pk, "warehouse": self.wh.pk,
                "received_date": "2026-09-01", "expiry_date": "2030-01-01",
                "qty_received": "50", "status": "SELLING",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-14")
        self.assertEqual(self._snapshot(), before)

    def test_s3_ac1_post_tao_lo_kem_field_khoa_bi_chan(self):
        count = Batch.objects.count()
        resp = client_for(self.chu).post(
            "/api/inventory/batches/",
            {
                "item": self.item.pk, "supplier": self.sup.pk, "warehouse": self.wh.pk,
                "received_date": "2026-09-01", "expiry_date": "2030-01-01",
                "qty_received": "50", "landed_unit_cost": "1",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-14")
        self.assertEqual(Batch.objects.count(), count)

    def test_s2_ac7_nv_kho_patch_status_lo_khong_doi_duoc(self):
        """S2-AC7: nv_kho không có change_batch → 403 (S3-AC6: quyền trước field);
        người có change_batch → 400 BR-PQ-14. Cả hai: lô không đổi, không AuditLog."""
        kho = make_user("kho1", "nv_kho")
        url = f"/api/inventory/batches/{self.batch.pk}/"
        self.assertEqual(client_for(kho).patch(url, {"status": "EXPIRED"}, format="json").status_code, 403)
        resp = client_for(self.ql).patch(url, {"status": "EXPIRED"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-PQ-14")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, Batch.Status.DRAFT)
        self.assertFalse(AuditLog.objects.exists())

    def test_s3_ac3_patch_field_khong_khoa_luu_duoc(self):
        new_sup = type(self.sup).objects.create(name="Đầu mối B")
        resp = client_for(self.ql).patch(
            f"/api/inventory/batches/{self.batch.pk}/", {"supplier": new_sup.pk}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.supplier_id, new_sup.pk)

    def test_s3_ac3_khong_ro_gia_von_khi_ql_patch_thanh_cong(self):
        resp = client_for(self.ql).patch(
            f"/api/inventory/batches/{self.batch.pk}/", {"received_date": str(timezone.localdate())},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertNotIn("landed_unit_cost", resp.json())
        self.assertNotIn("purchase_rate", resp.json())

    def test_s3_ac6_nv_giao_patch_lo_403_truoc_ca_kiem_field(self):
        giao = make_user("giao1", "nv_giao")
        before = self._snapshot()
        resp = client_for(giao).patch(
            f"/api/inventory/batches/{self.batch.pk}/", {"landed_unit_cost": "1"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self._snapshot(), before)

    def test_s3_ac6_chua_dang_nhap_401(self):
        resp = client_for(None).patch(
            f"/api/inventory/batches/{self.batch.pk}/", {"landed_unit_cost": "1"}, format="json"
        )
        self.assertEqual(resp.status_code, 401)


class S3DeliveryNoteLockTests(TestCase):
    def setUp(self):
        self.giao1 = make_user("giao1", "nv_giao")
        self.giao2 = make_user("giao2", "nv_giao")
        _, _, self.note = make_order_with_note("SO-1", "0900000001", assigned_to=self.giao1)
        DeliveryNote.objects.filter(pk=self.note.pk).update(status=DeliveryNote.Status.READY)
        self.url = f"/api/delivery/notes/{self.note.pk}/"

    def _snapshot(self):
        return DeliveryNote.objects.values().get(pk=self.note.pk)

    def test_s3_ac2_nv_giao_patch_status_bi_chan(self):
        before = self._snapshot()
        resp = client_for(self.giao1).patch(self.url, {"status": "COMPLETED"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-14")
        self.assertIn("status", resp.json()["detail"])
        self.assertEqual(self._snapshot(), before)

    def test_s3_ac2_nv_giao_patch_assigned_to_bi_chan(self):
        before = self._snapshot()
        resp = client_for(self.giao1).patch(self.url, {"assigned_to": self.giao2.pk}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-14")
        self.assertEqual(self._snapshot(), before)

    def test_s3_ac2_cac_field_khoa_khac_cua_phieu_giao(self):
        before = self._snapshot()
        for field, value in {
            "failed_attempts": 5, "completed_at": "2026-09-01T00:00:00Z",
            "sales_invoice": self.note.sales_invoice_id,
        }.items():
            resp = client_for(self.giao1).patch(self.url, {field: value}, format="json")
            self.assertEqual(resp.status_code, 400, (field, resp.content))
            self.assertEqual(resp.json()["code"], "BR-PQ-14")
        self.assertEqual(self._snapshot(), before)

    def test_s3_ac3_nv_giao_sua_ghi_chu_phieu_cua_minh(self):
        resp = client_for(self.giao1).patch(self.url, {"note": "Gọi trước 15'"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.note.refresh_from_db()
        self.assertEqual(self.note.note, "Gọi trước 15'")
        self.assertEqual(self.note.status, DeliveryNote.Status.READY)

    def test_s3_ac2_action_status_van_la_duong_hop_le(self):
        resp = client_for(self.giao1).post(
            f"{self.url}status/", {"to_status": "DELIVERING"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.note.refresh_from_db()
        self.assertEqual(self.note.status, DeliveryNote.Status.DELIVERING)


class S3OtherDocumentLockTests(TestCase):
    def setUp(self):
        self.item, self.sup, self.wh = make_master()
        self.batch = make_batch(self.item, self.sup, self.wh)
        self.ql = make_user("ql1", "quan_ly")
        self.kho = make_user("kho1", "nv_kho")
        self.chu = make_user("chu1", "chu")

    def test_s3_returns_khoa_status_decision_approved_by(self):
        rt = ReturnToStock.objects.create(batch=self.batch, qty=Decimal("1"), created_by=self.kho)
        for field, value in {"status": "APPROVED", "decision": "RESTOCK", "approved_by": self.chu.pk}.items():
            resp = client_for(self.chu).patch(
                f"/api/inventory/returns/{rt.pk}/", {field: value}, format="json"
            )
            self.assertEqual(resp.status_code, 400, (field, resp.content))
            self.assertEqual(resp.json()["code"], "BR-PQ-14")
        rt.refresh_from_db()
        self.assertEqual((rt.status, rt.decision, rt.approved_by_id), ("DRAFT", "PENDING", None))

    def test_s3_returns_post_kem_decision_bi_chan(self):
        resp = client_for(self.kho).post(
            "/api/inventory/returns/",
            {"batch": self.batch.pk, "qty": "1", "decision": "RESTOCK"}, format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-14")
        self.assertFalse(ReturnToStock.objects.exists())

    def test_s3_reconciliations_khoa_status_approved(self):
        rec = StockReconciliation.objects.create(count_date=timezone.localdate(), created_by=self.kho)
        for field, value in {
            "status": "APPROVED", "approved_by": self.ql.pk, "approved_at": "2026-09-01T00:00:00Z",
        }.items():
            resp = client_for(self.ql).patch(
                f"/api/inventory/reconciliations/{rec.pk}/", {field: value}, format="json"
            )
            self.assertEqual(resp.status_code, 400, (field, resp.content))
            self.assertEqual(resp.json()["code"], "BR-PQ-14")
        rec.refresh_from_db()
        self.assertEqual((rec.status, rec.approved_by_id, rec.approved_at), ("DRAFT", None, None))

    def test_s3_receipts_khoa_status(self):
        pr = PurchaseReceipt.objects.create(
            supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(), created_by=self.kho,
        )
        resp = client_for(self.ql).patch(
            f"/api/purchasing/receipts/{pr.pk}/", {"status": "SUBMITTED"}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-14")
        pr.refresh_from_db()
        self.assertEqual(pr.status, PurchaseReceipt.Status.DRAFT)

    def test_s3_receipts_patch_ghi_chu_van_duoc(self):
        pr = PurchaseReceipt.objects.create(
            supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(), created_by=self.kho,
        )
        resp = client_for(self.ql).patch(
            f"/api/purchasing/receipts/{pr.pk}/", {"note": "cân lại"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_s3_sales_chi_doc_qua_router(self):
        order, _, _ = make_order_with_note("SO-9", "0900000009")
        invoice = order.invoice
        for url in (
            f"/api/sales/orders/{order.pk}/",
            f"/api/sales/invoices/{invoice.pk}/",
        ):
            for method in ("patch", "put", "delete"):
                resp = getattr(client_for(self.chu), method)(url, {"status": "CANCELLED"}, format="json")
                self.assertEqual(resp.status_code, 405, (url, method))
        for url in ("/api/sales/orders/", "/api/sales/refunds/", "/api/sales/payments/", "/api/sales/invoices/"):
            self.assertEqual(client_for(self.chu).post(url, {}, format="json").status_code, 405, url)
        order.refresh_from_db()
        self.assertEqual(order.status, "PROCESSING")


class S3NoDeleteTests(TestCase):
    """S3-AC4: DELETE chứng từ → 405 với bất kỳ ai có quyền sửa (BR-PQ-10)."""

    def setUp(self):
        self.item, self.sup, self.wh = make_master()
        self.batch = make_batch(self.item, self.sup, self.wh)
        self.chu = make_user("chu1", "chu")
        self.ql = make_user("ql1", "quan_ly")
        self.kho = make_user("kho1", "nv_kho")
        self.giao = make_user("giao1", "nv_giao")
        order, _, self.note = make_order_with_note("SO-1", "0900000001", assigned_to=self.giao)
        self.refund = Refund.objects.create(
            sales_invoice=order.invoice, amount=Decimal("1000"), created_by=self.chu,
        )
        self.rt = ReturnToStock.objects.create(batch=self.batch, qty=Decimal("1"), created_by=self.kho)
        self.rec = StockReconciliation.objects.create(count_date=timezone.localdate(), created_by=self.kho)
        self.pr = PurchaseReceipt.objects.create(
            supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(), created_by=self.kho,
        )
        self.pi = PurchaseInvoice.objects.create(
            supplier=self.sup, receipt=self.pr, amount=Decimal("100"),
            invoice_date=timezone.localdate(), created_by=self.chu,
        )
        self.cost = PurchaseCost.objects.create(
            cost_type="ICE", amount=Decimal("100"), incurred_date=timezone.localdate(), created_by=self.chu,
        )

    def test_s3_ac4_delete_chung_tu_405(self):
        cases = [
            (f"/api/inventory/batches/{self.batch.pk}/", Batch, self.batch.pk, (self.chu,)),
            (f"/api/delivery/notes/{self.note.pk}/", DeliveryNote, self.note.pk, (self.chu, self.ql, self.kho, self.giao)),
            (f"/api/inventory/returns/{self.rt.pk}/", ReturnToStock, self.rt.pk, (self.chu,)),
            (f"/api/inventory/reconciliations/{self.rec.pk}/", StockReconciliation, self.rec.pk, (self.chu, self.ql, self.kho)),
            (f"/api/purchasing/receipts/{self.pr.pk}/", PurchaseReceipt, self.pr.pk, (self.chu, self.ql, self.kho)),
            (f"/api/sales/refunds/{self.refund.pk}/", Refund, self.refund.pk, (self.chu, self.ql)),
            (f"/api/purchasing/costs/{self.cost.pk}/", PurchaseCost, self.cost.pk, (self.chu,)),
            (f"/api/purchasing/invoices/{self.pi.pk}/", PurchaseInvoice, self.pi.pk, (self.chu,)),
        ]
        for url, model, pk, users in cases:
            for user in users:
                resp = client_for(user).delete(url)
                self.assertEqual(resp.status_code, 405, (url, user.username, resp.content))
            self.assertTrue(model.objects.filter(pk=pk).exists(), url)

    def test_s3_ac4_delete_chua_dang_nhap_van_401(self):
        self.assertEqual(client_for(None).delete(f"/api/inventory/batches/{self.batch.pk}/").status_code, 401)


class S3ErrorCodeTests(TestCase):
    """S3-AC5: mọi BusinessError qua API trả {"detail", "code"}."""

    def test_s3_ac5_business_error_nhan_code_tuong_minh(self):
        err = BusinessError("Thông điệp", code="BR-GH-07")
        self.assertEqual(err.code, "BR-GH-07")
        self.assertEqual(str(err), "Thông điệp")

    def test_s3_ac5_business_error_tu_rut_ma_br_tu_thong_diep(self):
        self.assertEqual(BusinessError("Người duyệt phải khác (BR-KK-02).").code, "BR-KK-02")
        self.assertEqual(BusinessError("Lỗi chung không mã").code, "BUSINESS_ERROR")

    def test_s3_ac5_api_tra_detail_va_code(self):
        item, sup, wh = make_master()
        batch = make_batch(item, sup, wh)
        Batch.objects.filter(pk=batch.pk).update(status=Batch.Status.SELLING)
        chu = make_user("chu1", "chu")
        resp = client_for(chu).post(f"/api/inventory/batches/{batch.pk}/publish/")
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(set(body), {"detail", "code"})
        self.assertTrue(body["detail"])
        self.assertEqual(body["code"], "BR-MH-05")

    def test_s3_ac5_ma_br_trong_thong_diep_thanh_code(self):
        item, sup, wh = make_master()
        batch = make_batch(item, sup, wh)
        Batch.objects.filter(pk=batch.pk).update(status=Batch.Status.SELLING)
        chu = make_user("chu1", "chu")
        resp = client_for(chu).post(f"/api/inventory/batches/{batch.pk}/close/")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-LO-04")


class S3ErrorCodeShopAndInternalTests(TestCase):
    """S3-AC5 trên các endpoint tự bắt BusinessError (Shop, webhook nội bộ)."""

    def test_s3_ac5_shop_order_loi_nghiep_vu_co_code(self):
        from apps.catalog.models import ItemPrice, PriceList

        item, _, _ = make_master()
        ItemPrice.objects.create(
            price_list=PriceList.objects.create(name="Bán lẻ", is_default=True), item=item,
            rate=Decimal("100000"), valid_from=timezone.localdate() - datetime.timedelta(days=1),
        )
        resp = client_for(None).post(
            "/api/shop/orders/",
            {
                "customer": {"phone": "0912345678", "name": "Anh A"},
                "delivery_address": "1 Bến Cảng", "phone": "0912345678",
                "items": [{"item_code": item.code, "qty": "1"}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("Không đủ tồn khả dụng", resp.json()["detail"])
        self.assertEqual(resp.json()["code"], "BR-BH-02")

    def test_s3_ac5_webhook_noi_bo_loi_nghiep_vu_co_code(self):
        from unittest import mock

        from django.test import override_settings

        make_order_with_note("SO-W1", "0900000001")
        with override_settings(INTERNAL_SERVICE_TOKEN="tok"), mock.patch(
            "apps.sales.payments.services.confirm_payment",
            side_effect=BusinessError("Giả lập lỗi (BR-TT-03)."),
        ):
            resp = client_for(None).post(
                "/api/internal/payments/sepay-webhook/",
                # received_at bắt buộc từ QA lần 2 · N3 (adapter luôn gửi).
                {"bank_txn_id": "T1", "order_code": "SO-W1", "amount": "100000",
                 "received_at": "2026-09-24T10:00:00+07:00"},
                format="json", HTTP_X_INTERNAL_TOKEN="tok",
            )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json(), {"detail": "Giả lập lỗi (BR-TT-03).", "code": "BR-TT-03"})
