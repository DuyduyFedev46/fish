"""
Lô L7 — bổ sung BE sau khi FE khớp contract S10 (03-dev-notes "Chỗ lệch contract").

1. `?q=` tìm thêm theo tên khách (không phân biệt hoa thường, không dấu) — vẫn giữ mã đơn/SĐT,
   phạm vi NV giao (S5, BR-PQ-12) giữ nguyên.
2. Chi tiết đơn: nhãn tiếng Việt (`*_label`) cạnh mã trạng thái phiếu giao/giao dịch/phiếu hoàn.
3. Chi tiết đơn: `timeline` [{at, kind, label, actor_display}] tăng dần theo thời gian, ghép từ
   dữ liệu thật + AuditLog (BR-PQ-04/05). Không số giá vốn (BR-PQ-15), actor=None → "Hệ thống".
"""
import datetime
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import StaffProfile
from apps.common.tests.fixtures import client_for
from apps.delivery import services as delivery_services
from apps.delivery.models import DeliveryNote
from apps.sales.models import Refund, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services
from apps.sales.refunds import services as refund_services

from .test_s10_api import SENSITIVE_KEYS, OrderApiBase, find_keys

TIMELINE_KEYS = {"at", "kind", "label", "actor_display"}


class L7SearchByNameTests(OrderApiBase):
    def _ids(self, user, q):
        resp = client_for(user).get("/api/sales/orders/", {"q": q})
        self.assertEqual(resp.status_code, 200, resp.content)
        return sorted(r["id"] for r in resp.json()["results"])

    def test_l7_tim_theo_ten_khach_khong_phan_biet_hoa_thuong(self):
        hoa = self._order(phone="0901234567", name="Chị Hoa")
        self._order(phone="0987654321", name="Anh Ba")
        self.assertEqual(self._ids(self.ql, "hoa"), [hoa.pk])
        self.assertEqual(self._ids(self.ql, "CHỊ HOA"), [hoa.pk])

    def test_l7_tim_theo_ten_khach_khong_dau(self):
        dat = self._order(phone="0901234567", name="Anh Đạt Nguyễn")
        self._order(phone="0987654321", name="Anh Ba")
        self.assertEqual(self._ids(self.kho, "dat nguyen"), [dat.pk])
        self.assertEqual(self._ids(self.kho, "ĐẠT"), [dat.pk])

    def test_l7_van_tim_theo_ma_don_va_sdt(self):
        hoa = self._order(phone="0901234567", name="Chị Hoa")
        self._order(phone="0987654321", name="Anh Ba")
        self.assertEqual(self._ids(self.ql, "0901234"), [hoa.pk])
        self.assertEqual(self._ids(self.ql, hoa.code[-6:].lower()), [hoa.pk])

    def test_l7_tim_theo_ten_nv_giao_van_trong_pham_vi_s5(self):
        mine = self._paid_order(phone="0901234567", txn="FTN1")
        other = self._paid_order(phone="0908888888", txn="FTN2")  # cùng tên "Chị Hoa"
        DeliveryNote.objects.filter(sales_invoice=mine.invoice).update(assigned_to=self.giao)
        self.assertEqual(self._ids(self.chu, "hoa"), sorted([mine.pk, other.pk]))
        self.assertEqual(self._ids(self.giao, "hoa"), [mine.pk])

    def test_l7_tim_ten_khong_co_quyen_403(self):
        self._order()
        self.assertEqual(client_for(self.nobody).get("/api/sales/orders/?q=hoa").status_code, 403)


