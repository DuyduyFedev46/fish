"""
Đặt giá mới (ED-31-AC1, BR-DM-02/03): `POST /api/catalog/item-prices/` tự đóng giá đang hiệu lực của cùng mặt hàng
và cùng bảng giá bằng `valid_upto = valid_from mới − 1 ngày`; chặn chồng lấn khoảng hiệu lực (BR-DM-03) bằng 400
mã `BR-DM-03`; không tự xoá hay sửa giá tương lai. Ghi AuditLog `create_itemprice` và `close_itemprice`.
"""
import datetime
from decimal import Decimal
from unittest import mock

from apps.accounts.models import AuditLog
from apps.catalog.items.tests.api_base import CatalogApiBase, today
from apps.catalog.models import ItemPrice, PriceList
from apps.catalog.pricing import services
from apps.catalog.pricing.services import effective_price

URL = "/api/catalog/item-prices/"
DAY = datetime.timedelta(days=1)


class SetItemPriceTests(CatalogApiBase):
    def post_price(self, user=None, *, rate="130000", valid_from=None, item=None, price_list=None, **extra):
        payload = {
            "price_list": (price_list or self.price_list).pk, "item": (item or self.item_a).pk, "rate": rate,
            "valid_from": (valid_from or today()).isoformat(), **extra,
        }
        return self.send(user or self.owner, "post", URL, payload)

    def reload(self, price):
        price.refresh_from_db()
        return price

    def test_ed31_ac1_new_price_closes_old_one_the_day_before(self):
        old = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)
        response = self.post_price(valid_from=today() + 2 * DAY)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["valid_from"], (today() + 2 * DAY).isoformat())
        self.assertIsNone(response.json()["valid_upto"])
        self.assertEqual(self.reload(old).valid_upto, today() + DAY)

    def test_ed31_ac1_exactly_one_price_stays_open(self):
        self.add_price(self.item_a, "100000", valid_from=today() - 60 * DAY)
        self.assertEqual(self.post_price(rate="110000", valid_from=today() - 30 * DAY).status_code, 201)
        self.assertEqual(self.post_price(rate="120000", valid_from=today() - 5 * DAY).status_code, 201)
        open_prices = ItemPrice.objects.filter(item=self.item_a, valid_upto__isnull=True)
        self.assertEqual([p.rate for p in open_prices], [Decimal("120000.00")])
        ordered = list(ItemPrice.objects.filter(item=self.item_a).order_by("valid_from"))
        for earlier, later in zip(ordered, ordered[1:]):
            self.assertEqual(earlier.valid_upto, later.valid_from - DAY)  # liền mạch, không chồng, không hở

    def test_ed31_ac1_shop_reads_new_price_from_its_effective_date(self):
        self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)
        self.assertEqual(self.post_price(rate="150000", valid_from=today() + 3 * DAY).status_code, 201)
        self.assertEqual(effective_price(self.item_a), Decimal("120000"))
        self.assertEqual(effective_price(self.item_a, today() + 2 * DAY), Decimal("120000"))
        self.assertEqual(effective_price(self.item_a, today() + 3 * DAY), Decimal("150000"))

    def test_ed31_ac1_price_starting_today_replaces_old_one_for_shop_and_erp(self):
        self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)
        self.assertEqual(self.post_price(rate="150000", valid_from=today()).status_code, 201)
        self.assertEqual(effective_price(self.item_a), Decimal("150000"))
        listed = self.get(self.owner, "/api/catalog/items/").json()["results"]
        shown = {row["code"]: row["current_price"] for row in listed}["CA01"]
        self.assertEqual(shown["rate"], "150000.00")

    def test_br_dm_03_same_start_date_as_open_price_is_400(self):
        old = self.add_price(self.item_a, "120000", valid_from=today() - 10 * DAY)
        response = self.post_price(valid_from=today() - 10 * DAY)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "BR-DM-03")
        self.assertEqual(ItemPrice.objects.count(), 1)
        self.assertIsNone(self.reload(old).valid_upto)

    def test_br_dm_03_start_before_open_price_is_400_and_nothing_changes(self):
        old = self.add_price(self.item_a, "120000", valid_from=today() - 10 * DAY)
        response = self.post_price(valid_from=today() - 20 * DAY)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "BR-DM-03")
        self.assertEqual(ItemPrice.objects.count(), 1)
        self.assertIsNone(self.reload(old).valid_upto)
        self.assertFalse(AuditLog.objects.filter(action__in=["create_itemprice", "close_itemprice"]).exists())

    def test_br_dm_03_future_price_is_never_touched(self):
        future = self.add_price(self.item_a, "150000", valid_from=today() + 10 * DAY)
        current = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY, valid_upto=today() + 9 * DAY)
        response = self.post_price(valid_from=today() + 5 * DAY)  # không có ngày kết thúc: đè lên giá tương lai
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "BR-DM-03")
        self.assertEqual(self.reload(future).valid_from, today() + 10 * DAY)
        self.assertIsNone(self.reload(future).valid_upto)
        self.assertEqual(self.reload(current).valid_upto, today() + 9 * DAY)

    def test_br_dm_03_price_with_end_date_fits_before_future_price(self):
        future = self.add_price(self.item_a, "150000", valid_from=today() + 10 * DAY)
        current = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY, valid_upto=today() + 9 * DAY)
        response = self.post_price(rate="125000", valid_from=today() + 5 * DAY, valid_upto=(today() + 9 * DAY).isoformat())
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.reload(current).valid_upto, today() + 4 * DAY)
        self.assertEqual(self.reload(future).valid_from, today() + 10 * DAY)

    def test_br_dm_03_end_date_shorter_than_open_price_is_400_and_old_price_unchanged(self):
        """Giá cũ đang mở, giá mới +5..+9: nếu nhận thì từ +10 mặt hàng mất giá (Shop ẩn, đơn không tạo được)."""
        old = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)
        response = self.post_price(rate="99000", valid_from=today() + 5 * DAY, valid_upto=(today() + 9 * DAY).isoformat())
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["code"], "BR-DM-03")
        self.assertIn("để trống", body["detail"].lower())
        self.assertEqual(ItemPrice.objects.count(), 1)
        self.assertIsNone(self.reload(old).valid_upto)
        self.assertEqual(effective_price(self.item_a, today() + 10 * DAY), Decimal("120000"))
        self.assertFalse(AuditLog.objects.filter(action__in=["create_itemprice", "close_itemprice"]).exists())

    def test_br_dm_03_end_date_shorter_than_closed_old_price_is_400(self):
        old = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY, valid_upto=today() + 20 * DAY)
        response = self.post_price(valid_from=today() + 5 * DAY, valid_upto=(today() + 9 * DAY).isoformat())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "BR-DM-03")
        self.assertEqual(self.reload(old).valid_upto, today() + 20 * DAY)

    def test_br_dm_03_end_date_not_shorter_than_old_price_is_allowed(self):
        old = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY, valid_upto=today() + 9 * DAY)
        response = self.post_price(valid_from=today() + 5 * DAY, valid_upto=(today() + 12 * DAY).isoformat())
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.reload(old).valid_upto, today() + 4 * DAY)

    def test_br_dm_03_does_not_touch_other_items_or_other_price_lists(self):
        other_list = PriceList.objects.create(name="Bán sỉ")
        other_item = self.add_price(self.item_b, "55000", valid_from=today() - 30 * DAY)
        other_pl = self.add_price(self.item_a, "70000", valid_from=today() - 30 * DAY, price_list=other_list)
        self.assertEqual(self.post_price(valid_from=today()).status_code, 201)
        self.assertIsNone(self.reload(other_item).valid_upto)
        self.assertIsNone(self.reload(other_pl).valid_upto)

    def test_ed31_ac1_first_price_of_an_item_just_creates(self):
        response = self.post_price(valid_from=today())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ItemPrice.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="close_itemprice").count(), 0)

    def test_ed31_ac1_two_people_one_after_another_get_consistent_result(self):
        self.add_price(self.item_a, "100000", valid_from=today() - 30 * DAY)
        first = self.post_price(self.owner, rate="110000", valid_from=today())
        second = self.post_price(self.owner, rate="120000", valid_from=today())  # cùng ngày với giá vừa đặt
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.json()["code"], "BR-DM-03")
        self.assertEqual(ItemPrice.objects.filter(item=self.item_a, valid_upto__isnull=True).count(), 1)
        self.assertEqual(effective_price(self.item_a), Decimal("110000"))

    def test_ed31_ac1_service_locks_price_list_and_prices(self):
        """SQLite bỏ qua `select_for_update`; kiểm là dòng khoá được yêu cầu trong cùng giao dịch (PostgreSQL thật khoá)."""
        import inspect

        self.assertTrue(hasattr(services.set_item_price, "__wrapped__"))  # bọc bởi transaction.atomic
        for helper in (services._lock_price_lists, services._lock_item_prices, services._lock_price_row):
            self.assertIn("select_for_update", inspect.getsource(helper))

    # --- quyền -------------------------------------------------------------------------------------------------
    def test_ed31_ac5_only_owner_can_set_price(self):
        old = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service, self.no_group):
            self.assertEqual(self.post_price(user, valid_from=today()).status_code, 403, user.username)
        anonymous = self.send(None, "post", URL, {
            "price_list": self.price_list.pk, "item": self.item_a.pk, "rate": "1", "valid_from": today().isoformat()})
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(ItemPrice.objects.count(), 1)
        self.assertIsNone(self.reload(old).valid_upto)

    # --- audit -------------------------------------------------------------------------------------------------
    def test_br_pq_04_audit_for_create_and_close(self):
        old = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)
        response = self.post_price(valid_from=today() + DAY)
        new_id = response.json()["id"]
        created = AuditLog.objects.get(action="create_itemprice")
        self.assertEqual(created.actor, self.owner)
        self.assertEqual(created.object_id, str(new_id))
        self.assertEqual(created.changes["item"], self.item_a.pk)
        self.assertEqual(created.changes["price_list"], self.price_list.pk)
        self.assertEqual(created.changes["valid_from"], (today() + DAY).isoformat())
        closed = AuditLog.objects.get(action="close_itemprice")
        self.assertEqual(closed.actor, self.owner)
        self.assertEqual(closed.object_id, str(old.pk))
        self.assertEqual(closed.changes["valid_upto"], {"from": None, "to": today().isoformat()})
        self.assertEqual(closed.changes["replaced_by"], new_id)

    def test_bat_bien_9_audit_changes_hold_only_ids_dates_and_codes(self):
        self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)
        self.post_price(valid_from=today() + DAY)
        for log in AuditLog.objects.filter(action__in=["create_itemprice", "close_itemprice"]):
            self.assertNotIn("rate", log.changes)  # khoá `rate` thuộc COST_KEYS; giá bán ghi bằng `sell_rate`


