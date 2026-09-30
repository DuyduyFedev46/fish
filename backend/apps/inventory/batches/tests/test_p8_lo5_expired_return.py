"""
P8 Lô 5 — SR-15 (chốt lô quá hạn phải xử lý hết tồn, BR-LO-04/07) và SR-16 (trả NCC, BR-MH-08).
Dữ liệu giả. Lô 100 kg từ `OrderApiBase`, giá mua 180000 đ/kg (số dùng để dò rò giá vốn).

SR-15
- AC1: EXPIRED còn tồn -> check_close_batch / close API -> 400 BR-LO-04; tồn 0 thì không dính lý do tồn.
- AC2: guidance EXPIRED còn tồn: cancel_expired ("Xác nhận Đã huỷ phần tồn"), return_to_supplier, close allowed=false.
       EXPIRED tồn 0: chỉ còn close (không có return_to_supplier).
- AC3: cancel-expired nhận confirm_qty; lệch tồn -> 400 BR-LO-07 "Tồn đã đổi"; khớp/không gửi -> 200.
- AC4: GET /api/dashboard/attention/ có expired_batches_open cho user có quyền; 403 chỉ khi thiếu cả 4 quyền.
SR-16
- AC1: trả một phần -> SUPPLIER_RETURN -kg, lô vẫn EXPIRED, response không có tiền.
- AC2: chặn: không EXPIRED / còn giữ chỗ / lô đã chốt / tồn 0 / qty sai (BR-MH-08).
- AC3: request_id trùng -> không trừ lần 2.
- AC4: kết hợp trả NCC + huỷ phần còn lại; batch_pnl (kg trả, tiền hoàn giảm total_cost) ở test reports.
- AC5: ghi chú có dãy số dài -> 400; audit không chứa dữ liệu cá nhân.
- AC6: không rò tiền NCC hoàn: response, Nhật ký của quan_ly, BatchSerializer.
- Ma trận Group: chu 200/400, quan_ly/nv_kho/nv_giao/cskh 403, khách 401.
"""
import datetime
import json
import uuid
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.execution import safety
from apps.ai.execution.tests import test_dw25_close_batch as dw25
from apps.ai.models import AiAction, AiConfigVersion, AiPolicyVersion
from apps.common.cost_keys import COST_KEYS
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, BatchSupplierReturn, StockLedgerEntry
from apps.sales.orders.tests.test_s10_api import OrderApiBase, find_keys

REFUND_SENTINEL = "1234567"  # tiền NCC hoàn giả, dùng để dò rò trong JSON


class Lo5Base(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.cs = make_user("cs_lo5", "cskh")
        self.c_chu = client_for(self.chu)
        self.url = f"/api/inventory/batches/{self.batch.pk}/return-to-supplier/"
        self.cancel_url = f"/api/inventory/batches/{self.batch.pk}/cancel-expired/"
        self.close_url = f"/api/inventory/batches/{self.batch.pk}/close/"

    def _expire(self):
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.EXPIRED)
        self.batch.refresh_from_db()

    def _set_stock(self, qty):
        Batch.objects.filter(pk=self.batch.pk).update(qty_available=Decimal(qty))
        self.batch.refresh_from_db()

    def _body(self, **kw):
        body = {"qty": "3.000", "supplier_refund_amount": REFUND_SENTINEL, "note": "",
                "request_id": str(uuid.uuid4())}
        body.update(kw)
        return body

    def _returns(self):
        return BatchSupplierReturn.objects.filter(batch=self.batch).count()

    def _ledger(self, mt):
        return StockLedgerEntry.objects.filter(batch=self.batch, movement_type=mt).count()


