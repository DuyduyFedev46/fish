"""
QA P8 Lô 5 — ca biên/ngoại lệ bổ sung cho SR-15 (lô quá hạn còn tồn), SR-16 (trả NCC), SR-17 (dashboard).
Không sửa code sản phẩm; chỉ bù ca ngoài đường thuận mà test của dev chưa phủ. Dữ liệu giả.

- Luồng đủ: trả NCC nhiều lần -> tồn 0 -> (thiếu kiểm kê thì vẫn chặn BR-KK-05) -> chốt.
- Lô đã từng bán / đơn đã thanh toán bị huỷ sau khi trả hết (kho được hoàn lại lô quá hạn).
- Tranh chấp trả NCC <-> huỷ lô <-> đơn giữ chỗ theo CẢ 2 thứ tự; job TTL chạy 2 lần.
- confirm_qty lệch (màn hình cũ), các dạng số; request_id bấm đúp / lô khác / body khác.
- Quét biên/rác của return-to-supplier: không bao giờ 5xx, 400 thì dữ liệu không đổi.
- Ma trận Group cho 3 endpoint + attention + dashboard, đếm response 200 > 0.
- Rò tiền NCC hoàn: quét mọi endpoint GET x Group, Nhật ký quan_ly, Admin HTML, AI (đếm 200).
- Rò dữ liệu cá nhân ở dashboard; chứng từ không xoá.
"""
import datetime
import json
import re
import unittest
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models import ProtectedError
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import (
    Batch, BatchSupplierReturn, StockLedgerEntry, StockReconciliation,
)
from apps.purchasing.receipts import services as receipt_services
from apps.reports import services as report_services
from apps.sales.models import SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase, find_keys
from apps.sales.payments import services as payment_services
from apps.accounts import roles

REFUND = "1234567"           # tiền NCC hoàn giả — dò rò
PII_NAME = "Khách Giả Năm"
PII_PHONE = "0900000456"
PII_ADDR = "Số 5 Đường Giả"
RECENT_KEYS = {"code", "amount", "status", "status_label", "expires_at"}


