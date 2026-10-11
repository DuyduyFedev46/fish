"""
Lượt dùng mã giảm giá của một đơn (SHOP-3b-04, BR-DM-19, 20). KHÔNG có tên, SĐT hay địa chỉ (bất biến 9):
đơn nào dùng mã nào thì tra qua `order`, ảnh chụp mã và tiền giảm đóng băng ở đây.
"""
from django.db import models


class VoucherRedemption(models.Model):
    class State(models.TextChoices):
        HELD = "HELD", "Đang giữ"
        USED = "USED", "Đã dùng"
        RELEASED = "RELEASED", "Đã nhả"

    order = models.OneToOneField("sales.SalesOrder", on_delete=models.PROTECT, related_name="voucher_redemption")
    voucher = models.ForeignKey("catalog.Voucher", on_delete=models.PROTECT, related_name="redemptions")
    code = models.CharField("Mã (ảnh chụp)", max_length=20)
    discount_amount = models.DecimalField("Tiền giảm (đóng băng)", max_digits=14, decimal_places=2)
    state = models.CharField("Trạng thái", max_length=10, choices=State.choices, default=State.HELD)
    held_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Lượt dùng mã giảm giá"
        verbose_name_plural = "Lượt dùng mã giảm giá"
        default_permissions = ()
        indexes = [models.Index(fields=["voucher", "state"])]

    def __str__(self):
        return f"{self.code} · {self.state}"
