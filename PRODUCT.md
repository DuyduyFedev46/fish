# Product

<!-- impeccable:product-schema 1 -->

> Bản ghi sự thật sản phẩm cho skill `impeccable` (đọc cùng `DESIGN.md`). Viết ngày 2026-09-24 từ tài liệu có sẵn
> (`doc/URD.md`, `doc/business-process-spec.md`, skill `caveve-ui`). Chưa có vòng phỏng vấn trực tiếp với Duy:
> mọi mục đánh dấu **(suy luận)** cần Duy xác nhận hoặc sửa. Nguồn sự thật nghiệp vụ vẫn là `doc/`.

## Platform

web

## Users

- **Chủ vựa (Lộc):** toàn quyền; dùng cả điện thoại lẫn máy tính. Việc chính: duyệt tiền (hoàn tiền, xác nhận đã nhận tiền), chốt lô, xem giá vốn và lãi lỗ.
- **Quản lý:** được uỷ các việc "làm khách phải chờ" (mở bán lô, xử lý đơn), không đụng tiền rời túi hay con số lời lỗ.
- **NV kho, NV giao:** dùng **điện thoại, ngoài trời, tay bận** (găng tay, thùng đá, trên xe). Việc chính: nhập lô, soạn hàng, giao hàng, kiểm kê.
- **Khách Shop:** cá nhân, mua trên điện thoại, không có tài khoản (guest checkout, thanh toán VietQR).

## Product Purpose

Cá Về số hoá vận hành một vựa hải sản đông lạnh bán lẻ B2C: mua tại cảng theo lô → bán online, giao tận nhà bằng
nhân viên nội bộ → tính đúng giá vốn và lãi lỗ theo từng lô. Thành công = không sai sót ghi chép, biết chính xác mỗi lô lời lỗ bao nhiêu, nhân viên làm việc trên điện thoại không cần hỏi lại.

## Positioning

Giá vốn và lãi lỗ **theo lô** là nguồn sự thật (landed cost gồm đá, vận chuyển, bốc vác); xuất kho FIFO theo lô. Một vựa, một kho. (suy luận: đây là điểm khác so với phần mềm bán hàng chung chung)

## Operating Context

- Ba bề mặt: **ERP console** (`erp-console/`, nội bộ), **Shop + Landing** (`frontend/`, công khai), app di động (sau này).
- Console có 4 nhóm quyền cộng dồn (Chủ, Quản lý, NV kho, NV giao); menu hiện theo quyền.
- Tiền VND không số lẻ, khối lượng theo kg; giữ chỗ đơn có thời hạn (TTL).
- Dự án chưa vận hành thực tế (URD §1.3): nhiều hành vi là giả định thiết kế, sẽ chỉnh khi Lộc vận hành.

## Capabilities and Constraints

- Web tĩnh (Next.js static export) trên Firebase Hosting; API Django. Không có server lúc chạy ở FE.
- **Không bao giờ lộ giá vốn/lãi lỗ ở Shop**; ở console chỉ hiện khi có quyền `view_costprice` / `view_profitreport` (backend là lớp chặn thật).
- Chứng từ không xoá, chỉ huỷ bằng trạng thái.
- Chỉ tiếng Việt (đa ngôn ngữ ngoài phạm vi).

## Brand Commitments

- Tên hiển thị: **"Cá Về"**. "Lộc" là chủ vựa (người), không phải brand. Chuỗi `cangca` chỉ là tên hạ tầng.
- Hướng giao diện Duy chốt 2026-09-24: **tinh gọn kiểu Linear/Notion**, một màu nhấn xanh biển, dark mode ngang hàng light (chi tiết ở `DESIGN.md`).
- Giọng văn: tiếng Việt đời thường, động từ rõ ("Mở bán lô", "Xác nhận đã nhận tiền"); lỗi phải nói cách sửa.

## Evidence on Hand

- Dữ liệu mock theo contract trong `erp-console/features/*/mock.ts` và `shared/lib/dashboardSummary.mock.ts`.
- `backend` có lệnh `seed_demo` tạo dữ liệu demo. Chưa có ảnh sản phẩm thật, lời chứng thực hay số liệu kinh doanh thật: không bịa.

## Product Principles

1. Người dùng ngoài trời trên điện thoại là chuẩn đo: vùng bấm ≥ 44 px, tương phản cao, thao tác chính dưới ngón cái.
2. Con số là nhân vật chính: tiền và kg phải dễ quét, căn phải, cùng độ rộng chữ số.
3. Quyền quyết định cái gì hiện ra; giao diện không bao giờ là lớp bảo mật duy nhất.
4. Ít mà rõ: một màu nhấn, trạng thái chỉ tô màu khi có ý nghĩa.

## Accessibility & Inclusion

- WCAG 2.1 AA cho cả light và dark. Tôn trọng `prefers-reduced-motion`. Font phải đủ dấu tiếng Việt.
