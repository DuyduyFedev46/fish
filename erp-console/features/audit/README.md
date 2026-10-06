# features/audit — Nhật ký hoạt động (ED-41 / board W3f)

Màn nghiệp vụ CHUNG (chốt Duy 27/09: dù admin hay nhân viên đều xem ở ERP, không chỉ Django Admin).
Mô-đun này tự chứa cả API, kiểu và mock (Lô 15 đã chuyển khỏi `features/ai/`).

- Route: `/audit-logs/` (bọc `ViewGuard view="audit-logs"` — cần `accounts.view_auditlog`, owner + manager).
- Endpoint: `GET /api/audit-logs/?page=&actor_kind=&action=&actor=`.
- Bố cục: bộ lọc (Người làm, Loại — Người/AI/Hệ thống, Thao tác, khoảng ngày, ô tìm mã) · bảng Thời điểm · Người làm · Thao tác · Đối tượng · Thay đổi · Người duyệt · "Tải thêm".
- Dòng AI hiện nhãn "AI" + tên người mà AI làm thay; dòng hệ thống hiện "Hệ thống".

## An toàn dữ liệu

- Cột "Thay đổi" CHỈ in khoá trong danh sách trắng (`auditModel.changeSummary`): trạng thái, số lượng, số tiền, giá bán, đang làm, nhóm quyền.
  Khoá khác (giá vốn, lãi lỗ, tên, SĐT, địa chỉ) bị bỏ; không bao giờ in JSON thô (bất biến 1 + 9).
- Không ghi tên đăng nhập hay giá trị nào ra console, localStorage hay URL.
- Thiếu quyền → ViewGuard chặn (không gọi API); gọi thẳng API vẫn 403 từ BE.

## Chỗ BE chưa có (FE xử lý tạm, ghi ở 03-dev-notes Lô 15)

- Chưa lọc theo ngày ở BE → khoảng ngày và ô tìm mã lọc phía máy trên các dòng đã tải.
- Chưa có người duyệt → lấy từ dòng `confirm_*`/`approve_*` cùng `proposal_ref`, không có thì "—".
- Dòng chưa có id người làm → hiện tên đăng nhập; `?actor=` chỉ trả dòng của chính người đó.
- `/api/staff/` chỉ Chủ gọi được → Quản lý không thấy danh sách "Mọi người" (ô lọc người làm ẩn).

## Files

| File | Vai trò |
|---|---|
| `types.ts` | `AuditLogRow`, `AuditLogParams` |
| `api.ts` | `getAuditLogs` (có nhánh mock theo `NEXT_PUBLIC_USE_MOCK`) |
| `mock.ts` | `mockAuditLogs` — dữ liệu giả có dòng người/AI/hệ thống |
| `messages.ts` | Chuỗi tiếng Việt của màn |
| `auditModel.ts` (+ `.test.ts`) | Logic thuần: nhãn thao tác, tên người làm, người duyệt, tóm tắt thay đổi, lọc phía máy |
| `components/AuditLogScreen.tsx` | Màn: lọc, bảng, tải thêm, đủ trạng thái tải/lỗi/rỗng/403 |
| `audit.module.css` | Style màn (token trong shared/ui/tokens.css) |
