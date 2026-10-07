"""
P8 Lô 5 — báo cáo lô có phần trả NCC (SR-16, BR-MH-08, BR-BC-04), F11 (expired_qty chỉ đếm huỷ lô quá hạn)
và SR-17 (dashboard `recent_orders` không có dữ liệu cá nhân). Dữ liệu giả.

- SR-16-AC4: batch_pnl có supplier_return_qty, supplier_refund_amount; total_cost = mua + phân bổ − tiền NCC hoàn.
- SR-16-AC4b: landed_unit_cost KHÔNG đổi khi NCC hoàn tiền; period_pnl không đổi.
- F11: WRITE_OFF của huỷ phiếu nhập không tính vào expired_qty.
- SR-17: recent_orders có đúng {id, code, amount, status, status_label, expires_at, reason} (không tên, SĐT).
"""
import json
import uuid
from decimal import Decimal

from django.utils import timezone

from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, StockLedgerEntry
from apps.inventory.stock import services as stock
from apps.reports import services as report_services
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase, find_keys
from apps.accounts import roles

DASH_URL = "/api/dashboard/summary/"
RECENT_KEYS = {"id", "code", "amount", "status", "status_label", "expires_at", "reason"}  # Lô 17a (TL15-dash)


class Lo5PnlTests(OrderApiBase):
    def _expire(self):
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.EXPIRED)
        self.batch.refresh_from_db()

    def _return(self, qty, refund):
        return batch_services.return_batch_to_supplier(
            batch=self.batch, qty=qty, supplier_refund_amount=refund, note="",
            request_id=uuid.uuid4(), actor=self.chu,
        )

    def test_sr16_ac4_batch_pnl_co_kg_tra_ncc_va_tien_hoan_giam_total_cost(self):
        self._expire()
        before = report_services.batch_pnl(batch=self.batch)
        self.assertEqual(before["supplier_return_qty"], Decimal("0"))
        self.assertEqual(before["supplier_refund_amount"], Decimal("0"))
        self._return("30", "1000000")
        self._return("10", "500000")
        self.batch.refresh_from_db()
        p = report_services.batch_pnl(batch=self.batch)
        self.assertEqual(p["supplier_return_qty"], Decimal("40.000"))
        self.assertEqual(p["supplier_refund_amount"], Decimal("1500000"))
        self.assertEqual(p["purchase_cost"], Decimal("180000") * Decimal("100"))
        self.assertEqual(p["total_cost"], p["purchase_cost"] + p["allocated_cost"] - Decimal("1500000"))
        self.assertEqual(p["profit"], p["revenue"] - p["total_cost"])

    def test_sr16_ac4_tra_ncc_khong_tinh_vao_expired_qty(self):
        self._expire()
        self._return("30", "0")
        p = report_services.batch_pnl(batch=Batch.objects.get(pk=self.batch.pk))
        self.assertEqual(p["expired_qty"], Decimal("0"))
        # huỷ phần còn lại: expired_qty chỉ là phần huỷ
        batch_services.cancel_expired_batch(batch=self.batch, actor=self.chu, confirm_qty="70.000")
        p2 = report_services.batch_pnl(batch=Batch.objects.get(pk=self.batch.pk))
        self.assertEqual(p2["expired_qty"], Decimal("70.000"))
        self.assertEqual(p2["supplier_return_qty"], Decimal("30.000"))

    def test_sr16_ac4_landed_unit_cost_khong_doi_khi_ncc_hoan_tien(self):
        self._expire()
        self.batch.refresh_from_db()
        landed = self.batch.landed_unit_cost
        self._return("30", "1000000")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.landed_unit_cost, landed)

    def test_sr16_ac4_period_pnl_khong_doi(self):
        today = timezone.localdate()
        before = report_services.period_pnl(year=today.year, month=today.month)
        self._expire()
        self._return("30", "1000000")
        after = report_services.period_pnl(year=today.year, month=today.month)
        self.assertEqual(before, after)

    def test_sr16_ac4_api_lo_chua_tra_ncc_van_du_khoa_bang_0(self):
        resp = client_for(self.chu).get(f"/api/reports/batch/{self.batch.batch_id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(Decimal(str(data["supplier_return_qty"])), Decimal("0"))
        self.assertEqual(Decimal(str(data["supplier_refund_amount"])), Decimal("0"))

    def test_sr16_ac6_bao_cao_lo_403_voi_nhom_khac_khong_lo_tien_hoan(self):
        self._expire()
        self._return("30", "1234567")
        url = f"/api/reports/batch/{self.batch.batch_id}/"
        for user in (self.ql, self.kho, self.giao):
            with self.subTest(user=user.username):
                resp = client_for(user).get(url)
                self.assertEqual(resp.status_code, 403)
                self.assertNotIn("1234567", resp.content.decode())
                self.assertFalse(find_keys(resp.json(), set(COST_KEYS)))
        self.assertEqual(client_for(None).get(url).status_code, 401)

    # --- F11 -----------------------------------------------------------------
    def test_f11_write_off_cua_huy_phieu_nhap_khong_tinh_expired_qty(self):
        stock.record_movement(
            batch=self.batch, qty_change=Decimal("-100"),
            movement_type=StockLedgerEntry.MovementType.WRITE_OFF,
            reference="cancel_purchase_receipt PR-1", actor=self.chu,
        )
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.CANCELLED)
        self.batch.refresh_from_db()
        p = report_services.batch_pnl(batch=self.batch)
        self.assertEqual(p["expired_qty"], Decimal("0"))
        self.assertEqual(p["expired_cost"], Decimal("0"))

    def test_f11_huy_lo_qua_han_van_tinh_expired_qty(self):
        self._expire()
        batch_services.cancel_expired_batch(batch=self.batch, actor=self.chu)
        p = report_services.batch_pnl(batch=Batch.objects.get(pk=self.batch.pk))
        self.assertEqual(p["expired_qty"], Decimal("100.000"))
        self.assertEqual(p["expired_cost"], Decimal("100.000") * p["landed_unit_cost"])

    def test_f11_batch_pnl_du_20_khoa(self):
        p = report_services.batch_pnl(batch=self.batch)
        self.assertEqual(len(p), 20)
        self.assertTrue({"supplier_return_qty", "supplier_refund_amount"} <= set(p))


