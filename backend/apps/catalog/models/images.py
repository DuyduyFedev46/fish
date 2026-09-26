"""Ảnh mặt hàng (A1/A2/A3, BR-DM-09..16).

Bảng riêng (không phải field JSON trên `Item`) để sau này mở rộng lên nhiều ảnh
(01-analysis §7 gợi ý của BA) mà không phải chuyển đổi dữ liệu: chỉ cần bỏ ràng buộc
1-1 (`OneToOneField` -> `ForeignKey`, Django coi OneToOneField là ForeignKey đã có sẵn
`unique=True`) và thêm field thứ tự / ảnh đại diện. Hiện tại (Q2) mỗi mặt hàng đúng 1 ảnh.

Ảnh KHÔNG phải chứng từ (BR-PQ-10 không áp dụng): xoá bản ghi này không vi phạm bất biến
"chứng từ không xoá" — file ở kho ảnh vẫn được giữ lại theo BR-DM-14 (services xử lý,
model không tự xoá object ở storage).
"""
import secrets

from django.conf import settings
from django.db import models


def generate_image_id() -> str:
    """Id công khai không đoán được, dùng làm tên thư mục object trong bucket."""
    return f"img_{secrets.token_hex(4)}"


class ItemImage(models.Model):
    item = models.OneToOneField(
        "catalog.Item",
        on_delete=models.CASCADE,
        related_name="image",
        verbose_name="Mặt hàng",
    )
    image_id = models.CharField(
        "Mã ảnh", max_length=32, unique=True, default=generate_image_id, editable=False
    )
    alt_text = models.CharField("Alt text", max_length=125, blank=True)
    is_illustration = models.BooleanField("Ảnh minh hoạ", default=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # bất biến 3: FK tới User luôn PROTECT
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Người tải lên",
    )
    created_at = models.DateTimeField("Tải lên lúc", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    class Meta:
        verbose_name = "Ảnh mặt hàng"
        verbose_name_plural = "Ảnh mặt hàng"

    def __str__(self):
        return f"{self.item.code} · {self.image_id}"
