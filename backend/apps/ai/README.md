# ai — AI Native ERP (điều phối lệnh, hồ sơ `doc/features/2026-09-27-ai-native-erp/`)

App mới cho lớp lệnh nghiệp vụ dùng chung (UI · Admin · AI) — **bọc + mở rộng service layer
hiện có, không viết lại lõi** (BR-AI-01, 02b-tech-design quyết định 1). Không đổi model nghiệp
vụ hiện có (bất biến 8).

Quy tắc chính: phân quyền 3 tầng áp nguyên vẹn cho kênh AI (BR-AI-04); registry là code
(ADR 2.5/V4); không rò giá vốn (bất biến 1) và không rò dữ liệu cá nhân khách (bất biến 9,
BR-AI-09).

| Module | Chức năng | Story / lô |
|---|---|---|
| `commands/` | Registry 14 lệnh + catalog `GET /api/commands/catalog` | S01 — Lô 1 (đã làm) |
| `commands/` | Kênh execute / propose / confirm + ma trận chặn channel + jsonschema | S02 — Lô 2 |
| `context/` | Context builder allowlist default-deny (không PII) | S06 — Lô 2 |
| `status.py` | `GET /api/ai/status` (công tắc AI_ENABLED) | S05 — Lô 2 |
| `usage/` | AiUsageLedger + AiMonthGate + `/api/ai/usage` | S04 — Lô 3 |
| `cloud/` | Orchestrator `/api/ai/cloud/complete` (gọi adapter) | S11 — Lô 5 |
| `alerts/` | `GET /api/alerts/` | S12 — Lô 6 |

Các story gắn với mã BR-AI-01…16 (xem 01-analysis §7) — trích mã BR trong test/commit.
Model `AiProposal` (02b mục 4.2) và `AiUsageLedger`/`AiMonthGate` (mục 4.3) sẽ thêm ở lô sau
cùng migration riêng.