class L7LabelTests(OrderApiBase):
    def test_l7_nhan_trang_thai_phieu_giao_giao_dich_phieu_hoan(self):
        order = self._paid_order()
        Refund.objects.create(sales_invoice=order.invoice, amount=Decimal("100000"), created_by=self.chu)
        body = client_for(self.ql).get(f"/api/sales/orders/{order.pk}/").json()
        pay = body["payments"][0]
        self.assertEqual(pay["match_status"], "MATCHED")
        self.assertEqual(pay["match_status_label"], "Khớp — đã xác nhận")
        self.assertEqual(pay["source"], "WEBHOOK")
        self.assertEqual(pay["source_label"], "Webhook SePay")
        self.assertEqual(body["delivery"]["status"], "PREPARING")
        self.assertEqual(body["delivery"]["status_label"], "Soạn hàng")
        self.assertEqual(body["refunds"][0]["status"], "PENDING")
        self.assertEqual(body["refunds"][0]["status_label"], "Chờ hoàn")

    def test_l7_nhan_giao_dich_thieu_tien(self):
        order = self._order()
        payment_services.confirm_payment(
            order=order, bank_txn_id="FTLOW", amount=Decimal("300000"), received_at=timezone.now(),
        )
        pay = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()["payments"][0]
        self.assertEqual(pay["match_status_label"], "Thiếu tiền — chờ Chủ")


