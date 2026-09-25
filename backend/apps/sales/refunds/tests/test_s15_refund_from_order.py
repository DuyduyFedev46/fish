"""
S15 — Tạo phiếu hoàn từ đơn, chống tạo trùng (UC-06, A5, Q12).

Nhánh hoá đơn (`sales_invoice`) của `POST /api/sales/refunds/create/`. `request_id` (Q12) và
việc chặn tạo trùng đã có từ Lô L8 (S13, dùng chung cho cả hai nhánh) — chỉ còn viết lại
thông điệp vượt số còn hoàn cho đúng câu chữ S15 (nợ của Lô L8, giả định #6).
"""
import uuid
from decimal import Decimal

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.sales.models import Refund
from apps.sales.orders.tests.test_s10_api import OrderApiBase

CREATE_URL = "/api/sales/refunds/create/"


class S15RefundFromOrderTests(OrderApiBase):
    def _create(self, user, **data):
        data.setdefault("reason", "Huỷ đơn — khách đổi ý")
        return client_for(user).post(CREATE_URL, data, format="json")

    def test_s15_ac1_tao_toan_phan(self):
        order = self._paid_order()
        rid = str(uuid.uuid4())
        resp = self._create(
            self.ql, sales_invoice=order.invoice.pk, amount="540000", is_partial=False, request_id=rid,
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], "PENDING")
        self.assertEqual(body["amount"], "540000")
        self.assertEqual(body["sales_invoice"], order.invoice.pk)
        self.assertFalse(body["is_partial"])
        self.assertTrue(AuditLog.objects.filter(action="create_refund").exists())
        row = client_for(self.chu).get("/api/sales/refunds/").json()["results"][0]
        self.assertEqual(row["status"], "PENDING")

    def test_s15_ac2_vuot_so_con_hoan_toi_da(self):
        order = self._paid_order()
        Refund.objects.create(sales_invoice=order.invoice, amount=Decimal("300000"), created_by=self.chu)
        resp = self._create(self.ql, sales_invoice=order.invoice.pk, amount="300000")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json(), {
            "code": "BR-HT-04", "detail": "Vượt số đã thu: còn được hoàn tối đa 240.000đ.",
        })

    def test_s15_ac3_phieu_that_bai_khong_tinh(self):
        order = self._paid_order()
        Refund.objects.create(
            sales_invoice=order.invoice, amount=Decimal("300000"), created_by=self.chu,
            status=Refund.Status.FAILED,
        )
        resp = self._create(self.ql, sales_invoice=order.invoice.pk, amount="540000")
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_s15_ac4_bam_dup_cung_request_id_van_mot_phieu(self):
        order = self._paid_order()
        rid = str(uuid.uuid4())
        first = self._create(self.ql, sales_invoice=order.invoice.pk, amount="540000", request_id=rid)
        second = self._create(self.ql, sales_invoice=order.invoice.pk, amount="540000", request_id=rid)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertTrue(second.json()["duplicate"])
        self.assertEqual(second.json()["id"], first.json()["id"])
        self.assertEqual(Refund.objects.count(), 1)

    def test_s15_ac5_so_tien_khong_hop_le(self):
        order = self._paid_order()
        for amount in ("0", "-1"):
            resp = self._create(self.ql, sales_invoice=order.invoice.pk, amount=amount)
            self.assertEqual(resp.status_code, 400, (amount, resp.content))
            self.assertEqual(resp.json()["code"], "BR-HT-04")
        self.assertFalse(Refund.objects.exists())

    def test_s15_ac6_nv_kho_403(self):
        order = self._paid_order()
        resp = self._create(self.kho, sales_invoice=order.invoice.pk, amount="540000")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Refund.objects.exists())
