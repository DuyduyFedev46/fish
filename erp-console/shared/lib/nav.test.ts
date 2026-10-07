// Menu trái theo UI-RULES §2.1: thứ tự, nhóm, quyền, mục con, mục `soon`. Người xem tự dựng (mock chưa có quyền mới).
import { describe, expect, it } from "vitest";
import { canView, homeLabel, homePath, menuItems, NAV, NAV_SECTIONS, navMatch, PERM, visibleNav, type Viewer } from "@/shared/lib/nav";
import { ROLE } from "@/shared/lib/roles";

const viewer = (over: Partial<Viewer>): Viewer => ({
  groups: [],
  permissions: [],
  can_view_profit: false,
  home: "dashboard",
  ...over,
});

const OWNER = viewer({
  groups: [ROLE.owner],
  can_view_profit: true,
  permissions: Object.values(PERM),
});
const DELIVERY = viewer({
  groups: [ROLE.deliveryStaff],
  home: "my-deliveries",
  permissions: [PERM.viewSalesOrder, PERM.viewDeliveryNote],
});
const WAREHOUSE = viewer({
  groups: [ROLE.warehouseStaff],
  permissions: [PERM.viewDashboard, PERM.viewBatch, PERM.viewPurchaseReceipt, PERM.viewStockReconciliation, PERM.viewItem],
});

describe("superuser chỉ thuộc delivery_staff (N1)", () => {
  it("thấy menu như Chủ, không bị thu gọn như nhân viên giao", () => {
    const su = viewer({ ...OWNER, groups: [ROLE.deliveryStaff], is_superuser: true });
    expect(menuItems(su).length).toBeGreaterThanOrEqual(menuItems(OWNER).length);
    expect(menuItems(su).length).toBeGreaterThan(menuItems(DELIVERY).length);
  });
});

describe("bảng NAV", () => {
  it("nhóm theo đúng thứ tự UI-RULES §2.1, không xen kẽ", () => {
    const seen: string[] = [];
    for (const n of NAV.filter((x) => x.menu !== false)) {
      if (seen[seen.length - 1] !== n.section) seen.push(n.section);
    }
    expect(seen).toEqual(NAV_SECTIONS);
  });

  it("key và href không trùng", () => {
    expect(new Set(NAV.map((n) => n.key)).size).toBe(NAV.length);
    expect(new Set(NAV.map((n) => n.href)).size).toBe(NAV.length);
  });

  it("mục con luôn trỏ tới một mục cha có thật và không hiện ở menu", () => {
    for (const n of NAV.filter((x) => x.parent)) {
      expect(NAV.some((p) => p.key === n.parent)).toBe(true);
      expect(n.menu).toBe(false);
    }
  });
});

describe("menuItems", () => {
  it("Chủ: không có mục con, không có mục chưa làm (soon), không có AI của tôi", () => {
    const keys = menuItems(OWNER).map((n) => n.key);
    expect(keys).not.toContain("payments");
    expect(keys).not.toContain("refunds");
    expect(keys).not.toContain("content-categories");
    expect(keys).not.toContain("ai-settings");
    expect(keys).not.toContain("ai-actions");
    for (const n of NAV.filter((x) => x.soon)) expect(keys).not.toContain(n.key);
    expect(keys[0]).toBe("overview");
  });

  it("visibleNav vẫn trả mục con và mục soon để tô sáng/chặn truy cập", () => {
    const keys = visibleNav(OWNER).map((n) => n.key);
    expect(keys).toContain("payments");
    expect(keys).toContain("customers");
  });

  it("NV giao chỉ thấy Việc giao của tôi (ngoại lệ onlyDelivery)", () => {
    expect(menuItems(DELIVERY).map((n) => n.key)).toEqual(["my-deliveries"]);
    expect(canView(DELIVERY, "orders")).toBe(false);
    expect(canView(DELIVERY, "deliveries")).toBe(false);
    expect(canView(DELIVERY, "ai-settings")).toBe(false);
  });

  it("Việc giao của tôi theo nhóm, không theo quyền", () => {
    expect(canView(OWNER, "my-deliveries")).toBe(false);
    expect(canView(viewer({ groups: [ROLE.owner, ROLE.deliveryStaff], permissions: [] }), "my-deliveries")).toBe(true);
  });

  it("NV kho thấy kho, mua hàng, kiểm kê, danh mục; không thấy báo cáo lãi lỗ hay nhân sự", () => {
    const keys = menuItems(WAREHOUSE).map((n) => n.key);
    expect(keys).toEqual(["overview", "purchasing", "inventory", "stocktake", "catalog"]);
  });

  it("không đăng nhập hoặc no-role: menu rỗng", () => {
    expect(menuItems(null)).toEqual([]);
    expect(menuItems(viewer({ home: "no-role", permissions: [PERM.viewDashboard] }))).toEqual([]);
  });
});

