"""
P5 (BR-BH-15): Tổng đơn là số nguyên đồng, làm tròn HALF-UP ngay lúc tạo đơn (Q6).
Mục đích: số gửi cổng SePay, số trên hoá đơn và số khách trả trùng nhau tuyệt đối.
Dòng đơn (SalesOrderLine.amount) vẫn giữ 2 chữ số thập phân như trước — chỉ tổng đơn
(`SalesOrder.total_amount`) làm tròn về nguyên đồng.
"""
from decimal import Decimal

from apps.catalog.models import PricingRule
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.base import SalesServiceBase


class RoundOrderTotalTests(SalesServiceBase):
    def test_p5_ac1_odd_cents_rounds_half_up_to_whole_dong(self):
        ca = self._item("CA90", price="150501")
        self._stocked_batch(ca, "10")
        order = order_services.create_order(
            customer_phone="0900000090", customer_name="A", delivery_address="x",
            phone="0900000090", lines=[{"item_code": "CA90", "qty": Decimal("1.5")}],
        )
        # 1,5kg × 150.501đ = 225.751,50đ -> half-up -> 225.752đ (BR-BH-15; số lượng theo bước 0,5 kg của BR-BH-22)
        self.assertEqual(order.total_amount, Decimal("225752"))
        self.assertEqual(order.total_amount, order.total_amount.to_integral_value())
        # dòng đơn vẫn lưu nguyên như hiện nay (2 chữ số thập phân)
        self.assertEqual(order.lines.first().amount, Decimal("225751.50"))

    def test_p5_ac2_percent_discount_total_is_whole_dong(self):
        ca = self._item("CA91", price="150501")
        self._stocked_batch(ca, "10")
        PricingRule.objects.create(
            name="giảm 5%", is_active=True, apply_on=PricingRule.ApplyOn.ITEM,
            item=ca, min_qty=Decimal("1"), discount_type=PricingRule.DiscountType.PERCENT,
            discount_value=Decimal("5"),
        )
        order = order_services.create_order(
            customer_phone="0900000091", customer_name="A", delivery_address="x",
            phone="0900000091", lines=[{"item_code": "CA91", "qty": Decimal("1.5")}],
        )
        # gross 225.751,50 - giảm 5% (11.287,575 -> 11.287,58) = 214.463,92 -> tổng nguyên đồng 214.464đ
        self.assertEqual(order.lines.first().amount, Decimal("214463.92"))
        self.assertEqual(order.total_amount, Decimal("214464"))
        self.assertEqual(order.total_amount, order.total_amount.to_integral_value())