class Base(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.cs = make_user("cs_qa5", roles.CUSTOMER_SERVICE)
        self.c_chu = client_for(self.chu)
        self._urls(self.batch)

    def _urls(self, batch):
        self.url = f"/api/inventory/batches/{batch.pk}/return-to-supplier/"
        self.cancel_url = f"/api/inventory/batches/{batch.pk}/cancel-expired/"
        self.close_url = f"/api/inventory/batches/{batch.pk}/close/"

    def _expire(self, batch=None):
        b = batch or self.batch
        Batch.objects.filter(pk=b.pk).update(status=Batch.Status.EXPIRED)
        b.refresh_from_db()

    def _b(self):
        return Batch.objects.get(pk=self.batch.pk)

    def _body(self, **kw):
        body = {"qty": "3.000", "supplier_refund_amount": REFUND, "note": "", "request_id": str(uuid.uuid4())}
        body.update(kw)
        return body

    def _post_return(self, client=None, **kw):
        return (client or self.c_chu).post(self.url, self._body(**kw), format="json")

    def _snap(self):
        b = self._b()
        return (
            b.status, b.qty_available, b.qty_reserved,
            StockLedgerEntry.objects.filter(batch=b).count(),
            BatchSupplierReturn.objects.filter(batch=b).count(),
            AuditLog.objects.count(),
        )

    def _approved_recon(self, batch=None):
        b = batch or self.batch
        rec = StockReconciliation.objects.create(
            count_date=timezone.localdate(), created_by=self.kho, approved_by=self.chu,
            status=StockReconciliation.Status.APPROVED, approved_at=timezone.now(),
        )
        rec.lines.create(batch=b, system_qty=Decimal("0"), counted_qty=Decimal("0"))
        return rec

    def _pay(self, order, txn):
        payment_services.confirm_payment(
            order=order, bank_txn_id=txn, amount=order.total_amount, received_at=timezone.now(),
        )
        order.refresh_from_db()

    def _attention(self, client):
        return client.get("/api/dashboard/attention/")


# ---------------------------------------------------------------------------
class QaFlowTests(Base):
    def test_qa_flow_tra_nhieu_lan_ton_0_roi_chot(self):
        """SR-15-AC2 + SR-16-AC2: 3 lần trả (30/30/40) -> tồn 0, vẫn EXPIRED; chốt cần kiểm kê (BR-KK-05)."""
        self._expire()
        self.assertEqual(self._attention(self.c_chu).json()["expired_batches_open"], 1)
        for qty in ("30", "30.000", "40"):
            r = self._post_return(qty=qty)
            self.assertEqual(r.status_code, 200, r.content)
        b = self._b()
        self.assertEqual((b.status, b.qty_available), (Batch.Status.EXPIRED, Decimal("0")))
        # sổ kho khớp: tổng biến động = tồn
        led = sum(e.qty_change for e in StockLedgerEntry.objects.filter(batch=b))
        self.assertEqual(led, b.qty_available)
        self.assertEqual(BatchSupplierReturn.objects.filter(batch=b).count(), 3)
        # thẻ Cần chú ý về 0 (tồn 0 không còn phải xử lý)
        self.assertEqual(self._attention(self.c_chu).json()["expired_batches_open"], 0)
        # còn 1 điều kiện chốt khác (kiểm kê), KHÔNG còn lý do tồn
        r = self.c_chu.post(self.close_url)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "BR-KK-05")
        self._approved_recon()
        r = self.c_chu.post(self.close_url)
        self.assertEqual(r.status_code, 200, r.content)
        b = self._b()
        self.assertEqual(b.status, Batch.Status.CLOSED)
        # sau chốt: mọi xử lý tồn bị chặn BR-LO-05, số lãi lỗ không đổi
        pnl = report_services.batch_pnl(batch=b)
        self.assertFalse(pnl["provisional"])
        self.assertEqual(pnl["supplier_return_qty"], Decimal("100.000"))
        self.assertEqual(pnl["supplier_refund_amount"], Decimal(REFUND) * 3)
        before = self._snap()
        for url in (self.url,):
            r = self.c_chu.post(url, self._body(qty="1"), format="json")
            self.assertEqual((r.status_code, r.json()["code"]), (400, "BR-LO-05"))
        r = self.c_chu.post(self.cancel_url)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._snap(), before)
        self.assertEqual(report_services.batch_pnl(batch=self._b()), pnl)

    def test_qa_expired_con_ton_khong_chot_duoc_moi_duong(self):
        """SR-15-AC1: API, service, và điều kiện có đủ kiểm kê vẫn không cứu được tồn > 0."""
        self._expire()
        self._approved_recon()
        r = self.c_chu.post(self.close_url)
        self.assertEqual((r.status_code, r.json()["code"]), (400, "BR-LO-04"))
        self.assertEqual(self._b().status, Batch.Status.EXPIRED)
        codes = [m.code for m in batch_services.check_close_batch(self._b())]
        self.assertIn("BR-LO-04", codes)
        # lô CANCELLED tồn 0 (sau huỷ) vẫn chốt được như cũ
        self.assertEqual(self.c_chu.post(self.cancel_url).status_code, 200)
        r = self.c_chu.post(self.close_url)
        self.assertEqual(r.status_code, 200, r.content)

    def test_qa_tra_mot_phan_roi_huy_phan_con_lai_roi_chot(self):
        self._expire()
        self.assertEqual(self._post_return(qty="60").status_code, 200)
        r = self.c_chu.post(self.cancel_url, {"confirm_qty": "40.000"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        b = self._b()
        self.assertEqual((b.status, b.qty_available), (Batch.Status.CANCELLED, Decimal("0")))
        pnl = report_services.batch_pnl(batch=b)
        self.assertEqual(pnl["expired_qty"], Decimal("40.000"))     # chỉ phần huỷ
        self.assertEqual(pnl["supplier_return_qty"], Decimal("60.000"))
        self._approved_recon()
        self.assertEqual(self.c_chu.post(self.close_url).status_code, 200)


# ---------------------------------------------------------------------------
class QaSoldLotTests(Base):
    def test_qa_lo_da_tung_ban_tra_ncc_khong_dong_vao_doanh_thu(self):
        order = self._paid_order(phone="0900000111", txn="FTQA5SOLD01")
        self._expire()
        before = report_services.batch_pnl(batch=self._b())
        self.assertGreater(before["revenue"], 0)
        r = self._post_return(qty="98", supplier_refund_amount="2000000")
        self.assertEqual(r.status_code, 200, r.content)
        after = report_services.batch_pnl(batch=self._b())
        for k in ("revenue", "qty_sold", "reversed_qty", "reversed_revenue", "purchase_cost",
                  "allocated_cost", "landed_unit_cost"):
            self.assertEqual(before[k], after[k], k)
        self.assertEqual(after["total_cost"], before["total_cost"] - Decimal("2000000"))
        self.assertEqual(after["profit"], before["profit"] + Decimal("2000000"))
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)   # đơn cũ không bị ảnh hưởng
        # đơn PAID/PROCESSING tham chiếu lô -> vẫn chặn chốt (BR-LO-04) dù tồn = 0
        codes = [m.code for m in batch_services.check_close_batch(self._b())]
        self.assertIn("BR-LO-04", codes)

    def test_qa_huy_don_da_thanh_toan_sau_khi_tra_het_hoan_kho_ve_lo_quan_han(self):
        """Ngoại lệ: tồn 0 rồi, khách huỷ đơn đã thanh toán -> +kg về lô EXPIRED -> thẻ Cần chú ý sáng lại."""
        order = self._paid_order(phone="0900000111", txn="FTQA5SOLD02")
        self._expire()
        self.assertEqual(self._post_return(qty="98").status_code, 200)
        self.assertEqual(self._attention(self.c_chu).json()["expired_batches_open"], 0)
        order_services.cancel_paid_order(order=order, actor=self.chu, reason="qa")
        b = self._b()
        self.assertEqual(b.status, Batch.Status.EXPIRED)
        self.assertEqual(b.qty_available, Decimal("2.000"))
        self.assertEqual(self._attention(self.c_chu).json()["expired_batches_open"], 1)
        # xử lý tiếp được bằng trả NCC hoặc huỷ
        self.assertEqual(self._post_return(qty="2").status_code, 200)
        self.assertEqual(self._b().qty_available, Decimal("0"))
        led = sum(e.qty_change for e in StockLedgerEntry.objects.filter(batch=self._b()))
        self.assertEqual(led, Decimal("0"))

    def test_qa_lo_da_chot_truoc_moi_thao_tac_khong_doi_lai_lo(self):
        """Quy tắc Duy: lô đã chốt không đổi số. Chốt xong, mọi thao tác Lô 5 chỉ bị chặn."""
        self._paid_order(phone="0900000111", txn="FTQA5CLOSE1")
        Batch.objects.filter(pk=self.batch.pk).update(qty_available=Decimal("0"), status=Batch.Status.CANCELLED)
        self._approved_recon()
        # đơn PAID chặn chốt -> ép trạng thái để chỉ kiểm bất biến lãi lỗ của lô CLOSED
        Batch.objects.filter(pk=self.batch.pk).update(
            status=Batch.Status.CLOSED, closed_at=timezone.now(), closed_by=self.chu)
        b = self._b()
        pnl0 = report_services.batch_pnl(batch=b)
        snap0 = self._snap()
        self.assertEqual(self._post_return(qty="1").status_code, 400)
        self.assertEqual(self.c_chu.post(self.cancel_url, {"confirm_qty": "0"}, format="json").status_code, 400)
        self.assertEqual(self.c_chu.post(self.close_url).status_code, 400)
        self.assertEqual(self._snap(), snap0)
        self.assertEqual(report_services.batch_pnl(batch=self._b()), pnl0)
        # lô khác trả NCC không ảnh hưởng lô đã chốt
        other = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            qty=Decimal("10"), purchase_rate=Decimal("100000"),
        )
        batch_services.publish_batch(batch=other, actor=None)
        self._expire(other)
        self.assertEqual(
            self.c_chu.post(f"/api/inventory/batches/{other.pk}/return-to-supplier/",
                            self._body(qty="10"), format="json").status_code, 200)
        self.assertEqual(report_services.batch_pnl(batch=self._b()), pnl0)

    def test_qa_f11_lo_da_chot_co_huy_phieu_nhap_chi_doi_so_hien_thi(self):
        """F11 áp cho mọi lô (Duy 30/09): expired_qty/cost = 0; total_cost, profit KHÔNG đổi."""
        receipt, batches = receipt_services.create_and_submit_receipt(
            supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            lines=[{"item_code": self.item, "qty": Decimal("5"), "rate": Decimal("1000")}],
            actor=self.kho,
        )
        lot = batches[0]
        receipt_services.cancel_receipt(receipt=receipt, actor=self.kho)
        lot.refresh_from_db()
        self.assertEqual(lot.status, Batch.Status.CANCELLED)
        self.assertTrue(StockLedgerEntry.objects.filter(
            batch=lot, movement_type="WRITE_OFF", reference__startswith="cancel_purchase_receipt").exists())
        Batch.objects.filter(pk=lot.pk).update(status=Batch.Status.CLOSED, closed_at=timezone.now())
        lot.refresh_from_db()
        p = report_services.batch_pnl(batch=lot)
        self.assertEqual(p["expired_qty"], Decimal("0"))
        self.assertEqual(p["expired_cost"], Decimal("0"))
        self.assertEqual(p["total_cost"], p["purchase_cost"] + p["allocated_cost"])
        self.assertEqual(p["profit"], p["revenue"] - p["total_cost"])
        self.assertEqual(p["supplier_refund_amount"], Decimal("0"))


