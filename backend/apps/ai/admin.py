from django.contrib import admin
from .models import AiConfigVersion, AiPolicyVersion, AiAction


class ReadOnlyAiAdmin(admin.ModelAdmin):
    """Admin chỉ đọc cho các bản ghi AI (02b §7.1 - §7.3). Không cho sửa/xoá."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AiConfigVersion)
class AiConfigVersionAdmin(ReadOnlyAiAdmin):
    list_display = ("user", "version", "killed", "created_by", "created_at")
    search_fields = ("user__username",)
    list_filter = ("killed",)


@admin.register(AiPolicyVersion)
class AiPolicyVersionAdmin(ReadOnlyAiAdmin):
    list_display = ("version", "global_mode", "created_by", "created_at")
    list_filter = ("global_mode",)


@admin.register(AiAction)
class AiActionAdmin(ReadOnlyAiAdmin):
    list_display = ("id", "command", "kind", "level", "status", "owner", "created_at")
    search_fields = ("command", "owner__username", "id")
    list_filter = ("status", "kind", "level")
