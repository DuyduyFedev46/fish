// Menu ↔ quyền (bảng trong S7). Dữ liệu quyền lấy từ `me` (/api/auth/me/, S6); backend vẫn là
// lớp chặn thật (BR-PQ-12). Mỗi mục là MỘT route trong app/(console)/; trang bọc
// <ViewGuard view="..."> (features/auth) để chặn hiển thị + chặn gọi API khi thiếu quyền (S7-AC3).
// Module mới chỉ thay nội dung trang, không sửa bảng này trừ khi đổi luật.

/** Phần của `me` mà menu cần. Khai ở đây để shared/ không phụ thuộc features/auth; `Me` khớp kiểu này. */
export type Viewer = {
  groups: string[];
  permissions: string[];
  can_view_profit: boolean;
  home: "dashboard" | "my-deliveries" | "no-role";
  /** S48: còn dùng mật khẩu tạm → chỉ được mở màn "Đặt mật khẩu mới". */
  must_change_password?: boolean;
};
type Me = Viewer;

export type ViewKey =
  | "overview"
  | "orders"
  | "payments"
  | "refunds"
  | "deliveries"
  | "my-deliveries"
  | "inventory"
  | "purchasing"
  | "stocktake"
  | "reports"
  | "catalog"
  | "staff";

export type NavItem = {
  key: ViewKey;
  href: string;
  label: string;
  /** Nhãn ngắn cho thanh menu đáy (điện thoại). */
  short: string;
  icon: string; // tên Material Symbols
  section: "Điều hành" | "Sổ sách" | "Quản trị";
  visible: (me: Me) => boolean;
  /** Mô tả ngắn + story sẽ làm — hiện ở khung chờ khi màn chưa có. */
  summary: string;
  plannedIn: string;
  /**
   * Mục con (menu con) — vẽ thụt vào ngay dưới mục cha ở menu trái, KHÔNG lên menu đáy điện thoại (trên điện thoại vào
   * qua tab con trong màn cha). S12: "Hàng chờ thanh toán" là con của "Đơn & tiền".
   */
  parent?: ViewKey;
};

/**
 * Tên quyền (`app_label.codename`, khớp `permissions` của /api/auth/me/) mà console dựa vào — MỘT chỗ, không viết
 * chuỗi quyền rải rác trong component/mock. BE đổi codename thì chỉ sửa ở đây.
 */
export const PERM = {
  viewDashboard: "reports.view_dashboard",
  viewSalesOrder: "sales.view_salesorder",
  /** S11/S12: chỉ Chủ — xác nhận tiền tay, xử lý hàng chờ thanh toán lệch (BR-TT-07, BR-TT-09). */
  confirmPaymentManual: "sales.confirm_payment_manual",
  /** S16: xem danh sách phiếu hoàn (Chủ, Quản lý có — nv_kho/nv_giao không). Nút xác nhận/thất bại/thử lại theo
   * `available_actions` của từng phiếu (chỉ Chủ có sales.confirm_refund, S16-AC7). */
  viewRefund: "sales.view_refund",
  viewDeliveryNote: "delivery.view_deliverynote",
  viewBatch: "inventory.view_batch",
  viewPurchaseReceipt: "purchasing.view_purchasereceipt",
  viewStockReconciliation: "inventory.view_stockreconciliation",
  viewItem: "catalog.view_item",
  manageStaff: "accounts.manage_staff",
} as const;

/** Mã Group dùng trong luật menu (danh sách đầy đủ + nhãn: shared/lib/groups.ts). */
export const GROUP = { chu: "chu", quanLy: "quan_ly", nvKho: "nv_kho", nvGiao: "nv_giao" } as const;

const has = (me: Me, perm: string) => me.permissions.includes(perm);
const inGroup = (me: Me, ...groups: string[]) => me.groups.some((g) => groups.includes(g));
/** Chỉ thuộc nv_giao (không kèm Group nào khác). */
export const onlyDelivery = (me: Me) => me.groups.length > 0 && me.groups.every((g) => g === GROUP.nvGiao);

