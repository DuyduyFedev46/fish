# features/audit — Màn Nhật ký hoạt động (S03-FE)

Màn nghiệp vụ CHUNG (không nằm trong `features/ai/` — chốt Duy 27/09: dù admin hay nhân viên đều
xem ở ERP, tính năng phải làm xong ở ERP chứ không chỉ Django Admin).

- Route: `/audit-logs/` (bọc `ViewGuard view="audit-logs"` — cần `accounts.view_auditlog`, chu + quan_ly).
- Menu: `shared/lib/nav.ts` — mục "Nhật ký hoạt động" (Quản trị, sau Nhân sự), `PERM.viewAuditLog`.
- Endpoint: `GET /api/audit-logs/?page=&actor_kind=&action=` — thuộc hồ sơ AI (S03) nên hàm `getAuditLogs`
  và kiểu `AuditLogRow` đặt ở `features/ai/api.ts` / `features/ai/types.ts`; màn này import từ đó.
  Mock Lô 1 (`mockAuditLogs`) cũng đặt ở `features/ai/mock.ts` theo phân công — **bỏ mock khi BE Lô 1 xong**.

## AC

- **S03-AC2**: dòng AI hiện `ai:<tên user>` rõ ràng (nhãn "AI" + tên), kèm lệnh (note/action) + thời điểm.
- **S03-AC4**: KHÔNG chép tên/SĐT/địa chỉ khách vào hiển thị — màn chỉ in nguyên văn trường API trả;
  BE đảm bảo `changes`/`note` chỉ chứa mã đơn/mã lệnh/mã đề xuất.
- **S03-AC5**: thiếu quyền → ViewGuard chặn màn (không gọi API); gọi thẳng API vẫn 403 từ BE.

## Files

| File | Vai trò |
|---|---|
| `components/AuditLogScreen.tsx` | Bảng nhật ký: lọc actor, tải thêm, thay đổi trong `<details>` |
| `audit.module.css` | Style màn (token trong shared/ui/tokens.css) |
