---
name: caveve-ui
description: Hướng thiết kế UI/UX của Cá Về (Shop theo bố cục bán lẻ trong doc/design/shop, ERP theo doc/design/erp/UI-RULES.md, token chung DESIGN.md) và bản đồ chọn skill thiết kế cho từng bề mặt — ERP console, Shop web, app di động. Dùng TRƯỚC khi thiết kế, dựng, review hay đánh bóng bất kỳ giao diện nào của Cá Về (erp-console/, frontend/, app sau này); nó chỉ định nên gọi impeccable, emil-design-eng, ui-ux-pro-max, baseline-ui, web-design-guidelines hay taste-skill.
---

# UI/UX Cá Về: hướng thiết kế và cách chọn skill

## Hướng thiết kế theo bề mặt

| Bề mặt | Hướng | Nguồn bắt buộc |
|---|---|---|
| **Shop** (`frontend/`) | Bố cục bán lẻ kiểu Long Châu, chỉ bản sáng (Duy chốt 10/10) | `doc/design/shop/UI-RULES.md`, `COMPONENTS.md`, `SO-CHUAN.md`, `HUONG-DAN-CODE.md`, màn mẫu `screens/*.dc.html` |
| **ERP console** (`erp-console/`) | Công cụ làm việc tinh gọn, có dark mode | `doc/design/erp/UI-RULES.md`, màn mẫu `doc/design/erp/screens/*.dc.html` |
| **App di động** (sau này) | Chưa chốt | Token `DESIGN.md` |

Chung cho mọi bề mặt (token ở **`DESIGN.md` gốc repo**, không hard-code màu hay khoảng cách):
- **Màu:** nền sáng dịu, xám trung tính. Chỉ **một màu nhấn xanh biển `#1F66D1`** (Shop thêm `brand-deep`), dùng cho hành động chính và trạng thái chọn. Màu trạng thái (xanh lá, hổ phách, đỏ) chỉ dùng khi có ý nghĩa: đã thanh toán, cận hạn/sắp hết, lỗi.
- **Chữ:** một họ sans **hỗ trợ đủ dấu tiếng Việt**, ví dụ Inter hoặc Be Vietnam Pro. Không dùng font thiếu glyph "ư ơ ạ ễ". Số tiền và số kg dùng `tabular-nums`, căn phải trong bảng.
- **Chuyển động:** nhẹ và nhanh (150–250 ms, ease-out), chỉ để báo phản hồi và chuyển trạng thái, không trang trí. Tôn trọng `prefers-reduced-motion`.
- **Ngôn ngữ UI:** tiếng Việt đời thường, động từ rõ ("Mở bán lô", "Xác nhận đã nhận tiền"). Thông báo lỗi phải nói cách sửa.
- **Người dùng thật:**
  - NV giao và NV kho dùng **điện thoại** ngoài trời, tay bận. Nút ≥ 44 px, tương phản cao, thao tác chính nằm dưới ngón cái.
  - Lộc dùng cả điện thoại lẫn máy tính.
  - Khách Shop dùng điện thoại (390 px) và máy tính (1280 px), một trang responsive.

## Shop: luật UI/UX bắt buộc (Duy chốt 10/10/2026)

Mọi việc dựng, sửa hay review màn **Shop** phải đọc **`doc/design/shop/UI-RULES.md`** trước, rồi `COMPONENTS.md` (47
component: giải phẫu, biến thể, trạng thái, props, a11y), `SO-CHUAN.md` (số chuẩn) và `HUONG-DAN-CODE.md`. Đối chiếu với màn
mẫu `doc/design/shop/screens/*.dc.html`; chỗ màn khác các chốt 10–11/10 trong `doc/design/shop/README.md` thì theo chốt.
Component trình bày dùng chung nằm ở `frontend/components/ui|catalog|cart|search`, khung trang là `ShopFrame`
(02b của `doc/features/2026-10-06-shop-giao-dien-moi/` §1.1, §1.10). QA chấm màn Shop theo `UI-RULES.md`.

## ERP: luật UI/UX bắt buộc (Duy chốt 30/09–01/10/2026)

Mọi việc dựng, sửa hay review màn **ERP** phải đọc **`doc/design/erp/UI-RULES.md`** trước và đối chiếu với thiết kế mẫu
`doc/design/erp/screens/*.dc.html` (enum: `doc/design/erp/enum-map.md`, tên chuẩn: `doc/thuat-ngu-va-trang-thai.md`).
Mật độ vừa phải: bảng dễ quét, thứ bậc bằng cỡ chữ, độ đậm và màu xám, không khung viền dày, tránh card lồng card. Dark
mode ngang hàng light. Luật này đi trước các gợi ý chung ở trên khi hai bên khác nhau. QA chấm màn ERP theo từng mục
của `UI-RULES.md`.

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
| Dựng màn Shop (gồm `/about/`) | Làm đúng `doc/design/shop/` + `impeccable` (craft, polish) + `nextjs-shop-patterns` | Không tự sáng tác hướng mới; `design-taste-frontend` chỉ để tham khảo khi thiết kế chưa có màn |
| App di động (sau này) | `mobile-native`, `animate-expo`, `impeccable adapt` | |

## Chạy impeccable

- Lần đầu chạy, launcher `scripts/impeccable` **tự tải binary** từ GitHub releases của `pbakaus/impeccable`, có kiểm checksum. **Chỉ chạy khi Duy đã đồng ý.** Chưa đồng ý thì dùng impeccable ở chế độ đọc: đọc `SKILL.md` và `reference/*.md` (có `reference/degraded`), không gọi script.
- **Không bật** `impeccable hooks` (hook tự chạy sau mỗi lần sửa file) khi Duy chưa yêu cầu.

## Cổng chất lượng UI (trước khi QA)

1. Chỉ dùng token trong `DESIGN.md`. Chạy `grep` phải không còn mã màu hex rời trong component.
2. Đủ trạng thái: tải, rỗng, lỗi, thành công, bị cấm (403), đang gửi.
3. Hai cỡ màn: 360 px không cuộn ngang, và 1280 px. Tương phản AA (ERP: cả light và dark; Shop: bản sáng).
4. `fixing-accessibility` không còn lỗi.
5. Chụp ảnh trước và sau, lưu vào `shots/` của hồ sơ tính năng (dữ liệu giả, không có dữ liệu cá nhân thật).
6. Không làm lộ dữ liệu giá vốn hay dữ liệu cá nhân chỉ vì đổi giao diện. Backend vẫn là lớp chặn.
