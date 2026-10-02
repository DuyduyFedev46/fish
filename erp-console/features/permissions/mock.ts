// Mock /api/staff/groups/… (ED-40) — chạy khi NEXT_PUBLIC_USE_MOCK=1. Mô phỏng contract THỰC TẾ BE B4 (02b §3 B4):
// danh sách nhóm kèm trạng thái việc, chi tiết nhóm (registry, phạm vi, dòng thời gian), PUT bật/tắt việc.
// Thành viên lấy từ kho người dùng mock của features/auth, nên đổi nhóm ở màn Nhân sự thấy ngay ở đây.
// Quy tắc BE giữ đủ: chỉ Chủ ghi (403), nhóm Chủ khoá (GROUP_LOCKED), việc "Chỉ Chủ" không cấp được (BR-PQ-32),
// khoá lạ INPUT_NOT_ALLOWED, giá trị không phải true/false INVALID_INPUT, cặp `requires` đổi cùng lúc (CAPABILITY_REQUIRES),
// tất cả hoặc không gì cả. Câu lỗi là xấp xỉ câu BE (UI hiện nguyên văn `detail` của BE thật).
// LƯU Ý: đổi việc ở đây KHÔNG đổi quyền khi đăng nhập mock (bảng quyền mock ở features/auth, không sửa ở lô này).
// Bật/tắt giữ trong sessionStorage (chỉ khoá việc → true/false, không dữ liệu cá nhân) để tải lại trang vẫn thấy.

import {
  MOCK_UNAUTHORIZED,
  mockPermsOf,
  mockRequireRecord,
  mockUsers,
  sortGroups,
  type MockUser,
} from "@/features/auth/mock";
import { GROUP_CODES, GROUP_LABEL } from "@/shared/lib/groups";
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { PERM } from "@/shared/lib/nav";
import { ROLE } from "@/shared/lib/roles";
import type { CapabilityChanges, CapabilityState, GroupDetail, GroupMember, GroupSummary, RegistryItem } from "./types";

const S_SALES = "Bán hàng";
const S_STOCK = "Hàng hoá & kho";
const S_ACC = "Kế toán";
const S_WEB = "Website";
const S_ADMIN = "Quản trị";