# ---------------------------------------------------------------------------
class QaRaceTests(Base):
    def test_qa_gio_cho_chan_ca_tra_ncc_va_huy_roi_ttl_nha_cho_thi_tra_duoc(self):
        """Thứ tự A: đơn giữ chỗ trước, lô hết hạn; chặn cả 2 xác nhận; job TTL chạy 2 lần; rồi trả được."""
        order = self._order(qty="4")
        self._expire()
        snap = self._snap()
        r = self._post_return(qty="1")
        self.assertEqual((r.status_code, r.json()["code"]), (400, "BR-LO-07"))
        r = self.c_chu.post(self.cancel_url)
        self.assertEqual((r.status_code, r.json()["code"]), (400, "BR-LO-07"))
        self.assertEqual(self._snap(), snap)
        future = timezone.now() + datetime.timedelta(days=1)
        self.assertEqual(order_services.cancel_unpaid_expired(now=future), 1)
        self.assertEqual(order_services.cancel_unpaid_expired(now=future), 0)   # job chạy lần 2
        self.assertEqual(self._b().qty_reserved, Decimal("0"))
        self.assertEqual(self._post_return(qty="100").status_code, 200)

    def test_qa_tra_ncc_truoc_don_thanh_toan_sau_don_khong_mat_tien(self):
        """Thứ tự B: trả NCC trước (lô không giữ chỗ), rồi đơn đặt trước đó... đơn đã giữ chỗ thì trả đã bị chặn.
        Ở đây kiểm: trả xong thì không thể đặt đơn mới trên lô quá hạn (không sellable)."""
        self._expire()
        self.assertEqual(self._post_return(qty="50").status_code, 200)
        from apps.common.exceptions import BusinessError
        with self.assertRaises(BusinessError):
            self._order(qty="1")
        self.assertEqual(self._b().qty_reserved, Decimal("0"))

    def test_qa_thanh_toan_thang_truoc_roi_tra_ncc_chi_tra_phan_con_lai(self):
        """Đơn giữ chỗ thanh toán xong (giữ chỗ -> xuất kho) rồi mới trả NCC: tồn còn 96, không vượt."""
        order = self._order(qty="4")
        self._expire()
        self._pay(order, "FTQA5RACE01")
        self.assertEqual(self._b().qty_available, Decimal("96.000"))
        r = self._post_return(qty="97")
        self.assertEqual((r.status_code, r.json()["code"]), (400, "BR-MH-08"))
        self.assertEqual(self._post_return(qty="96").status_code, 200)
        self.assertEqual(self._b().qty_available, Decimal("0"))
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)

    def test_qa_tra_ncc_truoc_roi_huy_man_hinh_cu_confirm_qty_lech(self):
        """Màn hình cũ mở khi tồn 100; giữa chừng trả 30; bấm 'Đã huỷ' với confirm 100 -> 400 Tồn đã đổi; không đổi gì."""
        self._expire()
        self.assertEqual(self._post_return(qty="30").status_code, 200)
        snap = self._snap()
        r = self.c_chu.post(self.cancel_url, {"confirm_qty": "100.000"}, format="json")
        self.assertEqual((r.status_code, r.json()["code"]), (400, "BR-LO-07"))
        self.assertIn("70,000", r.json()["detail"])
        self.assertEqual(self._snap(), snap)
        self.assertEqual(self._b().status, Batch.Status.EXPIRED)
        # tải lại rồi xác nhận theo số mới: được
        r = self.c_chu.post(self.cancel_url, {"confirm_qty": "70"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_qa_huy_truoc_roi_tra_man_hinh_cu_400_khong_ghi_gi(self):
        self._expire()
        self.assertEqual(self.c_chu.post(self.cancel_url).status_code, 200)
        snap = self._snap()
        r = self._post_return(qty="1")
        self.assertEqual((r.status_code, r.json()["code"]), (400, "BR-LO-07"))
        self.assertEqual(self._snap(), snap)

    def test_qa_huy_lo_ton_0_sau_tra_het_roi_tra_them_400(self):
        self._expire()
        self.assertEqual(self._post_return(qty="100").status_code, 200)
        self.assertEqual(self.c_chu.post(self.cancel_url, {"confirm_qty": "0.000"}, format="json").status_code, 200)
        self.assertEqual(self._b().status, Batch.Status.CANCELLED)
        self.assertEqual(self._post_return(qty="1").status_code, 400)


# ---------------------------------------------------------------------------
class QaConfirmQtyTests(Base):
    def setUp(self):
        super().setUp()
        self._expire()

    def _cancel(self, body):
        return self.c_chu.post(self.cancel_url, body, format="json")

    def test_qa_cac_dang_so_khop_van_huy(self):
        for val in ("100", "100.000", " 100 ", "1E+2", 100, 100.0):
            with self.subTest(val=val):
                Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.EXPIRED, qty_available=Decimal("100"))
                r = self._cancel({"confirm_qty": val})
                self.assertEqual(r.status_code, 200, (val, r.content))
                self.assertEqual(self._b().status, Batch.Status.CANCELLED)

    def test_qa_dang_lech_hoac_rac_400_khong_5xx(self):
        for val in ("99.999", "100.001", "0", "-100", "abc", "NaN", "Infinity", "1e999", "1,5", "100 kg", True):
            with self.subTest(val=val):
                snap = self._snap()
                r = self._cancel({"confirm_qty": val})
                self.assertIn(r.status_code, (400,), (val, r.status_code, r.content[:200]))
                self.assertEqual(self._snap(), snap)

    def test_qa_khong_body_hoac_null_hoac_rong_chay_nhu_cu(self):
        for body in (None, {}, {"confirm_qty": None}, {"confirm_qty": ""}):
            with self.subTest(body=body):
                Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.EXPIRED, qty_available=Decimal("100"))
                r = self.c_chu.post(self.cancel_url, body, format="json") if body is not None else self.c_chu.post(self.cancel_url)
                self.assertEqual(r.status_code, 200, (body, r.content))

    def test_qa_body_form_urlencoded_khong_5xx(self):
        r = self.c_chu.post(self.cancel_url, {"confirm_qty": "100"})
        self.assertEqual(r.status_code, 200, r.content)