export const NAV: NavItem[] = [
  {
    key: "overview",
    summary: "KPI trong ngày, đơn gần đây, lô cận hạn và tồn theo lô.",
    plannedIn: "S8",
    href: "/overview/",
    label: "Tổng quan",
    short: "Tổng quan",
    icon: "dashboard",
    section: "Điều hành",
    // S6 (BE đã chốt): quyền thật reports.view_dashboard (chu/quan_ly/nv_kho); /api/dashboard/summary/ đòi quyền này.
    visible: (me) => has(me, PERM.viewDashboard),
  },
  {
    key: "orders",
    summary: "Danh sách đơn, xác nhận thanh toán, huỷ và hoàn tiền.",
    plannedIn: "S10, S11",
    href: "/orders/",
    label: "Đơn & tiền",
    short: "Đơn",
    icon: "receipt_long",
    section: "Điều hành",
    // S10 (L7): màn Đơn đọc endpoint riêng GET /api/sales/orders/ (đòi sales.view_salesorder) → bỏ điều kiện tạm
    // reports.view_dashboard của code review trước deploy 1. Vẫn ẩn với người CHỈ thuộc nv_giao (S7-AC2, L-4).
    visible: (me) => has(me, PERM.viewSalesOrder) && !onlyDelivery(me),
  },
  {
    key: "payments",
    summary: "Khoản tiền về lệch: thiếu, thừa, về sau khi đơn tự huỷ, không khớp đơn.",
    plannedIn: "S12, S13",
    href: "/orders/payments/",
    label: "Hàng chờ thanh toán",
    short: "Hàng chờ",
    icon: "rule",
    section: "Điều hành",
    parent: "orders",
    // S12-AC7: chỉ người có sales.confirm_payment_manual (Chủ). Quản lý/NV kho có view_paymenttransaction nhưng BE trả 403
    // cho GET ?resolution_status=OPEN → menu con không hiện.
    visible: (me) => has(me, PERM.viewSalesOrder) && has(me, PERM.confirmPaymentManual) && !onlyDelivery(me),
  },
  {
    key: "refunds",
    summary: "Phiếu hoàn đang chờ Chủ chuyển khoản: xác nhận, báo thất bại, thử lại.",
    plannedIn: "S16",
    href: "/orders/refunds/",
    label: "Phiếu hoàn chờ chuyển",
    short: "Phiếu hoàn",
    icon: "currency_exchange",
    section: "Điều hành",
    parent: "orders",
    // S16-AC7: Quản lý có sales.view_refund nên VẪN thấy danh sách, chỉ không có nút (available_actions của từng
    // phiếu không có confirm/mark_failed/retry vì thiếu sales.confirm_refund) — khớp cách BE tính available_actions.
    visible: (me) => has(me, PERM.viewRefund) && !onlyDelivery(me),
  },
  {
    key: "deliveries",
    summary: "Bảng phiếu giao, gán và đổi người giao.",
    plannedIn: "S17",
    href: "/deliveries/",
    label: "Giao hàng",
    short: "Giao hàng",
    icon: "local_shipping",
    section: "Điều hành",
    visible: (me) => has(me, PERM.viewDeliveryNote) && !onlyDelivery(me),
  },
  {
    key: "my-deliveries",
    summary: "Các phiếu giao được gán cho bạn hôm nay.",
    plannedIn: "S20",
    href: "/my-deliveries/",
    label: "Việc giao của tôi",
    short: "Việc giao",
    icon: "two_wheeler",
    section: "Điều hành",
    visible: (me) => inGroup(me, GROUP.nvGiao),
  },
  {
    key: "inventory",
    summary: "Tồn theo lô, xuất theo hạn dùng sớm nhất (FEFO), mở bán và chốt lô.",
    plannedIn: "S8, S25",
    href: "/inventory/",
    label: "Kho & lô",
    short: "Kho",
    icon: "inventory_2",
    section: "Điều hành",
    // Code review trước deploy 1: màn Kho & lô (và tab "Hoạt động") hiện đọc TẠM /api/dashboard/summary/ → cần CẢ
    // inventory.view_batch VÀ reports.view_dashboard.
    // TODO(S25): khi Kho & lô chuyển sang endpoint lô riêng (S25) thì bỏ điều kiện viewDashboard.
    visible: (me) => has(me, PERM.viewBatch) && has(me, PERM.viewDashboard),
  },
  {
    key: "purchasing",
    summary: "Phiếu nhập lô tại cảng, hoá đơn và chi phí mua.",
    plannedIn: "S28",
    href: "/purchasing/",
    label: "Mua hàng",
    short: "Mua",
    icon: "shopping_cart",
    section: "Điều hành",
    visible: (me) => has(me, PERM.viewPurchaseReceipt),
  },
  {
    key: "stocktake",
    summary: "Nhập số kiểm kê và duyệt chênh lệch.",
    plannedIn: "S34",
    href: "/stocktake/",
    label: "Kiểm kê",
    short: "Kiểm kê",
    icon: "fact_check",
    section: "Điều hành",
    visible: (me) => has(me, PERM.viewStockReconciliation),
  },
  {
    key: "reports",
    summary: "Lãi lỗ theo lô và theo kỳ.",
    plannedIn: "S36",
    href: "/reports/",
    label: "Báo cáo lãi lỗ",
    short: "Lãi lỗ",
    icon: "monitoring",
    section: "Sổ sách",
    visible: (me) => me.can_view_profit,
  },
  {
    key: "catalog",
    summary: "Mặt hàng, nhóm hàng, giá niêm yết và combo.",
    plannedIn: "S38",
    href: "/catalog/",
    label: "Danh mục & giá",
    short: "Danh mục",
    icon: "sell",
    section: "Sổ sách",
    // Điều phối chốt 2026-09-24: menu hiện khi có catalog.view_item (nv_kho cũng có); phần GIÁ bên trong màn
    // chỉ hiện khi có catalog.view_itemprice (S38/S39 làm).
    visible: (me) => has(me, PERM.viewItem),
  },
  {
    key: "staff",
    summary: "Tài khoản nhân viên, nhóm quyền và nhật ký hoạt động.",
    plannedIn: "S41, S43",
    href: "/staff/",
    label: "Nhân sự · Nhật ký",
    short: "Nhân sự",
    icon: "badge",
    section: "Quản trị",
    visible: (me) => has(me, PERM.manageStaff),
  },
];

