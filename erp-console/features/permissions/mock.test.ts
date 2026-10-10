import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MockRequest } from "@/shared/lib/http";
import type { GroupDetail, GroupSummary, ScopePreview } from "./types";

// Mock giữ đúng luật BE (02b §2.3): thứ tự kiểm, CAS version, 409, 400 xác nhận, PO-Q1, không tăng version khi không đổi gì.
// Người dùng và kho tạm được giả để chạy ở môi trường node.

type Viewer = { id: number; username: string; display_name: string; groups: string[]; is_active: boolean; is_superuser: boolean };
const users: Viewer[] = [
  { id: 1, username: "loc", display_name: "Lộc", groups: ["owner"], is_active: true, is_superuser: false },
  { id: 2, username: "ql1", display_name: "Chị Quản", groups: ["manager"], is_active: true, is_superuser: false },
  { id: 3, username: "kho1", display_name: "Anh Tâm", groups: ["warehouse_staff"], is_active: true, is_superuser: false },
  { id: 4, username: "giao1", display_name: "Giao 1", groups: ["delivery_staff"], is_active: true, is_superuser: false },
  { id: 5, username: "giao2", display_name: "Giao 2", groups: ["delivery_staff", "warehouse_staff"], is_active: true, is_superuser: false },
  { id: 6, username: "admin", display_name: "Quản trị", groups: [], is_active: true, is_superuser: true },
  { id: 8, username: "ql9", display_name: "Chị Mai", groups: ["manager"], is_active: true, is_superuser: false },
];
let viewer: Viewer = users[0];

vi.mock("@/features/auth/mock", () => ({
  MOCK_UNAUTHORIZED: { status: 401, body: { detail: "Chưa đăng nhập." } },
  mockRequireRecord: () => viewer,
  mockPermsOf: (u: Viewer) => (u.username === "ql1" ? ["reports.view_dashboard"] : ["accounts.manage_staff"]),
  mockUsers: () => users,
  sortGroups: (g: string[]) => g,
}));

const store = new Map<string, string>();
vi.stubGlobal("window", {
  sessionStorage: {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
  },
});

const { mockPermissionsApi } = await import("./mock");

const call = (method: MockRequest["method"], path: string, body?: unknown) => mockPermissionsApi({ method, path, body, token: "t" });
const getGroup = (code: string) => call("GET", `/api/staff/groups/${code}/`).body as GroupDetail;
const put = (code: string, body: unknown) => call("PUT", `/api/staff/groups/${code}/capabilities/`, body);
const preview = (code: string, body: unknown) => call("POST", `/api/staff/groups/${code}/permissions-preview/`, body);
const codeOf = (r: { body: unknown }) => (r.body as { code?: string }).code;

beforeEach(() => {
  store.clear();
  viewer = users[0];
});

