// Menu ↔ quyền (bảng trong S7). Dữ liệu quyền lấy từ `me` (/api/auth/me/, S6); backend vẫn là
// lớp chặn thật (BR-PQ-12). Mỗi mục là MỘT route trong app/(console)/; trang bọc
// <ViewGuard view="..."> (features/auth) để chặn hiển thị + chặn gọi API khi thiếu quyền (S7-AC3).
// Module mới chỉ thay nội dung trang, không sửa bảng này trừ khi đổi luật.

import { HOME_CONFIRMATION_QUEUE, ROLE } from "./roles";

/** Phần của `me` mà menu cần. Khai ở đây để shared/ không phụ thuộc features/auth; `Me` khớp kiểu này. */
export type Viewer = {
  groups: string[];
  permissions: string[];
  can_view_profit: boolean;
  home: "dashboard" | "my-deliveries" | typeof HOME_CONFIRMATION_QUEUE | "no-role";
  /** S48: còn dùng mật khẩu tạm → chỉ được mở màn "Đặt mật khẩu mới". */
  must_change_password?: boolean;
};
type Me = Viewer;

export type ViewKey =
  | "overview"
  | "orders"
  | "payments"
  | "refunds"
  | "customers"
  | "confirmation"
  | "deliveries"
  | "my-deliveries"
  | "purchasing"
  | "suppliers"
  | "inventory"
  | "returns"
  | "stocktake"
  | "ledger"
  | "catalog"
  | "reports"
  | "sales-invoices"
  | "purchase-invoices"
  | "content"
  | "content-categories"
  | "staff"
  | "permissions"
  | "audit-logs"
  | "ai-policy"
  | "ai-report"
  | "ai-settings"
  | "ai-actions";

/** Nhóm trong menu trái, đúng thứ tự UI-RULES §2.1. "" = không tiêu đề (Tổng quan). */
export type NavSection = "" | "Bán hàng" | "Hàng hoá & kho" | "Kế toán" | "Website" | "Quản trị";
export const NAV_SECTIONS: NavSection[] = ["", "Bán hàng", "Hàng hoá & kho", "Kế toán", "Website", "Quản trị"];

