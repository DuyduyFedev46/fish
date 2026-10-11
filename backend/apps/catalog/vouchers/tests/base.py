"""Dữ liệu nền cho test mã giảm giá (SHOP-3b). Toàn bộ dữ liệu giả."""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone

from apps.accounts import roles
from apps.catalog.models import Voucher
from apps.common.tests.fixtures import client_for, make_user


def make_voucher(*, owner=None, **overrides) -> Voucher:
    """Mã đang chạy: CAVE10, 10%, trần 50.000, đơn tối thiểu 300.000, 100 lượt, hiệu lực quanh bây giờ."""
    now = timezone.now()
    owner = owner or User.objects.filter(username="voucher_maker").first() or make_user("voucher_maker", roles.OWNER)
    fields = dict(
        code="CAVE10", name="Khai trương", kind=Voucher.Kind.PERCENT, value=Decimal("10"),
        max_discount=Decimal("50000"), min_order_amount=Decimal("300000"),
        starts_at=now - datetime.timedelta(days=1), ends_at=now + datetime.timedelta(days=10),
        total_uses=100, customer_terms="Áp dụng cho đơn từ 300.000đ.", created_by=owner,
    )
    fields.update(overrides)
    return Voucher.objects.create(**fields)


def create_body(**overrides) -> dict:
    """Thân POST tạo mã hợp lệ (giờ ISO có múi giờ +07:00)."""
    now = timezone.now()
    body = {
        "code": "CAVE10", "name": "Khai trương", "kind": "PERCENT", "value": "10", "max_discount": "50000",
        "min_order_amount": "300000",
        "starts_at": (now + datetime.timedelta(days=1)).astimezone(datetime.timezone(datetime.timedelta(hours=7))).isoformat(),
        "ends_at": (now + datetime.timedelta(days=15)).astimezone(datetime.timezone(datetime.timedelta(hours=7))).isoformat(),
        "total_uses": 100, "customer_terms": "Áp dụng cho đơn từ 300.000đ.",
    }
    body.update(overrides)
    return body


class VoucherUsers:
    """Mỗi vai một user + client; `owner` là Chủ."""

    def make_users(self):
        self.owner = make_user("chu1", roles.OWNER)
        self.manager = make_user("ql1", roles.MANAGER)
        self.warehouse = make_user("kho1", roles.WAREHOUSE_STAFF)
        self.courier = make_user("giao1", roles.DELIVERY_STAFF)
        self.service = make_user("cs1", roles.CUSTOMER_SERVICE)
        self.owner_client = client_for(self.owner)
