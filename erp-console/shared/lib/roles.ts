// Hằng tên Group (vai) và giá trị `me.home` của hàng đợi gọi xác nhận — NƠI DUY NHẤT chứa các chuỗi này ở console (P8b Lô 1).
// Giá trị là tên BE đang lưu/trả (`auth_group`, `me.home`); BE đổi tên ở Lô 4 thì chỉ sửa file này.
// Mọi nơi khác (menu, mock, test, component) dùng `ROLE.*` và `HOME_CONFIRMATION_QUEUE`, không viết chuỗi trực tiếp.
// Nhãn hiển thị và thứ tự: shared/lib/groups.ts.

export const ROLE = {
  owner: "chu",
  manager: "quan_ly",
  warehouseStaff: "nv_kho",
  deliveryStaff: "nv_giao",
  customerService: "cskh",
} as const;

export type RoleCode = (typeof ROLE)[keyof typeof ROLE];

/** Giá trị `me.home` của BE cho người vào thẳng hàng đợi gọi xác nhận (đổi sang tên Anh ở Lô 4). */
export const HOME_CONFIRMATION_QUEUE = "cskh-queue";