describe("navMatch", () => {
  it("khớp dài nhất thắng: /orders/payments/ chọn mục con, không chọn Đơn & tiền", () => {
    expect(navMatch("/orders/payments/")?.key).toBe("payments");
    expect(navMatch("/orders/")?.key).toBe("orders");
    expect(navMatch("/ai/settings")?.key).toBe("ai-settings");
  });
  it("đường dẫn lạ -> undefined", () => {
    expect(navMatch("/khong-co/")).toBeUndefined();
  });
});

describe("homePath", () => {
  it("theo me.home và mật khẩu tạm", () => {
    expect(homePath(DELIVERY)).toBe("/my-deliveries/");
    expect(homePath(viewer({ home: "no-role" }))).toBe("/no-role/");
    expect(homePath(viewer({ must_change_password: true, permissions: [PERM.viewDashboard] }))).toBe("/set-password/");
    expect(homePath(OWNER)).toBe("/overview/");
  });
  it("không có Tổng quan: về mục đầu của menu", () => {
    expect(homePath(viewer({ groups: [ROLE.manager], permissions: [PERM.viewItem] }))).toBe("/catalog/");
  });
});

describe("homeLabel", () => {
  it("nhãn nút về trang chính theo đích của homePath", () => {
    expect(homeLabel("/overview/")).toBe("Về Tổng quan");
    expect(homeLabel(homePath(DELIVERY))).toBe("Về Việc giao của tôi");
  });
  it("đích không có trong menu -> Về trang chính", () => {
    expect(homeLabel("/no-role/")).toBe("Về trang chính");
    expect(homeLabel("/set-password/")).toBe("Về trang chính");
  });
});

// Lô 5 CSKH (CS-17, CS-18): hai màn con, không có dòng riêng ở menu, theo quyền thật.
describe("Lô 5 CSKH: Quét mã tem và Kịch bản gọi", () => {
  const CS = viewer({ groups: [ROLE.customerService], home: "confirmation-queue", permissions: [PERM.viewDeliveryNote, PERM.confirmWithCustomer, PERM.viewCallScript] });
  const MANAGER = viewer({ groups: [ROLE.manager], permissions: [PERM.viewDeliveryNote, PERM.printLabel, PERM.confirmWithCustomer, PERM.viewCallScript] });
  const STOREKEEPER = viewer({ groups: [ROLE.warehouseStaff], permissions: [PERM.viewDeliveryNote, PERM.printLabel, PERM.packDeliveryNote] });

  it("Quét mã tem: Chủ, Quản lý, NV kho thấy; CSKH và NV giao không", () => {
    for (const v of [OWNER, MANAGER, STOREKEEPER]) expect(canView(v, "delivery-lookup")).toBe(true);
    for (const v of [CS, DELIVERY]) expect(canView(v, "delivery-lookup")).toBe(false);
  });

  it("Kịch bản gọi: Chủ, Quản lý, CSKH xem được; NV kho và NV giao không", () => {
    for (const v of [OWNER, MANAGER, CS]) expect(canView(v, "call-scripts")).toBe(true);
    for (const v of [STOREKEEPER, DELIVERY]) expect(canView(v, "call-scripts")).toBe(false);
  });

  it("hai màn là mục con: không có dòng ở menu trái, mục cha sáng", () => {
    expect(menuItems(OWNER).some((n) => n.key === "delivery-lookup" || n.key === "call-scripts")).toBe(false);
    expect(navMatch("/deliveries/lookup/")?.key).toBe("delivery-lookup");
    expect(navMatch("/confirmation/scripts/")?.key).toBe("call-scripts");
  });
});
