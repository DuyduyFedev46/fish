from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Cá Về — Quản trị"
admin.site.site_title = "Cá Về"
admin.site.index_title = "Vận hành mua – bán – kho"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("config.api_urls")),
    path("api-auth/", include("rest_framework.urls")),  # login form cho browsable API
]