/** Trang "Tài khoản của tôi" (S46/S47): mọi người đã đăng nhập và có Group đều mở được — không nằm trong menu quyền. */
export const ACCOUNT_HREF = "/account/";
export const ACCOUNT_LABEL = "Tài khoản của tôi";

/**
 * Ghi chú S7 bảng quyền: "Đơn & tiền" chỉ ghi `sales.view_salesorder`. NV giao có quyền đó (để xem
 * đơn của phiếu mình, S5) nhưng S7-AC2 yêu cầu menu của giao1 CHỈ có "Việc giao của tôi" → ẩn
 * "Đơn & tiền" với người chỉ thuộc nv_giao. Đã ghi lệch này ở 03-dev-notes.md.
 */
export function visibleNav(me: Me | null): NavItem[] {
  if (!me || me.home === "no-role") return [];
  return NAV.filter((n) => n.visible(me));
}

/**
 * Mục menu ứng với đường dẫn: khớp dài nhất thắng, để "/orders/payments/" chọn mục con "Hàng chờ thanh toán" chứ không
 * phải mục cha "Đơn & tiền" ("/orders/").
 */
export function navMatch(pathname: string, items: NavItem[] = NAV): NavItem | undefined {
  const path = pathname.endsWith("/") ? pathname : pathname + "/";
  return items
    .filter((n) => path.startsWith(n.href))
    .sort((a, b) => b.href.length - a.href.length)[0];
}

export function navItem(key: ViewKey): NavItem {
  return NAV.find((n) => n.key === key)!;
}

export function canView(me: Me | null, key: ViewKey): boolean {
  if (!me || me.home === "no-role") return false;
  return navItem(key).visible(me);
}

/** S48: màn "Đặt mật khẩu mới" (bắt buộc khi `me.must_change_password`) — ngoài nhóm (console), không có menu. */
export const SET_PASSWORD_HREF = "/set-password/";

/** Trang đầu tiên sau đăng nhập, theo `me.home` (S6). Còn mật khẩu tạm (S48) → màn đặt mật khẩu mới. */
export function homePath(me: Me): string {
  if (me.must_change_password) return SET_PASSWORD_HREF;
  if (me.home === "no-role") return "/no-role/";
  if (me.home === "my-deliveries") return "/my-deliveries/";
  const first = visibleNav(me)[0];
  return canView(me, "overview") ? "/overview/" : first ? first.href : "/no-role/";
}

/** `next` sau đăng nhập chỉ nhận đường dẫn nội bộ (chống open redirect). */
export function safeNext(next: string | null): string | null {
  if (!next || !next.startsWith("/") || next.startsWith("//")) return null;
  return next;
}
