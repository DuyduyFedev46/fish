"""Khách hàng (7.1): guest checkout — gộp/khởi tạo Customer theo số điện thoại."""
from apps.sales.models import Customer


def get_or_create_by_phone(*, phone, name="", default_address=""):
    """
    Số điện thoại là khoá tự nhiên của khách. Khách cũ chưa có tên thì điền tên mới;
    không ghi đè tên/địa chỉ đã có. Gọi bên trong transaction của create_order.
    """
    customer, created = Customer.objects.get_or_create(
        phone=phone,
        defaults={"name": name or "", "default_address": default_address or ""},
    )
    if not created and name and not customer.name:
        customer.name = name
        customer.save(update_fields=["name"])
    return customer
