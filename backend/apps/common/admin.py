"""
Tiện ích Django Admin dùng chung — S9 (BR-PQ-14, BR-PQ-05, BR-PQ-16).

Admin là đường cứu hộ/cấu hình (Duy chốt Q3), không phải cửa sau đổi trạng thái / tồn /
giá vốn / người phụ trách:
- Người KHÔNG phải superuser (kể cả Chủ): `locked_fields` + `actor_fields` chỉ đọc. Django
  bỏ qua giá trị của field chỉ đọc trong POST, nên DB không đổi.
- Superuser: sửa được, nhưng mọi thay đổi ở các field đó ghi AuditLog `admin_edit`
  `{field: {"from", "to"}}` (FK ghi theo id).
- `actor_fields` (người ghi chứng từ): người thường tạo trong Admin → hệ thống ghi theo người
  đăng nhập (BR-PQ-16).
- `superuser_only_add`: chứng từ chỉ sinh từ nghiệp vụ (lô từ phiếu nhập, phiếu giao từ hoá đơn,
  giao dịch từ webhook, phiếu hoàn từ service) → người thường không tạo tay trong Admin.
"""
from apps.common.audit import record_audit

ADMIN_EDIT_ACTION = "admin_edit"


class LockedFieldsAdminMixin:
    locked_fields: tuple = ()
    actor_fields: tuple = ()
    superuser_only_add: bool = False

    def _guarded_fields(self):
        return (*self.locked_fields, *self.actor_fields)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly += [f for f in self._guarded_fields() if f not in readonly]
        return readonly

    def has_add_permission(self, request):
        if self.superuser_only_add and not request.user.is_superuser:
            return False
        return super().has_add_permission(request)

    def save_model(self, request, obj, form, change):
        user = request.user
        if not change and not user.is_superuser:
            for name in self.actor_fields:
                setattr(obj, name, user)
        changes = self._guarded_changes(obj) if change and user.is_superuser else {}
        super().save_model(request, obj, form, change)
        if changes:
            record_audit(
                ADMIN_EDIT_ACTION, actor=user, obj=obj, changes=changes,
                note="Superuser sửa trực tiếp trong Django Admin (đường cứu hộ, BR-PQ-05).",
            )

    def _guarded_changes(self, obj):
        old = type(obj)._default_manager.get(pk=obj.pk)
        changes = {}
        for name in self._guarded_fields():
            attname = obj._meta.get_field(name).attname
            before, after = getattr(old, attname), getattr(obj, attname)
            if before != after:
                changes[name] = {"from": before, "to": after}
        return changes