describe("GET (contract Lô 2)", () => {
  it("danh sách có version và data_scope_values 6 đối tượng", () => {
    const list = call("GET", "/api/staff/groups/").body as GroupSummary[];
    const courierGroup = list.find((g) => g.code === "delivery_staff")!;
    expect(courierGroup.version).toBe("1");
    expect(courierGroup.data_scope_values).toEqual({ orders: "assigned_deliveries", deliveries: "assigned", confirmation: "pending_or_called_recently", returns: "assigned_deliveries", receipts: "all", customers: "assigned_deliveries" });
  });
  it("chi tiết có 8 dòng theo thứ tự D1..D8", () => {
    const rows = getGroup("manager").data_scopes;
    expect(rows.map((r) => r.key)).toEqual(["orders", "invoices", "deliveries", "confirmation", "returns", "receipts", "customers", "audit_log"]);
    expect(rows.find((r) => r.key === "invoices")).toMatchObject({ value: "follows_orders", editable: false, note: "Theo Đơn hàng", options: [] });
  });
  it("nhãn đã sửa theo BE (L3): CSKH Đơn hàng và Phiếu giao", () => {
    const rows = getGroup("customer_service").data_scopes;
    const orders = rows.find((r) => r.key === "orders")!;
    expect(orders.options.find((o) => o.value === orders.value)?.label).toBe("Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận");
    const deliveries = rows.find((r) => r.key === "deliveries")!;
    expect(deliveries.options.find((o) => o.value === deliveries.value)?.label).toBe("Phiếu gán cho tôi");
    expect(JSON.stringify(rows)).not.toContain("Trong phạm vi gọi");
    expect(deliveries.inactive_reason).toBe("Nhóm không có quyền xem phiếu giao"); // gate_capability null → chỉ có lý do
    expect(deliveries.gate_capability).toBeNull();
  });
  it("ô mờ khi tắt việc gốc: NV kho không có Xem khách hàng", () => {
    const customers = getGroup("warehouse_staff").data_scopes.find((r) => r.key === "customers")!;
    expect(customers.inactive_reason).toBe('Không xem — bật việc "Xem khách hàng" trước');
    expect(customers.value).toBe("none");
  });
  it("nhóm Chủ: mọi dòng không sửa được, note 'Chủ luôn thấy tất cả'", () => {
    const rows = getGroup("owner").data_scopes;
    expect(rows.every((r) => !r.editable && r.note !== null)).toBe(true);
    expect(rows.find((r) => r.key === "orders")?.value).toBe("all");
  });
});

describe("PUT: thứ tự kiểm và CAS version", () => {
  it("403 với người không phải Chủ/superuser; superuser ngoài nhóm Chủ ghi được", () => {
    viewer = users[1];
    expect(put("manager", { version: "1", capabilities: { view_orders: false } }).status).toBe(403);
    viewer = users[6];
    expect(put("manager", { version: "1", capabilities: { view_orders: false } }).status).toBe(403);
    viewer = users[5];
    expect(put("manager", { version: "1", capabilities: { deliver: true } }).status).toBe(200);
  });
  it("L2: người không phải Chủ gọi PUT/POST vào nhóm lạ nhận 403 trước 404", () => {
    viewer = users[1];
    expect(put("zzz", { version: "1", capabilities: { deliver: true } }).status).toBe(403);
    expect(preview("zzz", { capabilities: { deliver: true } }).status).toBe(403);
  });
  it("404 nhóm lạ; 400 GROUP_LOCKED nhóm Chủ", () => {
    expect(put("zzz", { version: "1", capabilities: { view_orders: true } }).status).toBe(404);
    expect(codeOf(put("owner", { version: "1", capabilities: { view_orders: true } }))).toBe("GROUP_LOCKED");
  });
  it("400: khoá lạ, thiếu version, rỗng, kiểu sai, phạm vi lạ/chỉ đọc/giá trị lạ, việc chỉ-Chủ", () => {
    expect(codeOf(put("manager", { version: "1", capabilities: { x: true } }))).toBe("INPUT_NOT_ALLOWED");
    expect(codeOf(put("manager", { version: "1", mode: 1, capabilities: { view_orders: true } }))).toBe("INPUT_NOT_ALLOWED");
    expect(codeOf(put("manager", { capabilities: { view_orders: true } }))).toBe("INVALID_INPUT");
    expect(codeOf(put("manager", { version: "1" }))).toBe("INVALID_INPUT");
    expect(codeOf(put("manager", { version: "1", capabilities: { view_orders: "yes" } }))).toBe("INVALID_INPUT");
    expect(codeOf(put("manager", { version: "1", scopes: { stock: "all" } }))).toBe("SCOPE_OBJECT_UNKNOWN");
    expect(codeOf(put("manager", { version: "1", scopes: { invoices: "all" } }))).toBe("SCOPE_READ_ONLY");
    expect(codeOf(put("manager", { version: "1", scopes: { audit_log: "all" } }))).toBe("SCOPE_READ_ONLY");
    expect(codeOf(put("manager", { version: "1", scopes: { receipts: "mine" } }))).toBe("SCOPE_VALUE_INVALID");
    expect(codeOf(put("manager", { version: "1", capabilities: { set_price: true } }))).toBe("BR-PQ-32");
  });
  it("lưu việc + phạm vi trong MỘT yêu cầu, version tăng, có sự kiện phạm vi", () => {
    const r = put("warehouse_staff", { version: "1", capabilities: { deliver: false, pack_print: false }, scopes: { receipts: "created_by_me_today" } });
    expect(r.status).toBe(200);
    const g = r.body as GroupDetail;
    expect(g.version).toBe("2");
    expect(g.data_scope_values.receipts).toBe("created_by_me_today");
    expect(g.capabilities.deliver).toBe("off");
    const ev = g.timeline.find((e) => e.kind === "change_group_data_scopes");
    expect(ev?.label).toBe("Đổi phạm vi Phiếu nhập: Tất cả phiếu → Do tôi tạo trong ngày");
  });
  it("409 GROUP_CHANGED khi version cũ, không đổi gì (PV-10-AC1/AC2)", () => {
    expect(put("manager", { version: "1", capabilities: { deliver: false, pack_print: false } }).status).toBe(200);
    const stale = put("manager", { version: "1", scopes: { receipts: "created_by_me" } });
    expect(stale.status).toBe(409);
    expect(codeOf(stale)).toBe("GROUP_CHANGED");
    expect((stale.body as { detail: string }).detail).toBe("Nhóm này vừa được người khác đổi. Tải lại để xem bản mới.");
    expect(getGroup("manager").data_scope_values.receipts).toBe("all");
  });
  it("khác nhóm không xung đột (PV-10-AC3)", () => {
    put("manager", { version: "1", capabilities: { deliver: false, pack_print: false } });
    expect(put("warehouse_staff", { version: "1", scopes: { receipts: "created_by_me" } }).status).toBe(200);
  });
  it("không có thay đổi thật: 200, KHÔNG tăng version, không sự kiện", () => {
    const r = put("manager", { version: "1", scopes: { receipts: "all" } });
    expect(r.status).toBe(200);
    expect((r.body as GroupDetail).version).toBe("1");
    expect((r.body as GroupDetail).timeline.filter((e) => e.kind === "change_group_data_scopes")).toHaveLength(0);
  });
});

