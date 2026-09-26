"""
Giao hàng (P-06). 100% giao tận nhà bởi nhân viên nội bộ.

- BR-GH-01: người giao là nhân viên nội bộ, FK trỏ `User` (StaffProfile cấp SĐT).
- BR-GH-03: số kg cân khi soạn = số kg khách đặt (giả định V1, chưa kiểm chứng —
  KHÔNG có field "số kg thực xuất").
- Phạm vi dòng (1.6): nv_giao chỉ thấy & chỉ sửa TRẠNG THÁI phiếu gán cho mình.
"""
from django.conf import settings
from django.db import models


class DeliveryNote(models.Model):
    class Status(models.TextChoices):
        PREPARING = "PREPARING", "Soạn hàng"
        READY = "READY", "Chờ lấy hàng"
        DELIVERING = "DELIVERING", "Đang giao"
        COMPLETED = "COMPLETED", "Hoàn tất"      # điểm không quay lui (BR-GH-05)
        FAILED = "FAILED", "Giao thất bại"       # trạng thái tạm (BR-GH-04)
        CANCELLED = "CANCELLED", "Đã huỷ theo đơn"  # S14: đơn bị huỷ (BR-GH-07), không quay lui

    code = models.CharField("Mã phiếu giao", max_length=32, unique=True)
    sales_invoice = models.ForeignKey(
        "sales.SalesInvoice", on_delete=models.PROTECT, related_name="delivery_notes",
        verbose_name="Hoá đơn",
    )
    status = models.CharField(
        "Trạng thái", max_length=12, choices=Status.choices, default=Status.PREPARING
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="deliveries", verbose_name="Nhân viên giao",  # BR-GH-01
    )
    failed_attempts = models.PositiveSmallIntegerField("Số lần giao thất bại", default=0)
    note = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField("Thời điểm hoàn tất", null=True, blank=True)

    class Meta:
        verbose_name = "Phiếu giao hàng"
        verbose_name_plural = "Phiếu giao hàng"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.code
