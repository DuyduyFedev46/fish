// 4 Group cộng dồn (BR-PQ-09) và nhãn tiếng Việt. Dùng cho: dòng vai ở menu, danh sách nhân viên (S41),
// màn "Quyền của tôi" (S47). Nhãn của CHÍNH người đăng nhập lấy `me.group_labels` do BE trả (L6); bảng này
// chép đúng nhãn BE (`GROUP_LABELS`) để dịch mã nhóm trong danh sách nhân viên (BE /api/staff/ chỉ trả mã).

import { GROUP } from "./nav";

/** Thứ tự cố định như BE `sorted_groups`: chu, quan_ly, nv_kho, nv_giao. */
export const GROUP_CODES = [GROUP.chu, GROUP.quanLy, GROUP.nvKho, GROUP.nvGiao] as const;

export const GROUP_LABEL: Record<string, string> = {
  [GROUP.chu]: "Chủ",
  [GROUP.quanLy]: "Quản lý",
  [GROUP.nvKho]: "Nhân viên kho",
  [GROUP.nvGiao]: "Nhân viên giao",
};

/** Một dòng mô tả việc chính của nhóm — chỉ để Chủ chọn nhóm cho đúng, không phải luật (luật ở BE). */
export const GROUP_HINT: Record<string, string> = {
  [GROUP.chu]: "Toàn quyền: tiền, giá vốn, lãi lỗ, nhân viên",
  [GROUP.quanLy]: "Duyệt vận hành: mở bán lô, huỷ đơn, tạo phiếu hoàn, kiểm kê",
  [GROUP.nvKho]: "Nhập lô, soạn hàng, kiểm kê",
  [GROUP.nvGiao]: "Nhận và giao phiếu được gán",
};

export function groupLabel(code: string): string {
  return GROUP_LABEL[code] || code;
}
