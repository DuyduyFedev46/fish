# 03 — Dev notes (AI Native ERP)

> Lô 1: S01 (catalog lệnh) + S03 (AuditLog `ai:<user>` + endpoint nhật ký) — BE.
> FE ghi mục FE (S07/S08) ở dưới khi xong.

## BE — Lô 1

### Story đã xong
- **S01** — Command registry 14 lệnh khởi đầu (02b Phụ lục B) + `GET /api/commands/catalog/` trả lệnh active theo quyền (BR-AI-04, ADR 2.5/V4: registry là code, 0 query nghiệp vụ).
- **S03** — `AuditLog` thêm `actor_kind`/`ai_actor`/`proposal_ref` + backfill + `GET /api/audit-logs/` với quyền mới `accounts.view_auditlog`; dòng AI hiển thị `ai:<tên user>`.

### File đã sửa / thêm mới
| File | Nội dung |
|---|---|
| `backend/apps/ai/commands/registry.py` *(mới)* | `CommandSpec` (đóng băng) + 14 lệnh (12 active, 2 draft) + `active_commands_for(user)`; `PII_FORBIDDEN_KEYS` (bất biến 9) |
| `backend/apps/ai/commands/api.py` *(mới)* | `CommandCatalogView` — auth bắt buộc, trả `{commands:[...]}` |
| `backend/apps/ai/commands/serializers.py` *(mới)* | `command_item(spec)` — field tường minh theo contract; KHÔNG trả `context_fields`/`handler` |
| `backend/apps/ai/apps.py`, `__init__.py`, `admin.py`, `README.md`, `commands/README.md` *(mới)* | App `ai` (Lô 1 chưa có model — registry là code) |
| `backend/apps/ai/commands/tests/test_registry.py`, `test_catalog.py` *(mới)* | Bất biến registry + phân quyền catalog + 0 query nghiệp vụ |
| `backend/apps/accounts/models.py` | `AuditLog`: 3 field nullable + `ActorKind` + `__str__` dòng AI = `ai:<user>` |
| `backend/apps/common/audit.py` | `record_audit(..., actor_kind=, ai_actor=, proposal_ref=)` — chữ ký cũ tương thích; chuẩn hoá actor null → `system` |
| `backend/apps/accounts/migrations/0007_auditlog_ai_actor.py` *(mới)* | 3 AddField + backfill `actor_kind` + gán quyền `accounts.view_auditlog` cho chu/quan_ly |
| `backend/apps/accounts/audit/api.py`, `serializers.py`, `README.md`, `tests/` *(mới)* | Endpoint nhật ký + test S03 (API, migration, PII) |
| `backend/apps/accounts/admin.py` | AuditLogAdmin hiện `actor_kind`/`ai_actor`, lọc theo `actor_kind` |
| `backend/config/settings.py` | Thêm `apps.ai` vào INSTALLED_APPS |
| `backend/config/api_urls.py` | Route `commands/catalog/`, `audit-logs/` |
| `backend/requirements.txt` | `jsonschema>=4.20` (validate args theo `input_schema`, 02b mục 4.4) |

### Endpoint mới

**`GET /api/commands/catalog/`** — xác thực bắt buộc (401 khi ẩn danh). Trả lệnh `status="active"` mà user có đủ `min_permissions` (BR-AI-04). Không đọc DB nghiệp vụ (registry là code). JSON mẫu (1 phần tử):

```json
{
  "commands": [
    {
      "name": "nhap_lo",
      "channel": "ui",
      "sensitivity": "medium",
      "min_permissions": ["purchasing.add_purchasereceipt"],
      "input_schema": {"type": "object", "properties": {"items": {"type": "array"}}},
      "output_schema": {"type": "object", "properties": {"receipt_id": {"type": "integer"}}},
      "status": "active",
      "description": "Nhập lô mua tại cảng — mỗi dòng sinh một lô.",
      "needs_confirmation": true,
      "forbidden_channel": null
    }
  ]
}
```
Chu thấy đủ **12 lệnh**; `nv_giao` chỉ thấy `["tra_don"]`; `nv_kho` thấy 6 lệnh kho/đơn; lệnh có `forbidden_channel="ai"` (chot_lo, xac_nhan_hoan, xac_nhan_thanh_toan_tay) vẫn được liệt kê — field đó để FE hiểu lệnh bị chặn ở kênh AI, không lọc bỏ.

