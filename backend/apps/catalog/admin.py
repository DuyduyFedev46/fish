from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .images.serializers import image_urls
from .items.public_text import PUBLIC_TEXT_LIMITS, public_text_error
from .models import BundleLine, Item, ItemGroup, ItemPrice, PriceList, PricingRule


class BundleLineInline(admin.TabularInline):
    model = BundleLine
    fk_name = "bundle"
    extra = 1
    autocomplete_fields = ("component",)


@admin.register(ItemGroup)
class ItemGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    search_fields = ("name",)


class ItemAdminForm(forms.ModelForm):
    """Review lô 2 L1: 5 ô chữ công khai qua cùng kiểm BR-DM-25 như API."""

    class Meta:
        model = Item
        fields = "__all__"  # naming: allow - ModelForm admin nội bộ, không phải serializer API

    def _clean_public(self, name):
        value = self.cleaned_data.get(name, "")
        limit = PUBLIC_TEXT_LIMITS[name]
        if len(value) > limit:
            raise forms.ValidationError(f"Tối đa {limit} ký tự.")
        error = public_text_error(value)
        if error:
            raise forms.ValidationError(error)
        return value

    def clean_short_note(self):
        return self._clean_public("short_note")

    def clean_spec(self):
        return self._clean_public("spec")

    def clean_storage(self):
        return self._clean_public("storage")

    def clean_origin(self):
        return self._clean_public("origin")

    def clean_description(self):
        return self._clean_public("description")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    form = ItemAdminForm
    list_display = ("code", "name", "item_group", "item_type", "stock_uom", "is_active")
    list_filter = ("item_type", "item_group", "is_active")
    search_fields = ("code", "name")
    inlines = [BundleLineInline]
    # A2-AC18: Admin chỉ XEM ảnh (không có widget tải lên) — tải/thay/gỡ ảnh bắt buộc đi
    # qua `apps.catalog.images.services` để kiểm tệp (BR-DM-10) và ghi AuditLog (BR-DM-12).
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if not obj or not obj.pk:
            return "—"
        image = getattr(obj, "image", None)
        if image is None:
            return "Chưa có ảnh (dùng console hoặc API để tải lên)."
        urls = image_urls(obj.pk, image.image_id)
        illustration = " · Ảnh minh hoạ" if image.is_illustration else ""
        return format_html(
            '<img src="{}" alt="{}" style="max-height:120px" />{}',
            urls["thumb"], image.alt_text, illustration,
        )

    image_preview.short_description = "Ảnh (chỉ xem)"

    def get_inline_instances(self, request, obj=None):
        # Chỉ hiện công thức khi là BUNDLE.
        if obj and obj.is_bundle:
            return super().get_inline_instances(request, obj)
        return []


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ("name", "currency", "is_default")


@admin.register(ItemPrice)
class ItemPriceAdmin(admin.ModelAdmin):
    list_display = ("item", "price_list", "rate", "valid_from", "valid_upto")
    list_filter = ("price_list",)
    search_fields = ("item__code", "item__name")
    autocomplete_fields = ("item",)


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "apply_on", "discount_type", "discount_value", "is_active")
    list_filter = ("apply_on", "discount_type", "is_active")
    autocomplete_fields = ("item",)
