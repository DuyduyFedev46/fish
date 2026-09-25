# accounts — Nhân sự, phân quyền, nhật ký (§1)

`StaffProfile` (mở rộng User: SĐT…), `AuditLog` (append-only, BR-PQ-04/05/06), seed 4 Group
`chu`/`quan_ly`/`nv_kho`/`nv_giao` trong `migrations/0002`. App còn phẳng (`models.py`, `admin.py`).
`auth/`: `GET /api/auth/me/` (S6, S47 nhãn nhóm/việc), `POST /api/auth/logout/`, `POST /api/auth/change-password/` (S46). `staff/`: quản lý nhân viên `/api/staff/` (S41, S42 — BR-PQ-17/18).
`admin.py`: trang User/Group trong Admin chỉ superuser; superuser đổi nhóm ghi AuditLog `staff_groups_change`.
Migration `0003`: gán `reports.view_dashboard` cho chu/quan_ly/nv_kho (S6).
Command: `bootstrap_masterdata` (Kho chính + bảng giá Bán lẻ), `seed_demo` (dữ liệu demo):
`seed_demo` thêm (idempotent) · `seed_demo --remove [--dry-run] [--adopt-legacy]` gỡ CHỈ dữ liệu demo.
`demo/`: sổ đánh dấu `DemoRecord` (migration `0005`) + `services.track_demo_creations` /
`remove_demo` (D1 — ngoại lệ có chủ đích của BR-PQ-10, chỉ cho bản ghi demo).
Tập giữ lại tính theo bao đóng (QA lần 2 · B2): demo là "một phần" của bản ghi đang giữ (mọi FK ngoài `REFERENCE_FIELDS`) cũng giữ — chứng từ giữ cả cụm hoặc gỡ cả cụm.
Migration `0004`: `StaffProfile.must_change_password` (S48, BR-PQ-19; dữ liệu cũ = False).
