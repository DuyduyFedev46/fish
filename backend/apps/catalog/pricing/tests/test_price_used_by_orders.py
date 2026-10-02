"""
Lô bổ sung A #10 (Duy chốt 02/10): đặt giá lùi ngày và sửa giá chỉ được khi chưa có đơn nào chốt giá trong khoảng
hiệu lực bị ảnh hưởng; có đơn -> 400 `PRICE_USED_BY_ORDERS`. Giá đã chốt trong đơn (`SalesOrderLine.rate`) không đổi.
BR-DM-02 (giá chốt theo hiệu lực lúc đặt), BR-DM-03 (không chồng lấn). Dữ liệu giả.

`SalesOrderLine` không có khoá tới `ItemPrice` hay bảng giá, nên "đã dùng" = có dòng đơn cùng mặt hàng mà ngày tạo đơn
(giờ VN) nằm trong khoảng bị ảnh hưởng, trừ ngày mà bảng giá mặc định đã thắng khi giá đang xét thuộc bảng giá khác.
"""
import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from apps.accounts.models import AuditLog
from apps.catalog.items.tests.api_base import CatalogApiBase, today
from apps.catalog.models import ItemPrice, PriceList
from apps.sales.models import Customer, SalesOrder, SalesOrderLine

URL = "/api/catalog/item-prices/"
DAY = datetime.timedelta(days=1)
VN = ZoneInfo("Asia/Ho_Chi_Minh")
MESSAGE = "Giá này đã áp vào đơn hàng, không sửa được. Hãy đặt giá mới bắt đầu từ ngày mai. Muốn ngừng bán ngay thì tạm ẩn mặt hàng."
CODE = "PRICE_USED_BY_ORDERS"


class PriceUsedByOrdersBase(CatalogApiBase):
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(phone="0900000123", name="Khách Thử A")
        self._seq = 0

    def add_order(self, item, on_date, *, rate="120000", status=SalesOrder.Status.COMPLETED, hour=12, minute=0):
        """Đơn có một dòng `item`, tạo lúc `hour:minute` giờ VN của ngày `on_date`."""
        self._seq += 1
        order = SalesOrder.objects.create(
            code=f"SO-PU{self._seq}", customer=self.customer, status=status,
            delivery_address="[Địa chỉ giao] Thử", phone="0900000123", total_amount=Decimal("1"),
        )
        stamp = datetime.datetime.combine(on_date, datetime.time(hour, minute), tzinfo=VN)
        SalesOrder.objects.filter(pk=order.pk).update(created_at=stamp)
        line = SalesOrderLine.objects.create(order=order, item=item, qty=Decimal("1"), rate=Decimal(rate))
        return order, line

    def post_price(self, *, valid_from, rate="130000", item=None, price_list=None, **extra):
        payload = {
            "price_list": (price_list or self.price_list).pk, "item": (item or self.item_a).pk,
            "rate": rate, "valid_from": valid_from.isoformat(), **extra,
        }
        return self.send(self.owner, "post", URL, payload)

    def patch(self, price, data):
        return self.send(self.owner, "patch", f"{URL}{price.pk}/", data)

    def assert_used_error(self, response):
        self.assertEqual(response.status_code, 400, response.content)
        body = response.json()
        self.assertEqual(body["code"], CODE)
        self.assertEqual(body["detail"], MESSAGE)

    def audit_count(self):
        return AuditLog.objects.filter(action__in=["create_itemprice", "close_itemprice", "update_itemprice"]).count()


