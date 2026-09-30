"""
P8 Lô 3 — SR-08: không huỷ lô quá hạn khi còn giữ chỗ (F02, BR-LO-03, BR-LO-07, C1).
Chuyển từ test tái hiện R5 (repro/review_repro_tests.py). Dữ liệu giả.

- SR-08-AC1: lô EXPIRED còn giữ chỗ -> 400 BR-LO-07, lô vẫn EXPIRED, tồn không đổi, không WRITE_OFF.
- SR-08-AC2: tiếp AC1, thanh toán đơn đó vẫn thành công (tiền không mất).
- SR-08-AC3: giữ chỗ về 0 (đơn huỷ do TTL) -> huỷ lô 200, WRITE_OFF đúng qty_available.
- SR-08-AC4: guidance lô EXPIRED còn giữ chỗ: bước cancel_expired allowed=false, missing có BR-LO-07.
- SR-08-AC5: huỷ lần 2 trên lô đã CANCELLED -> 400 BR-LO-03, không ghi thêm ledger.
- Ma trận Group: chu 200/400 nghiệp vụ, quan_ly/nv_kho/nv_giao/cskh 403, khách 401.
"""
import datetime
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, StockLedgerEntry
from apps.sales.models import PaymentTransaction, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase, find_keys

PII_SENTINELS = ("0900000111", "0900000222", "Khách Giả A", "Khách Giả B", "1 Đường Giả")