describe("PO-Q1", () => {
  it("bật Xem khách hàng mà Khách hàng = Không xem → 400 SCOPE_VALUE_INVALID, không đổi gì", () => {
    const r = put("warehouse_staff", { version: "1", capabilities: { view_customers: true } });
    expect(r.status).toBe(400);
    expect(codeOf(r)).toBe("SCOPE_VALUE_INVALID");
    expect(getGroup("warehouse_staff").version).toBe("1");
  });
  it("gửi kèm scopes.customers = all thì qua bước PO-Q1, nhưng thiếu xác nhận mở rộng", () => {
    const r = put("warehouse_staff", { version: "1", capabilities: { view_customers: true }, scopes: { customers: "all" } });
    expect(codeOf(r)).toBe("CUSTOMER_DATA_WIDENING_UNCONFIRMED");
  });
  it("đặt Khách hàng = Không xem khi việc đang bật → 400", () => {
    const r = put("manager", { version: "1", scopes: { customers: "none" } });
    expect(codeOf(r)).toBe("SCOPE_VALUE_INVALID");
  });
});

describe("mở rộng dữ liệu khách cần xác nhận (PV-09)", () => {
  it("PUT thiếu xác nhận → 400 kèm impact; không đổi gì", () => {
    const r = put("delivery_staff", { version: "1", scopes: { orders: "all" } });
    expect(r.status).toBe(400);
    expect(codeOf(r)).toBe("CUSTOMER_DATA_WIDENING_UNCONFIRMED");
    const impact = (r.body as { impact: ScopePreview }).impact;
    expect(impact.widens_customer_data).toBe(true);
    expect(impact.affected_count).toBe(2);
    expect(impact.affected_members.map((m) => m.display_name).sort()).toEqual(["Giao 1", "Giao 2"]);
    expect(impact.message).toBe("2 người trong nhóm sẽ thấy tên, SĐT, địa chỉ khách của mọi đơn.");
    expect(getGroup("delivery_staff").data_scope_values.orders).toBe("assigned_deliveries");
  });
  it("PUT có confirm_customer_data_widening → 200", () => {
    const r = put("delivery_staff", { version: "1", scopes: { orders: "all" }, confirm_customer_data_widening: true });
    expect(r.status).toBe(200);
    expect((r.body as GroupDetail).data_scope_values.orders).toBe("all");
  });
  it("kiêm nhiệm: Giao 2 vẫn thấy nhờ nhóm NV kho (PV-09-AC6)", () => {
    const p = preview("delivery_staff", { scopes: { orders: "assigned_deliveries" } });
    expect(p.status).toBe(200);
    const body = p.body as ScopePreview;
    expect(body.widens_customer_data).toBe(false);
    const wider = preview("delivery_staff", { scopes: { orders: "assigned_or_confirmation" } }).body as ScopePreview;
    expect(wider.already_wider_elsewhere).toEqual([{ id: 5, display_name: "Giao 2", via_group: "warehouse_staff", key: "orders" }]);
  });
  it("thu hẹp: có rows_losing_access, không cần xác nhận", () => {
    const p = preview("warehouse_staff", { scopes: { receipts: "created_by_me" } }).body as ScopePreview;
    expect(p.widens_customer_data).toBe(false);
    expect(p.narrowed).toEqual([{ key: "receipts", from: "all", to: "created_by_me", rows_losing_access: 3 }]);
    expect(put("warehouse_staff", { version: "1", scopes: { receipts: "created_by_me" } }).status).toBe(200);
  });
  it("D6 Phiếu nhập không phải dữ liệu khách: mở rộng không cần xác nhận (PV-09-AC7)", () => {
    put("warehouse_staff", { version: "1", scopes: { receipts: "created_by_me" } });
    expect(put("warehouse_staff", { version: "2", scopes: { receipts: "all" } }).status).toBe(200);
  });
  it("xem trước không ghi gì, không cần version, chỉ Chủ/superuser", () => {
    preview("delivery_staff", { scopes: { orders: "all" } });
    expect(getGroup("delivery_staff").version).toBe("1");
    expect(preview("delivery_staff", { version: "9", confirm_customer_data_widening: true, scopes: { orders: "all" } }).status).toBe(200); // bỏ qua version/confirm
    expect(codeOf(preview("delivery_staff", { mode: 1, scopes: { orders: "all" } }))).toBe("INPUT_NOT_ALLOWED");
    viewer = users[1];
    expect(preview("delivery_staff", { scopes: { orders: "all" } }).status).toBe(403);
  });
  it("xem trước không có tên khách/SĐT/địa chỉ (bất biến 9)", () => {
    const text = JSON.stringify(preview("delivery_staff", { scopes: { orders: "all" } }).body);
    expect(text).not.toMatch(/0\d{9}/);
    expect(text).not.toMatch(/địa chỉ:/i);
  });
});

