"""
S13 — Hoàn tiền cho khoản tiền không có hoá đơn (UC-04 E2, Q9).

Schema: `Refund.sales_invoice` nullable + `Refund.payment_transaction` (nullable), ràng buộc
ĐÚNG MỘT trong hai; `Refund.request_id` (chống tạo trùng khi bấm đúp — Q12, dùng chung S15).
BR-HT-01/03/04/08, BR-TT-09 (xác nhận phiếu → giao dịch RESOLVED/REFUNDED), BR-BC-03/BR-TT-06
(khoản chưa từng ghi doanh thu thì không trừ lãi kỳ).
"""
import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.sales.models import PaymentTransaction, Refund, SalesInvoice
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.sales.payments import services as payment_services

CREATE_URL = "/api/sales/refunds/create/"


class S13Base(OrderApiBase):
    def setUp(self):
        super().setUp()
        order = self._order()
        order_services.cancel_unpaid_expired(now=timezone.now() + timezone.timedelta(hours=2))
        # ORPHAN 300.000đ: tiền về sau khi đơn đã tự huỷ (BR-TT-05)
        self.orphan = payment_services.confirm_payment(
            order=order, bank_txn_id="FTORPHAN", amount=Decimal("300000"), received_at=timezone.now(),
        )
        self.assertEqual(self.orphan.match_status, PaymentTransaction.MatchStatus.ORPHAN)

    def _create(self, user, **data):
        data.setdefault("reason", "Tiền về sau khi đơn tự huỷ")
        return client_for(user).post(CREATE_URL, data, format="json")


