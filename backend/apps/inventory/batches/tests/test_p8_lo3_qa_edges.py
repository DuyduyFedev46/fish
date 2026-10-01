"""
QA P8 Lô 3 — ca biên/ngoại lệ bổ sung cho SR-08 (huỷ lô quá hạn còn giữ chỗ) và SR-10 (publish có khoá).
Không sửa code sản phẩm; chỉ bù ca ngoài đường thuận mà test của dev chưa phủ. Dữ liệu giả.

SR-08: lô đã từng bán, tranh chấp huỷ lô <-> thanh toán theo CẢ 2 thứ tự, chạy job TTL 2 lần, khoá trước kiểm,
       guidance cho từng Group, không rò giá vốn / dữ liệu khách.
SR-10: object cũ với mọi trạng thái lô khác DRAFT, tranh chấp cancel_receipt <-> publish theo CẢ 2 thứ tự,
       bấm đúp API, audit không có khoá giá vốn.
"""
import datetime
from decimal import Decimal
from unittest import mock

from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.cost_keys import COST_KEYS
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.tests.test_confirmation_escalation import ConfirmationL3BaseTestCase
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, StockLedgerEntry
from apps.purchasing.models import PurchaseReceipt
from apps.purchasing.receipts import services as receipt_services
from apps.sales.models import PaymentTransaction, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase, find_keys
from apps.sales.payments import services as payment_services
from apps.accounts import roles

PII = ("0900000111", "0900000222", "Khách Giả A", "Khách Giả B", "1 Đường Giả")