/** Chép registry BE (26 việc). `groups` = nhóm đang bật việc theo mặc định (việc Chỉ Chủ chỉ có nhóm Chủ). */
const REGISTRY: { item: RegistryItem; groups: string[] }[] = [
  { item: { key: "view_orders", label: "Xem đơn", section: S_SALES, owner_only: false, requires: [] }, groups: ["manager", "warehouse_staff", "delivery_staff", "customer_service"] },
  { item: { key: "view_customers", label: "Xem khách hàng", section: S_SALES, owner_only: false, requires: [] }, groups: [] },
  { item: { key: "confirm_calls", label: "Gọi xác nhận đơn", section: S_SALES, owner_only: false, requires: [] }, groups: ["manager", "customer_service"] },
  { item: { key: "confirm_payment", label: "Xác nhận đã nhận tiền", section: S_SALES, owner_only: true, requires: [] }, groups: [] },
  { item: { key: "cancel_paid", label: "Huỷ đơn đã thanh toán", section: S_SALES, owner_only: false, requires: [] }, groups: ["manager"] },
  { item: { key: "create_refund", label: "Lập phiếu hoàn", section: S_SALES, owner_only: false, requires: [] }, groups: ["manager"] },
  { item: { key: "confirm_refund", label: "Xác nhận đã hoàn tiền", section: S_SALES, owner_only: true, requires: [] }, groups: [] },
  { item: { key: "pack_print", label: "Soạn hàng, in tem", section: S_SALES, owner_only: false, requires: ["deliver"] }, groups: ["manager", "warehouse_staff"] },
  { item: { key: "assign_delivery", label: "Giao phiếu cho người giao", section: S_SALES, owner_only: false, requires: [] }, groups: ["manager"] },
  { item: { key: "deliver", label: "Giao hàng, báo kết quả giao", section: S_SALES, owner_only: false, requires: [] }, groups: ["manager", "warehouse_staff", "delivery_staff"] },
  { item: { key: "receive", label: "Nhập lô tại cảng", section: S_STOCK, owner_only: false, requires: [] }, groups: ["manager", "warehouse_staff"] },
  { item: { key: "add_cost", label: "Thêm chi phí phụ vào lô", section: S_STOCK, owner_only: true, requires: [] }, groups: [] },
  { item: { key: "publish_batch", label: "Mở bán lô", section: S_STOCK, owner_only: false, requires: [] }, groups: ["manager"] },
  { item: { key: "close_batch", label: "Chốt lô", section: S_STOCK, owner_only: true, requires: [] }, groups: [] },
  { item: { key: "count_stock", label: "Nhập số kiểm kê", section: S_STOCK, owner_only: false, requires: [] }, groups: ["manager", "warehouse_staff"] },
  { item: { key: "approve_count", label: "Duyệt kiểm kê", section: S_STOCK, owner_only: false, requires: [] }, groups: ["manager"] },
  { item: { key: "create_return", label: "Ghi hàng hoàn về kho", section: S_STOCK, owner_only: false, requires: [] }, groups: ["manager", "warehouse_staff"] },
  { item: { key: "approve_return", label: "Duyệt hàng hoàn về kho", section: S_STOCK, owner_only: false, requires: [] }, groups: ["manager"] },
  { item: { key: "set_price", label: "Sửa giá bán", section: S_STOCK, owner_only: true, requires: [] }, groups: [] },
  { item: { key: "view_cost", label: "Xem giá vốn", section: S_ACC, owner_only: true, requires: [] }, groups: [] },
  { item: { key: "view_profit", label: "Xem báo cáo lãi lỗ", section: S_ACC, owner_only: true, requires: [] }, groups: [] },
  { item: { key: "write_content", label: "Viết bài", section: S_WEB, owner_only: false, requires: [] }, groups: ["manager"] },
  { item: { key: "publish_content", label: "Đăng bài lên Shop", section: S_WEB, owner_only: false, requires: [] }, groups: ["manager"] },
  { item: { key: "manage_staff", label: "Tạo tài khoản, đổi nhóm", section: S_ADMIN, owner_only: true, requires: [] }, groups: [] },
  { item: { key: "view_audit", label: "Xem nhật ký hoạt động", section: S_ADMIN, owner_only: false, requires: [] }, groups: ["manager"] },
  { item: { key: "ai_policy", label: "Cài đặt chính sách AI", section: S_ADMIN, owner_only: true, requires: [] }, groups: [] },
];

const ITEMS: RegistryItem[] = REGISTRY.map((r) => r.item);

const SCOPES_STATIC: Record<string, { orders: string; deliveries: string; customers: string }> = {
  owner: { orders: "Tất cả", deliveries: "Tất cả", customers: "Không xem" },
  manager: { orders: "Tất cả", deliveries: "Tất cả", customers: "Không xem" },
  warehouse_staff: { orders: "Tất cả", deliveries: "Tất cả", customers: "Không xem" },
  delivery_staff: { orders: "Được gán", deliveries: "Được gán", customers: "Được gán" },
  customer_service: { orders: "Trong phạm vi gọi", deliveries: "Trong phạm vi gọi", customers: "Không xem" },
};

const OVERRIDE_KEY = "cave_erp_mock_group_caps";
const EVENTS_KEY = "cave_erp_mock_group_events";

type Overrides = Record<string, Record<string, boolean>>;
type StoredEvent = { group: string; at: string; label: string; actor: string };

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = typeof window !== "undefined" ? window.sessionStorage.getItem(key) : null;
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function writeJson(key: string, value: unknown) {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* mock: không lưu được thì thôi */
  }
}

// Công cụ thử: window.__caveMock.resetGroupCaps() — về lại bảng quyền mặc định.
if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    resetGroupCaps: () => {
      window.sessionStorage.removeItem(OVERRIDE_KEY);
      window.sessionStorage.removeItem(EVENTS_KEY);
      return "Đã đặt lại bảng quyền nhóm về mặc định";
    },
  };
}

