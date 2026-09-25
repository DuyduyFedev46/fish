"""
Celery — chạy job nền, quan trọng nhất là huỷ đơn quá TTL (BR-BH-03/04).

Broker/backend cấu hình qua env (mặc định Redis local). Job huỷ TTL PHẢI idempotent
và GIÁM SÁT ĐƯỢC — xem apps/sales/orders/tasks.py và command check_ttl_job_health.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("cangca")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