# ---------------------------------------------------------------------------
class QaRequestIdTests(Base):
    def setUp(self):
        super().setUp()
        self._expire()

    def test_qa_bam_dup_10_lan_chi_tru_1_lan(self):
        rid = str(uuid.uuid4())
        results = [self._post_return(qty="5", request_id=rid) for _ in range(10)]
        self.assertTrue(all(r.status_code == 200 for r in results))
        self.assertEqual(len({r.json()["return_id"] for r in results}), 1)
        self.assertEqual(self._b().qty_available, Decimal("95.000"))
        self.assertEqual(StockLedgerEntry.objects.filter(batch=self.batch, movement_type="SUPPLIER_RETURN").count(), 1)
        self.assertEqual(BatchSupplierReturn.objects.filter(batch=self.batch).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="return_batch_to_supplier").count(), 1)

    def test_qa_cung_request_id_body_khac_tra_ban_cu_khong_ghi_de(self):
        rid = str(uuid.uuid4())
        r1 = self._post_return(qty="5", request_id=rid, supplier_refund_amount="111")
        r2 = self._post_return(qty="50", request_id=rid, supplier_refund_amount="999999")
        self.assertEqual(r1.json()["return_id"], r2.json()["return_id"])
        self.assertEqual(Decimal(r2.json()["returned_qty"]), Decimal("5.000"))
        rec = BatchSupplierReturn.objects.get()
        self.assertEqual((rec.qty, rec.supplier_refund_amount), (Decimal("5.000"), Decimal("111")))
        self.assertEqual(self._b().qty_available, Decimal("95.000"))

    def test_qa_request_id_lo_khac_400_khong_ghi(self):
        other = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            qty=Decimal("10"), purchase_rate=Decimal("100000"),
        )
        batch_services.publish_batch(batch=other, actor=None)
        self._expire(other)
        rid = str(uuid.uuid4())
        self.assertEqual(self._post_return(qty="5", request_id=rid).status_code, 200)
        r = self.c_chu.post(f"/api/inventory/batches/{other.pk}/return-to-supplier/",
                            self._body(qty="5", request_id=rid), format="json")
        self.assertEqual((r.status_code, r.json()["code"]), (400, "BR-MH-08"))
        other.refresh_from_db()
        self.assertEqual(other.qty_available, Decimal("10.000"))
        self.assertEqual(BatchSupplierReturn.objects.filter(batch=other).count(), 0)

    def test_qa_gui_lai_sau_khi_lo_da_huy_tra_ban_cu_200_khong_tru_kho(self):
        rid = str(uuid.uuid4())
        self.assertEqual(self._post_return(qty="5", request_id=rid).status_code, 200)
        self.assertEqual(self.c_chu.post(self.cancel_url).status_code, 200)
        led_before = StockLedgerEntry.objects.filter(batch=self.batch).count()
        r = self._post_return(qty="5", request_id=rid)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "CANCELLED")
        self.assertEqual(StockLedgerEntry.objects.filter(batch=self.batch).count(), led_before)

    def test_qa_request_id_rac_400(self):
        for rid in ("", "abc", None, "6f1c", [], {}):
            with self.subTest(rid=rid):
                snap = self._snap()
                r = self.c_chu.post(self.url, {"qty": "1", "request_id": rid}, format="json")
                self.assertEqual(r.status_code, 400, (rid, r.content))
                self.assertEqual(self._snap(), snap)


# ---------------------------------------------------------------------------
class QaFuzzReturnTests(Base):
    def setUp(self):
        super().setUp()
        self._expire()

    def _try(self, body, expect_ok=False):
        snap = self._snap()
        r = self.c_chu.post(self.url, body, format="json")
        self.assertLess(r.status_code, 500, (body, r.status_code, r.content[:300]))
        if not expect_ok:
            self.assertEqual(r.status_code, 400, (body, r.content[:300]))
            self.assertEqual(self._snap(), snap, body)
        return r

    def test_qa_qty_bien_va_rac(self):
        rid = lambda: str(uuid.uuid4())
        bad = ["0", "0.000", "-1", "-0.001", "100.001", "1000000000000", "abc", "", " ", "NaN", "sNaN",
               "Infinity", "-Infinity", "1e999", "1E+400", "3,5", "3.0001", "0.0001", "０", "١٢٣",
               None, True, False, [], {}, ["3"], {"a": 1}]
        for q in bad:
            with self.subTest(qty=q):
                self._try({"qty": q, "supplier_refund_amount": "0", "note": "", "request_id": rid()})
        self._try({"supplier_refund_amount": "0", "request_id": rid()})           # thiếu qty
        self._try({"qty": "1", "request_id": rid(), "supplier_refund_amount": "abc"})
        self._try(["qty"])                                                       # body không phải object
        self._try("qty=1")

    def test_qa_qty_hop_le_bien(self):
        for q, exp_left in (("0.001", "99.999"), ("99.999", "0.001")):
            with self.subTest(qty=q):
                Batch.objects.filter(pk=self.batch.pk).update(qty_available=Decimal("100"))
                r = self._try({"qty": q, "request_id": str(uuid.uuid4())}, expect_ok=True)
                self.assertEqual(r.status_code, 200, r.content)
                self.assertAlmostEqual(float(r.json()["qty_available"]), float(exp_left), places=6)
        Batch.objects.filter(pk=self.batch.pk).update(qty_available=Decimal("100"))
        for q in (3, 3.5, " 3 ", "3.0", "003", "3e0", "+3", "1_0"):   # "1_0" = 10 (Python Decimal) — chấp nhận, ghi nhận Low
            with self.subTest(qty=q):
                r = self._try({"qty": q, "request_id": str(uuid.uuid4())}, expect_ok=True)
                self.assertEqual(r.status_code, 200, (q, r.content))

    def test_qa_tien_bien_va_rac(self):
        for amt in ("-1", "-0.01", "0.001", "150000.005", "abc", "NaN", "Infinity", "1e13", "1000000000000",
                    "999999999999999", "1,5", True, [], {}):
            with self.subTest(amt=amt):
                self._try({"qty": "1", "supplier_refund_amount": amt, "request_id": str(uuid.uuid4())})
        for amt, exp in (("0", "0"), ("", "0"), (None, "0"), ("0.01", "0.01"), ("999999999999.99", "999999999999.99"),
                         (150000, "150000"), ("150000.50", "150000.50")):
            with self.subTest(amt=amt):
                r = self._try({"qty": "0.001", "supplier_refund_amount": amt, "request_id": str(uuid.uuid4())},
                              expect_ok=True)
                self.assertEqual(r.status_code, 200, (amt, r.content))
                self.assertEqual(BatchSupplierReturn.objects.order_by("-id").first().supplier_refund_amount,
                                 Decimal(exp))

    def test_qa_ghi_chu_bien(self):
        rid = lambda: str(uuid.uuid4())
        for note in ("x" * 501, "0901234567", "090 123 4567", "0901-234-567", "so tk 1234567890123",
                     "1234 5678 9", "090.123.456.7"):
            with self.subTest(note=note):
                self._try({"qty": "0.001", "note": note, "request_id": rid()})
        for note in ("x" * 500, "12345678", "lô 12, sọt 7, 2 kg", "  trả lại NCC  ", None, ""):
            with self.subTest(note=note):
                r = self._try({"qty": "0.001", "note": note, "request_id": rid()}, expect_ok=True)
                self.assertEqual(r.status_code, 200, (note, r.content))

    def test_qa_khong_5xx_voi_method_khac_va_content_type_sai(self):
        self.assertEqual(self.c_chu.get(self.url).status_code, 405)
        self.assertEqual(self.c_chu.put(self.url, {}, format="json").status_code, 405)
        self.assertEqual(self.c_chu.delete(self.url).status_code, 405)
        r = self.c_chu.post(self.url, "not json", content_type="application/json")
        self.assertLess(r.status_code, 500)
        r = self.c_chu.post(self.url, {"qty": "1", "request_id": str(uuid.uuid4())})  # multipart
        self.assertEqual(r.status_code, 200, r.content)