export type NavItem = {
  key: ViewKey;
  href: string;
  label: string;
  /** Nhãn ngắn cho thanh menu đáy (điện thoại). */
  short: string;
  icon: string; // tên Material Symbols
  section: NavSection;
  visible: (me: Me) => boolean;
  /** Mô tả ngắn + story sẽ làm — hiện ở khung chờ khi màn chưa có. */
  summary: string;
  plannedIn: string;
  /**
   * Mục con: KHÔNG có dòng riêng ở menu trái (UI-RULES §2.1). Vào qua tab/nút trong màn cha; khi đang ở mục con thì
   * mục cha sáng. Vẫn nằm trong bảng này để có quyền xem (ViewGuard), tiêu đề màn và đường dẫn.
   */
  parent?: ViewKey;
  /** `false` = không có dòng ở menu trái dù có quyền (mục con, màn vào từ menu avatar, màn sắp bỏ). Mặc định có. */
  menu?: boolean;
  /**
   * `true` = màn chưa làm ở lô hiện tại: có trong bảng (đủ thứ tự, quyền, icon) nhưng KHÔNG hiện ở menu để khỏi dẫn tới
   * trang 404. Lô làm màn đó bỏ dòng này. Xem 03-dev-notes.md, mục Lô 1 — FE.
   */
  soon?: boolean;
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
  /** S16: xem danh sách phiếu hoàn (Chủ, Quản lý có — warehouse_staff/delivery_staff không). Nút xác nhận/thất bại/thử lại theo
   * `available_actions` của từng phiếu (chỉ Chủ có sales.confirm_refund, S16-AC7). */
  viewRefund: "sales.view_refund",
  viewDeliveryNote: "delivery.view_deliverynote",
  viewBatch: "inventory.view_batch",
  /** Lô 7: mở bán lô (Quản lý, Chủ). */
  publishBatch: "inventory.publish_batch",
  /** Lô 7: chốt lô (chỉ Chủ). */
  closeBatch: "inventory.close_batch",
  /** Lô 7: huỷ phần tồn quá hạn và trả nhà cung cấp (chỉ Chủ). */
  cancelExpiredBatch: "inventory.cancel_expired_batch",
  /** Lô 7: thêm kho (chỉ Chủ). */
  addWarehouse: "inventory.add_warehouse",
  viewWarehouse: "inventory.view_warehouse",
  viewStockEntry: "inventory.view_stockentry",
  viewPurchaseReceipt: "purchasing.view_purchasereceipt",
  viewStockReconciliation: "inventory.view_stockreconciliation",
  viewItem: "catalog.view_item",
  /** A2 (02-stories.md, hồ sơ 2026-09-26-anh-mat-hang): Tầng 2 riêng cho ảnh mặt hàng — Chủ, Quản lý có;
   * warehouse_staff/delivery_staff không. KHÔNG mở rộng sang sửa mặt hàng (change_item) — đó vẫn là S38. */
  changeItemImage: "catalog.change_item_image",
  manageStaff: "accounts.manage_staff",
  /** S03 (AI Lô 1, chốt Duy 27/09): xem màn Nhật ký hoạt động — owner + manager; warehouse_staff/delivery_staff không (S03-AC5). */
  viewAuditLog: "accounts.view_auditlog",
  /** DW-13: quản lý chính sách AI — chỉ Chủ có (ai.manage_ai_policy). */
  manageAiPolicy: "ai.manage_ai_policy",
  /** CS-01 / CS-05 / CS-06: gọi xác nhận đơn khách hàng. */
  confirmWithCustomer: "delivery.confirm_with_customer",
  /** CS-12: đổi người nhận / địa chỉ giao. */
  changeRecipient: "delivery.change_recipient",
  /** CS-11 / CS-14: in tem nhãn giao hàng. */
  printLabel: "delivery.print_label",
  /** CS-07: Quản lý quyết định đơn không liên lạc được. */
  decideUnconfirmed: "delivery.decide_unconfirmed",
  /** CS-03: đóng gói chuyển READY. */
  packDeliveryNote: "delivery.pack_deliverynote",
  /** CMS-01: Quyền xem, soạn, đăng nội dung và quản lý chuyên mục */
  viewContentEntry: "content.view_entry",
  publishContentEntry: "content.publish_entry",
  addCategory: "content.add_category",
  changeCategory: "content.change_category",
  /** GL-05: xem bằng chứng đồng ý xử lý dữ liệu của đơn */
  viewPrivacyConsent: "sales.view_privacy_consent",
  /** B2 (02b): xem danh bạ khách — quyền Tầng 2 mới, khác `sales.view_customer` (phạm vi dòng của nv_kho, nv_giao). */
  viewCustomerList: "sales.view_customer_list",
  /** B6 (02b): giao / đổi người giao phiếu. */
  assignDelivery: "delivery.assign_deliverynote",
  viewSupplier: "purchasing.view_supplier",
  viewReturn: "inventory.view_returntostock",
  viewLedger: "inventory.view_stockledgerentry",
  viewSalesInvoice: "sales.view_salesinvoice",
  viewPurchaseInvoice: "purchasing.view_purchaseinvoice",
  /** Chi phí phụ của lô: chỉ Chủ (cả chứng từ là giá vốn). */
  viewPurchaseCost: "purchasing.view_purchasecost",
  viewItemPrice: "catalog.view_itemprice",
  /** Xem giá vốn (bất biến 1): chỉ Chủ. */
  viewCostPrice: "inventory.view_costprice",
  viewProfitReport: "reports.view_profitreport",
} as const;

const has = (me: Me, perm: string) => me.permissions.includes(perm);
const inGroup = (me: Me, ...groups: string[]) => me.groups.some((g) => groups.includes(g));
/** Chỉ thuộc delivery_staff (không kèm Group nào khác). */
export const onlyDelivery = (me: Me) => me.groups.length > 0 && me.groups.every((g) => g === ROLE.deliveryStaff);

/**
 * Thứ tự trong bảng = thứ tự ở menu trái (UI-RULES §2.1). Mỗi lô chỉ THÊM dòng/bỏ cờ `soon`, không đổi thứ tự nhóm.
 */
