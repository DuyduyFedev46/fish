"""
S12 — Hàng chờ thanh toán lệch: xem, gắn đơn, xác nhận khi khách đã bù (UC-04, A3).

BR-TT-04 (thiếu tiền), BR-TT-05 (tiền về sau khi huỷ), BR-TT-07 (chỉ Chủ),
BR-TT-09 (mới — mọi giao dịch lệch phải được Chủ ĐÓNG bằng một cách xử lý có ghi lại),
BR-TT-10 (mới, P5 — tiền về cho đơn đã thanh toán = "chuyển thừa", vào hàng chờ để Chủ hoàn),
Q9 (Chủ xác nhận đơn khi tổng các giao dịch ≥ tổng đơn, chỉ khi đơn chưa tự huỷ).
"""
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.delivery.models import DeliveryNote
from apps.inventory.models import Batch
from apps.sales.models import PaymentTransaction, Refund, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import SENSITIVE_KEYS, OrderApiBase, find_keys
from apps.sales.payments import services as payment_services

QUEUE_URL = "/api/sales/payments/"
WEBHOOK_URL = "/api/internal/payments/sepay-webhook/"


def resolve_url(payment):
    return f"/api/sales/payments/{payment.pk}/resolve"


class S12Base(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.order = self._order()  # BOOKED 540.000đ (2kg × 270.000)

    def _pay(self, order, txn, amount):
        return payment_services.confirm_payment(
            order=order, bank_txn_id=txn, amount=Decimal(amount), received_at=timezone.now(),
        )

    @override_settings(INTERNAL_SERVICE_TOKEN="tok")
    def _webhook(self, txn, amount, order_code=""):
        resp = client_for(None).post(
            WEBHOOK_URL,
            {"bank_txn_id": txn, "order_code": order_code, "amount": amount,
             "received_at": "2026-09-25T10:00:00+07:00"},
            format="json", HTTP_X_INTERNAL_TOKEN="tok",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        return PaymentTransaction.objects.get(bank_txn_id=txn)

    def _resolve(self, user, payment, data):
        return client_for(user).post(resolve_url(payment), data, format="json")

    def _expire(self):
        order_services.cancel_unpaid_expired(now=timezone.now() + timezone.timedelta(hours=2))


class S12QueueListTests(S12Base):
    def _four_kinds(self):
        under = self._pay(self.order, "FTUNDER", "300000")
        cancelled = self._order(phone="0902222222")
        self._expire()
        orphan = self._pay(cancelled, "FTORPHAN", "540000")
        unmatched = self._webhook("FTNOCODE", "540000")
        paid = self._paid_order(phone="0903333333", txn="FTMATCHED")
        matched = PaymentTransaction.objects.get(bank_txn_id="FTMATCHED")
        return under, orphan, unmatched, matched, paid

    def test_s12_ac1_hang_cho_chi_co_giao_dich_lech(self):
        under, orphan, unmatched, matched, _ = self._four_kinds()
        resp = client_for(self.chu).get(QUEUE_URL, {"resolution_status": "OPEN"})
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["count"], 3)
        rows = {r["id"]: r for r in body["results"]}
        self.assertEqual(set(rows), {under.pk, orphan.pk, unmatched.pk})
        self.assertNotIn(matched.pk, rows)

        row = rows[under.pk]
        self.assertEqual(row["bank_txn_id"], "FTUNDER")
        self.assertEqual(row["amount"], "300000")
        self.assertEqual(row["match_status"], "UNDERPAID")
        self.assertEqual(row["match_status_label"], "Thiếu tiền — chờ Chủ")
        self.assertEqual(row["resolution_status"], "OPEN")
        self.assertEqual(row["order"], {
            "id": self.order.pk, "code": self.order.code, "status": "AUTO_CANCELLED",
            "total_amount": "540000", "paid_total": "300000",
        })
        self.assertIn("received_at", row)
        self.assertIsNone(rows[unmatched.pk]["order"])
        self.assertEqual(rows[orphan.pk]["match_status"], "ORPHAN")

    def test_s12_ac1_giao_dich_khop_resolution_status_null(self):
        *_, matched, _ = self._four_kinds()
        matched.refresh_from_db()
        self.assertIsNone(matched.resolution_status)
        resp = client_for(self.chu).get(f"{QUEUE_URL}{matched.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["resolution_status"])
        self.assertEqual(resp.json()["available_actions"], [])

    def test_s12_ac1_loc_nhieu_trang_thai_va_phan_trang(self):
        self._four_kinds()
        resp = client_for(self.chu).get(QUEUE_URL, {"resolution_status": "OPEN,RESOLVED"})
        self.assertEqual(resp.json()["count"], 3)
        resp = client_for(self.chu).get(QUEUE_URL)
        self.assertEqual(resp.json()["count"], 4)  # không lọc = mọi giao dịch
        self.assertIn("next", resp.json())

    def test_s12_available_actions_theo_loai_lech(self):
        under, orphan, unmatched, *_ = self._four_kinds()
        rows = {r["id"]: r for r in client_for(self.chu).get(
            QUEUE_URL, {"resolution_status": "OPEN"}).json()["results"]}
        self.assertEqual(rows[unmatched.pk]["available_actions"], ["attach_to_order", "refund"])
        self.assertEqual(rows[orphan.pk]["available_actions"], ["refund"])
        # đơn của khoản thiếu đã tự huỷ → chỉ còn hoàn (BR-TT-05)
        self.assertEqual(rows[under.pk]["available_actions"], ["refund"])

    def test_s12_available_actions_confirm_order_khi_da_bu_du(self):
        self._pay(self.order, "FTA", "300000")
        first = PaymentTransaction.objects.get(bank_txn_id="FTA")
        row = client_for(self.chu).get(f"{QUEUE_URL}{first.pk}/").json()
        self.assertEqual(row["available_actions"], ["refund"])  # 300k < 540k: chưa xác nhận được
        self._pay(self.order, "FTB", "240000")
        row = client_for(self.chu).get(f"{QUEUE_URL}{first.pk}/").json()
        self.assertEqual(row["available_actions"], ["confirm_order", "refund"])
        self.assertEqual(row["order"]["paid_total"], "540000")

    def test_s12_khong_ro_gia_von(self):
        self._four_kinds()
        body = client_for(self.chu).get(QUEUE_URL).json()
        self.assertEqual(find_keys(body, SENSITIVE_KEYS), set())

    def test_s12_needs_attention_bo_giao_dich_da_xu_ly(self):
        self._pay(self.order, "FTA", "300000")
        self._pay(self.order, "FTB", "240000")

        def attention():
            rows = client_for(self.chu).get("/api/sales/orders/").json()["results"]
            return {r["id"]: r["needs_attention"] for r in rows}[self.order.pk]

        self.assertTrue(attention())
        pay = PaymentTransaction.objects.get(bank_txn_id="FTA")
        self.assertEqual(self._resolve(self.chu, pay, {"action": "CONFIRM_ORDER"}).status_code, 200)
        self.assertFalse(attention())


class S12P5OverpaidTests(S12Base):
    """P5 / BR-TT-10 (N-6): tiền về cho đơn đã thanh toán → OVERPAID, vào hàng chờ, không xử lại."""

    def test_s12_p5_webhook_lan_hai_cho_don_da_thanh_toan_vao_hang_cho(self):
        paid = self._paid_order(phone="0904444444", txn="FTFIRST")
        stock_before = Batch.objects.get(pk=self.batch.pk).qty_available
        resp = client_for(None)
        with override_settings(INTERNAL_SERVICE_TOKEN="tok"):
            resp = resp.post(
                WEBHOOK_URL,
                {"bank_txn_id": "FTSECOND", "order_code": paid.code, "amount": "540000",
                 "received_at": "2026-09-25T10:00:00+07:00"},
                format="json", HTTP_X_INTERNAL_TOKEN="tok",
            )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json(), {
            "matched": False, "order_status": "PROCESSING", "match_status": "OVERPAID",
        })
        second = PaymentTransaction.objects.get(bank_txn_id="FTSECOND")
        self.assertEqual(second.match_status, PaymentTransaction.MatchStatus.OVERPAID)
        self.assertEqual(second.resolution_status, PaymentTransaction.ResolutionStatus.OPEN)
        self.assertEqual(SalesInvoice.objects.filter(sales_order=paid).count(), 1)
        self.assertEqual(Batch.objects.get(pk=self.batch.pk).qty_available, stock_before)

        rows = client_for(self.chu).get(QUEUE_URL, {"resolution_status": "OPEN"}).json()["results"]
        row = next(r for r in rows if r["id"] == second.pk)
        self.assertEqual(row["match_status"], "OVERPAID")
        self.assertEqual(row["available_actions"], ["refund"])
        first = PaymentTransaction.objects.get(bank_txn_id="FTFIRST")
        self.assertIsNone(first.resolution_status)

    def test_s12_p5_service_don_dang_xu_ly_ghi_overpaid(self):
        paid = self._paid_order(phone="0904444444", txn="FTFIRST")
        pay = self._pay(paid, "FTX", "1000")
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.OVERPAID)
        self.assertEqual(payment_services.payment_outcome(pay)["result"], "OVERPAID")