# ---------------------------------------------------------------------------
class QaPermissionMatrixTests(Base):
    def _principals(self):
        return {
            roles.OWNER: self.c_chu, roles.MANAGER: client_for(self.ql), roles.WAREHOUSE_STAFF: client_for(self.kho),
            roles.DELIVERY_STAFF: client_for(self.giao), roles.CUSTOMER_SERVICE: client_for(self.cs), "khach": client_for(None),
            "khong_nhom": client_for(self.nobody),
        }

    def test_qa_ma_tran_3_endpoint_x_7_nguoi_dung(self):
        expect = {roles.OWNER: 200, roles.MANAGER: 403, roles.WAREHOUSE_STAFF: 403, roles.DELIVERY_STAFF: 403, roles.CUSTOMER_SERVICE: 403, "khach": 401,
                  "khong_nhom": 403}
        ok200 = 0
        for name, client in self._principals().items():
            for ep in ("return", "cancel", "close"):
                self._expire()
                Batch.objects.filter(pk=self.batch.pk).update(qty_available=Decimal("100"))
                if ep == "return":
                    r = client.post(self.url, self._body(qty="1"), format="json")
                    exp = expect[name]
                elif ep == "cancel":
                    r = client.post(self.cancel_url, {"confirm_qty": "100"}, format="json")
                    exp = expect[name]
                else:
                    r = client.post(self.close_url)
                    exp = 400 if name == roles.OWNER else expect[name]   # chu: 400 BR-LO-04 (còn tồn) là hợp lệ
                self.assertEqual(r.status_code, exp, (name, ep, r.status_code, r.content[:200]))
                if r.status_code == 200:
                    ok200 += 1
                if name != roles.OWNER:
                    self.assertEqual(self._b().qty_available, Decimal("100.000"), (name, ep))
                    self.assertNotIn(REFUND, r.content.decode())
                # trả về trạng thái để vòng sau
                Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.EXPIRED)
        self.assertGreater(ok200, 0)
        self.assertEqual(BatchSupplierReturn.objects.filter(created_by__in=[self.ql, self.kho, self.giao, self.cs, self.nobody]).count(), 0)

    def test_qa_403_uu_tien_truoc_validation_va_khong_lo_ton_lo(self):
        self._expire()
        r = client_for(self.ql).post(self.url, {}, format="json")   # body rác nhưng 403 trước
        self.assertEqual(r.status_code, 403)
        r = client_for(self.kho).post(self.url, {"qty": "abc"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_qa_nguoi_chi_co_quyen_cancel_expired_van_lam_duoc_va_chi_the_thoi(self):
        u = make_user("only_perm_qa5", perms=("inventory.cancel_expired_batch", "inventory.view_batch"))
        self._expire()
        c = client_for(u)
        r = c.post(self.url, self._body(qty="1"), format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._attention(c).json(), {"expired_batches_open": 1})


class QaAttentionMatrixTests(Base):
    def test_qa_attention_ma_tran(self):
        self._expire()
        rows = {}
        for name, user in ((roles.OWNER, self.chu), (roles.MANAGER, self.ql), (roles.WAREHOUSE_STAFF, self.kho),
                           (roles.DELIVERY_STAFF, self.giao), (roles.CUSTOMER_SERVICE, self.cs), ("khong_nhom", self.nobody)):
            r = self._attention(client_for(user))
            rows[name] = r
        r_anon = self._attention(client_for(None))
        self.assertEqual(r_anon.status_code, 401)
        self.assertEqual(rows[roles.OWNER].status_code, 200)
        self.assertEqual(rows[roles.OWNER].json()["expired_batches_open"], 1)
        n200 = 1
        for name in (roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE):
            if rows[name].status_code == 200:
                n200 += 1
                self.assertNotIn("expired_batches_open", rows[name].json(), name)
        self.assertEqual(rows["khong_nhom"].status_code, 403)
        self.assertGreaterEqual(n200, 2)
        # nv_giao: hành vi cũ giữ nguyên (chỉ 403 nếu không có quyền nào) — ghi lại thực tế để báo cáo
        self.qa_attention_statuses = {k: v.status_code for k, v in rows.items()}

    def test_qa_attention_dem_theo_trang_thai(self):
        def n():
            return self._attention(self.c_chu).json()["expired_batches_open"]
        self.assertEqual(n(), 0)                                  # đang bán
        self._expire()
        self.assertEqual(n(), 1)
        b2 = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            qty=Decimal("10"), purchase_rate=Decimal("1"))
        Batch.objects.filter(pk=b2.pk).update(status=Batch.Status.EXPIRED)
        self.assertEqual(n(), 2)
        self.c_chu.post(f"/api/inventory/batches/{b2.pk}/return-to-supplier/",
                        self._body(qty="10"), format="json")
        self.assertEqual(n(), 1)                                  # tồn 0 không tính
        self.c_chu.post(self.cancel_url)
        self.assertEqual(n(), 0)                                  # CANCELLED không tính


# ---------------------------------------------------------------------------
class QaDashboardPiiTests(Base):
    def setUp(self):
        super().setUp()
        self._paid_order_pii = order_services.create_order(
            customer_phone=PII_PHONE, customer_name=PII_NAME, delivery_address=PII_ADDR, phone=PII_PHONE,
            lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )
        payment_services.confirm_payment(
            order=self._paid_order_pii, bank_txn_id="FTQA5PII01", amount=self._paid_order_pii.total_amount,
            received_at=timezone.now(), raw_payload={"content": "NGUYEN VAN GIA chuyen", "counter_account_name": "NGUYEN VAN GIA"},
        )
        order_services.create_order(
            customer_phone="0900000789", customer_name="Khách Giả Sáu", delivery_address=PII_ADDR, phone="0900000789",
            lines=[{"item_code": self.item.code, "qty": Decimal("1")}],
        )

    def test_qa_dashboard_5_khoa_moi_group_khong_pii_dem_200(self):
        n200 = 0
        for name, user in ((roles.OWNER, self.chu), (roles.MANAGER, self.ql), (roles.WAREHOUSE_STAFF, self.kho)):
            r = client_for(user).get("/api/dashboard/summary/")
            self.assertEqual(r.status_code, 200, (name, r.content[:200]))
            n200 += 1
            data = r.json()
            self.assertGreaterEqual(len(data["recent_orders"]), 2, name)
            for row in data["recent_orders"]:
                self.assertEqual(set(row), RECENT_KEYS, name)
            raw = r.content.decode()
            for s in (PII_NAME, "Khách Giả Sáu", PII_PHONE, "0900000789", "0456", "0789", PII_ADDR, "NGUYEN VAN GIA",
                      "phone_last4", '"customer"', "delivery_address", "recipient"):
                self.assertNotIn(s, raw, (name, s))
            # có dữ liệu thật (mã đơn) — không xanh giả vì rỗng
            self.assertIn(self._paid_order_pii.code, raw)
        for name, user, exp in ((roles.DELIVERY_STAFF, self.giao, 403), (roles.CUSTOMER_SERVICE, self.cs, 403), ("khong_nhom", self.nobody, 403),
                                ("khach", None, 401)):
            self.assertEqual(client_for(user).get("/api/dashboard/summary/").status_code, exp, name)
        self.assertEqual(n200, 3)

    def test_qa_dashboard_cung_khong_lo_khi_lo_qua_han_va_khong_lo_tien_ncc(self):
        self._expire()
        self._post_return(qty="10")
        for user in (self.chu, self.ql, self.kho):
            r = client_for(user).get("/api/dashboard/summary/")
            self.assertEqual(r.status_code, 200)
            self.assertNotIn(REFUND, r.content.decode())
        r = client_for(self.kho).get("/api/dashboard/summary/")
        self.assertEqual(find_keys(r.json(), COST_KEYS - {"rate"}), set())


# ---------------------------------------------------------------------------
class QaLeakTests(Base):
    """Tiền NCC hoàn (REFUND) không được lọt sang bất kỳ đầu ra nào của người không có quyền."""

    def setUp(self):
        super().setUp()
        self._expire()
        r = self._post_return(qty="10")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.status_code, 200)
        self.return_resp = r

    def _urls_get(self):
        pk, bid = self.batch.pk, self.batch.batch_id
        return [
            "/api/inventory/batches/", f"/api/inventory/batches/{pk}/", f"/api/inventory/batches/{bid}/",
            "/api/inventory/batches/?status=EXPIRED", f"/api/guidance/batch/{pk}/", f"/api/guidance/batch/{bid}/",
            "/api/inventory/ledger/", f"/api/inventory/ledger/?batch={pk}", "/api/audit-logs/",
            "/api/audit-logs/?action=return_batch_to_supplier",
            f"/api/reports/batch/{bid}/", "/api/reports/period/", "/api/dashboard/summary/",
            "/api/dashboard/attention/", "/api/ai/actions/", "/api/ai/commands/index/", "/api/ai/report/daily/",
            "/api/inventory/stock-entries/", "/api/inventory/warehouses/",
        ]

    def test_qa_quet_get_moi_group_khong_lo_tien_ncc(self):
        n200 = 0
        per_group_200 = {}
        for name, user in ((roles.OWNER, self.chu), (roles.MANAGER, self.ql), (roles.WAREHOUSE_STAFF, self.kho),
                           (roles.DELIVERY_STAFF, self.giao), (roles.CUSTOMER_SERVICE, self.cs)):
            c = client_for(user)
            per_group_200[name] = 0
            for url in self._urls_get():
                r = c.get(url)
                self.assertLess(r.status_code, 500, (name, url, r.status_code))
                if r.status_code == 200:
                    n200 += 1
                    per_group_200[name] += 1
                    raw = r.content.decode()
                    if name != roles.OWNER:
                        self.assertNotIn(REFUND, raw, (name, url))
                        self.assertNotIn("1,234,567", raw, (name, url))
                        self.assertNotIn("supplier_refund_amount", raw, (name, url))
                        self.assertNotIn("supplier_return_qty", raw, (name, url))
        self.assertGreater(n200, 30)
        for name in (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF):
            self.assertGreater(per_group_200[name], 5, name)   # không xanh giả vì toàn 403/404

    def test_qa_nhat_ky_quan_ly_khong_thay_tien_chu_thay(self):
        rows_ql = []
        page = "/api/audit-logs/?action=return_batch_to_supplier"
        r = client_for(self.ql).get(page)
        self.assertEqual(r.status_code, 200, r.content[:200])
        rows_ql = r.json()["results"]
        self.assertEqual(len(rows_ql), 1)
        self.assertEqual(set(find_keys(rows_ql, COST_KEYS)), set())
        self.assertNotIn(REFUND, json.dumps(rows_ql))
        r = self.c_chu.get(page)
        raw = json.dumps(r.json()["results"])
        self.assertIn("supplier_refund_amount", raw)
        self.assertIn(REFUND, raw)

    def test_qa_response_tra_ncc_khong_co_tien_hay_khoa_gia_von(self):
        raw = self.return_resp.content.decode()
        self.assertNotIn(REFUND, raw)
        self.assertEqual(find_keys(self.return_resp.json(), COST_KEYS), set())
        self.assertEqual(set(self.return_resp.json()), {"batch_id", "status", "qty_available", "returned_qty", "return_id"})

    def test_qa_khong_suy_nguoc_gia_von_tu_khoa_moi_cua_nguoi_thieu_quyen(self):
        """Người thiếu view_costprice: trả NCC cho họ chỉ có kg (qty) — không có tiền nên không có tiền ÷ kg."""
        r = client_for(self.ql).get("/api/audit-logs/?action=return_batch_to_supplier")
        entry = r.json()["results"][0]
        blob = json.dumps(entry)
        self.assertNotIn("supplier_refund_amount", blob)
        self.assertNotIn("refund", blob.lower().replace("return_batch_to_supplier", ""))
        self.assertNotIn("note\": \"return_batch_to_supplier 10.000kg\"", "")   # noqa — chỉ ghi chú kg, không tiền

    def test_qa_admin_html_khong_lo_tien_ncc_voi_nhan_vien_khong_phai_chu(self):
        """Admin: BatchSupplierReturn không được đăng ký; trang Lô/Sổ kho/Nhật ký của user is_staff (nếu có) không lộ tiền."""
        staff = {}
        for name, grp in ((roles.MANAGER, roles.MANAGER), (roles.WAREHOUSE_STAFF, roles.WAREHOUSE_STAFF)):
            u = make_user(f"staff_{name}_qa5", grp)
            User.objects.filter(pk=u.pk).update(is_staff=True)
            staff[name] = User.objects.get(pk=u.pk)
        n200 = 0
        log = AuditLog.objects.filter(action="return_batch_to_supplier").first()
        pages = [
            "/admin/inventory/batch/", f"/admin/inventory/batch/{self.batch.pk}/change/",
            "/admin/inventory/stockledgerentry/", "/admin/accounts/auditlog/", f"/admin/accounts/auditlog/{log.pk}/change/",
            "/admin/inventory/batchsupplierreturn/",
        ]
        from django.test import Client
        for name, u in staff.items():
            c = Client()
            c.force_login(u)
            for p in pages:
                r = c.get(p)
                self.assertLess(r.status_code, 500, (name, p, r.status_code))
                if r.status_code == 200:
                    n200 += 1
                    raw = r.content.decode()
                    self.assertNotIn(REFUND, raw, (name, p))
                    self.assertNotIn("supplier_refund_amount", raw, (name, p))
        self.assertGreater(n200, 0)
        # superuser: trang BatchSupplierReturn không tồn tại (không đăng ký -> không có màn sửa/xoá)
        su = User.objects.create_superuser("su_qa5", password="x")
        c = Client()
        c.force_login(su)
        self.assertEqual(c.get("/admin/inventory/batchsupplierreturn/").status_code, 404)
        self.assertEqual(c.get("/admin/inventory/batch/").status_code, 200)

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_qa_ai_lenh_tra_ncc_chi_soan_nhap_va_khong_lo_tien_cho_nhom_khac(self):
        from apps.ai.registry.discovery import get_registry
        get_registry().build(force=True)
        rid = str(uuid.uuid4())
        r = self.c_chu.post(
            "/api/ai/commands/inventory.batch.return_to_supplier/call/",
            {"args": {"qty": "5", "supplier_refund_amount": REFUND, "note": "", "request_id": rid},
             "target_id": str(self.batch.pk)}, format="json",
        )
        self.assertEqual(r.status_code, 200, r.content[:300])   # không xanh giả vì AI tắt/403
        data = r.json()
        self.assertEqual((data["outcome"], data["level"]), ("proposal", "C"))
        # không bao giờ tự thực thi: kho không đổi vì AI (đã trả 10 ở setUp)
        self.assertEqual(self._b().qty_available, Decimal("90.000"))
        self.assertEqual(BatchSupplierReturn.objects.filter(batch=self.batch).count(), 1)
        n200 = 0
        for name, user in ((roles.MANAGER, self.ql), (roles.WAREHOUSE_STAFF, self.kho), (roles.DELIVERY_STAFF, self.giao), (roles.CUSTOMER_SERVICE, self.cs)):
            c = client_for(user)
            for url in ("/api/ai/actions/", "/api/ai/commands/index/", "/api/ai/report/daily/"):
                rr = c.get(url)
                self.assertLess(rr.status_code, 500, (name, url))
                if rr.status_code == 200:
                    n200 += 1
                    self.assertNotIn(REFUND, rr.content.decode(), (name, url))
        self.assertGreater(n200, 0)
        self.ai_outcome = data.get("outcome"), data.get("level")