function stateOf(group: string, key: string, overrides: Overrides): CapabilityState {
  if (group === ROLE.owner) return "on";
  const entry = REGISTRY.find((r) => r.item.key === key);
  if (!entry) return "off";
  const over = overrides[group]?.[key];
  if (typeof over === "boolean") return over ? "on" : "off";
  return entry.groups.includes(group) ? "on" : "off";
}

function capabilitiesOf(group: string, overrides: Overrides): Record<string, CapabilityState> {
  const out: Record<string, CapabilityState> = {};
  for (const item of ITEMS) out[item.key] = stateOf(group, item.key, overrides);
  return out;
}

const isOwnerViewer = (u: MockUser) => u.groups.includes(ROLE.owner) || u.is_superuser;
const ago = (days: number) => new Date(Date.now() - days * 86_400_000).toISOString();

function lastChange(group: string, events: StoredEvent[]) {
  const mine = events.filter((e) => e.group === group).sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0];
  return mine ? { at: mine.at, by: mine.actor } : { at: null, by: null };
}

function summary(group: string, users: MockUser[], overrides: Overrides, events: StoredEvent[]): GroupSummary {
  const caps = capabilitiesOf(group, overrides);
  const members = users.filter((u) => u.is_active && u.groups.includes(group));
  const last = lastChange(group, events);
  return {
    id: GROUP_CODES.indexOf(group as (typeof GROUP_CODES)[number]) + 1,
    code: group,
    label: GROUP_LABEL[group] ?? group,
    member_count: members.length,
    members: members.map((u) => ({ id: u.id, display_name: u.display_name || u.username })),
    can_view_cost: caps.view_cost === "on",
    last_changed_at: last.at,
    last_changed_by: last.by,
    capabilities: caps,
  };
}

function detail(group: string, users: MockUser[], overrides: Overrides, events: StoredEvent[]): GroupDetail {
  const base = summary(group, users, overrides, events);
  const caps = base.capabilities;
  const members: GroupMember[] = users
    .filter((u) => u.groups.includes(group))
    .sort((a, b) => a.username.localeCompare(b.username))
    .map((u) => ({
      id: u.id,
      display_name: u.display_name || u.username,
      username: u.username,
      other_groups: sortGroups(u.groups.filter((g) => g !== group)),
      is_active: u.is_active,
      added_at: null,
    }));
  const scopes = { ...(SCOPES_STATIC[group] ?? { orders: "Không xem", deliveries: "Không xem", customers: "Không xem" }) };
  // M2 (bất biến 9): nhóm có quyền xem danh sách khách thì xem MỌI khách.
  if (caps.view_customers === "on") scopes.customers = "Tất cả khách";
  const timeline = events
    .filter((e) => e.group === group)
    .map((e) => ({ at: e.at, kind: "capability", label: e.label, doc: "group", actor: { kind: "user" as const, display: e.actor } }));
  if (group === ROLE.owner || group === ROLE.manager) {
    timeline.push({ at: ago(30), kind: "capability", label: "Tạo nhóm quyền", doc: "group", actor: { kind: "user" as const, display: "Hệ thống" } });
  }
  return { ...base, members, registry: ITEMS, scopes, timeline: timeline as GroupDetail["timeline"] };
}

function fail(status: number, code: string, message: string): MockResponse {
  return { status, body: { detail: message, code } };
}

function labelOf(key: string): string {
  return ITEMS.find((i) => i.key === key)?.label ?? key;
}

