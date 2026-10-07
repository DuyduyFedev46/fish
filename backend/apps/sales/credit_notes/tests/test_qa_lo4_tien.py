"""
QA P8 Lô 4 — ca ngoài đường thuận, viết ĐỘC LẬP với test của be-dev (SR-12, SR-13, SR-14).

Nguyên tắc Duy 30/09: "báo cáo kỳ đã qua không bao giờ được đổi số". Mỗi kịch bản chụp báo cáo các kỳ
TRƯỚC khi thao tác rồi so lại SAU khi thao tác (mọi khoá). Dữ liệu hoàn toàn giả.
"""
import datetime
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.models import BundleLine, Item, ItemPrice
from apps.common.tests.fixtures import client_for
from apps.delivery.models import ConfirmationTask, DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch
from apps.reports import services as report_services
from apps.sales.credit_notes.tests.base import CreditNoteBase
from apps.sales.models import Refund, SalesCreditNote, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services
from apps.sales.refunds import services as refund_services


def cancel_url(pk):
    return f"/api/sales/orders/{pk}/cancel/"


def month_dt(n_back, day=15):
    """Thời điểm giữa tháng cách tháng hiện tại n_back tháng (giờ VN)."""
    d = timezone.localdate()
    y, m = d.year, d.month - n_back
    while m <= 0:
        m += 12
        y -= 1
    return timezone.make_aware(datetime.datetime(y, m, day, 12, 0)), (y, m)


def ym_back(n_back):
    return month_dt(n_back)[1]