# ---------------------------------------------------------------------------
class QaImmutabilityTests(Base):
    def test_qa_chung_tu_khong_xoa_duoc_qua_api_va_lo_bi_protect(self):
        self._expire()
        rec_id = self._post_return(qty="5").json()["return_id"]
        rec = BatchSupplierReturn.objects.get(pk=rec_id)
        # không có endpoint xoá/sửa bản ghi trả NCC
        for path in (f"/api/inventory/batch-supplier-returns/{rec_id}/", f"/api/inventory/supplier-returns/{rec_id}/"):
            self.assertEqual(self.c_chu.delete(path).status_code, 404)
        # lô có bản ghi trả NCC không xoá được (PROTECT); DELETE lô qua API bị chặn
        with self.assertRaises(ProtectedError):
            Batch.objects.get(pk=self.batch.pk).delete()
        r = self.c_chu.delete(f"/api/inventory/batches/{self.batch.pk}/")
        self.assertIn(r.status_code, (403, 405))
        self.assertTrue(Batch.objects.filter(pk=self.batch.pk).exists())
        # người tạo: PROTECT
        with self.assertRaises(ProtectedError):
            User.objects.get(pk=self.chu.pk).delete()
        # không Group nào có quyền xoá/sửa/thêm model
        from django.contrib.auth.models import Permission
        perms = Permission.objects.filter(content_type__app_label="inventory", content_type__model="batchsupplierreturn")
        self.assertEqual(sorted(p.codename for p in perms), ["view_batchsupplierreturn"])
        self.assertEqual(rec.request_id is not None, True)

    def test_qa_audit_log_ghi_dung_1_dong_moi_hanh_dong_tang_2(self):
        self._expire()
        before = AuditLog.objects.count()
        self._post_return(qty="5")
        rows = AuditLog.objects.filter(action="return_batch_to_supplier")
        self.assertEqual(rows.count(), 1)
        row = rows.first()
        self.assertEqual(row.actor, self.chu)
        self.assertEqual(set(row.changes), {"qty", "supplier_refund_amount"})
        self.assertNotIn("Khách", row.note)
        self.assertEqual(AuditLog.objects.count(), before + 1)
        self.c_chu.post(self.cancel_url, {"confirm_qty": "95"}, format="json")
        self.assertEqual(AuditLog.objects.filter(action="cancel_expired_batch").count(), 1)
        # 400 không ghi audit
        n = AuditLog.objects.count()
        self.assertEqual(self._post_return(qty="1").status_code, 400)
        self.assertEqual(AuditLog.objects.count(), n)

    def test_qa_ghi_chu_khong_lot_vao_audit_hay_api_nao(self):
        self._expire()
        secret = "ghi chu bi mat QA5 abc"
        self.assertEqual(self._post_return(qty="5", note=secret).status_code, 200)
        self.assertEqual(BatchSupplierReturn.objects.get().note, secret)
        row = AuditLog.objects.get(action="return_batch_to_supplier")
        self.assertNotIn(secret, json.dumps([row.note, row.changes], default=str))
        for user in (self.chu, self.ql, self.kho):
            c = client_for(user)
            for url in ("/api/audit-logs/", f"/api/guidance/batch/{self.batch.pk}/", f"/api/inventory/batches/{self.batch.pk}/",
                        f"/api/inventory/ledger/?batch={self.batch.pk}"):
                r = c.get(url)
                if r.status_code == 200:
                    self.assertNotIn(secret, r.content.decode(), (user.username, url))


