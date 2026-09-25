"""
Điểm vào cho Celery `autodiscover_tasks()` — Celery chỉ tìm `apps.<app>.tasks`.
Code thật ở `apps/sales/orders/tasks.py`; KHÔNG viết task mới ở đây.
"""
from apps.sales.orders.tasks import cancel_expired_orders  # noqa: F401
