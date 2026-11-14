"""Dữ liệu nền cho test tải file mặt hàng (FISH-66 S3, S4). Mọi dữ liệu là giả."""
import datetime
import io
from decimal import Decimal

import openpyxl

from apps.catalog.items.tests.api_base import CatalogApiBase, today
from apps.catalog.models import ItemPrice
from apps.common.tests.fixtures import client_for, make_batch
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier

EXPORT_URL = "/api/catalog/items/export/"
TEMPLATE_URL = "/api/catalog/items/export-template/"

HEADERS_NO_PRICE = [
    "Mã hàng", "Tên", "Nhóm hàng", "Loại", "Đơn vị", "Đang kinh doanh", "Hạn dùng mặc định (ngày)",
    "Quản lý theo lô", "Có hạn dùng", "Ghi chú ngắn", "Quy cách", "Bảo quản", "Nguồn hàng", "Mô tả",
]
PRICE_HEADERS = ["Giá bán hiện hành", "Giá mới", "Ngày áp dụng giá mới"]
HEADERS_FULL = HEADERS_NO_PRICE + PRICE_HEADERS
SELL_PRICE = Decimal("278000")


def open_xlsx(response):
    """Mở file xlsx thật từ response (không đoán chuỗi trong bytes)."""
    return openpyxl.load_workbook(io.BytesIO(response.content))


def sheet_rows(response):
    wb = open_xlsx(response)
    return [list(row) for row in wb["Hàng bán"].iter_rows(values_only=True)]


class ItemFilesBase(CatalogApiBase):
    def setUp(self):
        super().setUp()
        ItemPrice.objects.create(
            item=self.item_a, price_list=self.price_list, rate=SELL_PRICE,
            valid_from=today() - datetime.timedelta(days=3),
        )
        # Lô có giá mua = COST_SENTINEL (80000) để dò rò giá vốn.
        make_batch(self.item_a, Supplier.objects.create(name="Đầu mối giả"), Warehouse.objects.create(name="Kho giả"))

    def client_as(self, user):
        return client_for(user)

    def get(self, user, url=EXPORT_URL, **params):
        return self.client_as(user).get(url, params, HTTP_ORIGIN="http://localhost:3001")