**`GET /api/audit-logs/?page=&actor_kind=&action=`** — quyền `accounts.view_auditlog` (chu + quan_ly; 403 nhóm khác). Phân trang StandardPagination (page_size 20), sắp mới nhất trước, append-only (405 POST/PUT/DELETE). JSON mẫu dòng AI:

```json
{
  "id": 1,
  "actor_kind": "ai",
  "actor_display": "ai:giao_demo",
  "ai_actor": 6,
  "action": "propose_nhap_lo",
  "model_name": "",
  "object_id": "",
  "object_repr": "",
  "changes": {},
  "note": "",
  "proposal_ref": "P-1",
  "created_at": "2026-09-27T16:08:35.461177Z"
}
```
Field trả về đúng contract 02b mục 3, không trả thêm gì (đã test set field chính xác).

### Migration
`accounts/0007_auditlog_ai_actor` — 3 field nullable (bất biến 8: chỉ thêm, không đổi schema cũ), backfill `actor_kind` = `system` cho dòng có `actor` null (dữ liệu cũ giữ nguyên), gán quyền theo mẫu 0002/0006 (rollback gỡ quyền). Đã test bằng MigrationExecutor (TransactionTestCase): dữ liệu cũ không mất.

### Rule BR đã cài
- **BR-AI-04** (phân quyền 3 tầng áp nguyên vẹn cho kênh AI): catalog lọc theo `min_permissions`; endpoint nhật ký theo quyền T2 mới.
- **Bất biến 1** (không rò giá vốn): không có field giá vốn trong 2 endpoint.
- **Bất biến 3/5** (append-only, PROTECT FK): `ai_actor` PROTECT (xoá user bị chặn), endpoint chỉ GET.
- **Bất biến 8**: chỉ migration thêm field, không đổi model nghiệp vụ.
- **Bất biến 9** (không rò dữ liệu cá nhân — Critical): `PII_FORBIDDEN_KEYS` chặn key tên/SĐT/địa chỉ trong `context_fields`; test tạo đơn có SĐT/địa chỉ giả và assert `changes`/`note`/`object_repr` + response API không chứa chúng; không log PII.
- **ADR 2.5/V4**: registry là code, không DB.

### Lệch đã áp từ 02b mục 9 (Duy chưa đọc mục 9 — tổng hợp sau)
| Lệch | Áp | Lý do |
|---|---|---|
| **D6** | Thêm field `description` (tiếng Việt, ngắn) vào mỗi `CommandSpec` và trả trong catalog | FE cần mô tả để hiển thị cho Duy; trường mô tả không làm lộ nghiệp vụ/gía vốn |
| **D8** | `xac_nhan_hoan` + `xac_nhan_thanh_toan_tay`: `channel="local"`, GIỮ `forbidden_channel="ai"` | Đúng thiết kế kênh ở 02b mục 2 (2 lệnh chỉ chạy tại chỗ); vẫn chặn AI như bản gốc |

### Điều còn nợ (lô sau)
- **S02** (Lô 2): kênh execute/propose/confirm + ma trận chặn channel + validate jsonschema — nối `handler` vào service hiện có (Lô 1 `handler=None`).
- **S05/S06** (Lô 2): `GET /api/ai/status`, context builder allowlist.
- **Model `AiProposal`** (02b mục 4.2 — Lô 2) và `AiUsageLedger`/`AiMonthGate` (mục 4.3 — Lô 3) với migration riêng.
- S04/S11/S12: usage ledger, cloud orchestrator, alerts.

### Kết quả test (chạy thật lượt này)
- `backend`: `Ran 667 tests in 34.357s — OK` (0 failure; baseline 634 + 33 test mới của S01/S03).
- `makemigrations --check --dry-run`: `No changes detected`.
- Smoke thật trên dev DB: chu thấy 12 lệnh, `nv_giao` = `['tra_don']`, dòng audit AI hiển thị `ai:giao_demo` (đã dọn user demo sau khi chạy).

## FE — (fe-dev ghi mục này khi xong)