class SR17DashboardRecentOrdersTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.cs = make_user("cs_sr17", roles.CUSTOMER_SERVICE)
        order_services.create_order(
            customer_phone="0900000456", customer_name="Khách Giả Bảy",
            delivery_address="7 Đường Giả, Phường Giả", phone="0900000456",
            lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )

    def test_sr17_ac1_recent_orders_dung_5_khoa_cho_chu_quan_ly_kho(self):
        for user in (self.chu, self.ql, self.kho):
            with self.subTest(user=user.username):
                resp = client_for(user).get(DASH_URL)
                self.assertEqual(resp.status_code, 200)
                recent = resp.json()["recent_orders"]
                self.assertTrue(recent, "phải có đơn để kiểm khoá")
                for row in recent:
                    self.assertEqual(set(row.keys()), RECENT_KEYS)

    def test_sr17_ac2_khong_co_ten_sdt_dia_chi_trong_json(self):
        for user in (self.chu, self.ql, self.kho):
            with self.subTest(user=user.username):
                raw = client_for(user).get(DASH_URL).content.decode()
                for needle in ("Khách Giả Bảy", "0456", "0900000456", "Đường Giả", "phone_last4", "customer"):
                    self.assertNotIn(needle, raw)

    def test_sr17_ac3_nv_giao_va_cskh_403_khach_401(self):
        self.assertEqual(client_for(self.giao).get(DASH_URL).status_code, 403)
        self.assertEqual(client_for(self.cs).get(DASH_URL).status_code, 403)
        self.assertEqual(client_for(None).get(DASH_URL).status_code, 401)

    def test_sr17_ac4_recent_orders_van_co_gia_tri_dung(self):
        recent = client_for(self.chu).get(DASH_URL).json()["recent_orders"][0]
        self.assertTrue(recent["code"])
        self.assertEqual(recent["status"], "BOOKED")
        self.assertTrue(recent["status_label"])
        self.assertIsNotNone(recent["expires_at"])
        self.assertGreater(recent["amount"], 0)