class QABase(CreditNoteBase):
    N_PERIODS = 6

    def _snap_periods(self):
        return {
            ym_back(n): report_services.period_pnl(year=ym_back(n)[0], month=ym_back(n)[1])
            for n in range(self.N_PERIODS)
        }

    def _batch_pnl(self, batch=None):
        b = batch or self.batch
        b.refresh_from_db()
        return report_services.batch_pnl(batch=b)

    def _dash_revenue_today(self):
        resp = client_for(self.chu).get("/api/dashboard/summary/")
        self.assertEqual(resp.status_code, 200, resp.content)
        return Decimal(str(resp.json()["kpis"]["revenue_today"]))

    def _manual_cancel(self, order, user=None):
        resp = client_for(user or self.chu).post(
            cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp

    def _refund(self, invoice, amount, *, confirm=True, confirmed_at=None):
        r, _dup = refund_services.create_invoice_refund(
            invoice=invoice, amount=Decimal(amount), is_partial=Decimal(amount) < invoice.amount,
            reason="", actor=self.chu, request_id=uuid.uuid4(),
        )
        if confirm:
            refund_services.confirm_refund(refund=r, bank_txn_ref="BANK-GIA-QA", actor=self.chu)
            if confirmed_at is not None:
                Refund.objects.filter(pk=r.pk).update(confirmed_at=confirmed_at)
        return r

    def _sum(self, snaps, key):
        return sum((p[key] for p in snaps.values()), Decimal("0"))


# ----------------------------------------------------------------------------------------------
# 1. Mọi đường huỷ đơn đã thanh toán -> đúng 1 chứng từ, hoá đơn giữ ISSUED
# ----------------------------------------------------------------------------------------------
class QAPathsTests(QABase):
    def _escalate(self, task):
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = timezone.now()
        task.save()

    def test_qa_path_cskh_decide_cancel_lap_dung_1_chung_tu(self):
        order, note, task = self._paid()
        self._escalate(task)
        inv_before = SalesInvoice.objects.filter(pk=order.invoice.pk).values().get()
        resp = client_for(self.ql).post(
            f"/api/confirmation/queue/{note.pk}/decide/", {"decision": "CANCEL", "reason_code": "UNREACHABLE"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        cn = SalesCreditNote.objects.get()
        self.assertEqual(cn.created_by, self.ql)
        self.assertEqual(cn.sales_invoice_id, order.invoice.pk)
        self.assertEqual(cn.amount, order.invoice.amount)
        self.assertEqual(cn.lines.count(), 1)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(SalesInvoice.objects.filter(pk=order.invoice.pk).values().get(), inv_before)
        self.assertEqual(SalesInvoice.objects.get(pk=order.invoice.pk).status, SalesInvoice.Status.ISSUED)

        # màn hình cũ: quản lý bấm quyết định lần 2, rồi Chủ huỷ tay -> vẫn 1 chứng từ, lỗi 4xx
        again = client_for(self.ql).post(
            f"/api/confirmation/queue/{note.pk}/decide/", {"decision": "CANCEL", "reason_code": "UNREACHABLE"}, format="json",
        )
        self.assertGreaterEqual(again.status_code, 400, again.content)
        self.assertLess(again.status_code, 500, again.content)
        self.assertEqual(client_for(self.chu).post(
            cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json").status_code, 400)
        self.assertEqual(SalesCreditNote.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="issue_credit_note").count(), 1)

    def test_qa_path_cskh_decide_cancel_loi_lap_chung_tu_rollback(self):
        order, note, task = self._paid()
        self._escalate(task)
        self.batch.refresh_from_db()
        avail = self.batch.qty_available
        with mock.patch("apps.sales.credit_notes.services.issue_cancel_credit_note",
                        side_effect=RuntimeError("boom")):
            client = client_for(self.ql)
            client.raise_request_exception = False
            try:
                resp = client.post(f"/api/confirmation/queue/{note.pk}/decide/",
                                   {"decision": "CANCEL", "reason_code": "UNREACHABLE"}, format="json")
                self.assertGreaterEqual(resp.status_code, 500)
            except RuntimeError:
                pass
        order.refresh_from_db()
        task.refresh_from_db()
        note.refresh_from_db()
        self.batch.refresh_from_db()
        self.assertIn(order.status, (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING))
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)
        self.assertNotEqual(note.status, DeliveryNote.Status.CANCELLED)
        self.assertEqual(self.batch.qty_available, avail)
        self.assertEqual(SalesCreditNote.objects.count(), 0)
        self.assertFalse(AuditLog.objects.filter(action="cancel_paid_order").exists())

    def test_qa_path_job_tu_huy_hai_don_1_don_loi_don_kia_van_huy_va_chay_lai_khong_nhan_doi(self):
        o1, _n1, t1 = self._paid(phone="0900000111", name="Khách Giả Một")
        o2, _n2, t2 = self._paid(phone="0900000222", name="Khách Giả Hai")
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        for t in (t1, t2):
            t.state = ConfirmationTask.State.ESCALATED
            t.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
            t.escalated_at = t0
            t.save()
        from apps.delivery.confirmation import services as confirmation_services
        from apps.sales.credit_notes import services as cn_services
        real = cn_services.issue_cancel_credit_note

        def flaky(*, invoice, **kw):
            if invoice.pk == o2.invoice.pk:
                raise RuntimeError("boom")
            return real(invoice=invoice, **kw)

        with override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True):
            with mock.patch("apps.sales.credit_notes.services.issue_cancel_credit_note", side_effect=flaky):
                with self.assertLogs("cangca.delivery.confirmation", level="ERROR") as logs:
                    res = confirmation_services.auto_cancel_overdue(now=t0 + timedelta(minutes=31))
            # log lỗi không chứa dữ liệu cá nhân giả
            blob = "\n".join(logs.output)
            for s in ("0900000111", "0900000222", "Khách Giả", "Số 1 Đường Thử"):
                self.assertNotIn(s, blob)
            self.assertEqual(res["cancelled"], 1)
            o1.refresh_from_db()
            o2.refresh_from_db()
            self.assertEqual(o1.status, SalesOrder.Status.CANCELLED)
            self.assertIn(o2.status, (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING))
            self.assertEqual(SalesCreditNote.objects.count(), 1)
            # chạy lại (không lỗi nữa) -> đơn 2 được huỷ + có chứng từ, đơn 1 không bị nhân đôi
            res2 = confirmation_services.auto_cancel_overdue(now=t0 + timedelta(minutes=32))
            self.assertEqual(res2["cancelled"], 1)
            res3 = confirmation_services.auto_cancel_overdue(now=t0 + timedelta(minutes=33))
            self.assertEqual(res3["cancelled"], 0)
        self.assertEqual(SalesCreditNote.objects.count(), 2)
        self.assertEqual(SalesCreditNote.objects.filter(sales_invoice=o1.invoice).count(), 1)
        self.assertEqual(SalesCreditNote.objects.filter(sales_invoice=o2.invoice).count(), 1)

    def test_qa_path_thu_tu_a_b_va_b_a_huy_tay_roi_job_va_nguoc_lai(self):
        # A -> B: huỷ tay rồi job
        o1, _n, t1 = self._paid()
        self._manual_cancel(o1)
        r = self._auto_cancel(t1)
        self.assertEqual(r["cancelled"], 0)
        self.assertEqual(SalesCreditNote.objects.filter(sales_invoice=o1.invoice).count(), 1)
        self.assertEqual(SalesCreditNote.objects.get(sales_invoice=o1.invoice).created_by, self.chu)
        # B -> A: job rồi huỷ tay
        o2, _n, t2 = self._paid(phone="0900000222")
        self.assertEqual(self._auto_cancel(t2)["cancelled"], 1)
        self.assertEqual(client_for(self.chu).post(
            cancel_url(o2.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json").status_code, 400)
        self.assertEqual(SalesCreditNote.objects.filter(sales_invoice=o2.invoice).count(), 1)
        self.assertIsNone(SalesCreditNote.objects.get(sales_invoice=o2.invoice).created_by)

    def test_qa_db_rang_buoc_source_key_va_code_unique(self):
        from django.db import IntegrityError, transaction
        order, _n, _t = self._paid()
        self._manual_cancel(order)
        cn = SalesCreditNote.objects.get()
        with self.assertRaises(IntegrityError), transaction.atomic():
            SalesCreditNote.objects.create(
                code="DC-KHAC", source_key=cn.source_key, sales_invoice=cn.sales_invoice,
                issued_at=timezone.now(), amount=1, stock_restored=True,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            SalesCreditNote.objects.create(
                code=cn.code, source_key="cancel:khac", sales_invoice=cn.sales_invoice,
                issued_at=timezone.now(), amount=1, stock_restored=True,
            )

    def test_qa_khong_xoa_duoc_hoa_don_hay_lo_da_co_chung_tu(self):
        from django.db.models import ProtectedError
        order, _n, _t = self._paid()
        self._manual_cancel(order)
        with self.assertRaises(ProtectedError):
            order.invoice.delete()
        with self.assertRaises(ProtectedError):
            self.batch.delete()

    def test_qa_don_chua_thanh_toan_huy_khong_lap_chung_tu(self):
        # đơn giữ chỗ chưa TT: không có hoá đơn -> không có chứng từ; TTL hết hạn cũng vậy
        order = order_services.create_order(
            customer_phone="0900000333", customer_name="Khách Giả Ba",
            delivery_address="Số 1 Đường Thử", phone="0900000333",
            lines=[{"item_code": self.item.code, "qty": Decimal("1")}],
        )
        resp = client_for(self.chu).post(cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(SalesCreditNote.objects.count(), 0)


# ----------------------------------------------------------------------------------------------
# 2. Tiền: so kỳ cũ TRƯỚC / SAU huỷ cho nhiều kịch bản hoàn tiền
# ----------------------------------------------------------------------------------------------
class QAMoneyScenarioTests(QABase):
    """Hoá đơn 300.000 (2 kg x 150.000, giá vốn 220.000). Huỷ 'bây giờ'. Kỳ n>=1 không được đổi số."""

    def _scenario(self, *, inv_back, refunds_before=(), refund_after=None):
        """refunds_before: [(amount, back_or_None)] — back=None nghĩa là xác nhận 'bây giờ' trước huỷ."""
        order, _n, _t = self._paid()
        SalesInvoice.objects.filter(pk=order.invoice.pk).update(issued_at=month_dt(inv_back)[0])
        order.refresh_from_db()
        for amount, back in refunds_before:
            self._refund(order.invoice, amount, confirmed_at=None if back is None else month_dt(back)[0])
        before = self._snap_periods()
        batch_before = self._batch_pnl()

        self._manual_cancel(order)

        after = self._snap_periods()
        # kỳ đã qua giữ nguyên MỌI khoá; kỳ hiện tại (n=0) nhận điều chỉnh
        for n in range(1, self.N_PERIODS):
            self.assertEqual(after[ym_back(n)], before[ym_back(n)], f"kỳ -{n} bị đổi số")
        if refund_after is not None:
            self._refund(order.invoice, refund_after)
            after = self._snap_periods()
            for n in range(1, self.N_PERIODS):
                self.assertEqual(after[ym_back(n)], before[ym_back(n)], f"kỳ -{n} bị đổi số sau hoàn")
        # đơn huỷ toàn bộ: lãi ròng mọi kỳ cộng lại = 0, giá vốn ròng = 0
        self.assertEqual(self._sum(after, "profit"), Decimal("0"), after)
        self.assertEqual(self._sum(after, "cogs"), Decimal("0"), after)
        # lô chưa chốt: doanh thu lô về 0 (R6)
        b = self._batch_pnl()
        self.assertEqual(b["revenue"], Decimal("0"))
        self.assertEqual(b["qty_sold"], Decimal("0"))
        self.assertEqual(b["reversed_qty"], Decimal("2"))
        self.assertEqual(batch_before["revenue"], Decimal("300000"))
        return order, before, after

    def test_a_khong_hoan_hoa_don_2_thang_truoc(self):
        _o, _b, after = self._scenario(inv_back=2)
        cur = after[ym_back(0)]
        self.assertEqual(cur["credit_notes"], Decimal("300000"))
        self.assertEqual(cur["cogs_reversed"], Decimal("220000"))
        self.assertEqual(cur["revenue"], Decimal("-300000"))
        self.assertEqual(cur["refunds"], Decimal("0"))

    def test_b_hoan_mot_phan_thang_truoc_roi_huy(self):
        _o, _b, after = self._scenario(inv_back=2, refunds_before=[(50000, 1)])
        self.assertEqual(after[ym_back(1)]["refunds"], Decimal("50000"))
        self.assertEqual(after[ym_back(0)]["credit_notes"], Decimal("250000"))
        self.assertEqual(after[ym_back(0)]["refunds"], Decimal("0"))

    def test_c_hoan_du_truoc_huy(self):
        _o, _b, after = self._scenario(inv_back=2, refunds_before=[(300000, 1)])
        self.assertEqual(after[ym_back(1)]["refunds"], Decimal("300000"))
        self.assertEqual(after[ym_back(0)]["credit_notes"], Decimal("0"))
        self.assertEqual(after[ym_back(0)]["cogs_reversed"], Decimal("220000"))

    def test_d_hoan_mot_phan_cung_thang_huy_truoc_luc_huy(self):
        _o, _b, after = self._scenario(inv_back=1, refunds_before=[(50000, None)])
        cur = after[ym_back(0)]
        self.assertEqual(cur["credit_notes"], Decimal("250000"))
        self.assertEqual(cur["refunds"], Decimal("50000"))

    def test_e_hoa_don_cung_thang_hoan_mot_phan_truoc_huy(self):
        _o, _b, after = self._scenario(inv_back=0, refunds_before=[(50000, None)])
        cur = after[ym_back(0)]
        # hoá đơn 300.000, đảo 250.000, hoàn 50.000: doanh thu 50.000 - hoàn 50.000 = 0, giá vốn 0
        self.assertEqual(cur["revenue"] - cur["refunds"], Decimal("0"))
        self.assertEqual(cur["profit"], Decimal("0"))

    def test_f_hoan_sau_huy_khong_tru_lan_2(self):
        _o, _b, after = self._scenario(inv_back=2, refund_after=300000)
        self.assertEqual(after[ym_back(0)]["refunds"], Decimal("0"))
        self.assertEqual(after[ym_back(0)]["credit_notes"], Decimal("300000"))

    def test_g_hai_phieu_hoan_truoc_huy_o_hai_ky_khac_nhau(self):
        _o, _b, after = self._scenario(inv_back=3, refunds_before=[(50000, 2), (100000, None)])
        self.assertEqual(after[ym_back(2)]["refunds"], Decimal("50000"))
        self.assertEqual(after[ym_back(0)]["credit_notes"], Decimal("150000"))
        self.assertEqual(after[ym_back(0)]["refunds"], Decimal("100000"))

    def test_h_phieu_hoan_tao_truoc_huy_nhung_xac_nhan_sau_huy(self):
        order, _n, _t = self._paid()
        SalesInvoice.objects.filter(pk=order.invoice.pk).update(issued_at=month_dt(2)[0])
        order.refresh_from_db()
        r = self._refund(order.invoice, 300000, confirm=False)  # tạo phiếu, CHƯA xác nhận
        before = self._snap_periods()
        self._manual_cancel(order)
        refund_services.confirm_refund(refund=Refund.objects.get(pk=r.pk), bank_txn_ref="BANK-GIA-QA", actor=self.chu)
        after = self._snap_periods()
        for n in range(1, self.N_PERIODS):
            self.assertEqual(after[ym_back(n)], before[ym_back(n)])
        self.assertEqual(after[ym_back(0)]["refunds"], Decimal("0"))
        self.assertEqual(self._sum(after, "profit"), Decimal("0"))

    def test_i_luong_tu_huy_that_co_tao_phieu_hoan_roi_xac_nhan_lai_tien(self):
        """Đường job đầy đủ: tự huỷ -> tự tạo phiếu hoàn (REFUND_CALL) -> Chủ xác nhận hoàn."""
        order, _n, task = self._paid()
        SalesInvoice.objects.filter(pk=order.invoice.pk).update(issued_at=month_dt(2)[0])
        before = self._snap_periods()
        self.assertEqual(self._auto_cancel(task)["cancelled"], 1)
        r = Refund.objects.get(sales_invoice=order.invoice)
        refund_services.confirm_refund(refund=r, bank_txn_ref="BANK-GIA-QA", actor=self.chu)
        after = self._snap_periods()
        for n in range(1, self.N_PERIODS):
            self.assertEqual(after[ym_back(n)], before[ym_back(n)])
        cur = after[ym_back(0)]
        self.assertEqual(cur["refunds"], Decimal("0"))
        self.assertEqual(cur["credit_notes"], Decimal("300000"))
        self.assertEqual(self._sum(after, "profit"), Decimal("0"))

    def test_dashboard_revenue_today_dao_hom_nay_khong_dong_den_hom_qua(self):
        o_old, _n, _t = self._paid()
        # hoá đơn hôm qua (giả lập bằng .update)
        yesterday = timezone.now() - timedelta(days=1, hours=1)
        SalesInvoice.objects.filter(pk=o_old.invoice.pk).update(issued_at=yesterday)
        o_new, _n2, _t2 = self._paid(phone="0900000444")
        self.assertEqual(self._dash_revenue_today(), Decimal("300000"))
        self._manual_cancel(o_new)          # huỷ đơn của hôm nay -> hôm nay 0
        self.assertEqual(self._dash_revenue_today(), Decimal("0"))
        self._manual_cancel(o_old)          # huỷ hoá đơn hôm qua -> hôm nay bị điều chỉnh âm (kỳ hiện tại nhận)
        self.assertEqual(self._dash_revenue_today(), Decimal("-300000"))


# ----------------------------------------------------------------------------------------------
# 3. Lô: bán lại kg đã hoàn kho, lô đã chốt trước/sau huỷ, ranh giới closed_at, đơn 2 lô
# ----------------------------------------------------------------------------------------------
class QABatchTests(QABase):
    def _close(self, batch, closed_at):
        Batch.objects.filter(pk=batch.pk).update(status=Batch.Status.CLOSED, closed_at=closed_at)
        batch.refresh_from_db()

    def test_ban_lai_kg_da_hoan_kho_sau_huy_khong_cong_hai_lan_va_huy_lai_lan_nua(self):
        o1, _n, _t = self._paid()
        self._manual_cancel(o1)
        p = self._batch_pnl()
        self.assertEqual((p["revenue"], p["qty_sold"]), (Decimal("0"), Decimal("0")))
        o2, _n2, _t2 = self._paid(phone="0900000555")
        p = self._batch_pnl()
        self.assertEqual((p["revenue"], p["qty_sold"]), (Decimal("300000"), Decimal("2")))
        self.assertEqual(p["reversed_qty"], Decimal("2"))
        # huỷ đơn bán lại -> lại về 0, đảo lũy kế 4 kg / 600.000
        self._manual_cancel(o2)
        p = self._batch_pnl()
        self.assertEqual((p["revenue"], p["qty_sold"]), (Decimal("0"), Decimal("0")))
        self.assertEqual((p["reversed_qty"], p["reversed_revenue"]), (Decimal("4"), Decimal("600000")))
        self.assertEqual(SalesCreditNote.objects.count(), 2)
        self.assertEqual(len({c.code for c in SalesCreditNote.objects.all()}), 2)

    def test_lo_da_chot_truoc_khi_huy_khong_doi_lai_lo_nhung_ky_hien_tai_nhan(self):
        order, _n, _t = self._paid()
        self._close(self.batch, timezone.now() - timedelta(days=1))
        before = self._batch_pnl()
        self.assertEqual(before["revenue"], Decimal("300000"))
        cur_before = report_services.period_pnl(year=ym_back(0)[0], month=ym_back(0)[1])
        self._manual_cancel(order)
        self.assertEqual(self._batch_pnl(), before)                        # mọi khoá giống hệt
        cur_after = report_services.period_pnl(year=ym_back(0)[0], month=ym_back(0)[1])
        self.assertEqual(cur_after["credit_notes"] - cur_before["credit_notes"], Decimal("300000"))

    def test_lo_chot_sau_khi_huy_van_giu_so_da_dao(self):
        order, _n, _t = self._paid()
        self._manual_cancel(order)
        pre = self._batch_pnl()
        self._close(self.batch, timezone.now() + timedelta(minutes=5))
        post = self._batch_pnl()
        for k in ("revenue", "qty_sold", "reversed_qty", "reversed_revenue"):
            self.assertEqual(post[k], pre[k], k)

    def test_ranh_gioi_closed_at_bang_thi_tru_cham_1_micro_giay_thi_khong(self):
        order, _n, _t = self._paid()
        self._manual_cancel(order)
        cn = SalesCreditNote.objects.get()
        closed_at = timezone.now()
        SalesCreditNote.objects.filter(pk=cn.pk).update(issued_at=closed_at)
        self._close(self.batch, closed_at)
        self.assertEqual(self._batch_pnl()["reversed_qty"], Decimal("2"))       # issued_at == closed_at: trừ
        SalesCreditNote.objects.filter(pk=cn.pk).update(issued_at=closed_at + timedelta(microseconds=1))
        p = self._batch_pnl()
        self.assertEqual(p["reversed_qty"], Decimal("0"))                        # sau chốt 1µs: không trừ
        self.assertEqual(p["revenue"], Decimal("300000"))

    def test_don_2_lo_1_lo_da_chot_1_lo_chua_chot_moi_lo_tinh_rieng(self):
        small = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=timezone.localdate() - timedelta(days=1), qty=Decimal("1"),
            purchase_rate=Decimal("90000"),
        )
        batch_services.publish_batch(batch=small, actor=None)
        order, _n, _t = self._paid(qty=Decimal("2.5"))     # FEFO: 1 kg lô small + 1,5 kg lô X
        self._close(small, timezone.now() - timedelta(days=1))
        small_before = self._batch_pnl(small)
        x_before = self._batch_pnl(self.batch)
        self.assertEqual(x_before["revenue"], Decimal("225000"))
        self._manual_cancel(order)
        self.assertEqual(self._batch_pnl(small), small_before)      # lô đã chốt: đứng yên
        x = self._batch_pnl(self.batch)                             # lô chưa chốt: đảo
        self.assertEqual((x["revenue"], x["qty_sold"], x["reversed_qty"]), (Decimal("0"), Decimal("0"), Decimal("1.5")))
        cn = SalesCreditNote.objects.get()
        self.assertEqual(cn.lines.count(), 2)
        cur = report_services.period_pnl(year=ym_back(0)[0], month=ym_back(0)[1])
        self.assertEqual(cur["credit_notes"], Decimal("375000"))

    def test_combo_2_lo_thanh_phan_huy_ve_0_moi_lo(self):
        tom = Item.objects.create(code="TOM-QA", name="Tôm thẻ", item_group=self.item.item_group)
        muc = Item.objects.create(code="MUC-QA", name="Mực ống", item_group=self.item.item_group)
        combo = Item.objects.create(code="COMBO-QA", name="Combo hải sản", item_group=self.item.item_group,
                                    item_type=Item.ItemType.BUNDLE)
        today = timezone.localdate()
        for it, price in ((tom, "200000"), (muc, "150000"), (combo, "500000")):
            ItemPrice.objects.create(price_list=self.pl, item=it, rate=Decimal(price), valid_from=today - timedelta(days=1))
        BundleLine.objects.create(bundle=combo, component=tom, qty_per_bundle=Decimal("1"))
        BundleLine.objects.create(bundle=combo, component=muc, qty_per_bundle=Decimal("0.5"))
        lots = {}
        for it, cost in ((tom, "80000"), (muc, "60000")):
            b = batch_services.create_batch(item=it, supplier=self.sup, warehouse=self.wh, received_date=today,
                                            qty=Decimal("20"), purchase_rate=Decimal(cost))
            batch_services.publish_batch(batch=b, actor=None)
            lots[it.code] = b
        order = order_services.create_order(
            customer_phone="0900000666", customer_name="Khách Giả Combo",
            delivery_address="Số 1 Đường Thử", phone="0900000666",
            lines=[{"item_code": "COMBO-QA", "qty": Decimal("2")}],
        )
        payment_services.confirm_payment(order=order, bank_txn_id="TXN-COMBO", amount=order.total_amount,
                                         received_at=timezone.now())
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("1000000"))
        pre = {k: self._batch_pnl(b) for k, b in lots.items()}
        self._manual_cancel(order)
        cn = SalesCreditNote.objects.get()
        self.assertEqual(cn.amount, Decimal("1000000"))
        self.assertEqual(cn.lines.count(), 2)
        self.assertEqual({l.batch_id for l in cn.lines.all()}, {b.pk for b in lots.values()})
        for k, b in lots.items():
            p = self._batch_pnl(b)
            self.assertEqual((p["revenue"], p["qty_sold"]), (Decimal("0"), Decimal("0")), k)
            self.assertEqual(p["reversed_qty"], pre[k]["qty_sold"], k)
        cur = report_services.period_pnl(year=ym_back(0)[0], month=ym_back(0)[1])
        self.assertEqual(cur["revenue"], Decimal("0"))       # hoá đơn 1.000.000 - đảo 1.000.000
        self.assertEqual(cur["cogs"], Decimal("0"))          # giá vốn 2*80000 + 1*60000 đã đảo hết
        self.assertEqual(cur["profit"], Decimal("0"))
