// 4 Group cộng dồn (BR-PQ-09) và nhãn tiếng Việt. Dùng cho: dòng vai ở menu, danh sách nhân viên (S41),
// màn "Quyền của tôi" (S47). Nhãn của CHÍNH người đăng nhập lấy `me.group_labels` do BE trả (L6); bảng này
// chép đúng nhãn BE (`GROUP_LABELS`) để dịch mã nhóm trong danh sách nhân viên (BE /api/staff/ chỉ trả mã).

import { ROLE } from "./roles";

/** Thứ tự cố định như BE `sorted_groups`: owner, manager, warehouse_staff, delivery_staff. */
export const GROUP_CODES = [ROLE.owner, ROLE.manager, ROLE.warehouseStaff, ROLE.deliveryStaff, ROLE.customerService] as const;

export const GROUP_LABEL: Record<string, string> = {
  [ROLE.owner]: "Chủ",
  [ROLE.manager]: "Quản lý",
  [ROLE.warehouseStaff]: "Nhân viên kho",
  [ROLE.deliveryStaff]: "Nhân viên giao",
  [ROLE.customerService]: "CSKH",
};

/** Một dòng mô tả việc chính của nhóm — chỉ để Chủ chọn nhóm cho đúng, không phải luật (luật ở BE). */
export const GROUP_HINT: Record<string, string> = {
  [ROLE.owner]: "Toàn quyền: tiền, giá vốn, lãi lỗ, nhân viên",
  [ROLE.manager]: "Duyệt vận hành: mở bán lô, huỷ đơn, tạo phiếu hoàn tiền, kiểm kê",
  [ROLE.warehouseStaff]: "Nhập lô, soạn hàng, kiểm kê",
  [ROLE.deliveryStaff]: "Nhận và giao phiếu được gán",
  [ROLE.customerService]: "Gọi xác nhận đơn, đổi thông tin nhận",
};

export function groupLabel(code: string): string {
  return GROUP_LABEL[code] || code;
}
