"""
R14 — danh mục & giá cho ERP (02b §3.8, ED-30, ED-31, Lô 13): `item-prices`, `pricing-rules`, `item-groups`, `price-lists`.
T9: sửa giá bán và ưu đãi chỉ Chủ (`owner`); Quản lý chỉ xem. `warehouse_staff` không đọc được giá hay ưu đãi.
Giá ở đây là giá BÁN, không phải giá vốn (§0c W2h).
"""
import datetime
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.catalog.items.tests.api_base import (
    COST_SENTINEL, CatalogApiBase, find_cost_keys, today,
)
from apps.catalog.models import ItemGroup, ItemPrice, PriceList, PricingRule
from apps.common.tests.fixtures import client_for

PRICES = "/api/catalog/item-prices/"
RULES = "/api/catalog/pricing-rules/"
GROUPS = "/api/catalog/item-groups/"
LISTS = "/api/catalog/price-lists/"


class PricingReadPermissionTests(CatalogApiBase):
    def setUp(self):
        super().setUp()
        self.price = self.add_price(self.item_a)
        self.rule = self.add_rule()

    def test_r14_read_matrix_prices_rules_lists(self):
        for url in (PRICES, RULES, LISTS):
            for user, expected in (
                (self.owner, 200), (self.manager, 200), (self.warehouse_staff, 403),
                (self.courier, 403), (self.customer_service, 403), (self.no_group, 403), (None, 401),
            ):
                name = getattr(user, "username", "anon")
                self.assertEqual(client_for(user).get(url).status_code, expected, f"{url} {name}")

    def test_r14_read_matrix_groups(self):
        for user, expected in (
            (self.owner, 200), (self.manager, 200), (self.warehouse_staff, 200),
            (self.courier, 403), (self.customer_service, 403), (self.no_group, 403), (None, 401),
        ):
            self.assertEqual(client_for(user).get(GROUPS).status_code, expected, getattr(user, "username", "anon"))

    def test_r14_warehouse_staff_cannot_read_any_price_text(self):
        for url in (PRICES, RULES, LISTS):
            body = self.get(self.warehouse_staff, url).content.decode()
            self.assertNotIn("120000", body)


class PricingWritePermissionTests(CatalogApiBase):
    """T9 + ED-31-AC5: ghi giá và ưu đãi chỉ Chủ; Quản lý và nhân viên kho nhận 403, dữ liệu không đổi."""

    def payloads(self):
        return (
            (PRICES, {"price_list": self.price_list.pk, "item": self.item_a.pk, "rate": "99000",
                      "valid_from": today().isoformat()}),
            (RULES, {"name": "Giảm 5%", "apply_on": "ORDER", "min_amount": "500000",
                     "discount_type": "PERCENT", "discount_value": "5"}),
            (LISTS, {"name": "Bán sỉ"}),
            (GROUPS, {"name": "Mực"}),
        )

    def test_r14_t9_manager_and_warehouse_staff_get_403_on_create(self):
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service):
            for url, payload in self.payloads():
                self.assertEqual(self.send(user, "post", url, payload).status_code, 403, f"{url} {user.username}")
        self.assertEqual(ItemPrice.objects.count(), 0)
        self.assertEqual(PricingRule.objects.count(), 0)
        self.assertFalse(ItemGroup.objects.filter(name="Mực").exists())

    def test_r14_t9_manager_cannot_change_or_delete_price_and_rule(self):
        price, rule = self.add_price(self.item_a), self.add_rule()
        for user in (self.manager, self.warehouse_staff):
            self.assertEqual(self.send(user, "patch", f"{PRICES}{price.pk}/", {"rate": "1"}).status_code, 403)
            self.assertEqual(self.send(user, "patch", f"{RULES}{rule.pk}/", {"is_active": False}).status_code, 403)
        for url, pk in ((PRICES, price.pk), (RULES, rule.pk)):
            self.assertEqual(self.send(self.manager, "delete", f"{url}{pk}/").status_code, 405)
        price.refresh_from_db(), rule.refresh_from_db()
        self.assertEqual(price.rate, Decimal("120000"))
        self.assertTrue(rule.is_active)

    def test_r14_unauthenticated_cannot_write(self):
        for url, payload in self.payloads():
            self.assertEqual(self.send(None, "post", url, payload).status_code, 401)

    def test_r14_owner_can_write_price_rule_group_and_list(self):
        for url, payload in self.payloads():
            response = self.send(self.owner, "post", url, payload)
            self.assertEqual(response.status_code, 201, f"{url} {response.content[:200]}")


