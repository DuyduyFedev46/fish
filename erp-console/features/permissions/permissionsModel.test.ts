import { describe, expect, it } from "vitest";
import {
  ALL_CUSTOMERS_LABEL,
  CUSTOMERS_KEY,
  applyChanges,
  breakingWarning,
  cellMode,
  foldText,
  matchesTask,
  isAssignedOnly,
  isToggleable,
  labelOfGroup,
  parseGroupCode,
  planToggle,
  sectionsOf,
  toggleMessage,
} from "./permissionsModel";
import type { CapabilityState, RegistryItem } from "./types";

const item = (key: string, section: string, extra: Partial<RegistryItem> = {}): RegistryItem => ({
  key,
  label: `Việc ${key}`,
  section,
  owner_only: false,
  requires: [],
  ...extra,
});

const REGISTRY: RegistryItem[] = [
  item("set_price", "Hàng hoá & kho", { owner_only: true }),
  item("view_orders", "Bán hàng"),
  item("deliver", "Bán hàng"),
  item("pack_print", "Bán hàng", { requires: ["deliver"] }),
  item("view_audit", "Quản trị"),
  item("mystery", "Khu lạ"),
  item("view_profit", "Kế toán", { owner_only: true }),
];

describe("sectionsOf", () => {
  it("xếp khu theo thứ tự cố định, khu lạ đứng cuối, giữ thứ tự việc", () => {
    const names = sectionsOf(REGISTRY).map((s) => s.name);
    expect(names).toEqual(["Bán hàng", "Hàng hoá & kho", "Kế toán", "Quản trị", "Khu lạ"]);
    expect(sectionsOf(REGISTRY)[0].items.map((i) => i.key)).toEqual(["view_orders", "deliver", "pack_print"]);
  });
  it("registry rỗng → không có khu", () => {
    expect(sectionsOf([])).toEqual([]);
  });
});

describe("cellMode", () => {
  const price = REGISTRY[0];
  const orders = REGISTRY[1];
  it("cột Chủ luôn là owner dù trạng thái gì", () => {
    expect(cellMode(price, "owner", "off")).toBe("owner");
    expect(cellMode(orders, "owner", undefined)).toBe("owner");
  });
  it("việc Chỉ Chủ đang tắt ở nhóm khác → khoá", () => {
    expect(cellMode(price, "manager", "off")).toBe("locked");
    expect(cellMode(price, "manager", undefined)).toBe("locked");
  });
  it("việc thường theo trạng thái; thiếu = off", () => {
    expect(cellMode(orders, "manager", "on")).toBe("on");
    expect(cellMode(orders, "manager", "partial")).toBe("partial");
    expect(cellMode(orders, "manager", undefined)).toBe("off");
  });
  it("chỉ on/off/partial bấm được", () => {
    expect(isToggleable("on")).toBe(true);
    expect(isToggleable("off")).toBe(true);
    expect(isToggleable("partial")).toBe(true);
    expect(isToggleable("owner")).toBe(false);
    expect(isToggleable("locked")).toBe(false);
  });
});

describe("planToggle", () => {
  const states = (o: Record<string, CapabilityState>) => o;

  it("bật việc đang tắt: một việc, hoàn tác = tắt", () => {
    const p = planToggle(REGISTRY, states({ view_orders: "off" }), "view_orders");
    expect(p).toEqual({ changes: { view_orders: true }, undo: { view_orders: false }, alsoChanged: [], wanted: true });
  });
  it("tắt việc đang bật: hoàn tác = bật", () => {
    const p = planToggle(REGISTRY, states({ view_orders: "on" }), "view_orders");
    expect(p?.changes).toEqual({ view_orders: false });
    expect(p?.undo).toEqual({ view_orders: true });
    expect(p?.wanted).toBe(false);
  });
  it("bật việc phụ khi việc gốc đang tắt → bật cả gốc cùng lúc", () => {
    const p = planToggle(REGISTRY, states({ deliver: "off", pack_print: "off" }), "pack_print");
    expect(p?.changes).toEqual({ pack_print: true, deliver: true });
    expect(p?.alsoChanged).toEqual(["deliver"]);
    expect(p?.undo).toEqual({ pack_print: false, deliver: false });
  });
  it("bật việc phụ khi việc gốc đã bật → chỉ đổi một việc", () => {
    const p = planToggle(REGISTRY, states({ deliver: "on", pack_print: "off" }), "pack_print");
    expect(p?.changes).toEqual({ pack_print: true });
    expect(p?.alsoChanged).toEqual([]);
  });
  it("tắt việc gốc khi việc phụ đang bật → tắt cả phụ cùng lúc", () => {
    const p = planToggle(REGISTRY, states({ deliver: "on", pack_print: "on" }), "deliver");
    expect(p?.changes).toEqual({ deliver: false, pack_print: false });
    expect(p?.alsoChanged).toEqual(["pack_print"]);
    expect(p?.undo).toEqual({ deliver: true, pack_print: true });
  });
  it("tắt việc gốc khi việc phụ đã tắt → chỉ một việc", () => {
    const p = planToggle(REGISTRY, states({ deliver: "on", pack_print: "off" }), "deliver");
    expect(p?.changes).toEqual({ deliver: false });
  });
  it("đang partial: bấm = bật đủ, không có hoàn tác chính xác", () => {
    const p = planToggle(REGISTRY, states({ view_orders: "partial" }), "view_orders");
    expect(p?.wanted).toBe(true);
    expect(p?.changes).toEqual({ view_orders: true });
    expect(p?.undo).toBeNull();
  });
  it("việc không có trong registry → null", () => {
    expect(planToggle(REGISTRY, {}, "khong_co")).toBeNull();
  });
  it("thiếu trạng thái coi như tắt", () => {
    expect(planToggle(REGISTRY, {}, "view_orders")?.wanted).toBe(true);
  });
});

