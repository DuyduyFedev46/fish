"""
R14 — `GET /api/catalog/items/` (02b §3.8, ED-30-AC1/AC5, Lô 13).
`current_price` chỉ cho người có `catalog.view_itemprice` (T9, §5.2 Lô 13); không bao giờ có giá vốn (W2h).
"""
import datetime

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.catalog.models import Item, PriceList
from apps.catalog.pricing.services import effective_price
from apps.common.tests.fixtures import client_for

from .api_base import COST_SENTINEL, CatalogApiBase, find_cost_keys, today

URL = "/api/catalog/items/"


class ItemListPermissionTests(CatalogApiBase):
    def test_r14_permission_matrix_list_and_detail(self):
        for user, expected in (
            (self.owner, 200), (self.manager, 200), (self.warehouse_staff, 200),
            (self.courier, 403), (self.customer_service, 403), (self.no_group, 403), (None, 401),
        ):
            name = getattr(user, "username", "anon")
            self.assertEqual(client_for(user).get(URL).status_code, expected, name)
            self.assertEqual(client_for(user).get(f"{URL}{self.item_a.pk}/").status_code, expected, name)

    def test_r14_t9_only_owner_writes_items(self):
        payload = {"code": "MUC01", "name": "Mực thử", "item_group": self.group_fish.pk}
        for user in (self.manager, self.warehouse_staff):
            self.assertEqual(self.send(user, "post", URL, payload).status_code, 403)
            self.assertEqual(self.send(user, "patch", f"{URL}{self.item_a.pk}/", {"name": "X"}).status_code, 403)
        self.assertEqual(self.send(self.owner, "post", URL, payload).status_code, 201)


