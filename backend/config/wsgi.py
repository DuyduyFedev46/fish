import os

from django.conf import settings
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

# M-4/B11: web production không khởi động với token nội bộ yếu (job manage.py không đi qua đây).
if not settings.DEBUG:
    from apps.common.startup_checks import validate_internal_service_token

    validate_internal_service_token(settings.INTERNAL_SERVICE_TOKEN)
