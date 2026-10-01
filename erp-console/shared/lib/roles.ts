// Hằng tên Group (vai) và giá trị `me.home` của hàng đợi gọi xác nhận — NƠI DUY NHẤT chứa các chuỗi này ở console (P8b Lô 1).
// Giá trị là tên BE đang lưu/trả (`auth_group`, `me.home`); từ Lô 4b là tên tiếng Anh, khớp BE Lô 4a.
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

// ---- Lớp chuẩn hoá tên (P8b Lô 3) ----
// Từ Lô 4a BE trả tên Group và `me.home` bằng tiếng Anh. FE (Lô 4b) dùng tên Anh khắp nơi và gửi tên Anh ở đường ghi,
// nhưng ở ranh giới API (auth, staff, AI) vẫn nhận CẢ tên cũ (bản BE chưa migrate, bản cache cũ) rồi đổi về `ROLE.*`.
// Không rải trong component. Gỡ tên cũ ở Lô 5.

/** Tên Group (cũ và mới) → giá trị `ROLE` (tên mới). */
export const LEGACY_ROLE_NAMES: ReadonlyMap<string, RoleCode> = new Map<string, RoleCode>([
  ["chu", ROLE.owner],
  ["owner", ROLE.owner],
  ["quan_ly", ROLE.manager],
  ["manager", ROLE.manager],
  ["nv_kho", ROLE.warehouseStaff],
  ["warehouse_staff", ROLE.warehouseStaff],
  ["nv_giao", ROLE.deliveryStaff],
  ["delivery_staff", ROLE.deliveryStaff],
  ["cskh", ROLE.customerService],
  ["customer_service", ROLE.customerService],
]);

/** Tên Group bất kỳ (cũ hoặc mới) → giá trị `ROLE` (tên mới). Tên lạ giữ nguyên để UI vẫn hiện được. */
export function normalizeRole(name: string): string {
  return LEGACY_ROLE_NAMES.get(name) ?? name;
}

/** Chuẩn hoá danh sách tên Group; bỏ phần tử trùng sau khi chuẩn hoá, giữ thứ tự. */
export function normalizeRoles(names: readonly string[] | null | undefined): string[] {
  const out: string[] = [];
  for (const n of names ?? []) {
    const v = normalizeRole(n);
    if (!out.includes(v)) out.push(v);
  }
  return out;
}

/** `me.home`: nhận cả giá trị cũ và mới của hàng đợi gọi xác nhận; giá trị khác giữ nguyên. */
export function normalizeHome(home: string): string {
  return home === "cskh-queue" || home === "confirmation-queue" ? HOME_CONFIRMATION_QUEUE : home;
}