class QaAdminAuditBaselineTests(Base):
    """B1 (đã sửa): Admin Nhật ký lọc `changes` theo view_costprice, cùng nguồn với /api/audit-logs/."""

    def _logs(self):
        from apps.common.audit import record_audit
        old = record_audit("adjust_price", actor=self.chu, obj=self.batch,
                           changes={"purchase_rate": {"from": "7654321", "to": "7654322"},
                                    "status": ["A", "B"]}, note="khoá cũ")
        self._expire()
        self._post_return(qty="5")
        return old, AuditLog.objects.get(action="return_batch_to_supplier")

    def _get(self, user, log):
        from django.test import Client
        c = Client()
        c.force_login(user)
        r = c.get(f"/admin/accounts/auditlog/{log.pk}/change/")
        self.assertEqual(r.status_code, 200)   # không xanh giả vì 302/403
        return r.content.decode()

    def test_qa_admin_nhat_ky_khoa_cu_va_khoa_lo5_an_voi_staff_quan_ly(self):
        u = make_user("staff_ql_base_qa5", roles.MANAGER)
        User.objects.filter(pk=u.pk).update(is_staff=True)
        u = User.objects.get(pk=u.pk)
        self.assertFalse(u.has_perm("inventory.view_costprice"))
        old, new = self._logs()
        html_old, html_new = self._get(u, old), self._get(u, new)
        for html in (html_old, html_new):
            self.assertNotIn("7654321", html)
            self.assertNotIn(REFUND, html)
            self.assertNotIn("purchase_rate", html)
            self.assertNotIn("supplier_refund_amount", html)
        # khoá không phải giá vốn vẫn hiện (không ẩn quá tay), và chỉ còn kg trong log trả NCC
        self.assertIn("status", html_old)
        self.assertIn("return_batch_to_supplier", html_new)

    def test_qa_admin_nhat_ky_chu_va_superuser_van_thay_du(self):
        old, new = self._logs()
        chu = User.objects.get(pk=self.chu.pk)
        User.objects.filter(pk=chu.pk).update(is_staff=True)
        chu = User.objects.get(pk=chu.pk)
        su = User.objects.create_superuser("su_b1_qa5", password="x")
        for who in (chu, su):
            html_old, html_new = self._get(who, old), self._get(who, new)
            self.assertIn("7654321", html_old, who.username)
            self.assertIn("purchase_rate", html_old, who.username)
            self.assertIn(REFUND, html_new, who.username)
            self.assertIn("supplier_refund_amount", html_new, who.username)