class SR15CloseExpiredTests(Lo5Base):
    def test_sr15_ac1_close_expired_con_ton_bi_chan_br_lo_04(self):
        self._expire()
        codes = [m.code for m in batch_services.check_close_batch(self.batch)]
        self.assertIn("BR-LO-04", codes)
        texts = " ".join(m.text for m in batch_services.check_close_batch(self.batch))
        self.assertIn("tồn = 0", texts)
        with self.assertRaises(BusinessError) as ctx:
            batch_services.close_batch(batch=self.batch, actor=self.chu)
        self.assertEqual(ctx.exception.code, "BR-LO-04")

    def test_sr15_ac1_close_api_expired_con_ton_400(self):
        self._expire()
        resp = self.c_chu.post(self.close_url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-04")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, Batch.Status.EXPIRED)

    def test_sr15_ac1_expired_ton_0_khong_dinh_ly_do_ton(self):
        self._expire()
        self._set_stock("0")
        texts = [m.text for m in batch_services.check_close_batch(self.batch)]
        self.assertFalse([t for t in texts if "tồn = 0" in t], texts)

    def test_sr15_ac1_lo_dang_ban_van_bi_chan_khi_con_ton(self):
        codes = [m.code for m in batch_services.check_close_batch(self.batch)]
        self.assertIn("BR-LO-04", codes)

    def test_sr15_ac2_guidance_expired_con_ton_du_3_buoc(self):
        self._expire()
        resp = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, 200)
        steps = {s["key"]: s for s in resp.json()["next_steps"]}
        self.assertEqual(steps["cancel_expired"]["label"], "Xác nhận Đã huỷ phần tồn")
        self.assertTrue(steps["cancel_expired"]["allowed"])
        ret = steps["return_to_supplier"]
        self.assertEqual(ret["label"], "Xác nhận Đã trả NCC")
        self.assertEqual(ret["command"], "inventory.batch.return_to_supplier")
        self.assertTrue(ret["allowed"])
        self.assertFalse(steps["close"]["allowed"])
        self.assertIn("BR-LO-04", [m["code"] for m in steps["close"]["missing"]])

    def test_sr15_ac2_guidance_con_giu_cho_chan_ca_hai_buoc_xu_ly(self):
        self._order(qty="2")
        self._expire()
        resp = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        steps = {s["key"]: s for s in resp.json()["next_steps"]}
        for key in ("cancel_expired", "return_to_supplier"):
            self.assertFalse(steps[key]["allowed"], key)
            self.assertIn("BR-LO-07", [m["code"] for m in steps[key]["missing"]], key)

    def test_sr15_ac2_guidance_expired_ton_0_chi_con_buoc_chot(self):
        self._expire()
        self._set_stock("0")
        resp = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        steps = {s["key"]: s for s in resp.json()["next_steps"]}
        self.assertNotIn("return_to_supplier", steps)
        self.assertIn("close", steps)
        self.assertNotIn("BR-LO-04", [
            m["code"] for m in steps["close"]["missing"] if "tồn" in m["text"]
        ])

    def test_sr15_ac2_guidance_quan_ly_thay_buoc_khong_duoc_phep(self):
        self._expire()
        ql = make_user("ql_lo5g", "quan_ly")
        resp = client_for(ql).get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, 200)
        steps = {s["key"]: s for s in resp.json()["next_steps"]}
        self.assertFalse(steps["return_to_supplier"]["allowed"])
        self.assertIn("BR-PQ-12", [m["code"] for m in steps["return_to_supplier"]["missing"]])
        self.assertFalse(find_keys(resp.json(), set(COST_KEYS)))

    # --- AC3: confirm_qty ----------------------------------------------------
    def test_sr15_ac3_confirm_qty_lech_ton_400_khong_huy(self):
        self._expire()
        resp = self.c_chu.post(self.cancel_url, {"confirm_qty": "50.000"}, format="json")
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["code"], "BR-LO-07")
        self.assertEqual(body["detail"], "Tồn đã đổi (100,000 kg) — tải lại.")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, Batch.Status.EXPIRED)
        self.assertEqual(self.batch.qty_available, Decimal("100.000"))
        self.assertEqual(self._ledger("WRITE_OFF"), 0)

    def test_sr15_ac3_confirm_qty_khop_huy_thanh_cong(self):
        self._expire()
        resp = self.c_chu.post(self.cancel_url, {"confirm_qty": "100.000"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], Batch.Status.CANCELLED)
        self.assertEqual(self._ledger("WRITE_OFF"), 1)

    def test_sr15_ac3_confirm_qty_khong_gui_van_huy_duoc(self):
        self._expire()
        self.assertEqual(self.c_chu.post(self.cancel_url).status_code, 200)

    def test_sr15_ac3_confirm_qty_rac_400_br_lo_07(self):
        self._expire()
        resp = self.c_chu.post(self.cancel_url, {"confirm_qty": "abc"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-07")

    def test_sr15_ac3_tra_ncc_mot_phan_roi_huy_confirm_theo_ton_moi(self):
        self._expire()
        self.assertEqual(self.c_chu.post(self.url, self._body(qty="30"), format="json").status_code, 200)
        # màn hình cũ còn hiển thị 100 kg -> lệch
        stale = self.c_chu.post(self.cancel_url, {"confirm_qty": "100.000"}, format="json")
        self.assertEqual(stale.status_code, 400)
        self.assertEqual(stale.json()["detail"], "Tồn đã đổi (70,000 kg) — tải lại.")
        ok = self.c_chu.post(self.cancel_url, {"confirm_qty": "70.000"}, format="json")
        self.assertEqual(ok.status_code, 200)
        entry = StockLedgerEntry.objects.get(batch=self.batch, movement_type="WRITE_OFF")
        self.assertEqual(entry.qty_change, Decimal("-70.000"))

    # --- AC4: Cần chú ý ------------------------------------------------------
    def test_sr15_ac4_attention_dem_lo_qua_han_con_ton(self):
        self._expire()
        resp = self.c_chu.get("/api/dashboard/attention/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["expired_batches_open"], 1)

    def test_sr15_ac4_attention_khong_dem_lo_ton_0_hoac_lo_da_huy(self):
        self._expire()
        self._set_stock("0")
        self.assertEqual(self.c_chu.get("/api/dashboard/attention/").json()["expired_batches_open"], 0)

    def test_sr15_ac4_attention_quan_ly_khong_co_khoa(self):
        self._expire()
        resp = client_for(self.ql).get("/api/dashboard/attention/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("expired_batches_open", resp.json())

    def test_sr15_ac4_attention_chi_co_quyen_huy_lo_van_200(self):
        self._expire()
        only = make_user("only_lo5", perms=("inventory.cancel_expired_batch",))
        resp = client_for(only).get("/api/dashboard/attention/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"expired_batches_open": 1})

    def test_sr15_ac4_attention_thieu_ca_4_quyen_403_khach_401(self):
        self.assertEqual(client_for(self.nobody).get("/api/dashboard/attention/").status_code, 403)
        self.assertEqual(client_for(None).get("/api/dashboard/attention/").status_code, 401)


class SR16ReturnToSupplierTests(Lo5Base):
    def setUp(self):
        super().setUp()
        self._expire()

    # --- AC1 -----------------------------------------------------------------
    def test_sr16_ac1_tra_mot_phan_tru_kho_lo_van_expired(self):
        body = self._body(qty="3.000")
        resp = self.c_chu.post(self.url, body, format="json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(set(data.keys()), {"batch_id", "status", "qty_available", "returned_qty", "return_id"})
        self.assertEqual(data["batch_id"], self.batch.batch_id)
        self.assertEqual(data["status"], "EXPIRED")
        self.assertEqual(Decimal(data["qty_available"]), Decimal("97.000"))
        self.assertEqual(Decimal(data["returned_qty"]), Decimal("3.000"))

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, Batch.Status.EXPIRED)
        self.assertEqual(self.batch.qty_available, Decimal("97.000"))
        rec = BatchSupplierReturn.objects.get(pk=data["return_id"])
        self.assertEqual(rec.qty, Decimal("3.000"))
        self.assertEqual(rec.supplier_refund_amount, Decimal(REFUND_SENTINEL))
        self.assertEqual(rec.created_by, self.chu)
        entry = StockLedgerEntry.objects.get(batch=self.batch, movement_type="SUPPLIER_RETURN")
        self.assertEqual(entry.qty_change, Decimal("-3.000"))
        self.assertEqual(entry.reference, f"supplier_return SR-{rec.pk}")

    def test_sr16_ac1_khong_gui_tien_thi_mac_dinh_0(self):
        body = self._body()
        body.pop("supplier_refund_amount")
        resp = self.c_chu.post(self.url, body, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(BatchSupplierReturn.objects.get().supplier_refund_amount, Decimal("0"))

    def test_sr16_ac1_tra_het_ton_lo_van_expired_va_buoc_chot_mo(self):
        resp = self.c_chu.post(self.url, self._body(qty="100"), format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Decimal(resp.json()["qty_available"]), Decimal("0"))
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, Batch.Status.EXPIRED)
        texts = [m.text for m in batch_services.check_close_batch(self.batch)]
        self.assertFalse([t for t in texts if "tồn = 0" in t], texts)

    # --- AC2: chặn -----------------------------------------------------------
    def test_sr16_ac2_vuot_ton_400_br_mh_08(self):
        resp = self.c_chu.post(self.url, self._body(qty="100.001"), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-MH-08")
        self.assertEqual(resp.json()["detail"], "Số kg trả phải lớn hơn 0 và không vượt tồn 100,000 kg.")
        self.assertEqual(self._returns(), 0)
        self.assertEqual(self._ledger("SUPPLIER_RETURN"), 0)

    def test_sr16_ac2_qty_khong_hop_le_400_br_mh_08(self):
        for bad in ("0", "-1", "abc", "", "NaN", "Infinity", None):
            with self.subTest(qty=bad):
                resp = self.c_chu.post(self.url, self._body(qty=bad), format="json")
                self.assertEqual(resp.status_code, 400)
                self.assertEqual(resp.json()["code"], "BR-MH-08")
        self.assertEqual(self._returns(), 0)

    def test_sr16_ac2_tien_hoan_am_hoac_rac_400_br_mh_08(self):
        for bad in ("-1", "abc", "NaN", "Infinity"):
            with self.subTest(refund=bad):
                resp = self.c_chu.post(self.url, self._body(supplier_refund_amount=bad), format="json")
                self.assertEqual(resp.status_code, 400)
                self.assertEqual(resp.json()["code"], "BR-MH-08")
        self.assertEqual(self._returns(), 0)

    def test_sr16_ac2_tien_hoan_vuot_gioi_han_cot_400(self):
        resp = self.c_chu.post(self.url, self._body(supplier_refund_amount="1" + "0" * 15), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-MH-08")

    def test_sr16_ac2_khong_phai_expired_400_br_lo_07(self):
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.SELLING)
        resp = self.c_chu.post(self.url, self._body(), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-07")
        self.assertEqual(resp.json()["detail"], "Chỉ xác nhận trả NCC cho lô Quá hạn còn tồn.")
        self.assertEqual(self._returns(), 0)

    def test_sr16_ac2_ton_0_400_br_lo_07(self):
        self._set_stock("0")
        resp = self.c_chu.post(self.url, self._body(), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-07")
        self.assertEqual(resp.json()["detail"], "Chỉ xác nhận trả NCC cho lô Quá hạn còn tồn.")

    def test_sr16_ac2_con_giu_cho_400_br_lo_07(self):
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.SELLING)
        self._order(qty="2")
        self._expire()
        resp = self.c_chu.post(self.url, self._body(), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-07")
        self.assertEqual(
            resp.json()["detail"],
            "Còn 2,000 kg đang giữ chỗ của 1 đơn — chờ đơn thanh toán hoặc hết hạn giữ chỗ rồi huỷ.",
        )
        self.assertEqual(self._returns(), 0)
        self.assertEqual(self._ledger("SUPPLIER_RETURN"), 0)

    def test_sr16_ac2_lo_da_chot_400_br_lo_05(self):
        Batch.objects.filter(pk=self.batch.pk).update(
            status=Batch.Status.CLOSED, closed_at=timezone.now())
        resp = self.c_chu.post(self.url, self._body(), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-05")
        self.assertEqual(resp.json()["detail"], "Lô đã chốt.")
        self.assertEqual(self._returns(), 0)

    def test_sr16_ac2_lo_da_huy_400_khong_ghi_gi(self):
        self.assertEqual(self.c_chu.post(self.cancel_url).status_code, 200)
        resp = self.c_chu.post(self.url, self._body(), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-07")
        self.assertEqual(self._returns(), 0)

    def test_sr16_ac2_thieu_request_id_400(self):
        body = self._body()
        body.pop("request_id")
        resp = self.c_chu.post(self.url, body, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self._returns(), 0)

    # --- AC3: idempotent -----------------------------------------------------
    def test_sr16_ac3_request_id_trung_khong_tru_lan_2(self):
        body = self._body(qty="3")
        r1 = self.c_chu.post(self.url, body, format="json")
        r2 = self.c_chu.post(self.url, body, format="json")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json(), r2.json())
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("97.000"))
        self.assertEqual(self._returns(), 1)
        self.assertEqual(self._ledger("SUPPLIER_RETURN"), 1)
        self.assertEqual(AuditLog.objects.filter(action="return_batch_to_supplier").count(), 1)

    def test_sr16_ac3_hai_request_id_khac_nhau_tru_hai_lan(self):
        self.assertEqual(self.c_chu.post(self.url, self._body(qty="3"), format="json").status_code, 200)
        self.assertEqual(self.c_chu.post(self.url, self._body(qty="4"), format="json").status_code, 200)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("93.000"))
        self.assertEqual(self._returns(), 2)

    def test_sr16_ac3_request_id_trung_luc_ton_da_doi_van_tra_ban_cu(self):
        body = self._body(qty="60")
        self.assertEqual(self.c_chu.post(self.url, body, format="json").status_code, 200)
        # 60 kg > tồn còn 40, nhưng cùng request_id -> bản ghi cũ, không 400
        again = self.c_chu.post(self.url, body, format="json")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(self._returns(), 1)

    def test_sr16_ac3_request_id_da_dung_cho_lo_khac_400_br_mh_08(self):
        """T5-2: request_id của lô A gửi cho lô B -> 400, tồn B không đổi, không tạo bản ghi mới."""
        rid = str(uuid.uuid4())
        self.assertEqual(self.c_chu.post(self.url, self._body(qty="3", request_id=rid), format="json").status_code, 200)
        batch_b = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            qty=Decimal("50"), purchase_rate=Decimal("180000"),
        )
        Batch.objects.filter(pk=batch_b.pk).update(status=Batch.Status.EXPIRED)
        url_b = f"/api/inventory/batches/{batch_b.pk}/return-to-supplier/"
        before_total = BatchSupplierReturn.objects.count()
        before_ledger = StockLedgerEntry.objects.filter(movement_type="SUPPLIER_RETURN").count()

        resp = self.c_chu.post(url_b, self._body(qty="5", request_id=rid), format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-MH-08")
        batch_b.refresh_from_db()
        self.assertEqual(batch_b.qty_available, Decimal("50.000"))
        self.assertEqual(BatchSupplierReturn.objects.filter(batch=batch_b).count(), 0)
        self.assertEqual(BatchSupplierReturn.objects.count(), before_total)
        self.assertEqual(StockLedgerEntry.objects.filter(movement_type="SUPPLIER_RETURN").count(), before_ledger)
        # lô A giữ nguyên kết quả lần trả đầu
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("97.000"))
        self.assertEqual(self._returns(), 1)

    # --- AC4: kết hợp trả + huỷ ---------------------------------------------
    def test_sr16_ac4_tra_ncc_roi_huy_phan_con_lai(self):
        self.assertEqual(self.c_chu.post(self.url, self._body(qty="30"), format="json").status_code, 200)
        resp = self.c_chu.post(self.cancel_url, {"confirm_qty": "70.000"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, Batch.Status.CANCELLED)
        self.assertEqual(self.batch.qty_available, Decimal("0"))
        self.assertEqual(self._ledger("SUPPLIER_RETURN"), 1)
        self.assertEqual(self._ledger("WRITE_OFF"), 1)

    def test_sr16_ac4_huy_lo_ton_0_sau_khi_tra_het_van_duoc(self):
        self.assertEqual(self.c_chu.post(self.url, self._body(qty="100"), format="json").status_code, 200)
        resp = self.c_chu.post(self.cancel_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._ledger("WRITE_OFF"), 0)

    # --- AC5: ghi chú --------------------------------------------------------
    def test_sr16_ac5_ghi_chu_co_day_so_dai_400(self):
        for note in ("goi 0900000111 nhe", "0900 000 111", "0900.000.111", "so 090-000-0111"):
            with self.subTest(note=note):
                resp = self.c_chu.post(self.url, self._body(note=note), format="json")
                self.assertEqual(resp.status_code, 400)
                self.assertEqual(resp.json()["code"], "BR-MH-08")
                self.assertNotIn("0900000111", resp.content.decode())
        self.assertEqual(self._returns(), 0)

    def test_sr16_ac5_ghi_chu_dai_qua_500_400(self):
        resp = self.c_chu.post(self.url, self._body(note="a" * 501), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-MH-08")

    def test_sr16_ac5_ghi_chu_binh_thuong_luu_duoc_audit_khong_chua_ghi_chu(self):
        resp = self.c_chu.post(self.url, self._body(note="Cá ươn, NCC nhận lại"), format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(BatchSupplierReturn.objects.get().note, "Cá ươn, NCC nhận lại")
        log = AuditLog.objects.get(action="return_batch_to_supplier")
        self.assertNotIn("Cá ươn", json.dumps([log.changes, log.note], ensure_ascii=False))

    # --- AC6: không rò tiền / giá vốn ---------------------------------------
    def test_sr16_ac6_response_khong_chua_tien_hay_khoa_gia_von(self):
        resp = self.c_chu.post(self.url, self._body(), format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(find_keys(resp.json(), set(COST_KEYS)))
        raw = resp.content.decode()
        self.assertNotIn(REFUND_SENTINEL, raw)
        self.assertNotIn("180000", raw)

    def test_sr16_ac6_400_khong_chua_tien(self):
        resp = self.c_chu.post(self.url, self._body(qty="999"), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(set(resp.json().keys()), {"detail", "code"})
        self.assertNotIn(REFUND_SENTINEL, resp.content.decode())

    def test_sr16_ac6_batch_serializer_khong_them_field_tien(self):
        self.c_chu.post(self.url, self._body(), format="json")
        for user in (self.chu, self.kho):
            with self.subTest(user=user.username):
                data = client_for(user).get(f"/api/inventory/batches/{self.batch.pk}/").json()
                self.assertFalse({k for k in data if "refund" in k or "supplier_return" in k})
                self.assertNotIn(REFUND_SENTINEL, json.dumps(data))
        kho_data = client_for(self.kho).get(f"/api/inventory/batches/{self.batch.pk}/").json()
        self.assertNotIn("purchase_rate", kho_data)
        self.assertNotIn("landed_unit_cost", kho_data)

    def test_sr16_ac6_nhat_ky_quan_ly_khong_thay_tien_ncc_hoan_quet_het_trang(self):
        self.assertEqual(self.c_chu.post(self.url, self._body(qty="3"), format="json").status_code, 200)
        raw = AuditLog.objects.get(action="return_batch_to_supplier")
        self.assertIn("supplier_refund_amount", raw.changes)  # DB vẫn giữ (không đổi dữ liệu)

        client = client_for(self.ql)
        ok_responses = 0
        seen = set()
        blob = ""
        leaked = set()
        params = {}
        while True:
            resp = client.get("/api/audit-logs/", params)
            self.assertEqual(resp.status_code, 200)
            ok_responses += 1
            data = resp.json()
            blob += json.dumps([[r["changes"], r["note"]] for r in data["results"]], ensure_ascii=False)
            for row in data["results"]:
                seen.add(row["action"])
                leaked |= find_keys(row["changes"], set(COST_KEYS))
            if not data.get("next"):
                break
            params = {"page": (params.get("page") or 1) + 1}
        self.assertGreater(ok_responses, 0)
        self.assertIn("return_batch_to_supplier", seen)
        self.assertEqual(leaked, set())
        self.assertNotIn(REFUND_SENTINEL, blob)
        # Chủ thấy đủ
        chu_blob = json.dumps(client_for(self.chu).get("/api/audit-logs/").json())
        self.assertIn(REFUND_SENTINEL, chu_blob)

    # --- Ma trận Group -------------------------------------------------------
    def test_sr16_ma_tran_group(self):
        for user in (self.ql, self.kho, self.giao, self.cs):
            with self.subTest(user=user.username):
                self.assertEqual(client_for(user).post(self.url, self._body(), format="json").status_code, 403)
        self.assertEqual(client_for(None).post(self.url, self._body(), format="json").status_code, 401)
        self.assertEqual(self._returns(), 0)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("100.000"))
        # chu: 200 và 400 nghiệp vụ thật
        self.assertEqual(self.c_chu.post(self.url, self._body(), format="json").status_code, 200)
        self.assertEqual(self.c_chu.post(self.url, self._body(qty="0"), format="json").status_code, 400)

    def test_sr16_ma_tran_group_403_khong_chua_khoa_tien(self):
        resp = client_for(self.ql).post(self.url, self._body(), format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn(REFUND_SENTINEL, resp.content.decode())

    def test_sr16_lo_khong_ton_tai_404(self):
        url = "/api/inventory/batches/999999/return-to-supplier/"
        self.assertEqual(self.c_chu.post(url, self._body(), format="json").status_code, 404)

    def test_sr16_goi_bang_batch_id(self):
        url = f"/api/inventory/batches/{self.batch.batch_id}/return-to-supplier/"
        self.assertEqual(self.c_chu.post(url, self._body(qty="1"), format="json").status_code, 200)

    # --- Service -------------------------------------------------------------
    def test_sr16_service_raise_business_error_khong_doi_du_lieu(self):
        with self.assertRaises(BusinessError) as ctx:
            batch_services.return_batch_to_supplier(
                batch=self.batch, qty="500", supplier_refund_amount="0", note="",
                request_id=uuid.uuid4(), actor=self.chu,
            )
        self.assertEqual(ctx.exception.code, "BR-MH-08")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("100.000"))

    def test_sr16_ledger_khong_am_sau_nhieu_lan_tra(self):
        for _ in range(4):
            self.c_chu.post(self.url, self._body(qty="30"), format="json")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("10.000"))
        self.assertEqual(self._returns(), 3)
        last = self.c_chu.post(self.url, self._body(qty="30"), format="json")
        self.assertEqual(last.status_code, 400)


@override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
class SR15AiFloorTests(TestCase):
    """T5-1 (SR-15-AC1, BR-LO-04): luật sàn AI không chốt được lô EXPIRED còn tồn."""

    _create_fully_eligible_batch = dw25.CloseBatchAiTests._create_fully_eligible_batch

    def setUp(self):
        dw25.CloseBatchAiTests.setUp(self)

    def _expired_with_stock(self):
        batch = self._create_fully_eligible_batch()  # đủ mọi điều kiện sàn, tồn 0
        Batch.objects.filter(pk=batch.pk).update(status=Batch.Status.EXPIRED, qty_available=Decimal("40.000"))
        batch.refresh_from_db()
        return batch

    def _open_ai(self):
        AiPolicyVersion.objects.create(
            version=1, global_mode="on", red_zone_open={"inventory.close_batch": True}, created_by=self.u_chu)
        AiConfigVersion.objects.create(
            user=self.u_chu, version=1, overrides={"inventory.batch.close": "B"}, created_by=self.u_chu)

    def test_t5_1_sr15_ac1_luat_san_ai_expired_con_ton_khong_ok(self):
        batch = self._expired_with_stock()
        ok, reason = safety.check_ai_close_batch_conditions(batch)
        self.assertFalse(ok)
        self.assertEqual(reason["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")
        self.assertIn("tồn = 0", reason["text"])

    def test_t5_1_sr15_ac1_doi_chung_expired_ton_0_van_ok(self):
        batch = self._expired_with_stock()
        Batch.objects.filter(pk=batch.pk).update(qty_available=Decimal("0"))
        batch.refresh_from_db()
        ok, reason = safety.check_ai_close_batch_conditions(batch)
        self.assertTrue(ok, reason)

    def test_t5_1_sr15_ac1_lenh_ai_qua_api_ha_C_khong_chot(self):
        batch = self._expired_with_stock()
        self._open_ai()
        res = self.client_chu.post(
            "/api/ai/commands/inventory.batch.close/call/",
            {"args": {}, "target_id": str(batch.id)}, format="json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["outcome"], "proposal")
        self.assertEqual(data["level"], "C")
        self.assertEqual(data["downgrade_reason"]["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")
        self.assertEqual(AiAction.objects.get(pk=data["action_id"]).status, AiAction.Status.PENDING)
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.EXPIRED)
        self.assertEqual(batch.qty_available, Decimal("40.000"))

    def test_t5_1_sr15_ac1_job_run_due_ai_actions_escalated_khong_chot(self):
        batch = self._expired_with_stock()
        self._open_ai()
        act = AiAction.objects.create(
            command="inventory.batch.close", kind="write", level="B", status="SCHEDULED", owner=self.u_chu,
            target_model="batch", target_id=str(batch.id),
            execute_after=timezone.now() - datetime.timedelta(seconds=5),
        )
        call_command("run_due_ai_actions")
        act.refresh_from_db()
        batch.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.ESCALATED)
        self.assertEqual(act.assignee_group, "chu")
        self.assertEqual(act.downgrade_reason["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")
        self.assertEqual(batch.status, Batch.Status.EXPIRED)
        self.assertEqual(batch.qty_available, Decimal("40.000"))


class SR16AiCapTests(Lo5Base):
    def test_sr16_lenh_ai_return_to_supplier_toi_da_cap_C(self):
        from apps.ai.registry.discovery import get_registry
        spec = get_registry().get("inventory.batch.return_to_supplier")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.max_level, "C")
        self.assertTrue(spec.force_c)  # quyền huỷ lô quá hạn thuộc FORCE_C_PERMS: AI chỉ soạn nháp
        cancel = get_registry().get("inventory.batch.cancel_expired")
        self.assertIsNotNone(cancel)