class ItemCurrentPriceTests(CatalogApiBase):
    def rows(self, user, **params):
        response = self.get(user, URL, **params)
        self.assertEqual(response.status_code, 200)
        return {row["code"]: row for row in response.json()["results"]}

    def test_r14_owner_and_manager_see_current_price_shape(self):
        self.add_price(self.item_a, "120000", valid_from=today() - datetime.timedelta(days=3))
        for user in (self.owner, self.manager):
            price = self.rows(user)["CA01"]["current_price"]
            self.assertEqual(set(price), {"rate", "valid_from", "valid_upto"})
            self.assertEqual(price["rate"], "120000.00")
            self.assertEqual(price["valid_from"], (today() - datetime.timedelta(days=3)).isoformat())
            self.assertIsNone(price["valid_upto"])

    def test_r14_current_price_is_json_serializable_straight_from_serializer_data(self):
        """Lệnh AI đọc `serializer.data` rồi json.dumps thẳng: ngày phải là chuỗi ISO, không phải date."""
        import json

        from apps.catalog.items.serializers import ItemSerializer

        class FakeRequest:
            user = self.owner

        self.add_price(self.item_a)
        data = ItemSerializer(self.item_a, context={"request": FakeRequest()}).data
        json.dumps(data)
        self.assertIsInstance(data["current_price"]["valid_from"], str)

    def test_r14_item_without_price_has_null_current_price(self):
        row = self.rows(self.owner)["TOM01"]
        self.assertIn("current_price", row)
        self.assertIsNone(row["current_price"])

    def test_r14_future_and_expired_prices_are_not_current(self):
        self.add_price(self.item_a, "90000", valid_from=today() + datetime.timedelta(days=2))
        self.add_price(
            self.item_a, "80001", valid_from=today() - datetime.timedelta(days=20),
            valid_upto=today() - datetime.timedelta(days=1),
        )
        self.assertIsNone(self.rows(self.owner)["CA01"]["current_price"])

    def test_r14_picks_the_price_in_effect_today_even_with_history(self):
        self.add_price(
            self.item_a, "100000", valid_from=today() - datetime.timedelta(days=60),
            valid_upto=today() - datetime.timedelta(days=31),
        )
        self.add_price(self.item_a, "110000", valid_from=today() - datetime.timedelta(days=30))
        self.assertEqual(self.rows(self.owner)["CA01"]["current_price"]["rate"], "110000.00")

    def test_r14_price_ending_today_is_still_current(self):
        self.add_price(self.item_a, "105000", valid_upto=today())
        self.assertEqual(self.rows(self.owner)["CA01"]["current_price"]["rate"], "105000.00")

    def test_r14_default_price_list_wins_like_shop(self):
        other = PriceList.objects.create(name="Bán sỉ")
        self.add_price(self.item_a, "70000", price_list=other)
        self.add_price(self.item_a, "120000")
        shown = self.rows(self.owner)["CA01"]["current_price"]["rate"]
        self.assertEqual(shown, "120000.00")
        self.assertEqual(f"{effective_price(self.item_a):.2f}", shown)  # khớp giá Shop (BR-DM-02)

    def test_r14_detail_has_current_price_for_owner(self):
        self.add_price(self.item_a)
        body = self.get(self.owner, f"{URL}{self.item_a.pk}/").json()
        self.assertEqual(body["current_price"]["rate"], "120000.00")

    def test_r14_warehouse_staff_never_sees_current_price(self):
        self.add_price(self.item_a)
        listing = self.get(self.warehouse_staff, URL)
        self.assertEqual(listing.status_code, 200)
        for row in listing.json()["results"]:
            self.assertNotIn("current_price", row)
        detail = self.get(self.warehouse_staff, f"{URL}{self.item_a.pk}/").json()
        self.assertNotIn("current_price", detail)
        self.assertNotIn("120000", listing.content.decode())

    def test_r14_response_of_owner_write_has_current_price(self):
        self.add_price(self.item_a)
        created = self.send(
            self.owner, "post", URL, {"code": "MUC01", "name": "Mực thử", "item_group": self.group_fish.pk}
        )
        self.assertEqual(created.status_code, 201)
        self.assertIsNone(created.json()["current_price"])
        patched = self.send(self.owner, "patch", f"{URL}{self.item_a.pk}/", {"description": "Tươi"})
        self.assertEqual(patched.json()["current_price"]["rate"], "120000.00")

    def test_r14_no_cost_leak_for_any_role(self):
        self.add_price(self.item_a)
        self.add_costed_batch(self.item_a)
        for user in (self.owner, self.manager, self.warehouse_staff):
            for url in (URL, f"{URL}{self.item_a.pk}/"):
                response = self.get(user, url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(find_cost_keys(response.json()), set(), user.username)
                self.assertNotIn(COST_SENTINEL, response.content.decode(), user.username)


class ItemListFilterTests(CatalogApiBase):
    def test_r14_filter_item_group(self):
        response = self.get(self.owner, URL, item_group=self.group_shrimp.pk)
        self.assertEqual(self.ids(response), {self.item_b.pk})

    def test_r14_filter_is_active(self):
        self.assertEqual(self.ids(self.get(self.owner, URL, is_active="1")), {self.item_a.pk, self.combo.pk})
        self.assertEqual(self.ids(self.get(self.owner, URL, is_active="false")), {self.item_b.pk})

    def test_r14_filter_item_type(self):
        self.assertEqual(self.ids(self.get(self.owner, URL, item_type="BUNDLE")), {self.combo.pk})
        self.assertEqual(self.ids(self.get(self.owner, URL, item_type="SIMPLE")), {self.item_a.pk, self.item_b.pk})

    def test_r14_filters_combine(self):
        response = self.get(self.owner, URL, item_group=self.group_fish.pk, item_type="SIMPLE", is_active="1")
        self.assertEqual(self.ids(response), {self.item_a.pk})

    def test_r14_blank_filters_mean_no_filter(self):
        response = self.get(self.owner, URL, item_group="", is_active=" ", item_type="")
        self.assertEqual(len(self.ids(response)), 3)

    def test_r14_unknown_group_id_is_empty_not_error(self):
        self.assertEqual(self.ids(self.get(self.owner, URL, item_group="999999")), set())

    def test_r14_invalid_filters_return_400_without_echo(self):
        for name, bad in (
            ("item_group", "abc"), ("item_group", "-1"), ("item_group", "0"), ("item_group", "9" * 40),
            ("is_active", "maybe"), ("item_type", "COMBO"), ("item_type", "<script>"),
        ):
            with self.subTest(name=name, bad=bad):
                self.assert_invalid_filter(self.get(self.owner, URL, **{name: bad}), bad)

    def test_r14_l5_has_image_invalid_value_returns_400_without_echo(self):
        for bad in ("abc", "2", "<b>"):
            with self.subTest(bad=bad):
                self.assert_invalid_filter(self.get(self.owner, URL, has_image=bad), bad)

    def test_a2_ac16_has_image_accepts_old_spellings_and_blank(self):
        for good in ("1", "true", "TRUE", "yes", "0", "false", "no", "", " "):
            self.assertEqual(self.get(self.owner, URL, has_image=good).status_code, 200, good)
        self.assertEqual(len(self.ids(self.get(self.owner, URL, has_image="yes"))), 0)
        self.assertEqual(len(self.ids(self.get(self.owner, URL, has_image="no"))), 3)

    def test_a2_ac16_has_image_filter_still_works(self):
        self.assertEqual(len(self.ids(self.get(self.owner, URL, has_image="0"))), 3)
        self.assertEqual(self.ids(self.get(self.owner, URL, has_image="1")), set())


class ItemListQueryCountTests(CatalogApiBase):
    def count_queries(self, user):
        with CaptureQueriesContext(connection) as captured:
            self.assertEqual(self.get(user, URL).status_code, 200)
        return len(captured)

    def test_r14_query_count_does_not_grow_with_items(self):
        for user in (self.owner, self.warehouse_staff):
            self.count_queries(user)  # lần đầu nạp quyền của user vào cache, không tính
            before = self.count_queries(user)
            for index in range(8):
                item = Item.objects.create(
                    code=f"{user.username[2:4].upper()}{index:02d}", name=f"Hàng {index}", item_group=self.group_fish
                )
                self.add_price(item)
            after = self.count_queries(user)
            self.assertEqual(before, after, user.username)
