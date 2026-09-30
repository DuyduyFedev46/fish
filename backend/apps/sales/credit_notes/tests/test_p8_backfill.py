"""
P8 Lô 4 — SR-14: lệnh `backfill_credit_notes` lập bù chứng từ đảo cho đơn đã huỷ trước P8.
Chỉ chạy trên DB test, dữ liệu giả. Output lệnh không có tên/SĐT/địa chỉ/giá vốn.
"""
import datetime
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for
from apps.inventory.models import Batch
from apps.sales.credit_notes.tests.base import (
    SENTINEL_ADDRESS, SENTINEL_NAME, SENTINEL_PHONE, CreditNoteBase,
)
from apps.sales.models import SalesCreditNote, SalesInvoice, SalesOrder

OLD = datetime.datetime(2026, 9, 1, 8, 0, tzinfo=datetime.timezone.utc)


class SR14BackfillTests(CreditNoteBase):
    def _legacy_cancelled(self, **kw):
        """Đơn huỷ theo luồng CŨ (trước P8): huỷ xong, xoá chứng từ đảo để giả lập chưa có."""
        order, _note, task = self._paid(**kw)
        client_for(self.chu).post(
            f"/api/sales/orders/{order.pk}/cancel/", {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        SalesCreditNote.objects.filter(sales_invoice__sales_order=order).delete()
        return order

    def _run(self, *args):
        out = StringIO()
        call_command("backfill_credit_notes", *args, stdout=out)
        return out.getvalue()

    # ---- AC1 ----------------------------------------------------------------------------
    def test_sr14_ac1_dry_run_mac_dinh_chi_in_khong_ghi(self):
        o1 = self._legacy_cancelled()
        o2 = self._legacy_cancelled(phone="0900000456", name="Khách Giả B")
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.CLOSED)
        audits_before = AuditLog.objects.count()

        out = self._run()

        self.assertEqual(SalesCreditNote.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), audits_before)
        self.assertIn(o1.code, out)
        self.assertIn(o2.code, out)
        self.assertIn(o1.invoice.code, out)
        self.assertIn("300000", out.replace(".", "").replace(",", ""))
        self.assertIn(self.batch.batch_id, out)          # lô CLOSED bị ảnh hưởng
        self.assertIn("2", out)                          # số đơn

    def test_sr14_ac1_khong_bao_lo_chua_closed_va_bo_qua_don_da_co_chung_tu(self):
        o_old = self._legacy_cancelled()
        order, _n, task = self._paid(phone="0900000456", name="Khách Giả B")
        self._auto_cancel(task)  # đã có chứng từ (luồng mới)
        out = self._run()
        self.assertIn(o_old.code, out)
        self.assertNotIn(order.code, out)
        self.assertIn("Không có lô CLOSED bị ảnh hưởng", out)   # lô còn ACTIVE, không cần cảnh báo

    def test_sr14_ac1_khong_lap_cho_don_khong_huy_hoac_hoa_don_khong_issued(self):
        order, _n, _t = self._paid()          # đơn PAID, chưa huỷ
        out = self._run("--apply")
        self.assertEqual(SalesCreditNote.objects.count(), 0)
        self.assertNotIn(order.code, out)

    # ---- AC2 (đổi theo Duy 30/09, E1: issued_at = thời điểm chạy lệnh, KHÔNG lấy ngày audit huỷ gốc) ----
    def test_sr14_ac2_apply_lap_chung_tu_issued_at_la_luc_chay_lenh_created_by_none(self):
        order = self._legacy_cancelled()
        audit = AuditLog.objects.filter(action="cancel_paid_order", object_id=str(order.pk)).order_by("-id").first()
        AuditLog.objects.filter(pk=audit.pk).update(created_at=OLD)
        before = timezone.now()

        self._run("--apply")

        cn = SalesCreditNote.objects.get()
        self.assertGreaterEqual(cn.issued_at, before)            # KHÔNG phải ngày huỷ gốc (OLD)
        self.assertLessEqual(cn.issued_at, timezone.now())
        self.assertNotEqual(cn.issued_at, OLD)
        self.assertTrue(cn.backfilled)
        self.assertIsNone(cn.created_by)
        self.assertEqual(cn.amount, Decimal("300000"))
        self.assertEqual(cn.lines.count(), 1)
        self.assertTrue(cn.stock_restored)
        self.assertEqual(cn.sales_invoice.status, SalesInvoice.Status.ISSUED)  # hoá đơn không bị sửa

    def test_sr14_ac2_khong_co_audit_van_issued_at_la_luc_chay_lenh(self):
        order = self._legacy_cancelled()
        AuditLog.objects.filter(action="cancel_paid_order", object_id=str(order.pk)).delete()
        before = timezone.now()
        self._run("--apply")
        cn = SalesCreditNote.objects.get()
        self.assertGreaterEqual(cn.issued_at, before)
        self.assertTrue(cn.backfilled)
        self.assertTrue(cn.stock_restored)  # mặc định True khi không có audit

    def test_sr14_ac2_stock_restored_lay_tu_audit(self):
        order = self._legacy_cancelled()
        audit = AuditLog.objects.filter(action="cancel_paid_order", object_id=str(order.pk)).order_by("-id").first()
        changes = dict(audit.changes)
        changes["stock_restored"] = False
        AuditLog.objects.filter(pk=audit.pk).update(changes=changes)
        self._run("--apply")
        self.assertFalse(SalesCreditNote.objects.get().stock_restored)

    def test_sr14_ac2_stock_restored_lay_tu_audit_moi_nhat_khi_co_nhieu_dong(self):
        order = self._legacy_cancelled()
        first = AuditLog.objects.filter(action="cancel_paid_order", object_id=str(order.pk)).get()
        AuditLog.objects.filter(pk=first.pk).update(created_at=OLD)
        newer = AuditLog.objects.create(
            action="cancel_paid_order", model_name=first.model_name, object_id=first.object_id,
            actor=None, changes={"stock_restored": False},
        )
        AuditLog.objects.filter(pk=newer.pk).update(
            created_at=datetime.datetime(2026, 9, 5, 8, 0, tzinfo=datetime.timezone.utc),
        )
        self._run("--apply")
        self.assertFalse(SalesCreditNote.objects.get().stock_restored)  # dòng audit mới nhất thắng

    # ---- AC3 ----------------------------------------------------------------------------
    def test_sr14_ac3_chay_hai_lan_lan_2_khong_tao_them(self):
        self._legacy_cancelled()
        self._legacy_cancelled(phone="0900000456", name="Khách Giả B")
        self._run("--apply")
        self.assertEqual(SalesCreditNote.objects.count(), 2)
        out2 = self._run("--apply")
        self.assertEqual(SalesCreditNote.objects.count(), 2)
        self.assertIn("0", out2)

    # ---- AC4 ----------------------------------------------------------------------------
    def test_sr14_ac4_output_khong_pii_khong_gia_von(self):
        self._legacy_cancelled()
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.CLOSED)
        for args in ((), ("--apply",), ("--apply",)):
            out = self._run(*args)
            for secret in (SENTINEL_NAME, SENTINEL_PHONE, SENTINEL_ADDRESS, "Khách", "unit_cost", "110000", "220000"):
                self.assertNotIn(secret, out, f"{args}: {secret}")
            for key in COST_KEYS - {"rate"}:
                self.assertNotIn(key, out)