class BackdatedPriceTests(PriceUsedByOrdersBase):
    def setUp(self):
        super().setUp()
        self.current = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)

    def test_backdated_price_without_orders_is_allowed_and_closes_old_one(self):
        res = self.post_price(valid_from=today() - 5 * DAY)
        self.assertEqual(res.status_code, 201, res.content)
        self.current.refresh_from_db()
        self.assertEqual(self.current.valid_upto, today() - 6 * DAY)

    def test_backdated_price_with_order_in_affected_range_is_400_and_nothing_changes(self):
        self.add_order(self.item_a, today() - 3 * DAY)
        before = self.audit_count()
        self.assert_used_error(self.post_price(valid_from=today() - 5 * DAY))
        self.current.refresh_from_db()
        self.assertIsNone(self.current.valid_upto)
        self.assertEqual(ItemPrice.objects.count(), 1)
        self.assertEqual(self.audit_count(), before)

    def test_order_before_the_new_start_date_does_not_block(self):
        self.add_order(self.item_a, today() - 10 * DAY)
        self.assertEqual(self.post_price(valid_from=today() - 5 * DAY).status_code, 201)

    def test_boundary_start_date_is_inclusive(self):
        self.add_order(self.item_a, today() - 5 * DAY)
        self.assert_used_error(self.post_price(valid_from=today() - 5 * DAY))
        # Ngày liền trước ngày bắt đầu thì không dính.
        ItemPrice.objects.filter(pk=self.current.pk).update(valid_upto=None)
        self.assertEqual(self.post_price(valid_from=today() - 4 * DAY).status_code, 201)

    def test_order_date_uses_vietnam_time_not_utc(self):
        # 23:30 giờ VN ngày T-6 (= 16:30 UTC cùng ngày) vẫn là ngày T-6 -> không dính khi bắt đầu T-5.
        self.add_order(self.item_a, today() - 6 * DAY, hour=23, minute=30)
        self.assertEqual(self.post_price(valid_from=today() - 5 * DAY).status_code, 201)

    def test_order_just_after_midnight_vietnam_time_is_that_day(self):
        # 00:30 giờ VN ngày T-5 (= 17:30 UTC ngày T-6) là ngày T-5 -> dính.
        self.add_order(self.item_a, today() - 5 * DAY, hour=0, minute=30)
        self.assert_used_error(self.post_price(valid_from=today() - 5 * DAY))

    def test_order_of_another_item_does_not_block(self):
        self.add_order(self.item_b, today() - 3 * DAY)
        self.assertEqual(self.post_price(valid_from=today() - 5 * DAY).status_code, 201)

    def test_any_order_status_counts_including_cancelled(self):
        for status in (SalesOrder.Status.CANCELLED, SalesOrder.Status.AUTO_CANCELLED, SalesOrder.Status.BOOKED):
            order, _ = self.add_order(self.item_a, today() - 3 * DAY, status=status)
            self.assert_used_error(self.post_price(valid_from=today() - 5 * DAY))
            order.delete()

    def test_price_starting_today_or_later_is_never_blocked(self):
        self.add_order(self.item_a, today())
        self.assertEqual(self.post_price(valid_from=today()).status_code, 201)
        self.assertEqual(self.post_price(valid_from=today() + 3 * DAY, rate="140000").status_code, 201)

    def test_frozen_line_rate_never_changes(self):
        _, line = self.add_order(self.item_a, today() - 10 * DAY, rate="120000")
        self.assertEqual(self.post_price(valid_from=today() - 5 * DAY, rate="999000").status_code, 201)
        line.refresh_from_db()
        self.assertEqual(line.rate, Decimal("120000"))

    def test_overlap_rule_still_wins_when_no_orders(self):
        res = self.post_price(valid_from=today() - 30 * DAY)  # cùng ngày bắt đầu với giá đang mở
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "BR-DM-03")

    def test_backdated_price_still_owner_only(self):
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service):
            payload = {"price_list": self.price_list.pk, "item": self.item_a.pk, "rate": "1",
                       "valid_from": (today() - 5 * DAY).isoformat()}
            self.assertEqual(self.send(user, "post", URL, payload).status_code, 403)


