"""
S14 — Huỷ đơn đã thanh toán theo trạng thái phiếu giao (UC-05, A4, BR-GH-07 mới, Q8 mặc định).

Contract: POST /api/sales/orders/{id}/cancel/ {"reason_code": ..., "note": ""}. Chặn huỷ
khi phiếu giao Đang giao (BR-GH-07) hoặc Hoàn tất (BR-GH-05). Hoàn kho lô gốc CHỈ khi hàng
còn ở kho (Soạn hàng/Chờ lấy) — Q8b: giao thất bại thì KHÔNG hoàn kho ở bước huỷ (tránh cộng
kho hai lần với luồng duyệt hàng hoàn P-08).
"""
from decimal import Decimal

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.delivery import services as delivery_services
from apps.delivery.models import DeliveryNote
from apps.inventory.models import StockLedgerEntry
from apps.sales.models import SalesOrder
from apps.sales.orders.tests.test_s10_api import OrderApiBase


def cancel_url(pk):
    return f"/api/sales/orders/{pk}/cancel/"


class S14CancelPaidOrderTests(OrderApiBase):
    def _cancel(self, user, order, reason_code="CUSTOMER_CHANGED_MIND", note=""):
        return client_for(user).post(
            cancel_url(order.pk), {"reason_code": reason_code, "note": note}, format="json",
        )

    def test_s14_ac1_huy_khi_soan_hang_hoan_kho_lo_goc(self):
        order = self._paid_order()
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        self.batch.refresh_from_db()
        before = self.batch.qty_available

        resp = self._cancel(self.ql, order, reason_code="CUSTOMER_CHANGED_MIND")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["order_status"], "CANCELLED")
        self.assertTrue(body["stock_restored"])
        self.assertEqual(body["delivery_status"], "CANCELLED")
        self.assertEqual(body["suggest_refund_amount"], "540000")
        self.assertEqual(body["invoice_id"], order.invoice.pk)

        order.refresh_from_db()
        note.refresh_from_db()
        self.batch.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)
        self.assertEqual(self.batch.qty_available, before + Decimal("2"))
        self.assertTrue(
            StockLedgerEntry.objects.filter(
                batch=self.batch, movement_type=StockLedgerEntry.MovementType.CANCEL_RESTORE,
            ).exists()
        )
        audit = AuditLog.objects.filter(
            action="cancel_paid_order", object_id=str(order.pk)
        ).latest("id")
        self.assertIn("Khách đổi ý", audit.note)
        self.assertTrue(audit.changes.get("stock_restored"))

    def test_s14_ac2_phieu_khong_con_trong_danh_sach_mac_dinh(self):
        order = self._paid_order()
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        note.assigned_to = self.giao
        note.save(update_fields=["assigned_to"])

        resp = self._cancel(self.ql, order)
        self.assertEqual(resp.status_code, 200, resp.content)

        listed = client_for(self.giao).get(
            "/api/delivery/notes/?status=PREPARING,READY,DELIVERING,FAILED"
        ).json()
        rows = listed["results"] if isinstance(listed, dict) else listed
        self.assertNotIn(note.pk, [r["id"] for r in rows])

    def test_s14_ac3_phieu_that_bai_khong_hoan_kho(self):
        order = self._paid_order()
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        delivery_services.advance_status(note=note, to_status=DeliveryNote.Status.READY, actor=self.giao)
        delivery_services.advance_status(
            note=note, to_status=DeliveryNote.Status.DELIVERING, actor=self.giao
        )
        delivery_services.mark_failed(note=note, actor=self.giao)
        self.batch.refresh_from_db()
        before = self.batch.qty_available

        resp = self._cancel(self.ql, order, reason_code="GIVE_UP_AFTER_FAILED")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertFalse(body["stock_restored"])
        self.assertEqual(body["delivery_status"], "CANCELLED")

        order.refresh_from_db()
        note.refresh_from_db()
        self.batch.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)
        self.assertEqual(self.batch.qty_available, before)  # tồn lô không đổi (Q8b)
        self.assertFalse(
            StockLedgerEntry.objects.filter(
                batch=self.batch, movement_type=StockLedgerEntry.MovementType.CANCEL_RESTORE,
            ).exists()
        )

    def test_s14_ac4_dang_giao_bi_chan(self):
        order = self._paid_order()
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        delivery_services.advance_status(note=note, to_status=DeliveryNote.Status.READY, actor=self.giao)
        delivery_services.advance_status(
            note=note, to_status=DeliveryNote.Status.DELIVERING, actor=self.giao
        )

        resp = self._cancel(self.ql, order)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-GH-07")

        order.refresh_from_db()
        note.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        self.assertEqual(note.status, DeliveryNote.Status.DELIVERING)

        body = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertNotIn("cancel", body["available_actions"])

    def test_s14_ac5_da_hoan_tat_bi_chan(self):
        order = self._paid_order()
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        for st in (DeliveryNote.Status.READY, DeliveryNote.Status.DELIVERING, DeliveryNote.Status.COMPLETED):
            delivery_services.advance_status(note=note, to_status=st, actor=self.giao)

        resp = self._cancel(self.ql, order)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-GH-05")

        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        body = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertNotIn("cancel", body["available_actions"])

    def test_s14_ac6_ly_do_khac_bat_buoc_ghi_chu(self):
        order = self._paid_order()
        resp = self._cancel(self.ql, order, reason_code="OTHER", note="")
        self.assertEqual(resp.status_code, 400, resp.content)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)

        ok = self._cancel(self.chu, order, reason_code="OTHER", note="Cá bị dập khi soạn")
        self.assertEqual(ok.status_code, 200, ok.content)

    def test_s14_ac7_sau_huy_hien_nut_tao_phieu_hoan(self):
        order = self._paid_order()
        self._cancel(self.ql, order)
        body = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertIn("create_refund", body["available_actions"])
        self.assertNotIn("cancel", body["available_actions"])

    def test_s14_ac8_nv_kho_403(self):
        order = self._paid_order()
        resp = self._cancel(self.kho, order)
        self.assertEqual(resp.status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
