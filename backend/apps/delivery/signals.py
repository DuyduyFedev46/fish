"""
Tự tạo phiếu giao khi hoá đơn bán được xuất (P-06 nối sau P-05).
Đây là chỗ "wire ở tầng delivery" — issue_invoice KHÔNG tự tạo DeliveryNote để giữ
sales/delivery tách biệt.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.sales.models import SalesInvoice

from . import services


@receiver(post_save, sender=SalesInvoice, dispatch_uid="create_delivery_note_on_invoice")
def create_delivery_note_on_invoice(sender, instance, created, **kwargs):
    if created and instance.status == SalesInvoice.Status.ISSUED:
        services.create_delivery_note(invoice=instance)
