# Dev notes: ẩn tính năng AI (SR-HIDE-AI-01)

## FE (erp-console)
Cờ build `NEXT_PUBLIC_AI_FEATURES`, chỉ `"1"` là bật, mặc định tắt. Đọc ở một chỗ: `shared/lib/features.ts` (`AI_FEATURES_ENABLED`). Không xoá code AI.

| AC | Cách làm |
|---|---|
| AC1 | `shared/lib/nav.ts`: 4 mục `ai-policy`, `ai-report`, `ai-settings`, `ai-actions` có `visible` kèm `AI_FEATURES_ENABLED &&`. Menu trái, tìm lệnh, `canView` đều đi qua đây. `Shell.tsx` chỉ truyền `aiSettingsHref` cho avatar menu khi cờ bật. |
| AC2 | Component mới `shared/ui/states/AiFeatureGuard.tsx` bọc 4 trang `app/(console)/ai/*`: cờ tắt thì hiện `NoPermission` (cùng kiểu ViewGuard), không mount màn AI nên không gọi `/api/ai/*`. |
| AC3 | `AiDocBlockGate` và `ConfirmationAiBlock` không gọi status và trả null khi tắt. `AiBlockFrame` trả null. `DetailPage` bỏ `aiSlot` khi tắt (không còn cột phải rỗng). `GuidancePanel` ẩn "Để AI làm", huy hiệu AI và "Tóm tắt". |
| AC4 | Mọi đường vào runtime AI đều đi qua các khối trên nên không được mount, không tạo Worker, không hỏi tải model. |
| AC6 | `GuidanceEscalate`: nút "Nhờ" vẫn chạy (DW-23-AC7), nhưng bỏ câu nhắc "màn Việc AI" và link `/ai/actions?status=ESCALATED` khi tắt. |

Test: `vitest.config.ts` đặt `env NEXT_PUBLIC_AI_FEATURES=1` nên 900 test cũ giữ nguyên. Thêm `shared/lib/aiFeatures.off.test.ts` (mock cờ tắt: nav, gate không gọi `getAiStatus`, frame, DetailPage, guard) và `aiFeatures.on.test.ts` (cờ bật hiện như cũ, gate gọi status một lần).

Còn nợ / lưu ý:
- Mục menu `ai-*` vẫn nằm trong bảng NAV (chỉ `visible` = false), nên chuỗi `/ai/...` và nhãn còn trong JS bundle. HTML tĩnh không chứa "Chính sách AI".
- Dữ liệu mock của guidance vẫn trả `step.ai`, giao diện tự ẩn. `ConsoleGate` vẫn nạp `features/ai/mock` ở bản mock (công cụ thử, không chạm model).
- Không chụp ảnh Playwright (ẩn giao diện, kiểm bằng vitest).
