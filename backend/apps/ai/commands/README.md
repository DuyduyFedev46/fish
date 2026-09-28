# ai/commands — Command registry + catalog (S01)

| File | Vai trò |
|---|---|
| `registry.py` | `CommandSpec` + danh mục 14 lệnh khởi đầu (02b Phụ lục B) + `active_commands_for(user)`; hằng số `PII_FORBIDDEN_KEYS` (bất biến 9) |
| `api.py` | `GET /api/commands/catalog` — trả lệnh active lọc theo `min_permissions` (BR-AI-04) |
| `serializers.py` | `command_item(spec)` — field tường minh theo contract 02b mục 3; KHÔNG trả `context_fields`/`handler` |
| `tests/test_registry.py` | Bất biến registry: 6 trường ADR, JSON Schema hợp lệ, tên duy nhất, forbidden_channel, nhãn (S01-AC1/AC4/AC6), D6/D8, không PII trong context_fields |
| `tests/test_catalog.py` | Phân quyền catalog (S01-AC2/AC3/AC5), 0 query nghiệp vụ (C.4 #11) |

Lệch đã áp: D6 (`description` tiếng Việt), D8 (`xac_nhan_hoan`/`xac_nhan_thanh_toan_tay`
nhãn `local`, vẫn `forbidden_channel="ai"`). `handler` nối service hiện có ở S02 (Lô 2) —
Lô 1 chưa có kênh thực thi.
