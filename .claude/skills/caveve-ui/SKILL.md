---
name: caveve-ui
description: Hướng thiết kế UI/UX của Cá Về (Linear/Notion tinh gọn) và bản đồ chọn skill thiết kế cho từng bề mặt — ERP console, Shop web, app di động. Dùng TRƯỚC khi thiết kế, dựng, review hay đánh bóng bất kỳ giao diện nào của Cá Về (erp-console/, frontend/, app sau này); nó chỉ định nên gọi impeccable, emil-design-eng, ui-ux-pro-max, baseline-ui, web-design-guidelines hay taste-skill.
---

# UI/UX Cá Về: hướng thiết kế và cách chọn skill

## Hướng thiết kế (Duy chốt ngày 2026-09-24)

Phong cách **tinh gọn kiểu Linear/Notion**, dùng cho cả ba bề mặt:
- **Màu:** nền sáng dịu, xám trung tính. Chỉ **một màu nhấn là xanh biển**, dùng cho hành động chính và trạng thái chọn. Màu trạng thái (xanh lá, hổ phách, đỏ) chỉ dùng khi có ý nghĩa: đã thanh toán, cận hạn, lỗi. Dark mode phải ngang hàng với light, không làm cho có.
- **Chữ:** một họ sans **hỗ trợ đủ dấu tiếng Việt**, ví dụ Inter hoặc Be Vietnam Pro. Không dùng font thiếu glyph "ư ơ ạ ễ". Số tiền và số kg dùng `tabular-nums`, căn phải trong bảng.
- **Mật độ:** vừa phải. Bảng dễ quét, khoảng trắng có chủ đích, thứ bậc tạo bằng cỡ chữ, độ đậm và màu xám, không dùng khung viền dày. Tránh card lồng card và bóng đổ nặng.
- **Chuyển động:** nhẹ và nhanh (150–250 ms, ease-out), chỉ để báo phản hồi và chuyển trạng thái, không trang trí. Tôn trọng `prefers-reduced-motion`.
- **Ngôn ngữ UI:** tiếng Việt đời thường, động từ rõ ("Mở bán lô", "Xác nhận đã nhận tiền"). Thông báo lỗi phải nói cách sửa.
- **Người dùng thật:**
  - NV giao và NV kho dùng **điện thoại** ngoài trời, tay bận. Nút ≥ 44 px, tương phản cao, thao tác chính nằm dưới ngón cái.
  - Lộc dùng cả điện thoại lẫn máy tính.
  - Khách Shop dùng điện thoại.

Design system (token màu, chữ, khoảng cách, bo góc, bóng) lưu ở **`DESIGN.md` gốc repo**, dùng chung cho ERP, Shop và app. Chưa có file này thì việc đầu tiên là tạo nó (xem bước 1 bên dưới). Mọi màn hình phải dùng token, không hard-code màu hay khoảng cách.

## Chọn skill theo việc

| Việc | Skill | Ghi chú |
|---|---|---|
| Tạo/cập nhật design system (`DESIGN.md`, token) | `ui-ux-pro-max` (tra bảng màu, cặp font, quy tắc UX) → `impeccable init` / `document` | Làm một lần, rồi cập nhật khi cần |
| Dựng màn mới cho ERP (dashboard, bảng, form, empty state) | `impeccable` (shape → craft) + `nextjs-shop-patterns` | impeccable lo product UI, còn pattern repo lo cấu trúc code |
| Soát và chấm một màn đã có | `impeccable audit` / `critique` + `web-design-guidelines` | Chỉ báo lỗi dạng file:dòng, không sửa |
| Đánh bóng trước khi giao | `impeccable polish` + `emil-design-eng` | Chi tiết nhỏ, trạng thái hover/focus/pressed, micro-interaction |
| Dọn nhanh khoảng cách, thứ bậc, chữ | `baseline-ui` | Lượt nhanh, không đổi bản sắc |
| Truy cập (a11y) | `fixing-accessibility` | Bắt buộc trước QA |
| Chuyển động | `improve-animations` → `review-animations`; hiệu năng thì `fixing-motion-performance` | |
| Shop / landing page (web công khai) | `design-taste-frontend` (cài global) + `impeccable` | taste-skill chỉ dành cho landing/marketing, **không dùng cho ERP** |
| App di động (sau này) | `mobile-native`, `animate-expo`, `impeccable adapt` | |

## Chạy impeccable

- Lần đầu chạy, launcher `scripts/impeccable` **tự tải binary** từ GitHub releases của `pbakaus/impeccable`, có kiểm checksum. **Chỉ chạy khi Duy đã đồng ý.** Chưa đồng ý thì dùng impeccable ở chế độ đọc: đọc `SKILL.md` và `reference/*.md` (có `reference/degraded`), không gọi script.
- **Không bật** `impeccable hooks` (hook tự chạy sau mỗi lần sửa file) khi Duy chưa yêu cầu.

## Cổng chất lượng UI (trước khi QA)

1. Chỉ dùng token trong `DESIGN.md`. Chạy `grep` phải không còn mã màu hex rời trong component.
2. Đủ trạng thái: tải, rỗng, lỗi, thành công, bị cấm (403), đang gửi.
3. Hai cỡ màn: 360 px không cuộn ngang, và 1280 px. Light và dark đều đạt tương phản AA.
4. `fixing-accessibility` không còn lỗi.
5. Chụp ảnh trước và sau, lưu vào `shots/` của hồ sơ tính năng.
6. Không làm lộ dữ liệu giá vốn chỉ vì đổi giao diện. Backend vẫn là lớp chặn.
