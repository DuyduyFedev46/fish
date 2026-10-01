"""Dữ liệu nền cho test API danh mục & giá (R14, 02b §3.8, Lô 13). Mọi dữ liệu là giả."""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.accounts import roles
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList, PricingRule
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_batch, make_user
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier

# Mốc riêng: nếu giá vốn rò ra JSON thì tìm thấy chuỗi này.
COST_SENTINEL = "80000"  # = purchase_rate của lô do make_batch tạo
SELL_RATE = Decimal("120000")

# `rate` nằm trong COST_KEYS nhưng ở đây là giá BÁN (ItemPrice.rate) nên được phép.
COST_KEYS_FOR_LEAK_SCAN = COST_KEYS - {"rate"}


def today():
    return timezone.localdate()


def find_cost_keys(data):
    """Quét đệ quy JSON, trả tập khoá giá vốn tìm thấy (không tính `rate` = giá bán)."""
    found = set()
    if isinstance(data, dict):
        for key, value in data.items():
            if key in COST_KEYS_FOR_LEAK_SCAN:
                found.add(key)
            found |= find_cost_keys(value)
    elif isinstance(data, list):
        for value in data:
            found |= find_cost_keys(value)
    return found


class CatalogApiBase(TestCase):
    def setUp(self):
        self.group_fish = ItemGroup.objects.create(name="Cá")
        self.group_shrimp = ItemGroup.objects.create(name="Tôm")
        self.group_child = ItemGroup.objects.create(name="Cá biển", parent=self.group_fish)
        self.item_a = Item.objects.create(code="CA01", name="Cá thu", item_group=self.group_fish)
        self.item_b = Item.objects.create(
            code="TOM01", name="Tôm sú", item_group=self.group_shrimp, is_active=False
        )
        self.combo = Item.objects.create(
            code="CB01", name="Combo thử", item_group=self.group_fish, item_type=Item.ItemType.BUNDLE
        )
        self.price_list = PriceList.objects.create(name="Bán lẻ", is_default=True)
        self.owner = make_user("u_owner", roles.OWNER)
        self.manager = make_user("u_manager", roles.MANAGER)
        self.warehouse_staff = make_user("u_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("u_courier", roles.DELIVERY_STAFF)
        self.customer_service = make_user("u_cs", roles.CUSTOMER_SERVICE)
        self.no_group = User.objects.create_user("u_no_group", password="x")
        self.everyone = (
            self.owner, self.manager, self.warehouse_staff, self.courier, self.customer_service, self.no_group,
        )

    # --- dựng dữ liệu -----------------------------------------------------------------------------------------
    def add_price(self, item, rate=SELL_RATE, *, valid_from=None, valid_upto=None, price_list=None):
        return ItemPrice.objects.create(
            price_list=price_list or self.price_list, item=item, rate=Decimal(rate),
            valid_from=valid_from or today() - datetime.timedelta(days=30), valid_upto=valid_upto,
        )

    def add_costed_batch(self, item):
        """Lô có giá nhập mốc, để chắc không đường nào kéo giá vốn vào JSON danh mục."""
        sup = Supplier.objects.get_or_create(name="Đầu mối A")[0]
        wh = Warehouse.objects.get_or_create(name="Kho chính")[0]
        return make_batch(item, sup, wh)

    def add_rule(self, **overrides):
        data = dict(
            name="Mua nhiều giảm giá", apply_on=PricingRule.ApplyOn.ITEM, item=self.item_a,
            min_qty=Decimal("5"), discount_type=PricingRule.DiscountType.PERCENT,
            discount_value=Decimal("10"),
        )
        data.update(overrides)
        return PricingRule.objects.create(**data)

    # --- gọi API ----------------------------------------------------------------------------------------------
    def get(self, user, url, **params):
        return client_for(user).get(url, params)

    def send(self, user, method, url, data=None):
        return getattr(client_for(user), method)(url, data or {}, format="json")

    def ids(self, response):
        return {row["id"] for row in response.json()["results"]}

    def assert_invalid_filter(self, response, secret):
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["code"], "INVALID_FILTER")
        self.assertNotIn(secret, body["detail"])