class SR08CancelExpiredReservedTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.cs = make_user("cs_sr08", "cskh")
        self.c_chu = client_for(self.chu)
        self.url = f"/api/inventory/batches/{self.batch.pk}/cancel-expired/"

    # --- helpers -------------------------------------------------------------
    def _book(self, phone="0900000111", name="Khách Giả A", qty="2"):
        return order_services.create_order(
            customer_phone=phone, customer_name=name, delivery_address="1 Đường Giả, Phường Giả",
            phone=phone, lines=[{"item_code": self.item.code, "qty": Decimal(qty)}],
        )

    def _expire(self):
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.EXPIRED)
        self.batch.refresh_from_db()

    def _write_offs(self):
        return StockLedgerEntry.objects.filter(
            batch=self.batch, movement_type=StockLedgerEntry.MovementType.WRITE_OFF
        ).count()

    def _cancel_audits(self):
        return AuditLog.objects.filter(action="cancel_expired_batch", object_id=str(self.batch.pk)).count()

    # --- AC1 (R5) ------------------------------------------------------------
    def test_sr08_ac1_r5_khong_huy_lo_khi_con_giu_cho(self):
        order = self._book()
        self._expire()
        self.assertEqual(self.batch.qty_reserved, Decimal("2.000"))
        avail_before = self.batch.qty_available

        resp = self.c_chu.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        body = resp.json()
        self.assertEqual(body["code"], "BR-LO-07")
        self.assertEqual(
            body["detail"],
            "Còn 2,000 kg đang giữ chỗ của 1 đơn — chờ đơn thanh toán hoặc hết hạn giữ chỗ rồi huỷ.",
        )

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, Batch.Status.EXPIRED)
        self.assertEqual(self.batch.qty_available, avail_before)
        self.assertEqual(self.batch.qty_reserved, Decimal("2.000"))
        self.assertEqual(self._write_offs(), 0)
        self.assertEqual(self._cancel_audits(), 0)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.BOOKED)  # không tự huỷ đơn khách

    def test_sr08_ac1_dem_dung_so_don_giu_cho(self):
        self._book(phone="0900000111", qty="2")
        self._book(phone="0900000222", name="Khách Giả B", qty="3")
        self._expire()
        resp = self.c_chu.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-07")
        self.assertEqual(
            resp.json()["detail"],
            "Còn 5,000 kg đang giữ chỗ của 2 đơn — chờ đơn thanh toán hoặc hết hạn giữ chỗ rồi huỷ.",
        )

    def test_sr08_ac1_service_raise_business_error_khong_doi_du_lieu(self):
        from apps.common.exceptions import BusinessError
        from apps.inventory.batches import services as batch_services
        self._book()
        self._expire()
        with self.assertRaises(BusinessError) as ctx:
            batch_services.cancel_expired_batch(batch=self.batch, actor=self.chu)
        self.assertEqual(ctx.exception.code, "BR-LO-07")
        self.assertEqual(self._write_offs(), 0)

    def test_sr08_ac1_400_khong_ro_gia_von_va_du_lieu_khach(self):
        self._book()
        self._expire()
        resp = self.c_chu.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(set(resp.json().keys()), {"detail", "code"})
        self.assertFalse(find_keys(resp.json(), set(COST_KEYS)))
        raw = resp.content.decode()
        for sentinel in PII_SENTINELS:
            self.assertNotIn(sentinel, raw)

    # --- AC2 (tiền không mất) ------------------------------------------------
    def test_sr08_ac2_thanh_toan_van_thanh_cong_sau_khi_bi_chan_huy(self):
        order = self._book()
        self._expire()
        self.assertEqual(self.c_chu.post(self.url).status_code, 400)

        payment_services.confirm_payment(
            order=order, bank_txn_id="TXN-SR08-AC2", amount=order.total_amount,
            received_at=timezone.now(),
        )
        order.refresh_from_db()
        # Sau thanh toán đơn đã xuất hoá đơn và sang PROCESSING (đã trả tiền, chờ soạn) — không còn BOOKED.
        self.assertIn(order.status, (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING))
        txn = PaymentTransaction.objects.get(bank_txn_id="TXN-SR08-AC2")
        self.assertEqual(txn.match_status, PaymentTransaction.MatchStatus.MATCHED)
        self.assertTrue(SalesInvoice.objects.filter(sales_order=order).exists())

    # --- AC3 (huỷ được khi giữ chỗ về 0) -------------------------------------
    def test_sr08_ac3_giu_cho_ve_0_do_ttl_thi_huy_lo_duoc(self):
        order = self._book()
        self._expire()
        self.assertEqual(self.c_chu.post(self.url).status_code, 400)

        future = timezone.now() + datetime.timedelta(days=1)
        cancelled = order_services.cancel_unpaid_expired(now=future)
        self.assertEqual(cancelled, 1)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_reserved, Decimal("0.000"))
        avail = self.batch.qty_available

        resp = self.c_chu.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], Batch.Status.CANCELLED)
        entries = StockLedgerEntry.objects.filter(
            batch=self.batch, movement_type=StockLedgerEntry.MovementType.WRITE_OFF
        )
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().qty_change, -avail)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.AUTO_CANCELLED)

    def test_sr08_ac3_don_da_thanh_toan_khong_chan_huy_lo(self):
        """Đơn PAID không còn giữ chỗ (đã trừ kho) -> không dính BR-LO-07."""
        order = self._book()
        payment_services.confirm_payment(
            order=order, bank_txn_id="TXN-SR08-PAID", amount=order.total_amount,
            received_at=timezone.now(),
        )
        self._expire()
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_reserved, Decimal("0.000"))
        resp = self.c_chu.post(self.url)
        self.assertEqual(resp.status_code, 200)

    # --- AC4 (guidance) ------------------------------------------------------
    def test_sr08_ac4_guidance_cancel_expired_khong_allowed_khi_con_giu_cho(self):
        self._book()
        self._expire()
        resp = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, 200)
        steps = {s["key"]: s for s in resp.json()["next_steps"]}
        step = steps["cancel_expired"]
        self.assertFalse(step["allowed"])
        codes = [m["code"] for m in step["missing"]]
        self.assertIn("BR-LO-07", codes)
        texts = " ".join(m["text"] for m in step["missing"] if m["code"] == "BR-LO-07")
        self.assertIn("2,000 kg", texts)

    def test_sr08_ac4_guidance_allowed_khi_khong_giu_cho(self):
        self._expire()
        resp = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        steps = {s["key"]: s for s in resp.json()["next_steps"]}
        self.assertTrue(steps["cancel_expired"]["allowed"])
        self.assertEqual(steps["cancel_expired"]["missing"], [])

    # --- AC5 (chạy 2 lần) ----------------------------------------------------
    def test_sr08_ac5_huy_lan_2_400_br_lo_03_khong_ghi_them_ledger(self):
        self._expire()
        self.assertEqual(self.c_chu.post(self.url).status_code, 200)
        entries = StockLedgerEntry.objects.filter(batch=self.batch).count()
        writes = self._write_offs()
        audits = self._cancel_audits()

        resp = self.c_chu.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-03")
        self.assertEqual(StockLedgerEntry.objects.filter(batch=self.batch).count(), entries)
        self.assertEqual(self._write_offs(), writes)
        self.assertEqual(self._cancel_audits(), audits)

    # --- Ma trận Group -------------------------------------------------------
    def test_sr08_ma_tran_group_cancel_expired(self):
        self._book()
        self._expire()
        for user in (self.ql, self.kho, self.giao, self.cs):
            with self.subTest(user=user.username):
                resp = client_for(user).post(self.url)
                self.assertEqual(resp.status_code, 403)
        self.assertEqual(client_for(None).post(self.url).status_code, 401)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, Batch.Status.EXPIRED)
        self.assertEqual(self._write_offs(), 0)
        # chu: 400 nghiệp vụ (có 400 thật, không phải 403/404)
        self.assertEqual(self.c_chu.post(self.url).status_code, 400)
