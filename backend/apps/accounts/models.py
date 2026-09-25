"""
Nhân sự & phân quyền — StaffProfile, AuditLog.

Quyết định kiến trúc quan trọng (business-process-spec.md 1.8):
- Mọi FK nghiệp vụ (người giao, người nhập lô, người duyệt) TRỎ VÀO `User`.
  `StaffProfile` chỉ là OneToOne mở rộng — vì `User` không có số điện thoại.
- Chọn sai chiều FK này là cái đắt duy nhất trong toàn bộ mục phân quyền.

AuditLog (mục 1.10): Django `LogEntry` chỉ ghi thao tác trong Admin, không phủ
API — nên cần model riêng, append-only (BR-PQ-06).
"""
from django.conf import settings
from django.db import models


class StaffProfile(models.Model):
    """Hồ sơ nhân viên — mỏng có chủ đích (không lương/chấm công/KPI/hợp đồng)."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Đang làm"
        INACTIVE = "INACTIVE", "Nghỉ"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # BR-PQ-02: không xoá tài khoản, giữ vết chứng từ cũ
        related_name="staff_profile",
        verbose_name="Tài khoản",
    )
    phone = models.CharField("Số điện thoại", max_length=20)  # bắt buộc (1.8)
    display_name = models.CharField("Tên hiển thị", max_length=150, blank=True)
    joined_date = models.DateField("Ngày vào làm", null=True, blank=True)
    status = models.CharField(
        "Trạng thái", max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    note = models.TextField("Ghi chú", blank=True)
    # BR-PQ-19 (S48): Chủ tạo tài khoản / đặt lại mật khẩu → True; người đó tự đổi → False.
    # Khi True mọi API nghiệp vụ trả 403 AUTH_MUST_CHANGE_PASSWORD (trừ me/đổi mật khẩu/đăng xuất).
    must_change_password = models.BooleanField("Phải đổi mật khẩu", default=False)

    class Meta:
        verbose_name = "Hồ sơ nhân viên"
        verbose_name_plural = "Hồ sơ nhân viên"
        permissions = [
            ("manage_staff", "Quản lý nhân viên (tạo tài khoản, đổi Group)"),
        ]

    def __str__(self):
        return self.display_name or self.user.get_username()


class AuditLog(models.Model):
    """
    Nhật ký hành động nhạy cảm — append-only (BR-PQ-06: không sửa, không xoá).

    Ghi mọi permission Tầng 2 (BR-PQ-04) và mọi thay đổi `Batch.landed_unit_cost`
    + mọi chuyển trạng thái `Refund` (BR-PQ-05). Actor = None nghĩa là Hệ thống
    (job huỷ TTL, webhook) — không mượn tài khoản người (BR-PQ-07).
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,  # None = Hệ thống (system)
        related_name="audit_logs",
        verbose_name="Người thực hiện",
    )
    action = models.CharField("Hành động", max_length=100)  # vd: confirm_refund, close_batch
    model_name = models.CharField("Loại chứng từ", max_length=100, blank=True)
    object_id = models.CharField("Mã đối tượng", max_length=64, blank=True)
    object_repr = models.CharField("Mô tả đối tượng", max_length=255, blank=True)
    changes = models.JSONField("Giá trị trước → sau", default=dict, blank=True)
    note = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField("Thời điểm", auto_now_add=True)

    class Meta:
        verbose_name = "Nhật ký hành động"
        verbose_name_plural = "Nhật ký hành động"
        ordering = ["-created_at"]
        default_permissions = ("view",)  # BR-PQ-06: chỉ xem, không add/change/delete

    def __str__(self):
        who = self.actor.get_username() if self.actor else "system"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {who} · {self.action}"


class DemoRecord(models.Model):
    """
    Sổ đánh dấu dữ liệu demo (D1, Duy 2026-09-24) — `manage.py seed_demo` ghi mọi bản ghi nó
    TẠO MỚI vào đây; `seed_demo --remove` chỉ gỡ bản ghi có trong sổ.

    Vì sao cần bảng riêng (không dùng tiền tố mã/ghi chú): dữ liệu demo nằm ở nhiều model không
    có trường ghi chú chung (Item, Customer, Batch, ItemPrice, phiếu giao do signal sinh…), và
    `seed_demo` dùng get_or_create — bản ghi THẬT trùng mã không được bị nhận nhầm là demo.
    Sổ chỉ ghi bản ghi seed thật sự tạo ra, nên nhận diện chắc chắn.
    """

    content_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.CASCADE, verbose_name="Loại bản ghi"
    )
    object_id = models.CharField("Mã bản ghi", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bản ghi demo"
        verbose_name_plural = "Bản ghi demo"
        default_permissions = ("view",)
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"], name="uniq_demo_record"
            )
        ]

    def __str__(self):
        return f"demo {self.content_type.model}#{self.object_id}"
