import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Item, ItemGroup
from apps.common.exceptions import BusinessError
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, ReturnToStock, StockLedgerEntry, Warehouse
from apps.purchasing.models import PurchaseCost, PurchaseCostAllocation, Supplier
from apps.reports import services
from apps.sales.models import (
    Customer,
    Refund,
    SalesInvoice,
    SalesInvoiceLine,
    SalesInvoiceLineBatch,
    SalesOrder,
)


def _dt(y, m, d, h=8):
    return datetime.datetime(y, m, d, h, 0, tzinfo=datetime.timezone.utc)


class ReportsServiceTests(TestCase):
    """
    Dữ liệu dựng trực tiếp qua ORM (không gọi apps.sales.orders/payments services) để tránh phụ
    thuộc chéo — theo đúng yêu cầu sở hữu file của agent này.
    """

    def setUp(self):
        self.user = User.objects.create_user("chu", password="x")
        self.g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=self.g)
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.customer = Customer.objects.create(phone="0900000002", name="Khách B")

        # Lô: 100kg, giá mua 80.000đ/kg -> giá mua = 8.000.000đ
        self.batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=datetime.date(2026, 9, 1), qty=Decimal("100"),
            purchase_rate=Decimal("80000"),
        )
        self.batch.status = Batch.Status.SELLING
        self.batch.save(update_fields=["status"])

        # Chi phí phân bổ 200.000đ -> landed_unit_cost = (8.000.000+200.000)/100 = 82.000
        cost = PurchaseCost.objects.create(
            cost_type=PurchaseCost.CostType.ICE, amount=Decimal("200000"),
            allocation_method=PurchaseCost.AllocationMethod.BY_QTY,
            incurred_date=datetime.date(2026, 9, 1), created_by=self.user,
        )
        PurchaseCostAllocation.objects.create(
            purchase_cost=cost, batch=self.batch, allocated_amount=Decimal("200000"),
        )
        batch_services.recompute_landed_cost(batch=self.batch, actor=self.user)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.landed_unit_cost, Decimal("82000"))

    def _make_invoice(self, *, code, issued_at, qty_sold, sell_rate, unit_cost, amount=None):
        order = SalesOrder.objects.create(
            code=f"SO-{code}", customer=self.customer, status=SalesOrder.Status.PROCESSING,
            delivery_address="123 đường A", phone=self.customer.phone,
            total_amount=amount or (qty_sold * sell_rate),
        )
        invoice = SalesInvoice.objects.create(
            code=code, sales_order=order, customer=self.customer, issued_at=issued_at,
            amount=amount or (qty_sold * sell_rate), status=SalesInvoice.Status.ISSUED,
        )
        line = SalesInvoiceLine.objects.create(
            invoice=invoice, item=self.item, qty=qty_sold, rate=sell_rate,
            amount=qty_sold * sell_rate,
        )
        SalesInvoiceLineBatch.objects.create(
            invoice_line=line, batch=self.batch, component_item=self.item,
            qty=qty_sold, unit_cost=unit_cost,
        )
        return invoice

    # --- batch_pnl --------------------------------------------------------

    def test_batch_pnl_computes_profit_with_shrinkage_and_damage(self):
        # Bán 60kg với giá 120.000đ/kg -> doanh thu = 7.200.000đ
        self._make_invoice(
            code="INV-0001", issued_at=_dt(2026, 9, 5), qty_sold=Decimal("60"),
            sell_rate=Decimal("120000"), unit_cost=Decimal("80000"),  # snapshot cũ, KHÔNG dùng
        )
        # Hao hụt kiểm kê: -2kg
        StockLedgerEntry.objects.create(
            batch=self.batch, movement_type=StockLedgerEntry.MovementType.RECONCILE,
            qty_change=Decimal("-2"), reference="KK-1", created_by=self.user,
        )
        # Hàng hỏng đã duyệt huỷ bỏ: 3kg
        ReturnToStock.objects.create(
            batch=self.batch, qty=Decimal("3"), decision=ReturnToStock.Decision.WRITE_OFF,
            status=ReturnToStock.Status.APPROVED, created_by=self.user, approved_by=self.user,
        )

        result = services.batch_pnl(batch=self.batch)

        self.assertEqual(result["revenue"], Decimal("7200000"))          # 60 × 120.000
        self.assertEqual(result["purchase_cost"], Decimal("8000000"))    # 100 × 80.000
        self.assertEqual(result["allocated_cost"], Decimal("200000"))
        self.assertEqual(result["shrinkage_qty"], Decimal("2"))
        self.assertEqual(result["shrinkage_cost"], Decimal("164000"))    # 2 × 82.000 (hiện hành)
        self.assertEqual(result["damage_qty"], Decimal("3"))
        self.assertEqual(result["damage_cost"], Decimal("246000"))       # 3 × 82.000 (hiện hành)
        self.assertEqual(result["total_cost"], Decimal("8610000"))
        self.assertEqual(result["profit"], Decimal("-1410000"))          # lỗ vì lô chưa bán hết
        self.assertTrue(result["provisional"])                          # chưa CLOSED (BR-BC-05)

    def test_batch_pnl_not_provisional_when_closed(self):
        self.batch.status = Batch.Status.CLOSED
        self.batch.closed_at = timezone.now()
        self.batch.save(update_fields=["status", "closed_at"])
        result = services.batch_pnl(batch=self.batch)
        self.assertFalse(result["provisional"])

    def test_batch_pnl_requires_batch(self):
        with self.assertRaises(BusinessError):
            services.batch_pnl(batch=None)

    def test_batch_pnl_uses_current_landed_cost_not_line_snapshot(self):
        # unit_cost ảnh chụp trên dòng (80.000) khác landed_unit_cost hiện hành
        # (82.000) — BR-BC-04: báo cáo lô PHẢI dùng số hiện hành cho hao hụt/hàng hỏng.
        StockLedgerEntry.objects.create(
            batch=self.batch, movement_type=StockLedgerEntry.MovementType.RECONCILE,
            qty_change=Decimal("-1"), reference="KK-2", created_by=self.user,
        )
        result = services.batch_pnl(batch=self.batch)
        self.assertEqual(result["shrinkage_cost"], Decimal("82000"))  # không phải 80.000

    # --- period_pnl ---------------------------------------------------------

    def test_period_pnl_nets_revenue_cogs_and_refunds_in_period(self):
        inv_sep = self._make_invoice(
            code="INV-SEP", issued_at=_dt(2026, 9, 10), qty_sold=Decimal("5"),
            sell_rate=Decimal("100000"), unit_cost=Decimal("70000"),
        )
        # Hoá đơn tháng khác — không được tính vào kỳ 9/2026
        self._make_invoice(
            code="INV-AUG", issued_at=_dt(2026, 8, 20), qty_sold=Decimal("4"),
            sell_rate=Decimal("100000"), unit_cost=Decimal("70000"),
        )
        # Hoàn tiền phát sinh trong kỳ 9/2026
        Refund.objects.create(
            sales_invoice=inv_sep, amount=Decimal("100000"), is_partial=True,
            status=Refund.Status.REFUNDED, created_by=self.user, confirmed_by=self.user,
            confirmed_at=_dt(2026, 9, 15), bank_txn_ref="TXN-1",
        )
        # Hoàn tiền ở kỳ khác — không được trừ vào kỳ 9/2026
        Refund.objects.create(
            sales_invoice=inv_sep, amount=Decimal("50000"), is_partial=True,
            status=Refund.Status.REFUNDED, created_by=self.user, confirmed_by=self.user,
            confirmed_at=_dt(2026, 10, 1), bank_txn_ref="TXN-2",
        )
        # Phiếu hoàn còn PENDING — chưa xác nhận, không được tính
        Refund.objects.create(
            sales_invoice=inv_sep, amount=Decimal("20000"), is_partial=True,
            status=Refund.Status.PENDING, created_by=self.user,
        )

        result = services.period_pnl(year=2026, month=9)

        self.assertEqual(result["revenue"], Decimal("500000"))   # 5 × 100.000, tháng 8 loại ra
        self.assertEqual(result["cogs"], Decimal("350000"))      # 5 × 70.000 (ảnh chụp)
        self.assertEqual(result["refunds"], Decimal("100000"))   # chỉ khoản REFUNDED trong kỳ
        self.assertEqual(result["profit"], Decimal("50000"))     # 500.000 - 350.000 - 100.000

    def test_period_pnl_requires_year_month(self):
        with self.assertRaises(BusinessError):
            services.period_pnl(year=None, month=9)

    def test_period_pnl_empty_when_no_data(self):
        result = services.period_pnl(year=2020, month=1)
        self.assertEqual(result["revenue"], Decimal("0"))
        self.assertEqual(result["cogs"], Decimal("0"))
        self.assertEqual(result["refunds"], Decimal("0"))
        self.assertEqual(result["profit"], Decimal("0"))
