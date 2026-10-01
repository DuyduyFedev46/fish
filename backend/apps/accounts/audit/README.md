# accounts/audit — Endpoint nhật ký hành động (S03)

| File | Vai trò |
|---|---|
| `api.py` | `GET /api/audit-logs/` — quyền `accounts.view_auditlog` (owner + manager), lọc `?actor_kind=`/`?action=`, phân trang StandardPagination; append-only (chỉ GET) |
| `serializers.py` | `audit_item(row)` — `actor_display` dòng AI = `ai:<tên user>`; field tường minh theo contract 02b mục 3 |
| `tests/test_s03_auditlog.py` | S03-AC1…AC5: schema, `record_audit` 3 loại actor, quyền 403, append-only 405, không PII trong dòng audit đụng đơn |
| `tests/test_s03_migration.py` | MigrationExecutor: backfill `actor_kind` không mất dữ liệu cũ (bất biến 8) |

Model `AuditLog` (3 field mới) ở `apps/accounts/models.py`, migration `0007_auditlog_ai_actor`
(backfill + gán quyền theo mẫu 0002/0006). `record_audit()` ở `apps/common/audit.py` mở tham số
`actor_kind`/`ai_actor`/`proposal_ref` — chữ ký cũ tương thích, không đổi call-site.