class QaAdminB1MatrixTests(Base):
    """B1 lần 2 — quét MỌI đường Admin của AuditLog bằng HTML thật (đếm 200), Group x đường."""

    SECRET_OLD = "7654321"

    def _seed(self):
        from apps.common.audit import record_audit
        self.old = record_audit(
            "adjust_price", actor=self.chu, obj=self.batch,
            changes={"purchase_rate": {"from": self.SECRET_OLD, "to": "7654322"}, "status": ["A", "B"]},
            note="khoá cũ")
        self.nested = record_audit(
            "adjust_price", actor=self.chu, obj=self.batch,
            changes={"lines": [{"unit_cost": "5550001", "qty": "2"}], "meta": {"purchase_cost": "5550002", "ok": "giu"}},
            note="lồng nhau")
        self.empty = record_audit("adjust_price", actor=self.chu, obj=self.batch, changes={}, note="rỗng")
        self.none = record_audit("adjust_price", actor=self.chu, obj=self.batch, changes=None, note="none")
        self._expire()
        self._post_return(qty="5")
        self.ret = AuditLog.objects.get(action="return_batch_to_supplier")

    def _staff(self, username, group):
        from django.contrib.auth.models import Permission
        u = make_user(username, group)
        u.user_permissions.add(*Permission.objects.filter(codename="view_auditlog"))
        User.objects.filter(pk=u.pk).update(is_staff=True)
        return User.objects.get(pk=u.pk)

    def _pages(self):
        pk = self.ret.pk
        return [
            "/admin/accounts/auditlog/",
            "/admin/accounts/auditlog/?q=return_batch",
            f"/admin/accounts/auditlog/?q={REFUND}",
            f"/admin/accounts/auditlog/?q={self.SECRET_OLD}",
            "/admin/accounts/auditlog/?action=return_batch_to_supplier",
            "/admin/accounts/auditlog/?model_name=Batch",
            "/admin/accounts/auditlog/?actor_kind=USER",
            f"/admin/accounts/auditlog/?created_at__year={timezone.localdate().year}",
            "/admin/accounts/auditlog/?o=1",
            f"/admin/accounts/auditlog/{pk}/change/",
            f"/admin/accounts/auditlog/{self.old.pk}/change/",
            f"/admin/accounts/auditlog/{self.nested.pk}/change/",
            f"/admin/accounts/auditlog/{self.empty.pk}/change/",
            f"/admin/accounts/auditlog/{self.none.pk}/change/",
            f"/admin/accounts/auditlog/{pk}/history/",
            f"/admin/accounts/auditlog/{pk}/delete/",
            f"/admin/accounts/auditlog/{pk}/change/?_popup=1",
            f"/admin/accounts/auditlog/{pk}/",
            "/admin/accounts/auditlog/add/",
            "/admin/accounts/auditlog/export/",
        ]

    def _sweep(self, user, expect_full):
        from django.test import Client
        c = Client()
        c.force_login(user)
        n200 = 0
        leaked = []
        for p in self._pages():
            r = c.get(p, follow=True)
            self.assertLess(r.status_code, 500, (user.username, p, r.status_code))
            if r.status_code != 200:
                continue
            n200 += 1
            raw = r.content.decode()
            m = re.search(r"[?&]q=([^&]+)", p)
            if m:   # trang dội lại đúng chuỗi người dùng gõ (ô tìm kiếm + link lọc) — không phải dữ liệu từ DB
                raw = raw.replace(m.group(1), "<Q>")
            has_secret = any(s in raw for s in (REFUND, self.SECRET_OLD, "5550001", "5550002",
                                                "supplier_refund_amount", "purchase_rate", "unit_cost", "purchase_cost"))
            if has_secret and not expect_full:
                leaked.append(p)
        return n200, leaked

    def test_qa_b1_quan_ly_va_nv_kho_khong_thay_gia_von_o_moi_duong_admin(self):
        self._seed()
        for name, grp in (("b1_quan_ly", roles.MANAGER), ("b1_nv_kho", roles.WAREHOUSE_STAFF)):
            u = self._staff(name, grp)
            self.assertFalse(u.has_perm("inventory.view_costprice"), grp)
            n200, leaked = self._sweep(u, expect_full=False)
            self.assertGreaterEqual(n200, 12, (grp, n200))     # không xanh giả vì 302/403 hàng loạt
            self.assertEqual(leaked, [], grp)

    def test_qa_b1_khoa_khong_nhay_cam_van_hien_va_dong_rong_none_khong_5xx(self):
        from django.test import Client
        self._seed()
        u = self._staff("b1_ql_vis", roles.MANAGER)
        c = Client()
        c.force_login(u)
        html = c.get(f"/admin/accounts/auditlog/{self.nested.pk}/change/").content.decode()
        self.assertIn("giu", html)                      # meta.ok còn
        self.assertIn("qty", html)                      # lines[].qty còn
        for pk in (self.empty.pk, self.none.pk):
            self.assertEqual(c.get(f"/admin/accounts/auditlog/{pk}/change/").status_code, 200)

    def test_qa_b1_chu_va_superuser_thay_du_o_change_view(self):
        from django.test import Client
        self._seed()
        chu = self._staff("b1_chu_full", roles.OWNER)
        su = User.objects.create_superuser("b1_su_full", password="x")
        for who in (chu, su):
            self.assertTrue(who.has_perm("inventory.view_costprice"), who.username)
            c = Client()
            c.force_login(who)
            n200, _ = self._sweep(who, expect_full=True)
            self.assertGreater(n200, 8, who.username)
            r_old = c.get(f"/admin/accounts/auditlog/{self.old.pk}/change/")
            r_ret = c.get(f"/admin/accounts/auditlog/{self.ret.pk}/change/")
            r_nested = c.get(f"/admin/accounts/auditlog/{self.nested.pk}/change/")
            self.assertEqual((r_old.status_code, r_ret.status_code, r_nested.status_code), (200, 200, 200))
            self.assertIn(self.SECRET_OLD, r_old.content.decode())
            self.assertIn("supplier_refund_amount", r_ret.content.decode())
            self.assertIn(REFUND, r_ret.content.decode())
            self.assertIn("5550001", r_nested.content.decode())

    def test_qa_b1_admin_khong_sua_khong_xoa_nhat_ky_va_khong_lam_hong_du_lieu_goc(self):
        """Append-only: POST sửa/xoá bị từ chối; xem bằng staff không ghi đè `changes` trong DB."""
        from django.test import Client
        self._seed()
        before = AuditLog.objects.get(pk=self.ret.pk).changes
        note_before = AuditLog.objects.get(pk=self.ret.pk).note
        self.assertIn("supplier_refund_amount", before)
        n = AuditLog.objects.count()
        for who in (self._staff("b1_ql_ro", roles.MANAGER), User.objects.create_superuser("b1_su_ro", password="x")):
            c = Client()
            c.force_login(who)
            c.get(f"/admin/accounts/auditlog/{self.ret.pk}/change/")
            r_post = c.post(f"/admin/accounts/auditlog/{self.ret.pk}/change/", {"note": "sửa"})
            r_del = c.post(f"/admin/accounts/auditlog/{self.ret.pk}/delete/", {"post": "yes"})
            r_act = c.post("/admin/accounts/auditlog/",
                           {"action": "delete_selected", "_selected_action": [self.ret.pk], "post": "yes"})
            for r in (r_post, r_del, r_act):
                self.assertLess(r.status_code, 500)
        self.assertEqual(AuditLog.objects.count(), n)
        self.assertEqual(AuditLog.objects.get(pk=self.ret.pk).changes, before)
        self.assertEqual(AuditLog.objects.get(pk=self.ret.pk).note, note_before)
