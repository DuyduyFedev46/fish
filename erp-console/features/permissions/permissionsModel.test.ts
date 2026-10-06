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
  showsAllCustomers,
  isGroupWriter,
  EMPTY_DRAFT,
  cleanDraft,
  draftProblem,
  draftSize,
  isScopeInactive,
  saveBodyOf,
  scopeValueLabel,
  setScopeInDraft,
  toggleInDraft,
  breakingWarnings,
  labelOfGroup,
  parseGroupCode,
  planToggle,
  sectionsOf,
  toggleMessage,
} from "./permissionsModel";
import type { CapabilityState, DataScopeRow, RegistryItem } from "./types";

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
  it("chip Được gán lấy từ phạm vi BE trả, không còn hằng số theo nhóm (PV-11)", () => {
    const courierScope = { orders: "assigned_deliveries", deliveries: "assigned", customers: "assigned_deliveries" };
    const managerScope = { orders: "all", deliveries: "all", customers: "all" };
    expect(isAssignedOnly(courierScope, "deliver")).toBe(true);
    expect(isAssignedOnly(courierScope, "view_orders")).toBe(true);
    expect(isAssignedOnly(managerScope, "deliver")).toBe(false);
    expect(isAssignedOnly(managerScope, "view_orders")).toBe(false);
    // Chủ đổi Đơn hàng của nhóm Quản lý sang "gán cho tôi" thì chip hiện theo, không cần sửa FE.
    expect(isAssignedOnly({ ...managerScope, orders: "assigned_or_confirmation" }, "view_orders")).toBe(true);
    expect(isAssignedOnly(undefined, "view_orders")).toBe(false);
    expect(isAssignedOnly(courierScope, "pack_print")).toBe(false);
  });
  it("showsAllCustomers: chỉ khi việc bật và phạm vi Khách hàng = Tất cả", () => {
    expect(showsAllCustomers({ customers: "all" }, true)).toBe(true);
    expect(showsAllCustomers({ customers: "assigned_deliveries" }, true)).toBe(false);
    expect(showsAllCustomers({ customers: "all" }, false)).toBe(false);
    expect(showsAllCustomers(undefined, true)).toBe(true);
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

describe("isGroupWriter (Duy chốt 06/10: superuser ngoài nhóm Chủ được ghi)", () => {
  const OWNER_ONLY = ["sales.confirm_payment_manual", "sales.confirm_refund", "accounts.manage_staff", "ai.manage_ai_policy", "inventory.close_batch"];
  it("Chủ ghi được", () => {
    expect(isGroupWriter({ groups: ["owner"], permissions: [] })).toBe(true);
  });
  it("superuser ghi được dù không thuộc nhóm Chủ (cờ is_superuser)", () => {
    expect(isGroupWriter({ groups: [], permissions: [], is_superuser: true })).toBe(true);
    expect(isGroupWriter({ groups: ["manager"], permissions: [], is_superuser: true })).toBe(true);
  });
  it("me chưa có cờ: superuser nhận ra qua đủ quyền chỉ-Chủ", () => {
    expect(isGroupWriter({ groups: [], permissions: [...OWNER_ONLY, "reports.view_dashboard"] })).toBe(true);
  });
  it("người chỉ có manage_staff (Quản lý + quyền lẻ) vẫn chỉ xem", () => {
    expect(isGroupWriter({ groups: ["manager"], permissions: ["accounts.manage_staff"] })).toBe(false);
    expect(isGroupWriter({ groups: ["manager"], permissions: OWNER_ONLY.slice(0, 4) })).toBe(false);
    expect(isGroupWriter({ groups: ["manager"], permissions: [], is_superuser: false })).toBe(false);
    expect(isGroupWriter(null)).toBe(false);
  });
});

describe("bản nháp W3i (PV-11)", () => {
  const reg: RegistryItem[] = [item("view_orders", "Bán hàng"), item("view_customers", "Bán hàng"), item("deliver", "Bán hàng"), item("pack_print", "Bán hàng", { requires: ["deliver"] })];
  const states: Record<string, CapabilityState> = { view_orders: "off", view_customers: "off", deliver: "on", pack_print: "on" };
  const values = { orders: "all", customers: "none", receipts: "all" };

  it("bấm việc → vào bản nháp, bấm lại → hết thay đổi", () => {
    const a = toggleInDraft(reg, states, values, EMPTY_DRAFT, "view_orders");
    expect(a?.draft.capabilities).toEqual({ view_orders: true });
    const b = toggleInDraft(reg, states, values, a!.draft, "view_orders");
    expect(draftSize(b!.draft)).toBe(0);
  });
  it("việc có requires đi cùng cặp trong bản nháp", () => {
    const a = toggleInDraft(reg, states, values, EMPTY_DRAFT, "deliver");
    expect(a?.draft.capabilities).toEqual({ deliver: false, pack_print: false });
  });
  it("PO-Q1: bật Xem khách hàng khi Khách hàng = Không xem thì bản nháp tự đặt Tất cả", () => {
    const a = toggleInDraft(reg, states, values, EMPTY_DRAFT, "view_customers")!;
    expect(a.draft).toEqual({ capabilities: { view_customers: true }, scopes: { customers: "all" } });
    expect(draftProblem("manager", states, values, a.draft)).toBeNull();
    // bật rồi tắt lại: phạm vi tự đặt cũng bỏ
    const b = toggleInDraft(reg, states, values, a.draft, "view_customers")!;
    expect(draftSize(b.draft)).toBe(0);
  });
  it("PO-Q1 không ghi đè khi Chủ đã chọn phạm vi khách khác Không xem", () => {
    const withValue = { ...values, customers: "assigned_deliveries" };
    const a = toggleInDraft(reg, states, withValue, EMPTY_DRAFT, "view_customers")!;
    expect(a.draft.scopes).toEqual({});
  });
  it("draftProblem: bật Xem khách hàng mà Khách hàng = Không xem bị chặn ở FE (BE cũng chặn)", () => {
    const d = setScopeInDraft({ ...states, view_customers: "on" }, { ...values, customers: "all" }, EMPTY_DRAFT, "customers", "none");
    expect(draftProblem("manager", { ...states, view_customers: "on" }, { ...values, customers: "all" }, d)).toContain("khác Không xem");
    expect(draftProblem("owner", states, values, d)).toBeNull();
  });
  it("cleanDraft bỏ khoá trùng giá trị đang lưu", () => {
    expect(cleanDraft({ capabilities: { view_orders: false, deliver: false }, scopes: { orders: "all", receipts: "created_by_me" } }, states, values)).toEqual({
      capabilities: { deliver: false },
      scopes: { receipts: "created_by_me" },
    });
  });
  it("saveBodyOf: một PUT, chỉ khoá đã đổi, luôn có version (PV-10-AC8)", () => {
    const d = { capabilities: { view_orders: true }, scopes: { orders: "all" } };
    expect(saveBodyOf("41", d, false)).toEqual({ version: "41", capabilities: { view_orders: true }, scopes: { orders: "all" } });
    expect(saveBodyOf("41", { capabilities: {}, scopes: { orders: "all" } }, true)).toEqual({ version: "41", scopes: { orders: "all" }, confirm_customer_data_widening: true });
  });
  it("breakingWarnings chỉ nêu việc đang bật mà bản nháp tắt", () => {
    const out = breakingWarnings([item("view_orders", "Bán hàng")], { view_orders: "on" }, { capabilities: { view_orders: false }, scopes: {} }, 2);
    expect(out).toHaveLength(1);
    expect(out[0].text).toContain("Hiện có 2 người");
    expect(breakingWarnings([item("view_orders", "Bán hàng")], { view_orders: "off" }, { capabilities: { view_orders: false }, scopes: {} }, 2)).toEqual([]);
  });
});

describe("ô phạm vi mờ (PV-11-AC2, AC3)", () => {
  const row = (extra: Partial<DataScopeRow>): DataScopeRow => ({
    key: "orders",
    label: "Đơn hàng",
    value: "all",
    editable: true,
    customer_data: true,
    gate_capability: "view_orders",
    inactive_reason: 'Không xem — bật việc "Xem đơn" trước',
    note: null,
    options: [{ value: "all", label: "Tất cả đơn", rank: 2 }],
    ...extra,
  });
  it("mờ khi BE báo inactive_reason và việc gốc chưa bật", () => {
    expect(isScopeInactive(row({}), { view_orders: "off" }, EMPTY_DRAFT)).toBe(true);
  });
  it("hết mờ ngay khi bật việc gốc trong bản nháp, chưa cần lưu", () => {
    expect(isScopeInactive(row({}), { view_orders: "off" }, { capabilities: { view_orders: true }, scopes: {} })).toBe(false);
  });
  it("gate_capability null: chỉ dựa vào inactive_reason, không có gì để bỏ mờ", () => {
    const r = row({ gate_capability: null, inactive_reason: "Nhóm không có quyền xem phiếu giao" });
    expect(isScopeInactive(r, { view_orders: "on" }, { capabilities: { view_orders: true }, scopes: {} })).toBe(true);
  });
  it("inactive_reason null thì không mờ", () => {
    expect(isScopeInactive(row({ inactive_reason: null }), { view_orders: "off" }, EMPTY_DRAFT)).toBe(false);
  });
  it("scopeValueLabel: nhãn lựa chọn, 'Theo Đơn hàng', 'Tất cả', 'Không xem'", () => {
    expect(scopeValueLabel(row({}), "all")).toBe("Tất cả đơn");
    expect(scopeValueLabel(row({ options: [] }), "follows_orders")).toBe("Theo Đơn hàng");
    expect(scopeValueLabel(row({ options: [] }), "all")).toBe("Tất cả");
    expect(scopeValueLabel(row({ options: [] }), "none")).toBe("Không xem");
  });
});
