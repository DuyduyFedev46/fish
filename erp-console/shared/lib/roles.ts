// Hằng tên Group (vai) và giá trị `me.home` của hàng đợi gọi xác nhận — NƠI DUY NHẤT chứa các chuỗi này ở console (P8b Lô 1).
// Giá trị là tên BE đang lưu/trả (`auth_group`, `me.home`): tên tiếng Anh, khớp BE (P8b Lô 4a). Không còn lớp chuẩn hoá tên cũ (gỡ ở Lô 5).
// Mọi nơi khác (menu, mock, test, component) dùng `ROLE.*` và `HOME_CONFIRMATION_QUEUE`, không viết chuỗi trực tiếp.
// Nhãn hiển thị và thứ tự: shared/lib/groups.ts.

export const ROLE = {
  owner: "owner",
  manager: "manager",
  warehouseStaff: "warehouse_staff",
  deliveryStaff: "delivery_staff",
  customerService: "customer_service",
} as const;

export type RoleCode = (typeof ROLE)[keyof typeof ROLE];

/** Giá trị `me.home` của BE cho người vào thẳng hàng đợi gọi xác nhận. */
export const HOME_CONFIRMATION_QUEUE = "confirmation-queue";
