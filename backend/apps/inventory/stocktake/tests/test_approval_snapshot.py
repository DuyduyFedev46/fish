"""
Duyệt kiểm kê áp đúng chênh lệch đã chụp lúc nhập số (BR-KK-09, ĐỀ XUẤT — chờ Duy chốt), phiếu rỗng (L3),
`line_index` ở lỗi BR-KK-04 (L4), và tạo phiếu qua AI không mang `lines` (M1).
"""
from decimal import Decimal

from apps.common.audit import set_ai_audit_scope
from apps.inventory.models import StockLedgerEntry, StockReconciliation, StockReconciliationLine
from apps.inventory.stock import services as stock

from .base import URL, StocktakeApiBase, line


class ApproveSnapshotTests(StocktakeApiBase):
    def approve(self, user, rec):
        return self.api(user).post(f"{URL}{rec['id']}/approve/")

    def sell(self, batch, qty):
        stock.record_movement(batch=batch, qty_change=-Decimal(qty), movement_type=StockLedgerEntry.MovementType.SALE)

    def test_br_kk_09_sale_between_count_and_approval_keeps_counted_difference(self):
        """Đếm 48 / tồn 50 (chênh -2), bán 5, duyệt -> tồn 43, sổ -2 (không bơm +3)."""
        rec = self.make_draft(self.warehouse_staff, [line(self.batch, "48", "hao hụt")])
        self.assertEqual(rec["lines"][0]["difference_qty"], "-2.000")
        self.sell(self.batch, "5")
        resp = self.approve(self.owner, rec)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("43.000"))
        entry = StockLedgerEntry.objects.get(movement_type="RECONCILE")
        self.assertEqual(entry.qty_change, Decimal("-2.000"))
        saved = StockReconciliationLine.objects.get(reconciliation_id=rec["id"])
        self.assertEqual(saved.system_qty, Decimal("50.000"))
        self.assertEqual(saved.difference_qty, Decimal("-2.000"))
        self.assertEqual(resp.json()["lines"][0]["difference_qty"], "-2.000")

    def test_br_kk_09_shortage_without_reason_is_not_blocked_by_later_sale(self):
        """Đếm 49 không lý do (chênh -1), bán 5, duyệt -> không kẹt 400 BR-KK-04 sai."""
        rec = self.make_draft(self.warehouse_staff, [line(self.batch, "49")])
        self.sell(self.batch, "5")
        resp = self.approve(self.owner, rec)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("44.000"))

    def test_br_kk_09_surplus_snapshot_with_reason_is_applied_as_captured(self):
        rec = self.make_draft(self.warehouse_staff, [line(self.batch, "52", "cân lại")])
        self.sell(self.batch, "5")
        self.assertEqual(self.approve(self.owner, rec).status_code, 200)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("47.000"))

    def test_br_kk_09_would_go_negative_is_400_with_code_and_nothing_written(self):
        """Chênh -2 nhưng lô đã bán hết còn 1 kg -> 400 RECON_STOCK_INSUFFICIENT, không ghi sổ, phiếu vẫn DRAFT."""
        rec = self.make_draft(self.warehouse_staff, [line(self.batch2, "28", "hao"), line(self.batch, "48", "hao")])
        self.sell(self.batch, "49")
        resp = self.approve(self.owner, rec)
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "RECON_STOCK_INSUFFICIENT")
        self.assertEqual(body["line_index"], 1)
        self.assertEqual(StockLedgerEntry.objects.filter(movement_type="RECONCILE").count(), 0)
        self.batch.refresh_from_db()
        self.batch2.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("1.000"))
        self.assertEqual(self.batch2.qty_available, Decimal("30.000"))
        self.assertEqual(self.recon(rec["id"]).status, StockReconciliation.Status.DRAFT)

    def test_approve_legacy_surplus_without_reason_is_400_with_line_index(self):
        """L4: dòng chênh dương thiếu lý do (dữ liệu cũ, không qua service) -> BR-KK-04 kèm line_index."""
        rec = self.make_draft(self.warehouse_staff, [line(self.batch, "49"), line(self.batch2, "29")])
        StockReconciliationLine.objects.filter(reconciliation_id=rec["id"], batch=self.batch2).update(
            difference_qty=Decimal("2"), counted_qty=Decimal("32"), reason="",
        )
        resp = self.approve(self.owner, rec)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-KK-04")
        self.assertEqual(resp.json()["line_index"], 1)
        self.assertEqual(StockLedgerEntry.objects.filter(movement_type="RECONCILE").count(), 0)

    def test_approve_empty_reconciliation_is_400_recon_empty(self):
        """L3."""
        rec = self.create_via_api(self.warehouse_staff)
        resp = self.approve(self.owner, rec)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_EMPTY")
        self.assertEqual(self.recon(rec["id"]).status, StockReconciliation.Status.DRAFT)

    def test_approve_response_still_has_no_cost_after_snapshot_apply(self):
        rec = self.make_draft(self.warehouse_staff)
        self.assertNoCostLeak(self.approve(self.owner, rec))


class AiCreateIgnoresLinesTests(StocktakeApiBase):
    """M1: lệnh AI `inventory.stockreconciliation.create` chỉ có count_date, note; `lines` bị bỏ."""

    def test_create_from_ai_dispatch_drops_lines(self):
        payload = {"count_date": str(self.today), "note": "AI soạn", "lines": [line(self.batch, "48", "x")]}
        with set_ai_audit_scope(ai_actor=self.manager, level="C"):
            resp = self.api(self.warehouse_staff).post(URL, payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["lines"], [])
        self.assertEqual(StockReconciliationLine.objects.count(), 0)

    def test_create_from_ui_keeps_lines(self):
        payload = {"count_date": str(self.today), "note": "", "lines": [line(self.batch, "48", "x")]}
        resp = self.api(self.warehouse_staff).post(URL, payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(len(resp.json()["lines"]), 1)

    def test_manager_whose_ai_drafted_cannot_launder_counts_through_confirmer(self):
        """Mức C: Y xác nhận, X (chủ AI) không có cách nào để phiếu mang số đếm do AI của X soạn."""
        payload = {"count_date": str(self.today), "note": "", "lines": [line(self.batch, "10", "x")]}
        with set_ai_audit_scope(ai_actor=self.manager, level="C"):
            rec = self.api(self.warehouse_staff).post(URL, payload, format="json").json()
        resp = self.api(self.manager).post(f"{URL}{rec['id']}/approve/")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_EMPTY")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("50.000"))