class QaSR08Edges(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.cs = make_user("cs_qa08", roles.CUSTOMER_SERVICE)
        self.c_chu = client_for(self.chu)
        self.url = f"/api/inventory/batches/{self.batch.pk}/cancel-expired/"

    def _book(self, phone="0900000111", name="Khách Giả A", qty="2", lines=None):
        return order_services.create_order(
            customer_phone=phone, customer_name=name, delivery_address="1 Đường Giả, Phường Giả",
            phone=phone, lines=lines or [{"item_code": self.item.code, "qty": Decimal(qty)}],
        )

    def _pay(self, order, txn):
        payment_services.confirm_payment(
            order=order, bank_txn_id=txn, amount=order.total_amount, received_at=timezone.now(),
        )
        order.refresh_from_db()

    def _expire(self, batch=None):
        b = batch or self.batch
        Batch.objects.filter(pk=b.pk).update(status=Batch.Status.EXPIRED)
        b.refresh_from_db()

    def _ledger_sum(self, batch=None):
        b = batch or self.batch
        total = Decimal("0")
        for e in StockLedgerEntry.objects.filter(batch=b):
            total += e.qty_change
        return total

    # --- lô đã từng bán ------------------------------------------------------
    def test_qa_lo_da_tung_ban_don_da_tra_khong_bi_dem_va_khong_bi_dong_vao(self):
        """A đã PAID (đã xuất hoá đơn, đã trừ kho), B còn BOOKED 3kg. Chỉ B chặn; huỷ xong hoá đơn A còn nguyên."""
        a = self._book(phone="0900000111", qty="2")
        self._pay(a, "TXN-QA08-A")
        inv_a = SalesInvoice.objects.get(sales_order=a)
        inv_a_status, inv_a_amount = inv_a.status, inv_a.amount
        b = self._book(phone="0900000222", name="Khách Giả B", qty="3")
        self._expire()
        self.assertEqual(self.batch.qty_reserved, Decimal("3.000"))

        resp = self.c_chu.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-07")
        self.assertEqual(
            resp.json()["detail"],
            "Còn 3,000 kg đang giữ chỗ của 1 đơn — chờ đơn thanh toán hoặc hết hạn giữ chỗ rồi huỷ.",
        )

        # B thanh toán sau khi bị chặn -> tiền không mất
        self._pay(b, "TXN-QA08-B")
        self.assertTrue(PaymentTransaction.objects.filter(bank_txn_id="TXN-QA08-B", match_status="MATCHED").exists())

        # giờ không còn giữ chỗ -> huỷ được; WRITE_OFF đúng phần còn lại (100 - 2 - 3)
        resp = self.c_chu.post(self.url)
        self.assertEqual(resp.status_code, 200, resp.content)
        wo = StockLedgerEntry.objects.filter(batch=self.batch, movement_type=StockLedgerEntry.MovementType.WRITE_OFF)
        self.assertEqual(wo.count(), 1)
        self.assertEqual(wo.first().qty_change, Decimal("-95.000"))
        self.assertEqual(self._ledger_sum(), Decimal("0.000"))  # sổ kho khép về 0, không âm
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, Batch.Status.CANCELLED)
        self.assertEqual(self.batch.qty_available, Decimal("0.000"))
        # chứng từ không bị đụng
        inv_a.refresh_from_db()
        self.assertEqual((inv_a.status, inv_a.amount), (inv_a_status, inv_a_amount))
        for o in (a, b):
            o.refresh_from_db()
            self.assertEqual(o.status, SalesOrder.Status.PROCESSING)

    # --- tranh chấp, thứ tự B -> A (thanh toán trước, huỷ lô sau) -------------
    def test_qa_race_thanh_toan_truoc_huy_lo_sau(self):
        order = self._book(qty="4")
        self._expire()
        self._pay(order, "TXN-QA08-BA")  # thanh toán thắng
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_reserved, Decimal("0.000"))
        self.assertEqual(self.batch.qty_available, Decimal("96.000"))

        resp = self.c_chu.post(self.url)  # huỷ lô sau -> được, chỉ xoá phần còn lại
        self.assertEqual(resp.status_code, 200, resp.content)
        wo = StockLedgerEntry.objects.get(batch=self.batch, movement_type=StockLedgerEntry.MovementType.WRITE_OFF)
        self.assertEqual(wo.qty_change, Decimal("-96.000"))
        self.assertEqual(self._ledger_sum(), Decimal("0.000"))
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        self.assertTrue(SalesInvoice.objects.filter(sales_order=order).exists())

    # --- tranh chấp, thứ tự A -> B (huỷ lô trước bị chặn, thanh toán sau) ------
    def test_qa_race_huy_lo_truoc_bi_chan_roi_thanh_toan_sau_khong_mat_tien(self):
        order = self._book(qty="4")
        self._expire()
        before = StockLedgerEntry.objects.filter(batch=self.batch).count()
        self.assertEqual(self.c_chu.post(self.url).status_code, 400)
        self.assertEqual(StockLedgerEntry.objects.filter(batch=self.batch).count(), before)
        self._pay(order, "TXN-QA08-AB")
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        txn = PaymentTransaction.objects.get(bank_txn_id="TXN-QA08-AB")
        self.assertEqual(txn.match_status, PaymentTransaction.MatchStatus.MATCHED)
        # không có giao dịch mồ côi/OPEN nào phát sinh
        self.assertFalse(PaymentTransaction.objects.exclude(match_status="MATCHED").exists())

    def test_qa_khoa_lo_truoc_khi_kiem_dieu_kien_huy(self):
        """Thứ tự bắt buộc để chống tranh chấp: select_for_update rồi mới check_cancel_expired_batch."""
        self._expire()
        order_log = []
        real_lock = Batch.objects.select_for_update
        real_check = batch_services.check_cancel_expired_batch

        def spy_check(b):
            order_log.append("check")
            return real_check(b)

        with mock.patch.object(Batch.objects, "select_for_update",
                               side_effect=lambda *a, **k: (order_log.append("lock"), real_lock(*a, **k))[1]), \
                mock.patch.object(batch_services, "check_cancel_expired_batch", side_effect=spy_check):
            batch_services.cancel_expired_batch(batch=self.batch, actor=self.chu)
        self.assertEqual(order_log[:2], ["lock", "check"])

    def test_qa_khoa_lo_o_reserve_va_release_cung_dong_lo(self):
        """Phía giữ chỗ/nhả chỗ cũng khoá dòng lô -> hai bên xếp hàng trên cùng một khoá."""
        with mock.patch.object(Batch.objects, "select_for_update", wraps=Batch.objects.select_for_update) as spy:
            batch_services.reserve(batch=self.batch, qty=Decimal("1"))
            batch_services.release(batch=self.batch, qty=Decimal("1"))
        self.assertEqual(spy.call_count, 2)

    # --- job TTL chạy 2 lần, nhiều đơn ----------------------------------------
    def test_qa_ttl_job_chay_2_lan_va_nhieu_don(self):
        a = self._book(phone="0900000111", qty="2")
        b = self._book(phone="0900000222", name="Khách Giả B", qty="3")
        self._expire()
        self._pay(a, "TXN-QA08-TTL")  # a thanh toán, b vẫn giữ chỗ
        resp = self.c_chu.post(self.url)
        self.assertEqual((resp.status_code, resp.json()["code"]), (400, "BR-LO-07"))
        self.assertIn("3,000 kg", resp.json()["detail"])
        self.assertIn("1 đơn", resp.json()["detail"])

        future = timezone.now() + datetime.timedelta(days=1)
        self.assertEqual(order_services.cancel_unpaid_expired(now=future), 1)
        self.assertEqual(order_services.cancel_unpaid_expired(now=future), 0)  # lần 2: không làm gì
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_reserved, Decimal("0.000"))  # không âm, không lệch
        b.refresh_from_db(); a.refresh_from_db()
        self.assertEqual(b.status, SalesOrder.Status.AUTO_CANCELLED)
        self.assertEqual(a.status, SalesOrder.Status.PROCESSING)
        self.assertEqual(self.c_chu.post(self.url).status_code, 200)

    def test_qa_don_nhieu_dong_cung_lo_dem_la_1_don(self):
        order = self._book(lines=[
            {"item_code": self.item.code, "qty": Decimal("2")},
            {"item_code": self.item.code, "qty": Decimal("1")},
        ])
        self._expire()
        resp = self.c_chu.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-07")
        self.assertIn("3,000 kg", resp.json()["detail"])
        self.assertIn("của 1 đơn", resp.json()["detail"])
        self.assertEqual(order.lines.count() >= 1, True)

    def test_qa_giu_cho_o_lo_khac_khong_chan_lo_nay(self):
        """Lô 2 (hạn dùng sau) giữ chỗ; lô 1 hết hạn và không giữ chỗ -> huỷ lô 1 được, giữ chỗ lô 2 nguyên vẹn."""
        b2 = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            qty=Decimal("50"), purchase_rate=Decimal("190000"),
        )
        batch_services.publish_batch(batch=b2, actor=None)
        self._expire()  # lô 1 quá hạn (không còn bán) -> đơn mới dồn sang lô 2
        order = self._book(qty="2")
        b2.refresh_from_db()
        self.assertEqual(b2.qty_reserved, Decimal("2.000"))
        self.assertEqual(self.batch.qty_reserved, Decimal("0.000"))
        self.assertEqual(self.c_chu.post(self.url).status_code, 200)
        b2.refresh_from_db()
        self.assertEqual(b2.qty_reserved, Decimal("2.000"))
        self.assertEqual(b2.status, Batch.Status.SELLING)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.BOOKED)

    def test_qa_gia_tri_bien_giu_cho_rat_nho_van_chan(self):
        self._expire()
        Batch.objects.filter(pk=self.batch.pk).update(qty_reserved=Decimal("0.001"))
        resp = self.c_chu.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-LO-07")
        self.assertIn("0,001 kg", resp.json()["detail"])
        self.assertEqual(StockLedgerEntry.objects.filter(
            batch=self.batch, movement_type=StockLedgerEntry.MovementType.WRITE_OFF).count(), 0)

    def test_qa_lo_dang_ban_con_giu_cho_van_la_br_lo_03_khong_phai_lo_07(self):
        self._book()
        resp = self.c_chu.post(self.url)  # lô còn SELLING
        self.assertEqual((resp.status_code, resp.json()["code"]), (400, "BR-LO-03"))

    def test_qa_lo_da_chot_hoac_da_huy_khong_huy_lai(self):
        for st in (Batch.Status.CANCELLED, Batch.Status.CLOSED, Batch.Status.SOLD_OUT):
            with self.subTest(status=st):
                Batch.objects.filter(pk=self.batch.pk).update(status=st, qty_reserved=Decimal("0"))
                n = StockLedgerEntry.objects.filter(batch=self.batch).count()
                resp = self.c_chu.post(self.url)
                self.assertEqual((resp.status_code, resp.json()["code"]), (400, "BR-LO-03"))
                self.assertEqual(StockLedgerEntry.objects.filter(batch=self.batch).count(), n)

    def test_qa_chua_dang_nhap_va_id_khong_ton_tai(self):
        self.assertEqual(client_for(None).post(self.url).status_code, 401)
        self.assertEqual(self.c_chu.post("/api/inventory/batches/999999/cancel-expired/").status_code, 404)

    # --- guidance từng Group + rò giá vốn / PII --------------------------------
    def test_qa_guidance_tung_group_khong_ro_gia_von_va_pii(self):
        self._book()
        self._expire()
        ok_responses = 0
        seen_lo07 = 0
        for user in (self.chu, self.ql, self.kho, self.giao, self.cs):
            with self.subTest(user=user.username):
                resp = client_for(user).get(f"/api/guidance/batch/{self.batch.pk}/")
                if resp.status_code == 200:
                    ok_responses += 1
                    body = resp.json()
                    if user is not self.chu:
                        # nhóm không có view_costprice: không một khoá giá vốn nào
                        if not user.has_perm("inventory.view_costprice"):
                            self.assertFalse(find_keys(body, set(COST_KEYS)), user.username)
                    raw = resp.content.decode()
                    for s in PII:
                        self.assertNotIn(s, raw)
                    step = {x["key"]: x for x in body["next_steps"]}.get("cancel_expired")
                    if step:
                        self.assertFalse(step["allowed"], user.username)
                        if any(m["code"] == "BR-LO-07" for m in step["missing"]):
                            seen_lo07 += 1
                else:
                    self.assertIn(resp.status_code, (403, 404), user.username)
        self.assertGreater(ok_responses, 0)  # không xanh giả vì lỗi 4xx
        self.assertGreater(seen_lo07, 0)

    def test_qa_400_thieu_quyen_khong_lo_chi_tiet(self):
        """403 cho nhóm không phải Chủ: body không chứa kg giữ chỗ / số đơn / mã lô."""
        self._book()
        self._expire()
        for user in (self.ql, self.kho, self.giao, self.cs):
            with self.subTest(user=user.username):
                resp = client_for(user).post(self.url)
                self.assertEqual(resp.status_code, 403)
                raw = resp.content.decode()
                self.assertNotIn("giữ chỗ", raw)
                self.assertNotIn("2,000", raw)
                self.assertNotIn("BR-LO-07", raw)

    # --- audit ----------------------------------------------------------------
    def test_qa_audit_khong_ghi_khi_bi_chan_va_ghi_1_dong_khi_thanh_cong(self):
        self._book()
        self._expire()
        self.assertEqual(self.c_chu.post(self.url).status_code, 400)
        self.assertEqual(AuditLog.objects.filter(action="cancel_expired_batch").count(), 0)
        future = timezone.now() + datetime.timedelta(days=1)
        order_services.cancel_unpaid_expired(now=future)
        self.assertEqual(self.c_chu.post(self.url).status_code, 200)
        self.assertEqual(self.c_chu.post(self.url).status_code, 400)  # bấm lần 2
        self.assertEqual(AuditLog.objects.filter(action="cancel_expired_batch").count(), 1)
        # quan_ly xem nhật ký: không thấy loss_amount (SR-01 vẫn giữ)
        resp = client_for(self.ql).get("/api/audit-logs/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(find_keys(resp.json(), {"loss_amount"}))
        self.assertNotIn("loss_amount", resp.content.decode())


class QaSR10Edges(ConfirmationL3BaseTestCase):
    def setUp(self):
        super().setUp()
        self.receipt, batches = receipt_services.create_and_submit_receipt(
            supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            lines=[{"item_code": self.item, "qty": Decimal("5"), "rate": Decimal("1000")}],
            actor=self.kho,
        )
        self.pk = batches[0].pk
        self.url = f"/api/inventory/batches/{self.pk}/publish/"

    def _audits(self):
        return AuditLog.objects.filter(action="publish_batch", object_id=str(self.pk)).count()

    def test_qa_object_cu_la_draft_nhung_db_da_o_trang_thai_khac(self):
        """Màn hình cũ: bộ nhớ nói DRAFT, DB đã sang trạng thái khác -> 400 BR-MH-05, DB không bị ghi đè."""
        for st in (Batch.Status.SELLING, Batch.Status.NEAR_EXPIRY, Batch.Status.SOLD_OUT,
                   Batch.Status.EXPIRED, Batch.Status.CANCELLED, Batch.Status.CLOSED):
            with self.subTest(status=st):
                stale = Batch.objects.get(pk=self.pk)
                Batch.objects.filter(pk=self.pk).update(status=Batch.Status.DRAFT)
                stale = Batch.objects.get(pk=self.pk)  # object cũ: DRAFT
                Batch.objects.filter(pk=self.pk).update(status=st)
                with self.assertRaises(BusinessError) as ctx:
                    batch_services.publish_batch(batch=stale, actor=self.chu)
                self.assertEqual(ctx.exception.code, "BR-MH-05")
                self.assertEqual(Batch.objects.get(pk=self.pk).status, st)
        self.assertEqual(self._audits(), 0)

    def test_qa_race_publish_truoc_huy_phieu_sau(self):
        """Thứ tự B -> A: publish thắng, sau đó cancel_receipt phải bị chặn, lô vẫn SELLING."""
        batch_services.publish_batch(batch=Batch.objects.get(pk=self.pk), actor=self.chu)
        with self.assertRaises(BusinessError) as ctx:
            receipt_services.cancel_receipt(receipt=self.receipt, actor=self.kho)
        self.assertEqual(ctx.exception.code, "BR-MH-07")
        self.receipt.refresh_from_db()
        self.assertNotEqual(self.receipt.status, PurchaseReceipt.Status.CANCELLED)
        b = Batch.objects.get(pk=self.pk)
        self.assertEqual(b.status, Batch.Status.SELLING)
        self.assertEqual(b.qty_available, Decimal("5.000"))
        self.assertEqual(StockLedgerEntry.objects.filter(
            batch=b, movement_type=StockLedgerEntry.MovementType.WRITE_OFF).count(), 0)
        self.assertEqual(self._audits(), 1)

    def test_qa_race_huy_phieu_truoc_publish_sau_qua_api(self):
        """Thứ tự A -> B qua HTTP: cancel_receipt xong, request publish (đã get_object trước) -> 400, tồn = 0, không audit."""
        receipt_services.cancel_receipt(receipt=self.receipt, actor=self.kho)
        resp = client_for(self.chu).post(self.url)
        self.assertEqual((resp.status_code, resp.json()["code"]), (400, "BR-MH-05"))
        b = Batch.objects.get(pk=self.pk)
        self.assertEqual(b.status, Batch.Status.CANCELLED)
        self.assertEqual(b.qty_available, Decimal("0.000"))
        self.assertEqual(self._audits(), 0)
        self.assertEqual(client_for(self.ql).post(self.url).status_code, 400)

    def test_qa_bam_dup_api_chi_1_lan_thanh_cong(self):
        c = client_for(self.chu)
        r1, r2, r3 = c.post(self.url), c.post(self.url), c.post(self.url)
        self.assertEqual((r1.status_code, r2.status_code, r3.status_code), (200, 400, 400))
        self.assertEqual(r2.json()["code"], "BR-MH-05")
        self.assertEqual(self._audits(), 1)
        self.assertEqual(Batch.objects.get(pk=self.pk).status, Batch.Status.SELLING)

    def test_qa_id_khong_ton_tai_va_chua_dang_nhap(self):
        self.assertEqual(client_for(self.chu).post("/api/inventory/batches/999999/publish/").status_code, 404)
        self.assertEqual(client_for(None).post(self.url).status_code, 401)

    def test_qa_audit_publish_khong_co_gia_von_hay_pii(self):
        client_for(self.chu).post(self.url)
        row = AuditLog.objects.get(action="publish_batch", object_id=str(self.pk))
        blob = f"{row.changes} {row.note}"
        for k in COST_KEYS:
            self.assertNotIn(k, blob)
        for s in ("0900000", "Khách"):
            self.assertNotIn(s, blob)
        # quan_ly đọc nhật ký -> 200 và không có khoá giá vốn
        resp = client_for(self.ql).get("/api/audit-logs/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(find_keys(resp.json(), set(COST_KEYS)))

    def test_qa_publish_tra_ve_object_moi_trang_thai_selling(self):
        stale = Batch.objects.get(pk=self.pk)
        out = batch_services.publish_batch(batch=stale, actor=self.chu)
        self.assertEqual(out.status, Batch.Status.SELLING)
        self.assertEqual(out.pk, self.pk)
