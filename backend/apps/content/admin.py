"""Admin cứu hộ (chỉ đọc) cho app content (§1.1 02b-tech-design)."""
from django.contrib import admin
from apps.content.models import Category, Entry, EntryVersion, ContentImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "order", "is_active", "created_at")
    search_fields = ("name", "slug")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "kind", "status", "slug", "first_published_at", "updated_at")
    list_filter = ("kind", "status")
    search_fields = ("title", "slug")
    readonly_fields = ("created_at", "updated_at", "row_version", "draft_hash")


@admin.register(EntryVersion)
class EntryVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "entry_id", "version", "kind", "title", "published_at", "published_by")
    readonly_fields = ("published_at", "published_by")


@admin.register(ContentImage)
class ContentImageAdmin(admin.ModelAdmin):
    list_display = ("id", "entry_id", "image_id", "alt", "created_at")
    readonly_fields = ("created_at",)