describe("D7 theo rank hiệu lực (review F1 M1, luật H1)", () => {
  it("NV giao: đổi Khách hàng sang Tất cả khi việc còn tắt KHÔNG đòi xác nhận (rank hiệu lực vẫn 1)", () => {
    const r = put("delivery_staff", { version: "1", scopes: { customers: "all" } });
    expect(r.status).toBe(200);
    expect((r.body as GroupDetail).data_scope_values.customers).toBe("all");
  });
  it("NV giao lưu Tất cả rồi bật Xem khách hàng: mở rộng (1 → 2) phải đòi xác nhận", () => {
    put("delivery_staff", { version: "1", scopes: { customers: "all" } });
    const r = put("delivery_staff", { version: "2", capabilities: { view_customers: true } });
    expect(codeOf(r)).toBe("CUSTOMER_DATA_WIDENING_UNCONFIRMED");
    expect((r.body as { impact: ScopePreview }).impact.widened).toEqual([{ key: "customers", from: "all", to: "all" }]);
    expect(put("delivery_staff", { version: "2", capabilities: { view_customers: true }, confirm_customer_data_widening: true }).status).toBe(200);
  });
  it("Quản lý tắt rồi bật lại Xem khách hàng khi Khách hàng = Tất cả: bật lại là mở rộng", () => {
    expect(put("manager", { version: "1", capabilities: { view_customers: false } }).status).toBe(200);
    const r = put("manager", { version: "2", capabilities: { view_customers: true } });
    expect(codeOf(r)).toBe("CUSTOMER_DATA_WIDENING_UNCONFIRMED");
  });
  it("Quản lý tắt Xem khách hàng: ô Khách hàng không mờ (có view_customer Tầng 1)", () => {
    put("manager", { version: "1", capabilities: { view_customers: false } });
    const row = getGroup("manager").data_scopes.find((r) => r.key === "customers")!;
    expect(row.inactive_reason).toBeNull();
  });
});