class S13CreateTests(S13Base):
    def test_s13_ac1_tao_phieu_hoan_cho_giao_dich(self):
        rid = str(uuid.uuid4())
        resp = self._create(self.chu, payment_transaction=self.orphan.pk, amount="300000", request_id=rid)
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        refund = Refund.objects.get()
        self.assertEqual(body["id"], refund.pk)
        self.assertEqual(body["status"], "PENDING")
        self.assertEqual(body["amount"], "300000")
        self.assertEqual(body["payment_transaction"], self.orphan.pk)
        self.assertIsNone(body["sales_invoice"])
        self.assertEqual(body["request_id"], rid)
        self.assertFalse(body.get("duplicate", False))
        self.assertEqual(refund.created_by, self.chu)
        self.assertIsNone(refund.sales_invoice_id)
        log = AuditLog.objects.get(action="create_refund")
        self.assertEqual(log.actor, self.chu)
        self.assertEqual(log.changes["payment_transaction"], "FTORPHAN")
        self.orphan.refresh_from_db()
        self.assertEqual(self.orphan.resolution_status, "OPEN")  # chưa đóng tới khi xác nhận

    def test_s13_ac2_xac_nhan_phieu_thi_giao_dich_resolved_refunded(self):
        refund_id = self._create(self.chu, payment_transaction=self.orphan.pk, amount="300000").json()["id"]
        resp = client_for(self.chu).post(
            f"/api/sales/refunds/{refund_id}/confirm/", {"bank_txn_ref": "FTREF01"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "REFUNDED")
        self.orphan.refresh_from_db()
        self.assertEqual((self.orphan.resolution_status, self.orphan.resolution), ("RESOLVED", "REFUNDED"))
        self.assertEqual(self.orphan.resolved_by, self.chu)
        self.assertIsNotNone(self.orphan.resolved_at)
        self.assertIn("FTREF01", self.orphan.resolution_note)
        log = AuditLog.objects.get(action="resolve_payment")
        self.assertEqual(log.changes["resolution"], "REFUNDED")
        self.assertEqual(log.changes["refund_id"], refund_id)
        queue = client_for(self.chu).get("/api/sales/payments/", {"resolution_status": "OPEN"}).json()
        self.assertEqual(queue["count"], 0)

    def test_s13_ac3_vuot_so_con_duoc_hoan(self):
        Refund.objects.create(payment_transaction=self.orphan, amount=Decimal("200000"), created_by=self.chu)
        resp = self._create(self.chu, payment_transaction=self.orphan.pk, amount="150000")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {
            "code": "BR-HT-04", "detail": "Vượt số tiền còn được hoàn: tối đa 100.000đ.",
        })
        self.assertEqual(Refund.objects.count(), 1)

    def test_s13_ac3_phieu_that_bai_khong_tinh(self):
        Refund.objects.create(payment_transaction=self.orphan, amount=Decimal("200000"),
                              created_by=self.chu, status=Refund.Status.FAILED)
        resp = self._create(self.chu, payment_transaction=self.orphan.pk, amount="300000")
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_s13_ac3_hang_cho_bo_nut_hoan_khi_het_so_hoan(self):
        self._create(self.chu, payment_transaction=self.orphan.pk, amount="300000")
        row = client_for(self.chu).get(f"/api/sales/payments/{self.orphan.pk}/").json()
        self.assertEqual(row["available_actions"], [])
        self.assertEqual(row["refundable_amount"], "0")

    def test_s13_ac4_gui_ca_hai_hoac_khong_gui_gi_400(self):
        paid = self._paid_order(phone="0906666666", txn="FTPAID")
        both = self._create(self.chu, payment_transaction=self.orphan.pk,
                            sales_invoice=paid.invoice.pk, amount="1000")
        self.assertEqual(both.status_code, 400)
        self.assertEqual(both.json(), {
            "code": "BR-HT-01", "detail": "Chỉ gửi một trong hai: sales_invoice hoặc payment_transaction.",
        })
        neither = self._create(self.chu, amount="1000")
        self.assertEqual(neither.status_code, 400)
        self.assertEqual(neither.json()["code"], "BR-HT-01")
        self.assertFalse(Refund.objects.exists())

    def test_s13_ac4_rang_buoc_db_dung_mot_trong_hai(self):
        paid = self._paid_order(phone="0906666666", txn="FTPAID")
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Refund.objects.create(amount=Decimal("1"), created_by=self.chu)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Refund.objects.create(amount=Decimal("1"), created_by=self.chu,
                                  sales_invoice=paid.invoice, payment_transaction=self.orphan)

    def test_s13_ac5_bao_cao_ky_khong_tru_khoan_hoan_khong_hoa_don(self):
        paid = self._paid_order(phone="0906666666", txn="FTPAID")
        inv_refund = Refund.objects.create(sales_invoice=paid.invoice, amount=Decimal("100000"),
                                           created_by=self.chu)
        txn_refund = Refund.objects.create(payment_transaction=self.orphan, amount=Decimal("300000"),
                                           created_by=self.chu)
        for r in (inv_refund, txn_refund):
            client_for(self.chu).post(f"/api/sales/refunds/{r.pk}/confirm/",
                                      {"bank_txn_ref": f"FTR{r.pk}"}, format="json")
        today = timezone.localdate()
        resp = client_for(self.chu).get("/api/reports/period/", {"year": today.year, "month": today.month})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(Decimal(str(resp.json()["refunds"])), Decimal("100000"))  # chỉ khoản có hoá đơn

    def test_s13_ac6_quan_ly_tao_phieu_gan_giao_dich_403(self):
        resp = self._create(self.ql, payment_transaction=self.orphan.pk, amount="300000")
        self.assertEqual(resp.status_code, 403)
        for user in (self.kho, self.giao):
            self.assertEqual(self._create(user, payment_transaction=self.orphan.pk,
                                          amount="300000").status_code, 403)
        self.assertEqual(self._create(None, payment_transaction=self.orphan.pk,
                                      amount="300000").status_code, 401)
        self.assertFalse(Refund.objects.exists())
        # hồi quy: Quản lý vẫn tạo được phiếu hoàn theo hoá đơn (S15/BR-HT-07)
        paid = self._paid_order(phone="0906666666", txn="FTPAID")
        ok = self._create(self.ql, sales_invoice=paid.invoice.pk, amount="1000")
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(ok.json()["payment_transaction"], None)

    def test_s13_bam_dup_cung_request_id_chi_mot_phieu(self):
        rid = str(uuid.uuid4())
        first = self._create(self.chu, payment_transaction=self.orphan.pk, amount="300000", request_id=rid)
        second = self._create(self.chu, payment_transaction=self.orphan.pk, amount="300000", request_id=rid)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertTrue(second.json()["duplicate"])
        self.assertEqual(second.json()["id"], first.json()["id"])
        self.assertEqual(Refund.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="create_refund").count(), 1)

    def test_s13_request_id_cua_phieu_khac_hoac_sai_dang_400(self):
        rid = str(uuid.uuid4())
        self._create(self.chu, payment_transaction=self.orphan.pk, amount="100000", request_id=rid)
        paid = self._paid_order(phone="0906666666", txn="FTPAID")
        other = self._create(self.chu, sales_invoice=paid.invoice.pk, amount="1000", request_id=rid)
        self.assertEqual(other.status_code, 400)
        bad = self._create(self.chu, payment_transaction=self.orphan.pk, amount="1000", request_id="xyz")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(Refund.objects.count(), 1)

    def test_s13_giao_dich_khong_hop_le_de_hoan_truc_tiep(self):
        paid = self._paid_order(phone="0906666666", txn="FTPAID")
        matched = PaymentTransaction.objects.get(bank_txn_id="FTPAID")
        resp = self._create(self.chu, payment_transaction=matched.pk, amount="1000")
        self.assertEqual(resp.status_code, 400)  # đã có hoá đơn → hoàn theo hoá đơn
        self.assertEqual(resp.json()["code"], "BR-HT-01")
        missing = self._create(self.chu, payment_transaction=999999, amount="1000")
        self.assertEqual(missing.status_code, 400)
        PaymentTransaction.objects.filter(pk=self.orphan.pk).update(
            resolution_status="RESOLVED", resolution="REFUNDED")
        closed = self._create(self.chu, payment_transaction=self.orphan.pk, amount="1000")
        self.assertEqual(closed.status_code, 400)
        self.assertEqual(closed.json()["code"], "BR-TT-09")
        self.assertFalse(Refund.objects.filter(payment_transaction__isnull=False).exists())

    def test_s13_so_tien_khong_hop_le_400(self):
        for amount in ("0", "-1", "abc", "", None, "NaN"):
            resp = self._create(self.chu, payment_transaction=self.orphan.pk, amount=amount)
            self.assertEqual(resp.status_code, 400, (amount, resp.content))
            self.assertEqual(resp.json()["code"], "BR-HT-04")
        self.assertFalse(Refund.objects.exists())

    def test_s13_danh_sach_phieu_hoan_co_payment_transaction(self):
        self._create(self.chu, payment_transaction=self.orphan.pk, amount="300000")
        rows = client_for(self.ql).get("/api/sales/refunds/").json()
        rows = rows["results"] if isinstance(rows, dict) else rows
        self.assertEqual(rows[0]["payment_transaction"], self.orphan.pk)
        self.assertIsNone(rows[0]["sales_invoice"])
        self.assertFalse(SalesInvoice.objects.filter(sales_order__payments=self.orphan).exists())
