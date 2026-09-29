from django.apps import AppConfig
from django.conf import settings
from django.core.checks import register, Tags


class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.content"
    verbose_name = "Nội dung & CMS"

    def ready(self):
        from apps.content.site.checks import check_seller_info

        @register(Tags.compatibility)
        def _seller_check(app_configs=None, **kwargs):
            if getattr(settings, "TESTING", False):
                return []
            return check_seller_info(app_configs, **kwargs)
