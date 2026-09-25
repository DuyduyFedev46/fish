# common — Dùng chung cho mọi app (không có model)

`api.py`: phân quyền Tầng 1 (`BusinessModelPermissions`), ẩn giá vốn (`CostFieldSerializerMixin`),
khoá field/actor (`DocumentViewSet`, BR-PQ-14/16), `require_perm`, đổi `BusinessError` → HTTP 400.
`admin.py`: `LockedFieldsAdminMixin` (S9) — field trạng thái/tồn/giá vốn/người phụ trách chỉ đọc trong Django Admin với người không phải superuser; superuser sửa được nhưng ghi AuditLog `admin_edit`.
`exceptions.py`: `BusinessError` (thông điệp tiếng Việt + mã BR). `audit.py`: `record_audit`. `actors.py`: `actor=None` = Hệ thống.
`tests/`: test xuyên app của lô L2 (S3 khoá field, S4 người tạo, S5 phạm vi nv_giao) + S9 khoá field Admin + `fixtures.py` dựng dữ liệu test.