describe("2 việc mới của Lô 3 (view_sales_invoices, view_order_customer_info)", () => {
  it("registry có đủ hai việc, nhãn đúng từng chữ như BE", () => {
    const reg = getGroup("manager").registry;
    expect(reg.find((r) => r.key === "view_sales_invoices")?.label).toBe("Xem hoá đơn bán");
    expect(reg.find((r) => r.key === "view_order_customer_info")?.label).toBe("Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền");
    expect(reg).toHaveLength(28);
  });
  it("mặc định: V1 chỉ Quản lý và NV kho; V2 bật cho cả bốn nhóm", () => {
    const states = (g: string) => getGroup(g).capabilities;
    expect(states("manager").view_sales_invoices).toBe("on");
    expect(states("warehouse_staff").view_sales_invoices).toBe("on");
    expect(states("delivery_staff").view_sales_invoices).toBe("off");
    expect(states("customer_service").view_sales_invoices).toBe("off");
    for (const g of ["manager", "warehouse_staff", "delivery_staff", "customer_service"]) expect(states(g).view_order_customer_info).toBe("on");
  });
  it("dòng Hoá đơn bán mờ khi nhóm chưa bật V1, kèm tên việc", () => {
    const row = getGroup("customer_service").data_scopes.find((r) => r.key === "invoices")!;
    expect(row.gate_capability).toBe("view_sales_invoices");
    expect(row.inactive_reason).toBe('Không xem — bật việc "Xem hoá đơn bán" trước');
  });
  it("bật V1 cho nhóm chưa có → mở rộng dữ liệu khách ở Hoá đơn bán, cần xác nhận", () => {
    const r = put("customer_service", { version: "1", capabilities: { view_sales_invoices: true } });
    expect(codeOf(r)).toBe("CUSTOMER_DATA_WIDENING_UNCONFIRMED");
    expect((r.body as { impact: ScopePreview }).impact.widened.map((w) => w.key)).toEqual(["invoices"]);
  });
  it("tắt rồi bật lại V2 → widened có view_order_customer_info", () => {
    expect(put("delivery_staff", { version: "1", capabilities: { view_order_customer_info: false } }).status).toBe(200);
    const impact = preview("delivery_staff", { capabilities: { view_order_customer_info: true } }).body as ScopePreview;
    expect(impact.widens_customer_data).toBe(true);
    expect(impact.widened).toEqual([{ key: "view_order_customer_info", from: "off", to: "on" }]);
  });
});