describe("applyChanges", () => {
  it("áp bật/tắt, không đụng bản gốc", () => {
    const before: Record<string, CapabilityState> = { a: "on", b: "partial" };
    const next = applyChanges(before, { a: false, b: true, c: true });
    expect(next).toEqual({ a: "off", b: "on", c: "on" });
    expect(before).toEqual({ a: "on", b: "partial" });
  });
});

describe("breakingWarning", () => {
  it("tắt việc làm hỏng màn → có cảnh báo kèm số người", () => {
    expect(breakingWarning("view_orders", false, 3)).toContain("3 người");
    expect(breakingWarning("deliver", false, 0)).not.toContain("Hiện có");
    expect(breakingWarning("view_audit", false, 1)).toBeTruthy();
  });
  it("bật, hoặc việc thường → không cảnh báo", () => {
    expect(breakingWarning("view_orders", true, 3)).toBeNull();
    expect(breakingWarning("view_customers", false, 3)).toBeNull();
  });
});

describe("toggleMessage", () => {
  const labelOf = (k: string) => `Việc ${k}`;
  it("nói đúng việc + nhóm + việc đi kèm", () => {
    const p = planToggle(REGISTRY, { deliver: "off", pack_print: "off" }, "pack_print");
    expect(p).not.toBeNull();
    const msg = toggleMessage(REGISTRY[3], "Nhân viên giao", p!, labelOf);
    expect(msg).toBe("Đã bật “Việc pack_print” cho Nhân viên giao (kèm Việc deliver).");
  });
  it("tắt không kèm gì", () => {
    const p = planToggle(REGISTRY, { view_orders: "on" }, "view_orders");
    expect(toggleMessage(REGISTRY[1], "CSKH", p!, labelOf)).toBe("Đã tắt “Việc view_orders” cho CSKH.");
  });
});

describe("tìm việc trong ma trận", () => {
  const a = { ...item("view_orders", "Bán hàng"), label: "Xem đơn hàng" };
  it("khớp không dấu, theo nhãn, khoá hoặc khu", () => {
    expect(matchesTask(a, "don hang")).toBe(true);
    expect(matchesTask(a, "VIEW_ORD")).toBe(true);
    expect(matchesTask(a, "ban hang")).toBe(true);
    expect(matchesTask(a, "  ")).toBe(true);
    expect(matchesTask(a, "kế toán")).toBe(false);
  });
  it("đ/Đ được bỏ dấu", () => {
    expect(foldText("Đơn Đã giao")).toBe("don da giao");
  });
});

describe("hằng và tiện ích", () => {
  it("nhóm giao chỉ làm trên phiếu được gán", () => {
    expect(isAssignedOnly("delivery_staff", "deliver")).toBe(true);
    expect(isAssignedOnly("delivery_staff", "view_orders")).toBe(true);
    expect(isAssignedOnly("delivery_staff", "view_customers")).toBe(false);
    expect(isAssignedOnly("manager", "deliver")).toBe(false);
  });
  it("khoá và nhãn xem khách", () => {
    expect(CUSTOMERS_KEY).toBe("view_customers");
    expect(ALL_CUSTOMERS_LABEL).toBe("Tất cả khách");
  });
  it("labelOfGroup: nhãn, thiếu thì mã", () => {
    expect(labelOfGroup("manager", { manager: "Quản lý" })).toBe("Quản lý");
    expect(labelOfGroup("x", {})).toBe("x");
  });
  it("parseGroupCode chỉ nhận mã hợp lệ", () => {
    expect(parseGroupCode("?group=delivery_staff")).toBe("delivery_staff");
    expect(parseGroupCode("?group=")).toBeNull();
    expect(parseGroupCode("")).toBeNull();
    expect(parseGroupCode("?group=Nguyen%20Van%20A")).toBeNull();
    expect(parseGroupCode("?group=../x")).toBeNull();
    expect(parseGroupCode("?group=" + "a".repeat(60))).toBeNull();
  });
});