export const NAV: NavItem[] = [
  {
    key: "overview",
    summary: "KPI trong ngày, đơn gần đây, lô cận hạn và tồn theo lô.",
    plannedIn: "S8",
    href: "/overview/",
    label: "Tổng quan",
    short: "Tổng quan",
    icon: "dashboard",
    section: "",
    // S6 (BE đã chốt): quyền thật reports.view_dashboard (owner/manager/warehouse_staff); /api/dashboard/summary/ đòi quyền này.
    visible: (me) => has(me, PERM.viewDashboard),
  },

  // ---- Bán hàng ----
  {
    key: "orders",
    summary: "Danh sách đơn, xác nhận thanh toán, huỷ và hoàn tiền.",
    plannedIn: "S10, S11",
    href: "/orders/",
    label: "Đơn & tiền",
    short: "Đơn",
    icon: "receipt_long",
    section: "Bán hàng",
    // S10 (L7): màn Đơn đọc endpoint riêng GET /api/sales/orders/ (đòi sales.view_salesorder). Vẫn ẩn với người CHỈ
    // thuộc delivery_staff (S7-AC2, L-4).
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
    section: "Bán hàng",
    parent: "orders",
    menu: false, // tab của Đơn & tiền (UI-RULES §2.1)
    // S12-AC7: chỉ người có sales.confirm_payment_manual (Chủ).
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
    section: "Bán hàng",
    parent: "orders",
    menu: false, // tab của Đơn & tiền
    // S16-AC7: Quản lý có sales.view_refund nên VẪN thấy danh sách, chỉ không có nút.
    visible: (me) => has(me, PERM.viewRefund) && !onlyDelivery(me),
  },
  {
    key: "customers",
    summary: "Danh bạ khách hàng và lịch sử mua.",
    plannedIn: "Lô 6",
    href: "/customers/",
    label: "Khách hàng",
    short: "Khách",
    icon: "group",
    section: "Bán hàng",
    soon: true,
    visible: (me) => has(me, PERM.viewCustomerList),
  },
  {
    key: "confirmation",
    summary: "Hàng chờ gọi xác nhận đơn, hẹn gọi lại và xử lý đơn.",
    plannedIn: "CS-05",
    href: "/confirmation/",
    label: "Gọi xác nhận",
    short: "Xác nhận",
    icon: "phone_in_talk",
    section: "Bán hàng",
    visible: (me) => has(me, PERM.confirmWithCustomer),
  },
  {
    key: "deliveries",
    summary: "Bảng phiếu giao, gán và đổi người giao.",
    plannedIn: "S17",
    href: "/deliveries/",
    label: "Giao hàng",
    short: "Giao hàng",
    icon: "local_shipping",
    section: "Bán hàng",
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
    section: "Bán hàng",
    // Theo NHÓM (người nhận phiếu là thành viên nhóm delivery_staff), không theo quyền (02b mục 0 dòng 3).
    visible: (me) => inGroup(me, ROLE.deliveryStaff),
  },

  // ---- Hàng hoá & kho ----
  {
    key: "purchasing",
    summary: "Phiếu nhập lô tại cảng, hoá đơn và chi phí mua.",
    plannedIn: "S28",
    href: "/purchasing/",
    label: "Mua hàng",
    short: "Mua",
    icon: "shopping_cart",
    section: "Hàng hoá & kho",
    visible: (me) => has(me, PERM.viewPurchaseReceipt),
  },
  {
    key: "suppliers",
    summary: "Danh sách nhà cung cấp và số liệu mua.",
    plannedIn: "Lô 11",
    href: "/suppliers/",
    label: "Nhà cung cấp",
    short: "Nhà CC",
    icon: "storefront",
    section: "Hàng hoá & kho",
    soon: true,
    visible: (me) => has(me, PERM.viewSupplier),
  },
  {
    key: "inventory",
    summary: "Tồn theo lô, xuất theo hạn dùng sớm nhất, mở bán và chốt lô.",
    plannedIn: "S8, S25",
    href: "/inventory/",
    label: "Kho & lô",
    short: "Kho",
    icon: "inventory_2",
    section: "Hàng hoá & kho",
    // Lô 7: màn đọc từ R5 (GET /api/inventory/batches/) nên chỉ cần inventory.view_batch.
    visible: (me) => has(me, PERM.viewBatch),
  },
  {
    key: "returns",
    summary: "Hàng khách trả về, chờ duyệt nhập lại kho hoặc huỷ.",
    plannedIn: "Lô 9",
    href: "/returns/",
    label: "Hàng hoàn về kho",
    short: "Hoàn kho",
    icon: "assignment_return",
    section: "Hàng hoá & kho",
    soon: true,
    visible: (me) => has(me, PERM.viewReturn),
  },
  {
    key: "stocktake",
    summary: "Nhập số kiểm kê và duyệt chênh lệch.",
    plannedIn: "S34",
    href: "/stocktake/",
    label: "Kiểm kê",
    short: "Kiểm kê",
    icon: "fact_check",
    section: "Hàng hoá & kho",
    visible: (me) => has(me, PERM.viewStockReconciliation),
  },
  {
    key: "ledger",
    summary: "Mọi lần nhập, xuất, điều chỉnh tồn theo thời gian.",
    plannedIn: "Lô 7",
    href: "/ledger/",
    label: "Sổ nhập xuất",
    short: "Sổ kho",
    icon: "swap_vert",
    section: "Hàng hoá & kho",
    visible: (me) => has(me, PERM.viewLedger),
  },
  {
    key: "catalog",
    summary: "Mặt hàng, nhóm hàng, giá niêm yết và combo.",
    plannedIn: "S38",
    href: "/catalog/",
    label: "Danh mục & giá",
    short: "Danh mục",
    icon: "sell",
    section: "Hàng hoá & kho",
    // Điều phối chốt 2026-09-24: menu hiện khi có catalog.view_item (warehouse_staff cũng có); phần GIÁ bên trong màn
    // chỉ hiện khi có catalog.view_itemprice.
    visible: (me) => has(me, PERM.viewItem),
  },

  // ---- Kế toán ----
  {
    key: "reports",
    summary: "Lãi lỗ theo lô và theo kỳ.",
    plannedIn: "S36",
    href: "/reports/",
    label: "Báo cáo lãi lỗ",
    short: "Lãi lỗ",
    icon: "monitoring",
    section: "Kế toán",
    visible: (me) => me.can_view_profit,
  },
  {
    key: "sales-invoices",
    summary: "Hoá đơn bán đã phát hành, doanh thu và lãi gộp.",
    plannedIn: "Lô 12",
    href: "/sales-invoices/",
    label: "Hoá đơn bán",
    short: "HĐ bán",
    icon: "request_quote",
    section: "Kế toán",
    soon: true,
    visible: (me) => has(me, PERM.viewSalesInvoice) && !onlyDelivery(me),
  },
  {
    key: "purchase-invoices",
    summary: "Hoá đơn mua và chi phí phụ của lô.",
    plannedIn: "Lô 12",
    href: "/purchase-invoices/",
    label: "Hoá đơn mua & chi phí",
    short: "HĐ mua",
    icon: "receipt",
    section: "Kế toán",
    soon: true,
    visible: (me) => has(me, PERM.viewPurchaseInvoice) || has(me, PERM.viewPurchaseCost),
  },

  // ---- Website ----
  {
    key: "content",
    summary: "Bài viết, trang chính sách, chuyên mục và nội dung web.",
    plannedIn: "CMS-01",
    href: "/content/",
    label: "Nội dung",
    short: "Nội dung",
    icon: "article",
    section: "Website",
    visible: (me) => has(me, PERM.viewContentEntry),
  },
  {
    key: "content-categories",
    summary: "Quản lý chuyên mục bài viết.",
    plannedIn: "CMS-02",
    href: "/content/categories/",
    label: "Chuyên mục",
    short: "Chuyên mục",
    icon: "category",
    section: "Website",
    parent: "content",
    menu: false, // vào bằng nút trong màn Nội dung
    visible: (me) => has(me, PERM.viewContentEntry),
  },

  // ---- Quản trị ----
  {
    key: "staff",
    summary: "Tài khoản nhân viên và nhóm quyền.",
    plannedIn: "S41, S43",
    href: "/staff/",
    label: "Nhân sự",
    short: "Nhân sự",
    icon: "badge",
    section: "Quản trị",
    visible: (me) => has(me, PERM.manageStaff),
  },
  {
    key: "permissions",
    summary: "Ma trận quyền theo nhóm: nhóm nào làm được việc gì.",
    plannedIn: "Lô 14",
    href: "/permissions/",
    label: "Phân quyền",
    short: "Phân quyền",
    icon: "admin_panel_settings",
    section: "Quản trị",
    soon: true,
    visible: (me) => has(me, PERM.manageStaff),
  },
  {
    key: "audit-logs",
    summary: "Mọi thay đổi trong hệ thống, kể cả việc do trợ lý AI đề xuất (ai:<tên>).",
    plannedIn: "S03",
    href: "/audit-logs/",
    label: "Nhật ký hoạt động",
    short: "Nhật ký",
    icon: "history",
    section: "Quản trị",
    // S03: owner + manager (accounts.view_auditlog); NV kho/giao không đọc toàn bộ nhật ký (S03-AC5).
    visible: (me) => has(me, PERM.viewAuditLog) && !onlyDelivery(me),
  },
  {
    key: "ai-policy",
    summary: "Chính sách hoạt động toàn cục và quản lý AI của nhân viên.",
    plannedIn: "DW-13",
    href: "/ai/policy/",
    label: "Chính sách AI",
    short: "Chính sách AI",
    icon: "policy",
    section: "Quản trị",
    visible: (me) => has(me, PERM.manageAiPolicy),
  },
  {
    key: "ai-report",
    summary: "Báo cáo tổng hợp hoạt động của các trợ lý AI cuối ngày.",
    plannedIn: "DW-22",
    href: "/ai/report/",
    label: "Báo cáo AI",
    short: "Báo cáo AI",
    icon: "insights",
    section: "Quản trị",
    visible: (me) => has(me, PERM.manageAiPolicy),
  },

  // ---- Không có dòng ở menu trái ----
  {
    key: "ai-settings",
    summary: "Cấu hình phân quyền và mức độ tự chủ của AI cá nhân.",
    plannedIn: "DW-12",
    href: "/ai/settings/",
    label: "AI của tôi",
    short: "AI của tôi",
    icon: "auto_awesome",
    section: "Quản trị",
    menu: false, // vào từ menu avatar (UI-RULES §2.2)
    visible: (me) => !onlyDelivery(me),
  },
  {
    key: "ai-actions",
    summary: "Các việc do AI đề xuất cần duyệt hoặc kiểm tra.",
    plannedIn: "DW-11",
    href: "/ai/actions/",
    label: "Việc AI",
    short: "Việc AI",
    icon: "smart_toy",
    section: "Quản trị",
    menu: false, // bỏ khỏi menu (02b mục 0 dòng 2); trang cũ còn tới Lô 17
    visible: (me) => !onlyDelivery(me),
  },
];