function put(viewer: MockUser, group: string, body: unknown, users: MockUser[]): MockResponse {
  if (!isOwnerViewer(viewer)) return fail(403, "OWNER_ONLY", "Chỉ Chủ mới đổi được việc của nhóm.");
  if (group === ROLE.owner) return fail(400, "GROUP_LOCKED", "Nhóm Chủ luôn có đủ quyền, không sửa được.");
  const caps = body && typeof body === "object" ? (body as { capabilities?: unknown }).capabilities : undefined;
  if (!caps || typeof caps !== "object" || Array.isArray(caps) || Object.keys(caps).length === 0) {
    return fail(400, "INVALID_INPUT", "Cần gửi ít nhất một việc để đổi.");
  }
  const changes = caps as Record<string, unknown>;
  for (const key of Object.keys(changes)) {
    if (!ITEMS.some((i) => i.key === key)) return fail(400, "INPUT_NOT_ALLOWED", `Việc không có trong danh sách: ${key}.`);
    if (typeof changes[key] !== "boolean") return fail(400, "INVALID_INPUT", `Giá trị của “${labelOf(key)}” phải là bật hoặc tắt.`);
  }
  const overrides = readJson<Overrides>(OVERRIDE_KEY, {});
  const next: Overrides = { ...overrides, [group]: { ...(overrides[group] ?? {}) } };
  const diff: string[] = [];
  for (const [key, value] of Object.entries(changes as CapabilityChanges)) {
    const item = ITEMS.find((i) => i.key === key) as RegistryItem;
    if (value && item.owner_only) return fail(400, "BR-PQ-32", `“${item.label}” chỉ nhóm Chủ được bật, không cấp cho nhóm khác.`);
    if (stateOf(group, key, overrides) !== (value ? "on" : "off")) diff.push(`${value ? "Bật" : "Tắt"} “${item.label}”`);
    next[group][key] = value;
  }
  // `requires`: sau khi áp, mọi việc đang BẬT phải có đủ việc gốc BẬT (hai bên đổi cùng lúc mới qua).
  for (const item of ITEMS) {
    if (stateOf(group, item.key, next) !== "on") continue;
    for (const need of item.requires) {
      if (stateOf(group, need, next) !== "on") {
        return fail(400, "CAPABILITY_REQUIRES", `“${item.label}” cần bật cả “${labelOf(need)}”. Hãy đổi hai việc cùng lúc.`);
      }
    }
  }
  writeJson(OVERRIDE_KEY, next);
  const events = readJson<StoredEvent[]>(EVENTS_KEY, []);
  if (diff.length) {
    const at = new Date().toISOString();
    events.push(...diff.map((label) => ({ group, at, label, actor: viewer.username })));
    writeJson(EVENTS_KEY, events);
  }
  return { status: 200, body: detail(group, users, next, events) };
}

/** Một handler cho mọi đường /api/staff/groups/… (api.ts truyền chung). */
export function mockPermissionsApi(req: MockRequest): MockResponse {
  const viewer = mockRequireRecord(req);
  if (!viewer) return MOCK_UNAUTHORIZED;
  if (!mockPermsOf(viewer).includes(PERM.manageStaff)) {
    return fail(403, "DRF_FORBIDDEN", "Bạn không có quyền thực hiện thao tác này.");
  }
  const path = req.path.split("?")[0];
  const parts = path.replace(/^\/api\/staff\/groups\/?/, "").split("/").filter(Boolean);
  const users = mockUsers();
  const overrides = readJson<Overrides>(OVERRIDE_KEY, {});
  const events = readJson<StoredEvent[]>(EVENTS_KEY, []);

  if (parts.length === 0) {
    if (req.method !== "GET") return fail(405, "METHOD_NOT_ALLOWED", `Không dùng được phương thức ${req.method} ở đây.`);
    return { status: 200, body: GROUP_CODES.map((g) => summary(g, users, overrides, events)) };
  }
  const code = decodeURIComponent(parts[0]);
  if (!(GROUP_CODES as readonly string[]).includes(code)) return fail(404, "GROUP_NOT_FOUND", "Không tìm thấy nhóm này.");
  if (parts.length === 1 && req.method === "GET") return { status: 200, body: detail(code, users, overrides, events) };
  if (parts[1] === "capabilities" && req.method === "PUT") return put(viewer, code, req.body, users);
  return fail(404, "NOT_FOUND", "Không tìm thấy.");
}