class SR14E2DryRunTests(CreditNoteBase):
    """E2 (Duy 30/09): dry-run liệt kê riêng đơn thuộc lô CLOSED — lãi lỗ lô giữ nguyên."""

    def test_sr14_e2_dry_run_liet_ke_rieng_don_thuoc_lo_closed(self):
        order, _n, _t = self._paid()
        client_for(self.chu).post(
            f"/api/sales/orders/{order.pk}/cancel/", {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        SalesCreditNote.objects.all().delete()
        Batch.objects.filter(pk=self.batch.pk).update(
            status=Batch.Status.CLOSED, closed_at=timezone.now() - datetime.timedelta(days=1),
        )
        out = StringIO()
        call_command("backfill_credit_notes", stdout=out)
        text = out.getvalue()
        self.assertIn("lãi lỗ lô giữ nguyên, điều chỉnh vào kỳ hiện tại", text)
        closed_section = text.split("lãi lỗ lô giữ nguyên, điều chỉnh vào kỳ hiện tại", 1)[1]
        self.assertIn(order.code, closed_section)
        self.assertIn(self.batch.batch_id, closed_section)
        for secret in (SENTINEL_NAME, SENTINEL_PHONE, SENTINEL_ADDRESS, "unit_cost", "110000", "220000"):
            self.assertNotIn(secret, text)
        self.assertEqual(SalesCreditNote.objects.count(), 0)