class ItemPriceListTests(CatalogApiBase):
    def setUp(self):
        super().setUp()
        self.price_a = self.add_price(self.item_a)
        self.price_b = self.add_price(self.item_b, "55000")

    def test_r14_row_shape_has_item_name_and_code(self):
        rows = {row["id"]: row for row in self.get(self.owner, PRICES).json()["results"]}
        row = rows[self.price_a.pk]
        self.assertEqual(
            set(row),
            {"id", "price_list", "item", "item_name", "item_code", "rate", "valid_from", "valid_upto"},
        )
        self.assertEqual((row["item_name"], row["item_code"]), ("Cá thu", "CA01"))
        self.assertEqual(row["rate"], "120000.00")
        self.assertIsNone(row["valid_upto"])

    def test_r14_filter_by_item(self):
        older = self.add_price(
            self.item_a, "100000", valid_from=today() - datetime.timedelta(days=90),
            valid_upto=today() - datetime.timedelta(days=31),
        )
        response = self.get(self.manager, PRICES, item=self.item_a.pk)
        self.assertEqual(self.ids(response), {self.price_a.pk, older.pk})

    def test_r14_unknown_item_is_empty_not_error(self):
        self.assertEqual(self.ids(self.get(self.owner, PRICES, item="999999")), set())

    def test_r14_blank_item_filter_means_no_filter(self):
        self.assertEqual(len(self.ids(self.get(self.owner, PRICES, item=" "))), 2)

    def test_r14_invalid_item_filter_returns_400_without_echo(self):
        for bad in ("abc", "-3", "0", "1.5", "9" * 40, "<script>"):
            with self.subTest(bad=bad):
                self.assert_invalid_filter(self.get(self.owner, PRICES, item=bad), bad)

    def test_r14_no_cost_leak(self):
        self.add_costed_batch(self.item_a)
        for user in (self.owner, self.manager):
            response = self.get(user, PRICES)
            self.assertEqual(find_cost_keys(response.json()), set())
            self.assertNotIn(COST_SENTINEL, response.content.decode())

    def test_r14_query_count_does_not_grow(self):
        self.count(self.owner)  # nạp cache quyền
        before = self.count(self.owner)
        for index in range(6):
            self.add_price(self.item_a, "90000", valid_from=today() - datetime.timedelta(days=100 + index * 10),
                           valid_upto=today() - datetime.timedelta(days=95 + index * 10))
        self.assertEqual(before, self.count(self.owner))

    def count(self, user):
        with CaptureQueriesContext(connection) as captured:
            self.assertEqual(self.get(user, PRICES).status_code, 200)
        return len(captured)

    def test_r14_ac3_valid_upto_before_valid_from_is_rejected(self):
        payload = {"price_list": self.price_list.pk, "item": self.item_a.pk, "rate": "99000",
                   "valid_from": "2026-11-10", "valid_upto": "2026-11-01"}
        response = self.send(self.owner, "post", PRICES, payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("valid_upto", response.json())

    def test_r14_negative_rate_is_rejected(self):
        payload = {"price_list": self.price_list.pk, "item": self.item_a.pk, "rate": "-1", "valid_from": "2026-11-01"}
        self.assertEqual(self.send(self.owner, "post", PRICES, payload).status_code, 400)


class PricingRuleTests(CatalogApiBase):
    def setUp(self):
        super().setUp()
        self.item_rule = self.add_rule(name="Mua 5 kg giảm 10%")
        self.order_rule = self.add_rule(
            name="Đơn từ 500k giảm 20k", apply_on=PricingRule.ApplyOn.ORDER, item=None, min_qty=None,
            min_amount=Decimal("500000"), discount_type=PricingRule.DiscountType.AMOUNT,
            discount_value=Decimal("20000"), is_active=False,
        )

    def test_r14_row_shape_and_item_name(self):
        rows = {row["id"]: row for row in self.get(self.manager, RULES).json()["results"]}
        self.assertEqual(rows[self.item_rule.pk]["item_name"], "Cá thu")
        self.assertIsNone(rows[self.order_rule.pk]["item_name"])
        self.assertEqual(
            set(rows[self.item_rule.pk]),
            {"id", "name", "is_active", "apply_on", "item", "item_name", "min_qty", "min_amount",
             "discount_type", "discount_value", "valid_from", "valid_upto"},
        )

    def test_r14_filter_is_active(self):
        self.assertEqual(self.ids(self.get(self.owner, RULES, is_active="1")), {self.item_rule.pk})
        self.assertEqual(self.ids(self.get(self.owner, RULES, is_active="0")), {self.order_rule.pk})

    def test_r14_filter_apply_on(self):
        self.assertEqual(self.ids(self.get(self.owner, RULES, apply_on="ORDER")), {self.order_rule.pk})
        self.assertEqual(self.ids(self.get(self.owner, RULES, apply_on="ITEM")), {self.item_rule.pk})

    def test_r14_filters_combine_and_blank_means_all(self):
        self.assertEqual(self.ids(self.get(self.owner, RULES, apply_on="ORDER", is_active="1")), set())
        self.assertEqual(len(self.ids(self.get(self.owner, RULES, apply_on="", is_active=""))), 2)

    def test_r14_invalid_filters_return_400_without_echo(self):
        for name, bad in (("is_active", "maybe"), ("apply_on", "BATCH"), ("apply_on", "<b>x</b>")):
            with self.subTest(name=name, bad=bad):
                self.assert_invalid_filter(self.get(self.owner, RULES, **{name: bad}), bad)

    def test_r14_query_count_does_not_grow(self):
        def count():
            with CaptureQueriesContext(connection) as captured:
                self.assertEqual(self.get(self.owner, RULES).status_code, 200)
            return len(captured)

        count()
        before = count()
        for index in range(6):
            self.add_rule(name=f"Ưu đãi {index}")
        self.assertEqual(before, count())

    def test_r14_ac3_percent_over_100_is_rejected(self):
        payload = {"name": "Giảm quá tay", "apply_on": "ORDER", "min_amount": "100000",
                   "discount_type": "PERCENT", "discount_value": "101"}
        response = self.send(self.owner, "post", RULES, payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("discount_value", response.json())
        self.assertEqual(PricingRule.objects.count(), 2)

    def test_r14_ac3_percent_100_is_allowed_and_amount_over_100_is_allowed(self):
        base = {"apply_on": "ORDER", "min_amount": "100000"}
        self.assertEqual(self.send(self.owner, "post", RULES, {
            **base, "name": "Tặng", "discount_type": "PERCENT", "discount_value": "100"}).status_code, 201)
        self.assertEqual(self.send(self.owner, "post", RULES, {
            **base, "name": "Giảm 30k", "discount_type": "AMOUNT", "discount_value": "30000"}).status_code, 201)

    def test_r14_ac3_valid_upto_before_valid_from_is_rejected(self):
        payload = {"name": "Sai ngày", "apply_on": "ORDER", "min_amount": "100000", "discount_type": "AMOUNT",
                   "discount_value": "1000", "valid_from": "2026-11-10", "valid_upto": "2026-11-01"}
        response = self.send(self.owner, "post", RULES, payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("valid_upto", response.json())

    def test_r14_br_dm_08_rule_by_item_needs_item_and_min_qty(self):
        base = {"name": "Theo hàng", "apply_on": "ITEM", "discount_type": "AMOUNT", "discount_value": "1000"}
        no_item = self.send(self.owner, "post", RULES, {**base, "min_qty": "5"})
        self.assertEqual(no_item.status_code, 400)
        self.assertIn("item", no_item.json())
        no_qty = self.send(self.owner, "post", RULES, {**base, "item": self.item_a.pk})
        self.assertEqual(no_qty.status_code, 400)
        self.assertIn("min_qty", no_qty.json())

    def test_r14_br_dm_08_rule_by_order_needs_min_amount(self):
        payload = {"name": "Theo đơn", "apply_on": "ORDER", "discount_type": "AMOUNT", "discount_value": "1000"}
        response = self.send(self.owner, "post", RULES, payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("min_amount", response.json())

    def test_r14_patch_toggle_active_does_not_need_full_payload(self):
        response = self.send(self.owner, "patch", f"{RULES}{self.item_rule.pk}/", {"is_active": False})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_active"])

    def test_r14_l2_broken_old_rule_can_still_be_switched_off(self):
        """Ưu đãi cũ sai dữ liệu (API trước Lô 13 nhận) vẫn tắt được; không kiểm lại ràng buộc khác."""
        broken = PricingRule.objects.create(
            name="Sai từ trước", apply_on="ITEM", item=None, min_qty=None,
            discount_type="PERCENT", discount_value=Decimal("150"),
        )
        response = self.send(self.owner, "patch", f"{RULES}{broken.pk}/", {"is_active": False})
        self.assertEqual(response.status_code, 200, response.content)
        broken.refresh_from_db()
        self.assertFalse(broken.is_active)

    def test_r14_l2_switching_on_or_editing_a_broken_rule_is_still_validated(self):
        broken = PricingRule.objects.create(
            name="Sai từ trước", apply_on="ITEM", item=None, min_qty=None, is_active=False,
            discount_type="PERCENT", discount_value=Decimal("150"),
        )
        self.assertEqual(self.send(self.owner, "patch", f"{RULES}{broken.pk}/", {"is_active": True}).status_code, 400)
        self.assertEqual(
            self.send(self.owner, "patch", f"{RULES}{broken.pk}/", {"is_active": False, "name": "Đổi tên"}).status_code, 400
        )

    def test_r14_patch_validates_against_stored_values(self):
        response = self.send(self.owner, "patch", f"{RULES}{self.item_rule.pk}/", {"discount_value": "150"})
        self.assertEqual(response.status_code, 400)  # luật đang là PERCENT
        self.item_rule.refresh_from_db()
        self.assertEqual(self.item_rule.discount_value, Decimal("10.00"))


class ItemGroupTests(CatalogApiBase):
    def rows(self, user=None):
        response = self.get(user or self.owner, GROUPS)
        self.assertEqual(response.status_code, 200)
        return {row["name"]: row for row in response.json()["results"]}

    def test_r14_parent_name_and_item_count(self):
        rows = self.rows()
        self.assertEqual(set(rows["Cá"]), {"id", "name", "slug", "parent", "parent_name", "item_count"})
        self.assertEqual(rows["Cá"]["item_count"], 2)  # Cá thu + Combo thử
        self.assertEqual(rows["Tôm"]["item_count"], 1)  # kể cả mặt hàng đang ẩn
        self.assertEqual(rows["Cá biển"]["item_count"], 0)
        self.assertEqual(rows["Cá biển"]["parent_name"], "Cá")
        self.assertIsNone(rows["Cá"]["parent_name"])
        self.assertIsNone(rows["Cá"]["parent"])

    def test_r14_all_read_roles_get_same_shape(self):
        for user in (self.manager, self.warehouse_staff):
            self.assertEqual(self.rows(user)["Cá"]["item_count"], 2)

    def test_r14_created_group_has_item_count_zero(self):
        response = self.send(self.owner, "post", GROUPS, {"name": "Mực", "parent": self.group_fish.pk})
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual((body["item_count"], body["parent_name"]), (0, "Cá"))

    def test_r14_ac4_duplicate_group_name_is_400(self):
        self.assertEqual(self.send(self.owner, "post", GROUPS, {"name": "Cá"}).status_code, 400)

    def test_r14_query_count_does_not_grow(self):
        def count():
            with CaptureQueriesContext(connection) as captured:
                self.assertEqual(self.get(self.owner, GROUPS).status_code, 200)
            return len(captured)

        count()
        before = count()
        for index in range(6):
            ItemGroup.objects.create(name=f"Nhóm {index}", parent=self.group_fish)
        self.assertEqual(before, count())


class PriceListTests(CatalogApiBase):
    def test_r14_price_list_shape_has_no_extra_field(self):
        row = self.get(self.manager, LISTS).json()["results"][0]
        self.assertEqual(set(row), {"id", "name", "currency", "is_default"})


class NoHardDeleteTests(CatalogApiBase):
    """B13-1, N13-3: giá, ưu đãi, bảng giá không xoá cứng (bất biến 3). Ưu đãi tắt bằng is_active=false,
    giá đóng bằng ngày kết thúc. DELETE trả 405 cho mọi người đã đăng nhập (kể cả người thiếu quyền, như S3-AC4),
    không bao giờ 500 (ProtectedError)."""

    def setUp(self):
        super().setUp()
        self.price = self.add_price(self.item_a)
        self.rule = self.add_rule()

    def targets(self):
        return ((PRICES, self.price.pk), (RULES, self.rule.pk), (LISTS, self.price_list.pk))

    def test_b13_1_delete_is_405_for_every_logged_in_role(self):
        for url, pk in self.targets():
            for user in self.everyone:
                response = self.send(user, "delete", f"{url}{pk}/")
                self.assertEqual(response.status_code, 405, f"{url} {user.username}")
        self.assertTrue(ItemPrice.objects.filter(pk=self.price.pk).exists())
        self.assertTrue(PricingRule.objects.filter(pk=self.rule.pk).exists())
        self.assertTrue(PriceList.objects.filter(pk=self.price_list.pk).exists())

    def test_b13_1_delete_unauthenticated_is_401(self):
        for url, pk in self.targets():
            self.assertEqual(self.send(None, "delete", f"{url}{pk}/").status_code, 401)

    def test_b13_1_delete_rule_already_used_on_an_order_is_405_not_500(self):
        """Ưu đãi đã dùng ở dòng đơn (FK PROTECT): xoá cứng trước đây ném ProtectedError → 500."""
        from apps.sales.models import Customer, SalesOrder, SalesOrderLine

        customer = Customer.objects.create(phone="0900000001", name="Khách thử", default_address="1 Cảng")
        order = SalesOrder.objects.create(
            code="DH-R14-DEL", customer=customer, status=SalesOrder.Status.PROCESSING, delivery_address="1 Cảng",
            phone="0900000001", total_amount=Decimal("100000"),
        )
        SalesOrderLine.objects.create(
            order=order, item=self.item_a, qty=Decimal("5"), rate=Decimal("120000"), pricing_rule=self.rule,
        )
        for user in (self.owner, self.manager):
            response = self.send(user, "delete", f"{RULES}{self.rule.pk}/")
            self.assertEqual(response.status_code, 405, user.username)
        self.assertTrue(PricingRule.objects.filter(pk=self.rule.pk).exists())

    def test_b13_1_methods_still_work(self):
        self.assertEqual(self.send(self.owner, "patch", f"{RULES}{self.rule.pk}/", {"is_active": False}).status_code, 200)
        self.assertEqual(self.get(self.owner, f"{PRICES}{self.price.pk}/").status_code, 200)
        self.assertEqual(self.get(self.manager, f"{LISTS}{self.price_list.pk}/").status_code, 200)
        self.assertEqual(self.send(self.owner, "patch", f"{LISTS}{self.price_list.pk}/", {"name": "Bán lẻ 2"}).status_code, 200)
        self.assertEqual(client_for(self.owner).options(PRICES).status_code, 200)


class PositiveValueTests(CatalogApiBase):
    def test_b13_2_rate_zero_or_negative_is_400_with_vietnamese_message(self):
        for bad in ("0", "0.00", "-1", "-100000"):
            with self.subTest(rate=bad):
                response = self.send(self.owner, "post", PRICES, {
                    "price_list": self.price_list.pk, "item": self.item_a.pk, "rate": bad, "valid_from": today().isoformat()})
                self.assertEqual(response.status_code, 400)
                message = " ".join(response.json()["rate"])
                self.assertIn("lớn hơn 0", message)
        self.assertEqual(ItemPrice.objects.count(), 0)

    def test_b13_2_patch_rate_to_zero_is_400_and_price_unchanged(self):
        price = self.add_price(self.item_a)
        response = self.send(self.owner, "patch", f"{PRICES}{price.pk}/", {"rate": "0"})
        self.assertEqual(response.status_code, 400)
        price.refresh_from_db()
        self.assertEqual(price.rate, Decimal("120000"))

    def test_b13_2_rate_positive_is_ok(self):
        response = self.send(self.owner, "post", PRICES, {
            "price_list": self.price_list.pk, "item": self.item_a.pk, "rate": "0.01", "valid_from": today().isoformat()})
        self.assertEqual(response.status_code, 201)

    def rule_payload(self, **overrides):
        data = {"name": "Mua nhiều", "apply_on": "ITEM", "item": self.item_a.pk, "min_qty": "5",
                "discount_type": "AMOUNT", "discount_value": "1000"}
        data.update(overrides)
        return data

    def test_n13_3_min_qty_must_be_positive(self):
        for bad in ("0", "0.000", "-1"):
            with self.subTest(min_qty=bad):
                response = self.send(self.owner, "post", RULES, self.rule_payload(min_qty=bad))
                self.assertEqual(response.status_code, 400)
                self.assertIn("lớn hơn 0", " ".join(response.json()["min_qty"]))
        self.assertEqual(PricingRule.objects.count(), 0)

    def test_n13_3_discount_value_must_be_positive(self):
        for bad in ("0", "-5"):
            with self.subTest(discount_value=bad):
                response = self.send(self.owner, "post", RULES, self.rule_payload(discount_value=bad))
                self.assertEqual(response.status_code, 400)
                self.assertIn("lớn hơn 0", " ".join(response.json()["discount_value"]))
        self.assertEqual(PricingRule.objects.count(), 0)

    def test_n13_3_patch_to_zero_is_400(self):
        rule = self.add_rule()
        self.assertEqual(self.send(self.owner, "patch", f"{RULES}{rule.pk}/", {"min_qty": "0"}).status_code, 400)
        self.assertEqual(self.send(self.owner, "patch", f"{RULES}{rule.pk}/", {"discount_value": "0"}).status_code, 400)

    def test_n13_3_order_rule_without_min_qty_is_still_fine(self):
        response = self.send(self.owner, "post", RULES, {
            "name": "Đơn lớn", "apply_on": "ORDER", "min_amount": "500000", "discount_type": "AMOUNT",
            "discount_value": "20000"})
        self.assertEqual(response.status_code, 201, response.content)


class ItemGroupCycleTests(CatalogApiBase):
    def test_n13_3_group_cannot_be_its_own_parent(self):
        response = self.send(self.owner, "patch", f"{GROUPS}{self.group_fish.pk}/", {"parent": self.group_fish.pk})
        self.assertEqual(response.status_code, 400)
        self.assertIn("parent", response.json())
        self.group_fish.refresh_from_db()
        self.assertIsNone(self.group_fish.parent_id)

    def test_n13_3_group_cannot_take_its_child_or_grandchild_as_parent(self):
        grandchild = ItemGroup.objects.create(name="Cá thu nhóm", parent=self.group_child)
        for new_parent in (self.group_child, grandchild):
            response = self.send(self.owner, "patch", f"{GROUPS}{self.group_fish.pk}/", {"parent": new_parent.pk})
            self.assertEqual(response.status_code, 400, new_parent.name)
        self.group_fish.refresh_from_db()
        self.assertIsNone(self.group_fish.parent_id)

    def test_n13_3_cycle_message_is_vietnamese_and_does_not_echo_names(self):
        response = self.send(self.owner, "patch", f"{GROUPS}{self.group_fish.pk}/", {"parent": self.group_child.pk})
        message = " ".join(response.json()["parent"])
        self.assertIn("nhóm", message.lower())
        self.assertNotIn("Cá biển", message)

    def test_n13_3_valid_moves_still_work(self):
        moved = self.send(self.owner, "patch", f"{GROUPS}{self.group_child.pk}/", {"parent": self.group_shrimp.pk})
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(moved.json()["parent_name"], "Tôm")
        cleared = self.send(self.owner, "patch", f"{GROUPS}{self.group_child.pk}/", {"parent": None})
        self.assertEqual(cleared.status_code, 200)
        created = self.send(self.owner, "post", GROUPS, {"name": "Mực", "parent": self.group_child.pk})
        self.assertEqual(created.status_code, 201)

    def test_n13_3_cycle_check_terminates_on_legacy_cycle_data(self):
        ItemGroup.objects.filter(pk=self.group_fish.pk).update(parent=self.group_child)  # dữ liệu cũ đã vòng
        response = self.send(self.owner, "patch", f"{GROUPS}{self.group_shrimp.pk}/", {"parent": self.group_fish.pk})
        self.assertIn(response.status_code, (200, 400))  # quan trọng: không treo, không 500
