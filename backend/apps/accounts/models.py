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

from apps.common.formatting import format_local_datetime


class StaffProfile(models.Model):
    """Hồ sơ nhân viên — mỏng có chủ đích (không lương/chấm công/KPI/hợp đồng)."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Đang làm"
        INACTIVE = "INACTIVE", "Đã nghỉ"

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

    S03 (AI Native ERP, BR-AI-08/Q6): phân biệt 3 loại tác nhân qua `actor_kind`:
    - user   — người bấm nút / xác nhận (actor = người đó).
    - system — job/webhook, actor = None.
    - ai     — AI đề xuất thay cho user nào (ai_actor), actor = None; dòng thực thi
               ghi actor=người xác nhận + `proposal_ref`/note mã đề xuất.
    Dòng AI hiển thị `ai:<tên user>` (BR-AI-14) — phục vụ giải trình Luật AI 134/2025.
    """

    class ActorKind(models.TextChoices):
        USER = "user", "Người"
        SYSTEM = "system", "Hệ thống"
        AI = "ai", "AI (thay người dùng)"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,  # None = Hệ thống (system) hoặc dòng AI (xem ai_actor)
        related_name="audit_logs",
        verbose_name="Người thực hiện",
    )
    actor_kind = models.CharField(
        "Loại tác nhân", max_length=10, choices=ActorKind.choices, default=ActorKind.USER
    )
    ai_actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",  # "AI thay cho user nào" (BR-AI-08)
        verbose_name="AI thay cho ai",
    )
    proposal_ref = models.CharField("Mã đề xuất AI", max_length=64, blank=True)
    ai_level = models.CharField("Mức tự chủ AI", max_length=1, blank=True, default="")
    ai_config_version = models.PositiveIntegerField(
        "Phiên bản cấu hình AI", null=True, blank=True
    )
    ai_policy_version = models.PositiveIntegerField(
        "Phiên bản chính sách AI", null=True, blank=True
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
        indexes = [
            models.Index(
                fields=["model_name", "object_id", "created_at"],
                name="auditlog_timeline_idx",
            ),
        ]

    def __str__(self):
        if self.actor_kind == self.ActorKind.AI:
            who = f"ai:{self.ai_actor.get_username()}" if self.ai_actor else "ai:?"
        else:
            who = self.actor.get_username() if self.actor else "system"
        return f"[{format_local_datetime(self.created_at)}] {who} · {self.action}"


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


class GroupAccessConfig(models.Model):
    """
    Một dòng cho mỗi nhóm quyền: khoá lạc quan cho MỌI lần lưu của nhóm (việc lẫn phạm vi), PV-02, 02b §3.

    `row_version` tăng 1 mỗi lần lưu có thay đổi thật; client gửi lại giá trị đã đọc, lệch thì 409 (Lô 5).
    Lý do thêm bảng (bất biến 8): `auth.Group` không có chỗ lưu số phiên bản; Duy chốt 02/10 (#9, #12, #13).
    CASCADE vì đây là cấu hình, không phải chứng từ (bất biến 3 chỉ áp FK tới User và chứng từ).
    """

    group = models.OneToOneField("auth.Group", on_delete=models.CASCADE, related_name="access_config")
    row_version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ()  # chỉ sửa qua service (Lô 5), không qua Admin hay ma trận Tầng 1

    def __str__(self):
        return f"cấu hình {self.group.name} v{self.row_version}"


class GroupDataScope(models.Model):
    """
    Phạm vi dữ liệu (Tầng 3) của nhóm × đối tượng, PV-02. `object_key` là khoá ở `data_scopes/catalog.py`
    (orders, deliveries, confirmation, returns, receipts, customers); `value` là một lựa chọn trong catalog.
    Không lưu dòng cho nhóm `owner` (luôn rộng nhất) và cho đối tượng suy ra (invoices, audit_log).
    """

    group = models.ForeignKey("auth.Group", on_delete=models.CASCADE, related_name="data_scopes")
    object_key = models.CharField(max_length=32)
    value = models.CharField(max_length=40)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(fields=["group", "object_key"], name="uniq_group_data_scope"),
        ]

    def __str__(self):
        return f"{self.group.name}/{self.object_key}={self.value}"
