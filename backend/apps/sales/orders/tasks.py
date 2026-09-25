"""
Job nền đơn hàng (Celery).

`cancel_expired_orders` — nhả giữ chỗ của đơn quá TTL (BR-BH-03). IDEMPOTENT
(BR-BH-04): chạy trùng không huỷ nhầm. Job này chết thì hàng bị khoá vô hình →
xem command `check_ttl_job_health` để giám sát/cảnh báo.

Tên task giữ nguyên "apps.sales.tasks.cancel_expired_orders" (CELERY_BEAT_SCHEDULE và
hàng đợi đang dùng tên này) dù code đã chuyển vào module orders.
"""
import logging

from celery import shared_task

from . import services

logger = logging.getLogger("cangca.sales.ttl")


@shared_task(name="apps.sales.tasks.cancel_expired_orders")
def cancel_expired_orders():
    n = services.cancel_unpaid_expired()
    if n:
        logger.info("Đã tự huỷ %s đơn quá TTL, nhả giữ chỗ.", n)
    return n
