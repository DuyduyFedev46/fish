# features/ai — Trợ lý vận hành (AI-Native ERP)

Hồ sơ: `doc/features/2026-09-27-ai-native-erp/` (02b-tech-design.md là chuẩn, 02-stories.md đã duyệt).
Module này chỉ đặt logic AI của **erp-console** — không đụng `frontend/` (Shop) và không sửa `backend/`.

## Cấu trúc

| File | Vai trò |
|---|---|
| `types.ts` | Kiểu contract Lô 1–2 (S01/S02/S03/S05) |
| `api.ts` | Gọi HTTP: status, catalog (nhẹ — **không** import runtime). Nhật ký đã chuyển sang `features/audit` (Lô 15) |
| `settings/` · `policy/` · `report/` | Lô 15: màn "AI của tôi" (`/ai/settings/`), "Chính sách AI" (`/ai/policy/`), "Báo cáo AI" (`/ai/report/`); mỗi thư mục có `api.ts` + `mock.ts` + `view.ts` (logic thuần) + `components/` + `.module.css` |
| `commands/` | Kênh thực thi lệnh (execute/propose/confirm): `index.ts`, `call.ts`, `planner.ts`, `search.ts`, `budget.ts` (nhẹ — **không** import runtime) |
| `mock.ts` | Mock endpoint Lô 1–2 (status, catalog, execute/propose) — dữ liệu giả |
| `commandGroups.ts` | Giá trị nhóm lệnh / mức nhạy cảm / id lệnh "Nhập lô" hiện hành (tên tiếng Anh, khớp BE). P8b Lô 5 đã gỡ `legacyIds.ts` (lớp chuẩn hoá tên cũ); id lệnh và khoá `caps`/`overrides` dùng đúng id BE trả |
| `consent.ts` | Cờ đồng ý tải model (boolean thuần, localStorage — không dữ liệu cá nhân) |
| `messages.ts` | Chuỗi tiếng Việt (e2e đọc qua `__caveMock.msg`) |
| `runtime/feature-detect.ts` | Kiểm tra máy: WebGPU / RAM (≥8 GB) / Wi-Fi / iOS |
| `runtime/model-store.ts` | Cache GGUF trong IndexedDB (key = URL, immutable theo version) |
| `runtime/model-downloader.ts` | Tải sequential full-file GGUF: Range 64 MB, % + tốc độ + ETA, tạm dừng/tải tiếp/huỷ, tự dừng khi rời Wi-Fi |
| `runtime/worker-manager.ts` | Vòng đời worker: tạo khi dùng lần đầu, 1 việc/lúc (mới huỷ cũ), nhàn 10 phút → dispose+terminate |
| `runtime/worker.ts` | Worker suy luận (giao thức init/infer/cancel/dispose; LLMock lô 1–2) |
| `runtime/wllama.ts` + `wllama.d.ts` | KHUNG gọi @wllama/wllama (chưa cài — Lô 4), fail-closed |
| `runtime/engine.ts` | Cửa vào runtime: chọn engine, n_ctx từ env, askAi, shutdownRuntime |
| `components/AiAssistantGate.tsx` | Cánh cổng MỎNG (import tĩnh ở layout): gọi status + cờ đồng ý; tắt/lỗi → null |
| `components/AiAssistantPanel.tsx` | Tấm NẶNG (next/dynamic ssr:false): kiểm tra máy → tải model → chat |

## Endpoint (Lô 1–2)

- `GET /api/ai/status/` — luôn 200; `ai_enabled=false` khi tắt; `model=null` khi chưa chốt (S17); `budget` chỉ chu.
- `GET /api/commands/catalog/` — 12 lệnh active (Phụ lục B), lọc theo `min_permissions`.
- `POST /api/commands/execute/` · `propose/` · `proposals/<id>/confirm/` — kênh duy nhất, 3 tầng quyền.
- `GET /api/audit-logs/` — màn Nhật ký hoạt động: API, kiểu và mock nay nằm trong `features/audit` (Lô 15).

## Biến môi trường (Phụ lục A)

| Biến | Ý nghĩa |
|---|---|
| `NEXT_PUBLIC_AI_MAX_CONTEXT_TOKENS` | n_ctx (mặc định 2048; 512–8192). **KHÔNG BAO GIỜ để mặc định 32k** (H3) |
| `NEXT_PUBLIC_AI_ENGINE` | ghi đè engine: `llmock` \| `wllama` (mặc định: mock → llmock, thật → wllama — BR-AI-16) |
| `NEXT_PUBLIC_AI_MODEL_NAME` + `NEXT_PUBLIC_AI_MODEL_GGUF_URL` | ghi đè model cục bộ (thử tải file test; mock cũng đọc 2 biến này) |

## Vòng đời (Phụ lục C.2)

- Cổng: gọi `/api/ai/status/` CHỈ khi người mở tab Trợ lý lần đầu (IntersectionObserver trên pane `[hidden]`); `ai_enabled=false`/lỗi → null. AI không bật mà không ai mở tab = 0 request.
- Tấm nặng: `next/dynamic(…, {ssr:false})`, chỉ nạp khi `ai_enabled && đã đồng ý`.
- Worker: tạo khi hỏi lần đầu; `terminate()` khi đóng màn AI / đăng xuất / tắt AI; ẩn tab 60s → `shutdown("close")`; nhàn 10 phút → `shutdown("idle")` kèm `dispose()`; hàng đợi 1 việc, câu mới huỷ câu cũ.
- Tải model: sequential full-file (KHÔNG "core trước, full sau"); % + ETA; tạm dừng/tải tiếp/huỷ; resume bằng Range; cache IndexedDB key = URL; rời Wi-Fi giữa chừng → tự tạm dừng.
- Suy luận on-device: không gọi mạng (S08-AC5); không log prompt (S08-AC8).
- Cấm `<link rel="preload">` tới model/wasm trong metadata layout.

## Ranh giới

- `api.ts`, `commands/` **không** import `runtime/` `voice/` `chat/`.
- `shared/` và `features/auth/` **không** import gì từ `features/ai`.
- Không có barrel `index.ts` — import đường dẫn cụ thể.
- Mọi `dynamic(() => import(...))` nặng đều đứng sau cánh cổng.

## Nợ còn lại

- **Lô 4 (S17 chốt model)**: cài `@wllama/wllama` (xem 4 bước trong `runtime/wllama.ts`); đổi worker sang `{type:"module"}` hoặc `importScripts` (classic worker không có `import()`); chép wasm vào `public/wllama/`; đối chiếu API thật.
- **COOP/COEP (H7)**: chạy wasm threads cần header Cross-Origin — việc deploy/ops, ghi rõ trong dev notes.
- **python http.server phục vụ file test không hỗ trợ Range** → downloader tự chuyển một lượt streaming.
- **E2E**: QA thêm kịch bản bật `__caveMock.ai("on")` + `__caveMock.aiConsent(true)`; khung chờ "Trợ lý đang được nối, sắp có" giữ nguyên khi AI tắt (mặc định mock tắt).
- **S02 UI** (đề xuất → xác nhận trên màn) chưa làm — `commands/` sẵn hàm, lô sau ghép.
- **S03 mock**: `mockAuditLogs` đã chuyển sang `features/audit/mock.ts` (Lô 15).