class EditPriceTests(PriceUsedByOrdersBase):
    def setUp(self):
        super().setUp()
        self.older = self.add_price(self.item_a, "100000", valid_from=today() - 60 * DAY, valid_upto=today() - 31 * DAY)
        self.current = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)

    def test_edit_rate_without_orders_is_allowed(self):
        res = self.patch(self.current, {"rate": "125000"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["rate"], "125000.00")

    def test_edit_rate_with_order_in_window_is_400_and_unchanged(self):
        self.add_order(self.item_a, today() - 3 * DAY)
        before = self.audit_count()
        self.assert_used_error(self.patch(self.current, {"rate": "125000"}))
        self.current.refresh_from_db()
        self.assertEqual(self.current.rate, Decimal("120000"))
        self.assertEqual(self.audit_count(), before)

    def test_put_is_guarded_too(self):
        self.add_order(self.item_a, today() - 3 * DAY)
        payload = {"price_list": self.price_list.pk, "item": self.item_a.pk, "rate": "125000",
                   "valid_from": (today() - 30 * DAY).isoformat()}
        self.assert_used_error(self.send(self.owner, "put", f"{URL}{self.current.pk}/", payload))

    def test_order_in_older_window_blocks_only_the_older_price(self):
        self.add_order(self.item_a, today() - 40 * DAY, rate="100000")
        self.assert_used_error(self.patch(self.older, {"rate": "101000"}))
        self.assertEqual(self.patch(self.current, {"rate": "125000"}).status_code, 200)

    def test_order_of_another_item_does_not_block(self):
        self.add_order(self.item_b, today() - 3 * DAY)
        self.assertEqual(self.patch(self.current, {"rate": "125000"}).status_code, 200)

    def test_any_order_status_counts_including_auto_cancelled(self):
        self.add_order(self.item_a, today() - 3 * DAY, status=SalesOrder.Status.AUTO_CANCELLED)
        self.assert_used_error(self.patch(self.current, {"rate": "125000"}))

    def test_unchanged_value_is_a_noop_even_with_orders(self):
        self.add_order(self.item_a, today() - 3 * DAY)
        res = self.patch(self.current, {"rate": "120000"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.audit_count(), 0)

    def test_closing_a_price_after_its_last_order_is_allowed(self):
        self.add_order(self.item_a, today() - 3 * DAY)
        res = self.patch(self.current, {"valid_upto": (today() - 3 * DAY).isoformat()})
        self.assertEqual(res.status_code, 200, res.content)

    def test_shortening_a_price_below_an_order_date_is_400(self):
        self.add_order(self.item_a, today() - 3 * DAY)
        self.assert_used_error(self.patch(self.current, {"valid_upto": (today() - 4 * DAY).isoformat()}))
        self.current.refresh_from_db()
        self.assertIsNone(self.current.valid_upto)

    def test_moving_start_date_over_an_order_is_400(self):
        self.add_order(self.item_a, today() - 20 * DAY)
        self.assert_used_error(self.patch(self.current, {"valid_from": (today() - 10 * DAY).isoformat()}))

    def test_moving_item_checks_the_target_item_too(self):
        self.add_order(self.item_b, today() - 3 * DAY)
        self.assert_used_error(self.patch(self.current, {"item": self.item_b.pk}))

    def test_changing_item_checks_old_item_window(self):
        self.add_order(self.item_a, today() - 3 * DAY)
        self.assert_used_error(self.patch(self.current, {"item": self.item_b.pk}))

    def test_frozen_line_rate_never_changes_after_allowed_edit(self):
        _, line = self.add_order(self.item_a, today() - 40 * DAY, rate="100000")
        # giá `current` không có đơn trong khoảng của nó -> sửa được; dòng đơn cũ vẫn nguyên.
        self.assertEqual(self.patch(self.current, {"rate": "125000"}).status_code, 200)
        line.refresh_from_db()
        self.assertEqual(line.rate, Decimal("100000"))

    def test_edit_still_owner_only_and_error_body_has_no_cost_or_personal_data(self):
        self.add_order(self.item_a, today() - 3 * DAY)
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service):
            self.assertEqual(self.send(user, "patch", f"{URL}{self.current.pk}/", {"rate": "1"}).status_code, 403)
        raw = self.patch(self.current, {"rate": "125000"}).content.decode()
        for secret in ("0900000123", "Khách Thử A", "[Địa chỉ giao]", "purchase_rate", "landed_unit_cost", "SO-PU"):
            self.assertNotIn(secret, raw)


class OtherPriceListTests(PriceUsedByOrdersBase):
    """Đơn chọn bảng giá mặc định trước (`EFFECTIVE_ORDER`): ngày mà bảng mặc định đã có giá thì giá ở bảng khác không bị dính."""

    def setUp(self):
        super().setUp()
        self.other_list = PriceList.objects.create(name="Bán sỉ", is_default=False)
        self.default_price = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)
        self.other_price = self.add_price(
            self.item_a, "110000", valid_from=today() - 30 * DAY, price_list=self.other_list,
        )

    def test_default_list_price_is_blocked_by_order(self):
        self.add_order(self.item_a, today() - 3 * DAY)
        self.assert_used_error(self.patch(self.default_price, {"rate": "125000"}))

    def test_other_list_price_not_blocked_when_default_list_covers_the_date(self):
        self.add_order(self.item_a, today() - 3 * DAY)
        self.assertEqual(self.patch(self.other_price, {"rate": "115000"}).status_code, 200)

    def test_other_list_price_blocked_on_date_default_list_has_no_price(self):
        ItemPrice.objects.filter(pk=self.default_price.pk).update(valid_from=today() - 2 * DAY)
        self.add_order(self.item_a, today() - 3 * DAY)
        self.assert_used_error(self.patch(self.other_price, {"rate": "115000"}))


class PriceStartingTodayTests(PriceUsedByOrdersBase):
    """TLA-M2 (BR-DM-03): giá bắt đầu hôm nay mà đã có đơn hôm nay. Đặt giá mới "từ hôm nay" bị chặn vì đã có giá
    bắt đầu cùng ngày, nên thông điệp phải chỉ đường đi được: giá mới từ ngày mai, hoặc tạm ẩn mặt hàng."""

    def setUp(self):
        super().setUp()
        self.todays = self.add_price(self.item_a, "15000", valid_from=today())
        self.add_order(self.item_a, today(), rate="15000")

    def test_edit_of_price_starting_today_with_order_today_suggests_tomorrow_or_hiding(self):
        res = self.patch(self.todays, {"rate": "150000"})
        self.assert_used_error(res)
        detail = res.json()["detail"]
        self.assertIn("ngày mai", detail)
        self.assertIn("tạm ẩn", detail)
        self.assertNotIn("hôm nay", detail)
        self.todays.refresh_from_db()
        self.assertEqual(self.todays.rate, Decimal("15000"))

    def test_suggestion_from_today_is_really_blocked_by_br_dm_03_and_tomorrow_works(self):
        res_today = self.post_price(valid_from=today(), rate="150000")
        self.assertEqual(res_today.status_code, 400)
        self.assertEqual(res_today.json()["code"], "BR-DM-03")
        res_tomorrow = self.post_price(valid_from=today() + DAY, rate="150000")
        self.assertEqual(res_tomorrow.status_code, 201, res_tomorrow.content)
        self.todays.refresh_from_db()
        self.assertEqual(self.todays.valid_upto, today())
