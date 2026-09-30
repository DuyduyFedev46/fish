"""QA P8 Lô 5 — kỳ (period_pnl) không đổi khi trả NCC; lô đã chốt lãi lỗ không đổi. Dữ liệu giả."""
from decimal import Decimal

from django.utils import timezone

from apps.common.tests.fixtures import client_for
from apps.inventory.batches.tests.test_p8_lo5_qa_edges import Base
from apps.inventory.models import Batch
from apps.reports import services as report_services


class QaPeriodTests(Base):
    def test_qa_period_pnl_khong_doi_khi_tra_ncc_va_huy_lo_qua_han(self):
        self._paid_order(phone="0900000111", txn="FTQA5PERIOD1")
        today = timezone.localdate()
        before = report_services.period_pnl(year=today.year, month=today.month)
        self.assertGreater(before["revenue"], 0)
        self._expire()
        self.assertEqual(self._post_return(qty="50", supplier_refund_amount="3000000").status_code, 200)
        self.assertEqual(report_services.period_pnl(year=today.year, month=today.month), before)
        self.assertEqual(self.c_chu.post(self.cancel_url, {"confirm_qty": "48"}, format="json").status_code, 200)
        after = report_services.period_pnl(year=today.year, month=today.month)
        # kỳ chỉ tính giá vốn hàng đã bán: huỷ lô/ trả NCC không đổi doanh thu/gvhb; không được đổi doanh thu
        self.assertEqual(after["revenue"], before["revenue"])
        self.assertEqual(after["cogs"], before["cogs"])
        # API kỳ cho quan_ly không có khoá tiền NCC
        r = client_for(self.ql).get(f"/api/reports/period/?year={today.year}&month={today.month}")
        if r.status_code == 200:
            self.assertNotIn("supplier_refund", r.content.decode())
