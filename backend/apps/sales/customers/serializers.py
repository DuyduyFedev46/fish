"""Serializer khách hàng."""
from rest_framework import serializers

from apps.sales.models import Customer, Refund
from apps.sales.utils import money_str

DETAIL_LIST_LIMIT = 50  # đơn / phiếu hoàn mới nhất hiện ở chi tiết khách


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "phone", "name", "default_address", "note", "created_at"]
        read_only_fields = ["created_at"]


class CourierCustomerSerializer(serializers.ModelSerializer):
    """NV giao (SR-PII-02 AC4): chỉ thông tin cần để giao; không `note` nội bộ, không `default_address`
    (địa chỉ giao của chính đơn đã có ở chi tiết đơn). Read-only: nv_giao cũng không có quyền ghi."""

    class Meta:
        model = Customer
        fields = ["id", "phone", "name", "created_at"]
        read_only_fields = fields


# --- B2: danh bạ khách (`/api/sales/customer-directory/`), field liệt kê tường minh (bất biến 1, 9) ----------

class MoneyField(serializers.Field):
    """Tiền dạng chuỗi thập phân (bất biến 7)."""

    def to_representation(self, value):
        return money_str(value if value is not None else 0)


class DirectoryListSerializer(serializers.ModelSerializer):
    """Một dòng danh bạ. Đọc các số liệu từ annotate của `CustomerDirectoryViewSet.get_queryset`."""

    order_count = serializers.IntegerField(read_only=True)
    cancelled_count = serializers.IntegerField(read_only=True)
    total_spent = MoneyField(read_only=True)
    last_order_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = Customer
        fields = [
            "id", "name", "phone", "order_count", "total_spent", "cancelled_count", "last_order_at", "note",
        ]
        read_only_fields = fields


class DirectoryDetailSerializer(DirectoryListSerializer):
    first_order_at = serializers.DateTimeField(read_only=True, allow_null=True)
    orders = serializers.SerializerMethodField()
    refunds = serializers.SerializerMethodField()

    class Meta(DirectoryListSerializer.Meta):
        fields = DirectoryListSerializer.Meta.fields + [
            "default_address", "created_at", "first_order_at", "orders", "refunds",
        ]
        read_only_fields = fields

    def get_orders(self, customer):
        rows = customer.orders.order_by("-created_at", "-id")[:DETAIL_LIST_LIMIT]
        return [
            {
                "id": o.pk, "code": o.code, "status": o.status, "status_label": o.get_status_display(),
                "total_amount": money_str(o.total_amount), "created_at": o.created_at,
            }
            for o in rows
        ]

    def get_refunds(self, customer):
        rows = (
            Refund.objects.filter(sales_invoice__customer=customer)
            .select_related("sales_invoice__sales_order")
            .order_by("-created_at", "-id")[:DETAIL_LIST_LIMIT]
        )
        # Không có `reason`/`failure_reason` (chữ tự do, có thể chứa dữ liệu cá nhân): xem ở trang phiếu hoàn.
        return [
            {
                "id": r.pk, "order_code": r.sales_invoice.sales_order.code, "status": r.status,
                "status_label": r.get_status_display(), "amount": money_str(r.amount),
                "created_at": r.created_at,
            }
            for r in rows
        ]


class DirectoryUpdateSerializer(serializers.Serializer):
    """Đầu vào PATCH: chỉ bốn trường được sửa. Chuỗi, không nhận object/list. `phone` được chuẩn hoá ở service."""

    name = serializers.CharField(max_length=200, allow_blank=True, required=False)
    phone = serializers.CharField(max_length=40, allow_blank=True, required=False)
    default_address = serializers.CharField(allow_blank=True, required=False, max_length=1000)
    note = serializers.CharField(allow_blank=True, required=False, max_length=1000)
