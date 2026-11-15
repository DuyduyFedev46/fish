from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.common.throttling import throttle_admin_login

admin.site.site_header = "Cá Về — Quản trị"
admin.site.site_title = "Cá Về"
admin.site.index_title = "Vận hành mua – bán – kho"
# H-1: đăng nhập Admin có giới hạn tần suất như /api/auth/token/.
admin.site.login = throttle_admin_login(admin.site.login)

urlpatterns = [
    path("api/", include("config.api_urls")),
]
if settings.ADMIN_ENABLED:
    urlpatterns.insert(0, path("admin/", admin.site.urls))
if settings.DEBUG:
    # Form đăng nhập của browsable API: chỉ khi dev (H-1).
    urlpatterns.append(path("api-auth/", include("rest_framework.urls")))