/** Màn "AI của tôi" (menu avatar). */
export const AI_SETTINGS_HREF = "/ai/settings/";

/** Trang "Tài khoản của tôi" (S46/S47): mọi người đã đăng nhập và có Group đều mở được — không nằm trong menu quyền. */
export const ACCOUNT_HREF = "/account/";
export const ACCOUNT_LABEL = "Tài khoản của tôi";

/**
 * Ghi chú S7 bảng quyền: "Đơn & tiền" chỉ ghi `sales.view_salesorder`. NV giao có quyền đó (để xem
 * đơn của phiếu mình, S5) nhưng S7-AC2 yêu cầu menu của giao1 CHỈ có "Việc giao của tôi" → ẩn
 * "Đơn & tiền" với người chỉ thuộc delivery_staff. Đã ghi lệch này ở 03-dev-notes.md.
 */
export function visibleNav(me: Me | null): NavItem[] {
  if (!me || me.home === "no-role") return [];
  return NAV.filter((n) => n.visible(me));
}

/** Các mục có dòng ở menu trái / menu đáy: có quyền, không phải mục con, chưa bị cờ `soon`. */
export function menuItems(me: Me | null): NavItem[] {
  return visibleNav(me).filter((n) => n.menu !== false && !n.soon);
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
  if (me.home === HOME_CONFIRMATION_QUEUE) return "/confirmation/";
  const first = menuItems(me)[0];
  return canView(me, "overview") ? "/overview/" : first ? first.href : "/no-role/";
}

