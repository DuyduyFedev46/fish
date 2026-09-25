from django.apps import AppConfig


class DeliveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.delivery"
    label = "delivery"
    verbose_name = "Giao hàng"

    def ready(self):
        from . import signals  # noqa: F401  (đăng ký signal tạo phiếu giao)
