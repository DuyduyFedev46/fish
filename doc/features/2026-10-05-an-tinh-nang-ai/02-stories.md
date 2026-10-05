# Ẩn hết tính năng AI (luồng NHANH)
> Điều phối · 2026-10-05 · Trạng thái: **ĐÃ DUYỆT** (Duy chọn "Tắt cứng bằng cờ") · Phạm vi: chỉ `erp-console/`. Shop `frontend/` không có AI. Backend không đổi vì `AI_ENABLED` mặc định đã là "0".

## SR-HIDE-AI-01: Cờ build tắt mọi giao diện AI
Cờ `NEXT_PUBLIC_AI_FEATURES`. Chỉ đúng giá trị `"1"` mới là bật. Vắng cờ hoặc bất kỳ giá trị nào khác đều là **tắt**, và đây là mặc định ở mọi môi trường. Bản mock (`NEXT_PUBLIC_USE_MOCK=1`) cũng tuân theo cờ này.

- **AC1. Menu và tìm kiếm.** Khi cờ tắt, menu trái, menu avatar (link "AI của tôi") và ô tìm lệnh (CommandSearch) không còn mục nào dẫn tới `/ai/*`. Các mục cần ẩn gồm "Chính sách AI", "Báo cáo AI", "AI của tôi" và "Việc AI". Quyền của người dùng không ảnh hưởng: Chủ cũng không thấy.
- **AC2. Trang `/ai/*`.** Khi cờ tắt, gõ thẳng URL `/ai/policy/`, `/ai/report/`, `/ai/settings/` hay `/ai/actions/` không hiện nội dung AI. Trang hiện trạng thái "không có trang này" theo cách sẵn có của ERP, hoặc chuyển về trang chủ. Màn AI không được gọi API `/api/ai/*`.
- **AC3. Trên trang chi tiết.** Khi cờ tắt, mọi trang chi tiết không hiện khối Trợ lý AI và không gọi `GET /api/ai/status/`. Các khối cần ẩn gồm `AiDocBlockGate`, `ConfirmationAiBlock` và `AiBlockFrame`, cùng các nút "Để AI làm" và "Tóm tắt" trong GuidancePanel. Bố cục trang không để lại ô trống hay khung rỗng.
- **AC4. Không tải phần chạy AI.** Khi cờ tắt, không tạo Worker AI và không tải model hay wllama. Cũng không hỏi đồng ý tải model.
- **AC5. Bật lại được.** Build với `NEXT_PUBLIC_AI_FEATURES=1` thì giao diện AI hiện lại đúng như trước khi sửa, gồm cả cổng `ai_enabled` hiện có. Có test vitest cho cả hai trạng thái của cờ.
- **AC6. Không hồi quy.** `npm run test`, `npm run typecheck` và `npm run build` của erp-console đều xanh. Số gốc trước khi sửa là 76 file và 900 test. Các luồng không thuộc AI không đổi. Riêng "Nhờ" (escalate) dẫn tới `/ai/actions?status=ESCALATED` thì phải ẩn hoặc tắt theo cờ, để không tạo link chết.

## Ghi chú
- Đặt cờ ở một chỗ duy nhất, ví dụ `shared/lib/features.ts` với `AI_FEATURES_ENABLED`. Không rải `process.env` khắp nơi.
- Ghi cờ vào `erp-console/.env.example` và `doc/ops/moi-truong.md`, kèm câu "mặc định tắt, build với =1 để bật".
- Không xoá code AI. Chỉ ẩn để có thể bật lại.