/** Nhãn nút "về trang chính" theo đích của `homePath`: "Về Tổng quan", "Về Việc giao của tôi"; đích lạ → "Về trang chính". */
export function homeLabel(href: string): string {
  const item = navMatch(href);
  return item ? `Về ${item.label}` : "Về trang chính";
}

const MAX_NEXT_LENGTH = 2000;

/**
 * `next` sau đăng nhập chỉ nhận đường dẫn nội bộ (chống open redirect, L7-1).
 * Cùng luật nhánh "đường dẫn nội bộ" của `features/content/editor/safeHref.ts` (chép, không import chéo module):
 * bắt đầu bằng "/", ký tự thứ hai không phải "/" hay "\" (trình duyệt coi "/\host" là "//host"), không có ký tự
 * điều khiển hay khoảng trắng (mã <= 32, 127-159) và không quá 2000 ký tự. Không trim: chuỗi phải bắt đầu đúng bằng "/".
 * Giá trị vào là chuỗi đã giải mã (`URLSearchParams.get`), nên "/%5Cevil.example" tới đây là "/\evil.example".
 */
export function safeNext(next: string | null): string | null {
  if (!next || next.length > MAX_NEXT_LENGTH || !next.startsWith("/")) return null;
  if (next[1] === "/" || next[1] === "\\") return null;
  for (let i = 0; i < next.length; i++) {
    const code = next.charCodeAt(i);
    if (code <= 32 || (code >= 127 && code <= 159)) return null;
  }
  return next;
}
