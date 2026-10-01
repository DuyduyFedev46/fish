// Dữ liệu khách (tên, SĐT, địa chỉ, ghi chú) bị ẩn theo thời hạn — SR-PII-02 (BR-PQ-12, bất biến 9).
// Hợp đồng BE: NV giao xem phiếu đã kết thúc quá hạn → các trường trên là `null` (khoá JSON vẫn có).
// Chuỗi rỗng "" là "chưa có dữ liệu" thật (vd khách chưa có địa chỉ) và vẫn hiện như cũ; chỉ `null` mới là "đã ẩn".
import type { Me } from "@/features/auth/types";
import { MSG } from "./messages";
import { ROLE } from "./roles";

/** Chữ hiển thị cho một trường dữ liệu khách: null → "Đã ẩn (quá 7 ngày)", rỗng/thiếu → `whenEmpty`. */
export function personalText(value: string | null | undefined, whenEmpty = "—"): string {
  if (value === null) return MSG.personalDataHidden;
  return value || whenEmpty;
}

/**
 * Người dùng chỉ có phạm vi giao hàng HẠN CHẾ: có Group nv_giao nhưng KHÔNG có chủ, quản lý hay NV kho
 * (đảo của BE `has_full_delivery_scope`). Với họ: (1) chỉ thấy phiếu/đơn gán cho mình, (2) dữ liệu khách của phiếu đã
 * kết thúc quá 7 ngày bị ẩn (SR-PII-02). Người kiêm nhiệm như cskh + nv_giao cũng thuộc diện này.
 * Dùng chung cho mock Đơn và mock Giao hàng; BE thật mới là lớp chặn, FE chỉ dựng lại cho khớp.
 */
export function hasLimitedCourierScope(me: Pick<Me, "groups">): boolean {
  const g = me.groups;
  if (!g.includes(ROLE.deliveryStaff)) return false;
  return !g.includes(ROLE.owner) && !g.includes(ROLE.manager) && !g.includes(ROLE.warehouseStaff);
}