class UpdateItemPriceOverlapTests(CatalogApiBase):
    """PATCH không được tạo chồng lấn (BR-DM-03). Sửa đơn giá khi không đổi ngày thì không bị chặn."""

    def setUp(self):
        super().setUp()
        self.older = self.add_price(self.item_a, "100000", valid_from=today() - 60 * DAY, valid_upto=today() - 31 * DAY)
        self.current = self.add_price(self.item_a, "120000", valid_from=today() - 30 * DAY)

    def patch(self, price, data):
        return self.send(self.owner, "patch", f"{URL}{price.pk}/", data)

    def test_br_dm_03_patch_extending_into_next_price_is_400(self):
        response = self.patch(self.older, {"valid_upto": (today() - 10 * DAY).isoformat()})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "BR-DM-03")
        self.older.refresh_from_db()
        self.assertEqual(self.older.valid_upto, today() - 31 * DAY)

    def test_br_dm_03_patch_rate_only_is_allowed(self):
        response = self.patch(self.current, {"rate": "125000"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rate"], "125000.00")

    def test_br_dm_03_patch_dates_inside_free_space_is_allowed(self):
        response = self.patch(self.older, {"valid_upto": (today() - 40 * DAY).isoformat()})
        self.assertEqual(response.status_code, 200)

    def test_patch_still_owner_only(self):
        for user in (self.manager, self.warehouse_staff):
            self.assertEqual(self.send(user, "patch", f"{URL}{self.current.pk}/", {"rate": "1"}).status_code, 403)


class UpdateLockOrderTests(CatalogApiBase):
    """L3: PATCH khoá bảng giá TRƯỚC dòng giá, cùng thứ tự với POST, để không deadlock khi hai thao tác chạy cùng lúc."""

    def test_update_locks_price_list_before_price_row(self):
        price = self.add_price(self.item_a, "120000")
        order = []
        real_lists, real_row = services._lock_price_lists, services._lock_price_row
        with mock.patch.object(services, "_lock_price_lists", side_effect=lambda *a, **k: (order.append("price_list"), real_lists(*a, **k))[1]), \
                mock.patch.object(services, "_lock_price_row", side_effect=lambda *a, **k: (order.append("price"), real_row(*a, **k))[1]):
            response = self.send(self.owner, "patch", f"{URL}{price.pk}/", {"rate": "125000"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order, ["price_list", "price"])

    def test_set_price_locks_price_list_before_prices(self):
        order = []
        real_lists, real_prices = services._lock_price_lists, services._lock_item_prices
        with mock.patch.object(services, "_lock_price_lists", side_effect=lambda *a, **k: (order.append("price_list"), real_lists(*a, **k))[1]), \
                mock.patch.object(services, "_lock_item_prices", side_effect=lambda *a, **k: (order.append("price"), real_prices(*a, **k))[1]):
            response = self.send(self.owner, "post", URL, {
                "price_list": self.price_list.pk, "item": self.item_a.pk, "rate": "1", "valid_from": today().isoformat()})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(order, ["price_list", "price"])