class S12ResolveTests(S12Base):
    def test_s12_ac2_gan_giao_dich_khong_khop_vao_don(self):
        pay = self._webhook("FTNOCODE", "540000")
        resp = self._resolve(self.chu, pay, {
            "action": "ATTACH_TO_ORDER", "order_id": self.order.pk,
            "note": "Khách ghi sai nội dung CK",
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        invoice = SalesInvoice.objects.get(sales_order=self.order)
        note = DeliveryNote.objects.get(sales_invoice=invoice)
        self.assertEqual(resp.json(), {
            "payment_id": pay.pk, "resolution_status": "RESOLVED", "resolution": "ATTACHED",
            "order_status": "PROCESSING", "invoice_id": invoice.pk,
            "delivery_note_code": note.code, "resolved_payment_ids": [pay.pk],
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.PROCESSING)
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        b = Batch.objects.get(pk=self.batch.pk)
        self.assertEqual((b.qty_available, b.qty_reserved), (Decimal("98"), Decimal("0")))
        pay.refresh_from_db()
        self.assertEqual(pay.sales_order_id, self.order.pk)
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.MATCHED)
        self.assertEqual(pay.resolution_status, "RESOLVED")
        self.assertEqual(pay.resolution, "ATTACHED")
        self.assertEqual(pay.resolved_by, self.chu)
        self.assertIsNotNone(pay.resolved_at)
        self.assertEqual(pay.resolution_note, "Khách ghi sai nội dung CK")
        self.assertEqual(invoice.payment_txn_ref, "FTNOCODE")
        log = AuditLog.objects.get(action="resolve_payment")
        self.assertEqual(log.actor, self.chu)
        self.assertEqual(log.object_id, str(pay.pk))
        self.assertEqual(log.note, "Khách ghi sai nội dung CK")
        self.assertEqual(log.changes["resolution"], "ATTACHED")
        self.assertEqual(log.changes["order"], self.order.code)
        self.assertEqual(log.changes["resolution_status"], {"from": "OPEN", "to": "RESOLVED"})
        self.assertEqual(log.changes["order_status"], {"from": "BOOKED", "to": "PROCESSING"})

    def test_s12_ac2_gan_khoan_thieu_thi_van_mo_cho_bu(self):
        pay = self._webhook("FTNOCODE", "300000")
        resp = self._resolve(self.chu, pay, {"action": "ATTACH_TO_ORDER", "order_id": self.order.pk})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["resolution_status"], "OPEN")
        self.assertEqual(resp.json()["resolution"], "")
        self.assertEqual(resp.json()["order_status"], "BOOKED")
        pay.refresh_from_db()
        self.assertEqual(pay.sales_order_id, self.order.pk)
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.UNDERPAID)
        self.assertEqual(pay.resolution_status, "OPEN")
        self.assertFalse(SalesInvoice.objects.exists())
        self.assertTrue(AuditLog.objects.filter(action="attach_payment", actor=self.chu).exists())
        # khách bù phần còn lại → Chủ xác nhận theo tổng (Q9)
        self._pay(self.order, "FTBU", "240000")
        resp = self._resolve(self.chu, pay, {"action": "CONFIRM_ORDER"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["order_status"], "PROCESSING")

    def test_s12_ac3_hai_khoan_thieu_du_tong_thi_xac_nhan_ca_hai(self):
        a = self._pay(self.order, "FTA", "300000")
        b = self._pay(self.order, "FTB", "240000")
        self.assertEqual({a.match_status, b.match_status}, {"UNDERPAID"})
        resp = self._resolve(self.chu, b, {"action": "CONFIRM_ORDER", "note": "Khách đã chuyển bù FTB"})
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["resolution"], "CONFIRMED")
        self.assertEqual(body["resolution_status"], "RESOLVED")
        self.assertEqual(body["order_status"], "PROCESSING")
        self.assertEqual(sorted(body["resolved_payment_ids"]), sorted([a.pk, b.pk]))
        for p in (a, b):
            p.refresh_from_db()
            self.assertEqual((p.resolution_status, p.resolution), ("RESOLVED", "CONFIRMED"))
            self.assertEqual(p.resolved_by, self.chu)
            self.assertEqual(p.resolution_note, "Khách đã chuyển bù FTB")
        self.assertEqual(SalesInvoice.objects.filter(sales_order=self.order).count(), 1)
        inv = SalesInvoice.objects.get(sales_order=self.order)
        self.assertEqual(inv.amount, Decimal("540000"))
        self.assertEqual(inv.payment_txn_ref, "FTA,FTB")
        self.assertEqual(Batch.objects.get(pk=self.batch.pk).qty_available, Decimal("98"))
        self.assertEqual(AuditLog.objects.filter(action="resolve_payment", actor=self.chu).count(), 2)

    def test_s12_ac4_chua_du_tien_400_khong_doi_gi(self):
        pay = self._pay(self.order, "FTA", "300000")
        resp = self._resolve(self.chu, pay, {"action": "CONFIRM_ORDER"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {
            "code": "BR-TT-09", "detail": "Tổng tiền đã nhận 300.000đ < tổng đơn 540.000đ.",
        })
        pay.refresh_from_db()
        self.assertEqual(pay.resolution_status, "OPEN")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.BOOKED)
        self.assertFalse(SalesInvoice.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action="resolve_payment").exists())

    def test_s12_ac4_khoan_dang_hoan_khong_tinh_vao_tong(self):
        a = self._pay(self.order, "FTA", "300000")
        b = self._pay(self.order, "FTB", "240000")
        Refund.objects.create(payment_transaction=a, amount=Decimal("300000"), created_by=self.chu)
        resp = self._resolve(self.chu, b, {"action": "CONFIRM_ORDER"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-TT-09")

    def test_s12_ac5_don_tu_huy_trong_luc_cho(self):
        pay = self._pay(self.order, "FTA", "300000")
        self._pay(self.order, "FTB", "240000")
        self._expire()
        resp = self._resolve(self.chu, pay, {"action": "CONFIRM_ORDER"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {
            "code": "BR-TT-05", "detail": "Đơn đã tự huỷ, chỉ còn cách hoàn tiền.",
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.AUTO_CANCELLED)
        self.assertFalse(SalesInvoice.objects.exists())

    def test_s12_ac5_gan_vao_don_tu_huy_400(self):
        pay = self._webhook("FTNOCODE", "540000")
        self._expire()
        resp = self._resolve(self.chu, pay, {"action": "ATTACH_TO_ORDER", "order_id": self.order.pk})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-TT-05")
        pay.refresh_from_db()
        self.assertIsNone(pay.sales_order_id)
        self.assertEqual(pay.resolution_status, "OPEN")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.AUTO_CANCELLED)

    def test_s12_ac6_da_xu_ly_roi_goi_lai_400(self):
        pay = self._webhook("FTNOCODE", "540000")
        data = {"action": "ATTACH_TO_ORDER", "order_id": self.order.pk}
        self.assertEqual(self._resolve(self.chu, pay, data).status_code, 200)
        again = self._resolve(self.chu, pay, data)  # bấm đúp
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.json()["code"], "BR-TT-09")
        self.assertEqual(SalesInvoice.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="resolve_payment").count(), 1)
        confirm = self._resolve(self.chu, pay, {"action": "CONFIRM_ORDER"})
        self.assertEqual(confirm.status_code, 400)
        self.assertEqual(confirm.json()["code"], "BR-TT-09")

    def test_s12_loi_dau_vao(self):
        unmatched = self._webhook("FTNOCODE", "540000")
        under = self._pay(self.order, "FTA", "300000")
        paid = self._paid_order(phone="0905555555", txn="FTPAID")
        cases = [
            (unmatched, {"action": "XOA"}),
            (unmatched, {}),
            (unmatched, {"action": "ATTACH_TO_ORDER"}),                        # thiếu order_id
            (unmatched, {"action": "ATTACH_TO_ORDER", "order_id": "abc"}),
            (unmatched, {"action": "ATTACH_TO_ORDER", "order_id": 999999}),    # không có đơn
            (unmatched, {"action": "ATTACH_TO_ORDER", "order_id": paid.pk}),   # đơn đã thanh toán
            (unmatched, {"action": "CONFIRM_ORDER"}),                          # chưa gắn đơn
            (under, {"action": "ATTACH_TO_ORDER", "order_id": self.order.pk}), # đã có đơn
        ]
        for pay, data in cases:
            resp = self._resolve(self.chu, pay, data)
            self.assertEqual(resp.status_code, 400, (data, resp.content))
            self.assertIn("code", resp.json())
        for pay in (unmatched, under):
            pay.refresh_from_db()
            self.assertEqual(pay.resolution_status, "OPEN")
        self.assertEqual(SalesInvoice.objects.filter(sales_order=self.order).count(), 0)
        self.assertFalse(AuditLog.objects.filter(action__in=("resolve_payment", "attach_payment")).exists())

    def test_s12_route_co_va_khong_co_gach_cheo(self):
        pay = self._webhook("FTNOCODE", "540000")
        resp = client_for(self.chu).post(f"{resolve_url(pay)}/", {"action": "XOA"}, format="json")
        self.assertEqual(resp.status_code, 400)  # tới được view (không 404)


class S12PermissionTests(S12Base):
    def test_s12_ac7_quan_ly_nv_kho_nv_giao_403(self):
        pay = self._webhook("FTNOCODE", "540000")
        for user in (self.ql, self.kho, self.giao, self.nobody):
            self.assertEqual(client_for(user).get(QUEUE_URL, {"resolution_status": "OPEN"}).status_code,
                             403, user.username)
            self.assertEqual(client_for(user).get(f"{QUEUE_URL}{pay.pk}/").status_code, 403)
            resp = self._resolve(user, pay, {"action": "ATTACH_TO_ORDER", "order_id": self.order.pk})
            self.assertEqual(resp.status_code, 403, user.username)
        pay.refresh_from_db()
        self.assertIsNone(pay.sales_order_id)
        self.assertEqual(pay.resolution_status, "OPEN")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.BOOKED)

    def test_s12_ac7_chua_dang_nhap_401(self):
        pay = self._webhook("FTNOCODE", "540000")
        self.assertEqual(client_for(None).get(QUEUE_URL).status_code, 401)
        self.assertEqual(self._resolve(None, pay, {"action": "CONFIRM_ORDER"}).status_code, 401)
