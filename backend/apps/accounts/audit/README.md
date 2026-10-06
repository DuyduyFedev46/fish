# accounts/audit — Endpoint nhật ký hành động (S03)

| File | Vai trò |
|---|---|
| `api.py` | `GET /api/audit-logs/` — quyền `accounts.view_auditlog` (owner + manager), lọc `?actor_kind=`/`?action=`/`?actor=`, `?date_from=&date_to=` (YYYY-MM-DD, giờ VN, gồm cả hai ngày) và `?q=` (chỉ mã chứng từ, 2–40 ký tự `[0-9A-Za-z#._-]`, dãy từ 9 chữ số trở lên → 400 để không tra bằng SĐT; khớp `object_repr`/`proposal_ref`), sai tham số → 400 `INVALID_FILTER`, phân trang StandardPagination; append-only (chỉ GET) |
| `serializers.py` | `audit_item(row)` — `actor_display` dòng AI = `ai:<tên user>`; field tường minh theo contract 02b mục 3 |
| `tests/test_s03_auditlog.py` | S03-AC1…AC5: schema, `record_audit` 3 loại actor, quyền 403, append-only 405, không PII trong dòng audit đụng đơn |
| `tests/test_date_and_code_filters.py` | Lô 17a (ED-41-AC2): biên giờ VN, `q` chỉ mã, 400 không lặp lại giá trị gửi lên |
| `tests/test_s03_migration.py` | MigrationExecutor: backfill `actor_kind` không mất dữ liệu cũ (bất biến 8) |

Model `AuditLog` (3 field mới) ở `apps/accounts/models.py`, migration `0007_auditlog_ai_actor`
(backfill + gán quyền theo mẫu 0002/0006). `record_audit()` ở `apps/common/audit.py` mở tham số
`actor_kind`/`ai_actor`/`proposal_ref` — chữ ký cũ tương thích, không đổi call-site.
