"""
P8 Lô 4 — SR-13: lãi lỗ theo lô / theo kỳ / dashboard trừ chứng từ đảo; phiếu hoàn không trừ hai lần
(F04, BR-BC-03, BR-BC-04, BR-HT-06, BR-HT-10). R6 chuyển thành test chính thức. Dữ liệu hoàn toàn giả.

Lô X 100 kg giá mua 110.000 (không chi phí phụ -> giá vốn 110.000/kg), giá bán 150.000/kg.
"""
import datetime
import json
import uuid
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.common.tests.fixtures import client_for
from apps.reports import services as report_services
from apps.sales.credit_notes.tests.base import CreditNoteBase, find_keys
from apps.inventory.models import Batch
from apps.sales.models import Refund, SalesCreditNote, SalesInvoice
from apps.sales.refunds import services as refund_services
from apps.accounts import roles

SEP = datetime.datetime(2026, 9, 15, 8, 0, tzinfo=datetime.timezone.utc)
OCT = datetime.datetime(2026, 10, 10, 8, 0, tzinfo=datetime.timezone.utc)


def cancel_url(pk):
    return f"/api/sales/orders/{pk}/cancel/"


class SR13PnlCreditNoteTests(CreditNoteBase):
    def _pnl(self):
        self.batch.refresh_from_db()
        return report_services.batch_pnl(batch=self.batch)

    def _issued_at(self, invoice, when):
        SalesInvoice.objects.filter(pk=invoice.pk).update(issued_at=when)

    def _credit_at(self, cn, when):
        SalesCreditNote.objects.filter(pk=cn.pk).update(issued_at=when)

    def _cancel(self, order, user=None):
        resp = client_for(user or self.chu).post(
            cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

    # ---- AC1 (R6) -----------------------------------------------------------------------
    def test_sr13_ac1_r6_batch_pnl_sau_tu_huy_doanh_thu_ve_0(self):
        order, _note, task = self._paid()
        before = self._pnl()
        self.assertEqual(before["revenue"], Decimal("300000"))  # đối chứng: trước huỷ có doanh thu
        self.assertEqual(before["reversed_qty"], Decimal("0"))

        self._auto_cancel(task)

        p = self._pnl()
        self.assertEqual(p["revenue"], Decimal("0"))
        self.assertEqual(p["qty_sold"], Decimal("0"))
        self.assertEqual(p["reversed_qty"], Decimal("2"))
        self.assertEqual(p["reversed_revenue"], Decimal("300000"))
        # kg hoàn về lô (hàng còn ở kho) -> tồn 100, chi phí lô không đổi -> lỗ đúng bằng chi phí
        self.assertEqual(p["profit"], -p["total_cost"])

    # ---- AC2 ----------------------------------------------------------------------------
    def test_sr13_ac2_ban_lai_kg_da_hoan_khong_cong_hai_lan(self):
        order, _note, task = self._paid()
        self._auto_cancel(task)
        self._paid(phone="0900000456", name="Khách Giả B", qty=Decimal("2"))  # bán lại 2 kg

        p = self._pnl()
        self.assertEqual(p["qty_sold"], Decimal("2"))       # không phải 4
        self.assertEqual(p["revenue"], Decimal("300000"))   # không phải 600.000
        self.assertEqual(p["reversed_qty"], Decimal("2"))
        self.assertEqual(p["reversed_revenue"], Decimal("300000"))

    # ---- AC3 ----------------------------------------------------------------------------
    def _sep_invoice_cancelled_in_oct(self):
        """Hoá đơn tháng 9 (2 kg, 300.000, giá vốn 220.000), huỷ tháng 10; kèm 1 hoá đơn tháng 10 (1 kg)."""
        order, _n, _t = self._paid()
        self._issued_at(order.invoice, SEP)
        self._cancel(order)
        cn = SalesCreditNote.objects.get()
        self._credit_at(cn, OCT)
        oct_order, _n2, _t2 = self._paid(phone="0900000456", name="Khách Giả B", qty=Decimal("1"))
        self._issued_at(oct_order.invoice, OCT)
        return order, cn, oct_order

    def test_sr13_ac3_period_pnl_khong_sua_ky_cu_dao_vao_ky_huy(self):
        order, cn, oct_order = self._sep_invoice_cancelled_in_oct()

        sep = report_services.period_pnl(year=2026, month=9)
        self.assertEqual(sep["revenue"], Decimal("300000"))
        self.assertEqual(sep["cogs"], Decimal("220000"))
        self.assertEqual(sep["credit_notes"], Decimal("0"))
        self.assertEqual(sep["cogs_reversed"], Decimal("0"))
        self.assertEqual(sep["profit"], Decimal("80000"))

        octo = report_services.period_pnl(year=2026, month=10)
        self.assertEqual(octo["credit_notes"], Decimal("300000"))
        expected_reversed = sum(x.qty * x.unit_cost for x in cn.lines.all())
        self.assertEqual(expected_reversed, Decimal("220000"))
        self.assertEqual(octo["cogs_reversed"], expected_reversed)
        self.assertEqual(octo["revenue"], Decimal("150000") - Decimal("300000"))
        self.assertEqual(octo["cogs"], Decimal("110000") - Decimal("220000"))
        self.assertEqual(octo["refunds"], Decimal("0"))
        self.assertEqual(octo["profit"], octo["revenue"] - octo["cogs"] - octo["refunds"])

    # ---- AC4 ----------------------------------------------------------------------------
    def _refund(self, invoice, amount, partial, confirmed_at):
        r, _dup = refund_services.create_invoice_refund(
            invoice=invoice, amount=amount, is_partial=partial, reason="", actor=self.chu,
            request_id=uuid.uuid4(),
        )
        refund_services.confirm_refund(refund=r, bank_txn_ref="BANK-GIA-1", actor=self.chu)
        Refund.objects.filter(pk=r.pk).update(confirmed_at=confirmed_at)
        return r

    def test_sr13_ac4_phieu_hoan_cua_hoa_don_da_dao_khong_tru_lan_2(self):
        order, _cn, oct_order = self._sep_invoice_cancelled_in_oct()
        self._refund(order.invoice, Decimal("300000"), False, OCT)

        octo = report_services.period_pnl(year=2026, month=10)
        self.assertEqual(octo["refunds"], Decimal("0"))  # đã đảo bằng chứng từ
        self.assertEqual(octo["credit_notes"], Decimal("300000"))

    def test_sr13_ac4_phieu_hoan_mot_phan_hoa_don_khong_chung_tu_van_tru(self):
        order, _cn, oct_order = self._sep_invoice_cancelled_in_oct()
        self._refund(order.invoice, Decimal("300000"), False, OCT)
        self._refund(oct_order.invoice, Decimal("50000"), True, OCT)  # hoàn một phần khi giao thiếu

        octo = report_services.period_pnl(year=2026, month=10)
        self.assertEqual(octo["refunds"], Decimal("50000"))
        self.assertEqual(
            octo["profit"], octo["revenue"] - octo["cogs"] - Decimal("50000"),
        )

    # ---- AC5 ----------------------------------------------------------------------------
    def test_sr13_ac5_dashboard_revenue_today_tru_chung_tu_dao_hom_nay(self):
        order, _n, task = self._paid()
        self._paid(phone="0900000456", name="Khách Giả B", qty=Decimal("1"))  # 150.000 hôm nay
        resp = client_for(self.chu).get("/api/dashboard/summary/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["kpis"]["revenue_today"], 450000.0)

        self._auto_cancel(task)
        resp = client_for(self.chu).get("/api/dashboard/summary/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["kpis"]["revenue_today"], 150000.0)  # 450.000 − 300.000

    def test_sr13_ac5_chung_tu_dao_hom_qua_khong_tru_hom_nay(self):
        order, _n, task = self._paid()
        self._auto_cancel(task)
        cn = SalesCreditNote.objects.get()
        self._credit_at(cn, timezone.now() - timedelta(days=2))
        resp = client_for(self.chu).get("/api/dashboard/summary/")
        self.assertEqual(resp.json()["kpis"]["revenue_today"], 300000.0)  # hoá đơn hôm nay, chứng từ kỳ khác

    # ---- AC6 ----------------------------------------------------------------------------
    def test_sr13_ac6_ma_tran_quyen_bao_cao_khong_doi(self):
        order, _n, task = self._paid()
        self._auto_cancel(task)
        urls = (
            f"/api/reports/batch/{self.batch.batch_id}/",
            f"/api/reports/period/?year={timezone.localdate().year}&month={timezone.localdate().month}",
        )
        for url in urls:
            resp = client_for(self.chu).get(url)
            self.assertEqual(resp.status_code, 200, url)
            for user in (self.ql, self.kho, self.giao, self.cs1):
                self.assertEqual(client_for(user).get(url).status_code, 403, f"{user.username} {url}")
            self.assertEqual(client_for(None).get(url).status_code, 401, url)

        body = client_for(self.chu).get(urls[0]).json()
        self.assertEqual(Decimal(str(body["reversed_qty"])), Decimal("2"))
        self.assertEqual(Decimal(str(body["reversed_revenue"])), Decimal("300000"))
        period = client_for(self.chu).get(urls[1]).json()
        self.assertEqual(Decimal(str(period["credit_notes"])), Decimal("300000"))

    def test_sr13_ac6_dashboard_ma_tran_va_khong_lo_gia_von(self):
        order, _n, task = self._paid()
        self._auto_cancel(task)
        expected = {roles.OWNER: 200, "ql": 200, "kho": 200, "giao": 403, "cs1": 403}
        users = {roles.OWNER: self.chu, "ql": self.ql, "kho": self.kho, "giao": self.giao, "cs1": self.cs1}
        ok = 0
        for key, status in expected.items():
            resp = client_for(users[key]).get("/api/dashboard/summary/")
            self.assertEqual(resp.status_code, status, key)
            if status == 200:
                ok += 1
                if key != roles.OWNER:
                    self.assertNotIn("unit_cost", json.dumps(resp.json()))
                    self.assertEqual(find_keys(resp.json(), {"unit_cost", "cogs", "cogs_reversed"}), set())
        self.assertEqual(client_for(None).get("/api/dashboard/summary/").status_code, 401)
        self.assertEqual(ok, 3)


SEP_END = datetime.datetime(2026, 9, 20, 8, 0, tzinfo=datetime.timezone.utc)


class SR13D1PhuongAnBTests(CreditNoteBase):
    """
    D1 (Duy quyết 30/09, phương án B, BR-HT-06): KHÔNG sửa kỳ cũ.
    Hoá đơn 300.000 (2 kg, giá vốn 220.000) ghi tháng 9; hoàn một phần 50.000 xác nhận tháng 9;
    huỷ cả đơn tháng 10.
    """

    def _sep_invoice_partial_refund(self, refund_amount=Decimal("50000"), invoice_at=SEP, refund_at=SEP_END):
        order, _n, _t = self._paid()
        SalesInvoice.objects.filter(pk=order.invoice.pk).update(issued_at=invoice_at)
        r, _dup = refund_services.create_invoice_refund(
            invoice=order.invoice, amount=refund_amount, is_partial=True, reason="", actor=self.chu,
            request_id=uuid.uuid4(),
        )
        refund_services.confirm_refund(refund=r, bank_txn_ref="BANK-GIA-2", actor=self.chu)
        Refund.objects.filter(pk=r.pk).update(confirmed_at=refund_at)
        return order, r

    def _cancel_in_oct(self, order):
        resp = client_for(self.chu).post(
            cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        cn = SalesCreditNote.objects.get(sales_invoice__sales_order=order)
        SalesCreditNote.objects.filter(pk=cn.pk).update(issued_at=OCT)
        cn.refresh_from_db()
        return cn

    def test_sr13_d1_ky_cu_khong_doi_ky_huy_dao_phan_con_lai(self):
        order, _r = self._sep_invoice_partial_refund()
        sep_before = report_services.period_pnl(year=2026, month=9)
        self.assertEqual(sep_before["refunds"], Decimal("50000"))
        self.assertEqual(sep_before["profit"], Decimal("30000"))

        self._cancel_in_oct(order)

        sep_after = report_services.period_pnl(year=2026, month=9)
        self.assertEqual(sep_after, sep_before)  # KHÔNG sửa kỳ cũ (mọi khoá)

        octo = report_services.period_pnl(year=2026, month=10)
        self.assertEqual(octo["credit_notes"], Decimal("250000"))  # 300.000 − 50.000 đã hoàn trước
        self.assertEqual(octo["cogs_reversed"], Decimal("220000"))  # giữ nguyên
        self.assertEqual(octo["refunds"], Decimal("0"))
        self.assertEqual(octo["revenue"], Decimal("-250000"))
        self.assertEqual(octo["profit"], Decimal("-30000"))
        # tổng hai kỳ: đơn huỷ toàn bộ nên lãi ròng 0, doanh thu − hoàn = 0
        self.assertEqual(sep_after["profit"] + octo["profit"], Decimal("0"))
        self.assertEqual(
            sep_after["revenue"] + octo["revenue"] - sep_after["refunds"] - octo["refunds"], Decimal("0"),
        )

    def test_sr13_d1_khong_hoan_truoc_nhu_cu(self):
        order, _n, _t = self._paid()
        SalesInvoice.objects.filter(pk=order.invoice.pk).update(issued_at=SEP)
        cn = self._cancel_in_oct(order)
        octo = report_services.period_pnl(year=2026, month=10)
        self.assertEqual(cn.amount, Decimal("300000"))
        self.assertEqual(octo["credit_notes"], Decimal("300000"))
        self.assertEqual(octo["revenue"], Decimal("-300000"))

    def test_sr13_d1_hoan_sau_huy_khong_tru_hai_lan(self):
        order, _r = self._sep_invoice_partial_refund()
        self._cancel_in_oct(order)
        # hoàn nốt 250.000 SAU khi huỷ (confirmed_at >= issued_at) -> phiếu chỉ là dòng tiền
        r2, _dup = refund_services.create_invoice_refund(
            invoice=order.invoice, amount=Decimal("250000"), is_partial=False, reason="", actor=self.chu,
            request_id=uuid.uuid4(),
        )
        refund_services.confirm_refund(refund=r2, bank_txn_ref="BANK-GIA-3", actor=self.chu)
        Refund.objects.filter(pk=r2.pk).update(confirmed_at=OCT + timedelta(days=1))

        sep = report_services.period_pnl(year=2026, month=9)
        octo = report_services.period_pnl(year=2026, month=10)
        self.assertEqual(sep["refunds"], Decimal("50000"))   # phiếu trước huỷ vẫn ở kỳ của nó
        self.assertEqual(octo["refunds"], Decimal("0"))      # phiếu sau huỷ không trừ lần hai
        self.assertEqual(octo["credit_notes"], Decimal("250000"))

    def test_sr13_d1_da_hoan_du_truoc_huy_thi_so_dao_khong_am(self):
        order, _r = self._sep_invoice_partial_refund(refund_amount=Decimal("300000"))
        self._cancel_in_oct(order)
        octo = report_services.period_pnl(year=2026, month=10)
        self.assertEqual(octo["credit_notes"], Decimal("0"))  # max(0, 300.000 − 300.000), không âm
        self.assertEqual(report_services.period_pnl(year=2026, month=9)["refunds"], Decimal("300000"))

    def test_sr13_d1_backfill_ca_co_hoan_truoc(self):
        """E1 (Duy 30/09): chứng từ lập bù ghi vào kỳ chạy lệnh; D1-B tự trừ phần đã hoàn trước đó."""
        from io import StringIO

        from django.core.management import call_command

        # hoá đơn + phiếu hoàn ở tháng 8 (khác kỳ hiện tại của lệnh, bất kể ngày chạy test)
        aug_end = AUG + timedelta(days=5)
        order, _r = self._sep_invoice_partial_refund(invoice_at=AUG, refund_at=aug_end)
        sep_before = report_services.period_pnl(year=2026, month=8)
        self.assertEqual(sep_before["refunds"], Decimal("50000"))
        # đơn huỷ theo luồng CŨ (trước P8): huỷ xong xoá chứng từ đảo
        resp = client_for(self.chu).post(
            cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        SalesCreditNote.objects.all().delete()

        call_command("backfill_credit_notes", "--apply", stdout=StringIO())

        cn = SalesCreditNote.objects.get()
        self.assertTrue(cn.backfilled)
        self.assertGreater(cn.issued_at, aug_end)                       # ghi vào kỳ chạy lệnh
        self.assertEqual(report_services.period_pnl(year=2026, month=8), sep_before)  # kỳ cũ giữ nguyên
        d = timezone.localdate()
        cur = report_services.period_pnl(year=d.year, month=d.month)
        self.assertEqual(cur["credit_notes"], Decimal("250000"))         # 300.000 − 50.000 đã hoàn trước
        self.assertEqual(cur["refunds"], Decimal("0"))


AUG = datetime.datetime(2026, 8, 15, 8, 0, tzinfo=datetime.timezone.utc)


class SR14E1E2BackfillReportTests(CreditNoteBase):
    """E1/E2 (Duy 30/09, "báo cáo đã qua thì không được sửa số")."""

    def _legacy_cancel(self, *, phone=None, name=None, invoice_at=None):
        kw = {}
        if phone:
            kw["phone"], kw["name"] = phone, name
        order, _n, _t = self._paid(**kw)
        if invoice_at is not None:
            SalesInvoice.objects.filter(pk=order.invoice.pk).update(issued_at=invoice_at)
        resp = client_for(self.chu).post(
            cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        SalesCreditNote.objects.filter(sales_invoice__sales_order=order).delete()  # giả lập luồng cũ
        return order

    def _apply(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("backfill_credit_notes", "--apply", stdout=out)
        return out.getvalue()

    def _close_batch(self, closed_at):
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.CLOSED, closed_at=closed_at)
        self.batch.refresh_from_db()

    def _batch_pnl(self):
        self.batch.refresh_from_db()
        return report_services.batch_pnl(batch=self.batch)

    # (a)
    def test_sr14_e1_don_huy_thang_8_bao_cao_thang_8_giu_nguyen_ky_hien_tai_nhan_dieu_chinh(self):
        order = self._legacy_cancel(invoice_at=AUG)
        from apps.accounts.models import AuditLog
        AuditLog.objects.filter(action="cancel_paid_order", object_id=str(order.pk)).update(created_at=AUG)
        aug_before = report_services.period_pnl(year=2026, month=8)
        self.assertEqual(aug_before["revenue"], Decimal("300000"))

        self._apply()

        self.assertEqual(report_services.period_pnl(year=2026, month=8), aug_before)  # mọi khoá
        d = timezone.localdate()
        cur = report_services.period_pnl(year=d.year, month=d.month)
        self.assertEqual(cur["credit_notes"], Decimal("300000"))
        self.assertEqual(cur["cogs_reversed"], Decimal("220000"))
        self.assertEqual(cur["revenue"], Decimal("-300000"))

    # (b)
    def test_sr14_e2_lo_da_chot_batch_pnl_khong_doi_sau_apply(self):
        self._legacy_cancel()
        self._close_batch(timezone.now() - timedelta(days=1))
        before = self._batch_pnl()
        self.assertEqual(before["revenue"], Decimal("300000"))  # đối chứng: đơn huỷ cũ còn tính (lỗi F04 cũ)

        self._apply()

        self.assertEqual(SalesCreditNote.objects.count(), 1)
        self.assertEqual(self._batch_pnl(), before)             # mọi khoá giữ nguyên
        d = timezone.localdate()
        cur = report_services.period_pnl(year=d.year, month=d.month)
        self.assertEqual(cur["credit_notes"], Decimal("300000"))  # vẫn vào kỳ hiện tại

    # (c)
    def test_sr14_e2_lo_chua_chot_batch_pnl_tru_nhu_cu(self):
        self._legacy_cancel()
        self._apply()
        p = self._batch_pnl()
        self.assertEqual(p["revenue"], Decimal("0"))
        self.assertEqual(p["qty_sold"], Decimal("0"))
        self.assertEqual(p["reversed_qty"], Decimal("2"))
        self.assertEqual(p["reversed_revenue"], Decimal("300000"))

    # (d)
    def test_sr14_e2_luong_huy_thuong_lo_chua_chot_khong_doi(self):
        order, _n, task = self._paid()
        self._auto_cancel(task)
        p = self._batch_pnl()
        self.assertEqual(p["revenue"], Decimal("0"))
        self.assertEqual(p["reversed_qty"], Decimal("2"))

    def test_sr14_e2_huy_thuong_truoc_khi_chot_van_tru_sau_khi_chot(self):
        order, _n, task = self._paid()
        self._auto_cancel(task)                                # chứng từ lập TRƯỚC lúc chốt
        self._close_batch(timezone.now() + timedelta(hours=1))
        p = self._batch_pnl()
        self.assertEqual(p["revenue"], Decimal("0"))
        self.assertEqual(p["reversed_qty"], Decimal("2"))

    def test_sr14_e2_chung_tu_lap_sau_chot_khong_doi_lai_lo_nhung_vao_ky_hien_tai(self):
        order, _n, _t = self._paid()
        self._close_batch(timezone.now() - timedelta(days=1))
        before = self._batch_pnl()
        client_for(self.chu).post(
            cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        self.assertEqual(SalesCreditNote.objects.count(), 1)
        self.assertEqual(self._batch_pnl(), before)
        d = timezone.localdate()
        self.assertEqual(report_services.period_pnl(year=d.year, month=d.month)["credit_notes"], Decimal("300000"))

    # (e)
    def test_sr14_e1_apply_hai_lan_lan_hai_khong_tao_moi(self):
        self._legacy_cancel()
        self._apply()
        self.assertEqual(SalesCreditNote.objects.count(), 1)
        first = SalesCreditNote.objects.get()
        self._apply()
        self.assertEqual(SalesCreditNote.objects.count(), 1)
        self.assertEqual(SalesCreditNote.objects.get().issued_at, first.issued_at)
