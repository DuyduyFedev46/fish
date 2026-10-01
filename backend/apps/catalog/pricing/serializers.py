"""
Serializer bảng giá, giá niêm yết, ưu đãi (R14). Chỉ có giá BÁN và mức giảm, không có field giá vốn.

Quyền ghi giá bán và ưu đãi là Tầng 1 (`add/change_itemprice`, `add/change_pricingrule`), chỉ Chủ có (T9);
phần kiểm dữ liệu ở đây là để màn Đặt giá / Tạo ưu đãi báo lỗi nói rõ cách sửa (ED-31-AC3).
"""
from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import ItemPrice, PriceList, PricingRule

MAX_PERCENT = Decimal("100")
RATE_MESSAGE = "Giá bán phải lớn hơn 0. Hãy nhập lại giá bán."
MIN_QTY_MESSAGE = "Số kg tối thiểu phải lớn hơn 0. Hãy nhập lại số kg tối thiểu."
DISCOUNT_VALUE_MESSAGE = "Mức giảm phải lớn hơn 0. Hãy nhập lại mức giảm."


class PriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceList
        fields = ["id", "name", "currency", "is_default"]


class _MergedValuesMixin:
    """`validate` thấy cả giá trị đang lưu khi PATCH một phần (chỉ gửi vài field)."""

    def merged(self, attrs, name):
        if name in attrs:
            return attrs[name]
        return getattr(self.instance, name, None) if self.instance is not None else None


def _check_date_order(merged, attrs):
    errors = {}
    valid_from, valid_upto = merged(attrs, "valid_from"), merged(attrs, "valid_upto")
    if valid_from and valid_upto and valid_upto < valid_from:
        errors["valid_upto"] = "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu. Hãy chọn lại ngày kết thúc."
    return errors


class ItemPriceSerializer(_MergedValuesMixin, serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_code = serializers.CharField(source="item.code", read_only=True)

    class Meta:
        model = ItemPrice
        fields = ["id", "price_list", "item", "item_name", "item_code", "rate", "valid_from", "valid_upto"]
        # Model có MinValueValidator(0): số âm bị chặn ở đó, nên đổi lời báo sang tiếng Việt; số 0 do validate_rate chặn.
        extra_kwargs = {"rate": {"error_messages": {"min_value": RATE_MESSAGE}}}

    def validate_rate(self, value):
        if value <= 0:
            raise serializers.ValidationError(RATE_MESSAGE)
        return value

    def validate(self, attrs):
        errors = _check_date_order(self.merged, attrs)
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class PricingRuleSerializer(_MergedValuesMixin, serializers.ModelSerializer):
    # Mặt hàng điều kiện: null với ưu đãi theo đơn (BR-DM-08).
    item_name = serializers.CharField(source="item.name", read_only=True, default=None)

    class Meta:
        model = PricingRule
        fields = [
            "id", "name", "is_active", "apply_on", "item", "item_name", "min_qty", "min_amount",
            "discount_type", "discount_value", "valid_from", "valid_upto",
        ]
        extra_kwargs = {
            "min_qty": {"error_messages": {"min_value": MIN_QTY_MESSAGE}},
            "discount_value": {"error_messages": {"min_value": DISCOUNT_VALUE_MESSAGE}},
        }

    def validate(self, attrs):
        # Tắt một ưu đãi cũ sai dữ liệu (API trước Lô 13 nhận) phải được, nên không kiểm gì khác.
        if self.instance is not None and set(attrs) == {"is_active"} and attrs["is_active"] is False:
            return attrs
        errors = _check_date_order(self.merged, attrs)
        apply_on = self.merged(attrs, "apply_on")
        if apply_on == PricingRule.ApplyOn.ITEM:
            if not self.merged(attrs, "item"):
                errors["item"] = "Ưu đãi theo mặt hàng phải chọn mặt hàng."
            if self.merged(attrs, "min_qty") is None:
                errors["min_qty"] = "Nhập số kg tối thiểu cho ưu đãi theo mặt hàng."
        elif apply_on == PricingRule.ApplyOn.ORDER and self.merged(attrs, "min_amount") is None:
            errors["min_amount"] = "Nhập giá trị đơn tối thiểu cho ưu đãi theo đơn."
        min_qty = self.merged(attrs, "min_qty")
        if min_qty is not None and min_qty <= 0:
            errors["min_qty"] = MIN_QTY_MESSAGE
        discount_type, value = self.merged(attrs, "discount_type"), self.merged(attrs, "discount_value")
        if value is not None and value <= 0:
            errors["discount_value"] = DISCOUNT_VALUE_MESSAGE
        if discount_type == PricingRule.DiscountType.PERCENT and value is not None and value > MAX_PERCENT:
            errors["discount_value"] = "Phần trăm giảm không được lớn hơn 100. Hãy nhập lại từ 0 đến 100."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