class L7TimelineTests(OrderApiBase):
    def _timeline(self, user, order):
        resp = client_for(user).get(f"/api/sales/orders/{order.pk}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        tl = resp.json()["timeline"]
        for row in tl:
            self.assertEqual(set(row.keys()), TIMELINE_KEYS)
        ats = [datetime.datetime.fromisoformat(r["at"]) for r in tl]
        self.assertEqual(ats, sorted(ats), "timeline phải tăng dần theo thời gian")
        return tl

    def test_l7_timeline_don_giu_cho_chi_co_dat_don(self):
        order = self._order()
        tl = self._timeline(self.ql, order)
        self.assertEqual([r["kind"] for r in tl], ["order_placed"])
        self.assertEqual(tl[0]["actor_display"], "Hệ thống")
        self.assertIn(order.code, tl[0]["label"])

    def test_l7_timeline_webhook_hoa_don_giao_hoan_theo_thu_tu(self):
        StaffProfile.objects.create(user=self.giao, phone="0908111222", display_name="Anh Tư")
        StaffProfile.objects.create(user=self.ql, phone="0908000111", display_name="Chị Quản")
        StaffProfile.objects.create(user=self.chu, phone="0908000222", display_name="Anh Lộc")
        order = self._paid_order()
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        note.assigned_to = self.giao
        note.save(update_fields=["assigned_to"])
        for st in (DeliveryNote.Status.READY, DeliveryNote.Status.DELIVERING):
            delivery_services.advance_status(note=note, to_status=st, actor=self.giao)
        delivery_services.mark_failed(note=note, actor=self.giao)
        delivery_services.advance_status(note=note, to_status=DeliveryNote.Status.DELIVERING, actor=self.giao)
        delivery_services.advance_status(note=note, to_status=DeliveryNote.Status.COMPLETED, actor=self.giao)
        refund = refund_services.create_refund(
            invoice=order.invoice, amount=Decimal("100000"), is_partial=True, reason="Thiếu cân",
            actor=self.ql,
        )
        refund_services.confirm_refund(refund=refund, bank_txn_ref="FTREF1", actor=self.chu)

        tl = self._timeline(self.chu, order)
        kinds = [r["kind"] for r in tl]
        self.assertEqual(kinds, [
            "order_placed", "payment_received", "invoice_issued", "delivery_created",
            "delivery_status", "delivery_status", "delivery_failed", "delivery_status",
            "delivered", "refund_created", "refund_confirmed",
        ])
        by_kind = {r["kind"]: r for r in tl}
        self.assertEqual(by_kind["payment_received"]["actor_display"], "Hệ thống")  # webhook
        self.assertIn("540.000", by_kind["payment_received"]["label"])
        self.assertIn(order.invoice.code, by_kind["invoice_issued"]["label"])
        self.assertIn(note.code, by_kind["delivery_created"]["label"])
        self.assertEqual(by_kind["delivered"]["actor_display"], "Anh Tư")
        self.assertEqual(by_kind["delivery_failed"]["actor_display"], "Anh Tư")
        self.assertIn("1", by_kind["delivery_failed"]["label"])
        self.assertEqual(by_kind["refund_created"]["actor_display"], "Chị Quản")
        self.assertIn("100.000", by_kind["refund_created"]["label"])
        self.assertEqual(by_kind["refund_confirmed"]["actor_display"], "Anh Lộc")

    def test_l7_timeline_xac_nhan_tay_actor_la_chu(self):
        StaffProfile.objects.create(user=self.chu, phone="0908000222", display_name="Anh Lộc")
        order = self._order()
        payment_services.confirm_payment_manual(
            order=order, bank_txn_id="FTTAY1", amount=None, actor=self.chu,
        )
        tl = self._timeline(self.ql, order)
        pay = [r for r in tl if r["kind"] == "payment_received"]
        self.assertEqual(len(pay), 1)  # AuditLog confirm_payment_manual không nhân đôi dòng
        self.assertEqual(pay[0]["actor_display"], "Anh Lộc")
        self.assertIn("Xác nhận tay", pay[0]["label"])
        self.assertIn("invoice_issued", [r["kind"] for r in tl])

    def test_l7_timeline_tu_huy_he_thong(self):
        order = self._order()
        later = order.booked_expires_at + datetime.timedelta(minutes=1)
        order_services.cancel_unpaid_expired(now=later)
        tl = self._timeline(self.ql, order)
        self.assertEqual([r["kind"] for r in tl], ["order_placed", "auto_cancelled"])
        self.assertEqual(tl[-1]["actor_display"], "Hệ thống")

    def test_l7_timeline_huy_don_co_ly_do_actor_ten_dang_nhap_khi_khong_ho_so(self):
        order = self._paid_order()
        order_services.cancel_paid_order(order=order, actor=self.ql, reason="Khách đổi ý")
        tl = self._timeline(self.chu, order)
        cancel = [r for r in tl if r["kind"] == "cancelled"]
        self.assertEqual(len(cancel), 1)
        self.assertEqual(cancel[0]["actor_display"], "ql1")  # không có StaffProfile → username
        self.assertIn("Khách đổi ý", cancel[0]["label"])

    def test_l7_timeline_khong_ro_gia_von(self):
        order = self._paid_order()
        body = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()
        text = " ".join(r["label"] for r in body["timeline"])
        self.assertNotIn("180000", text.replace(".", ""))  # landed_unit_cost/unit_cost của lô
        for user in (self.ql, self.kho):
            b = client_for(user).get(f"/api/sales/orders/{order.pk}/").json()
            self.assertEqual(find_keys(b, SENSITIVE_KEYS), set(), user.username)

    def test_l7_timeline_khong_lo_audit_cua_don_khac(self):
        other = self._paid_order(phone="0908888888", txn="FTO1")
        order_services.cancel_paid_order(order=other, actor=self.ql, reason="Đơn khác")
        mine = self._order(phone="0907777777", name="Cô Năm")
        tl = self._timeline(self.chu, mine)
        self.assertEqual([r["kind"] for r in tl], ["order_placed"])

    def test_l7_timeline_hang_ve_kho_va_duyet(self):
        from apps.inventory.models import ReturnToStock
        from apps.inventory.returns import services as return_services

        order = self._paid_order()
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        for st in (DeliveryNote.Status.READY, DeliveryNote.Status.DELIVERING):
            delivery_services.advance_status(note=note, to_status=st, actor=self.giao)
        delivery_services.mark_failed(note=note, actor=self.giao)
        rt = delivery_services.return_to_warehouse(
            note=note, batch=self.batch, qty=Decimal("2"), actor=self.giao,
        )
        rt.decision = ReturnToStock.Decision.RESTOCK
        rt.save(update_fields=["decision"])
        return_services.apply_return(return_to_stock=rt, approver=self.ql)

        tl = self._timeline(self.chu, order)
        kinds = [r["kind"] for r in tl]
        self.assertEqual(kinds[-2:], ["return_to_warehouse", "return_approved"])
        self.assertIn("2.000 kg", tl[-2]["label"])
        self.assertEqual(tl[-2]["actor_display"], "giao1")
        self.assertIn("Tái nhập", tl[-1]["label"])
        self.assertEqual(tl[-1]["actor_display"], "ql1")
