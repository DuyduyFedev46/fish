// Mock /api/staff/groups/… (ED-40, PV-09..PV-11) — chạy khi NEXT_PUBLIC_USE_MOCK=1. Mô phỏng contract BE (02b §2, §3 B4):
// danh sách nhóm kèm trạng thái việc + `version` + `data_scope_values`, chi tiết nhóm (registry, `data_scopes` 8 dòng, dòng thời gian),
// PUT lưu việc + phạm vi trong MỘT lần, POST xem trước ảnh hưởng.
// Thành viên lấy từ kho người dùng mock của features/auth, nên đổi nhóm ở màn Nhân sự thấy ngay ở đây.
// Luật BE giữ đủ, theo THỨ TỰ KIỂM của 02b §2.3: chỉ Chủ/superuser ghi (403) · nhóm lạ 404 · nhóm Chủ khoá GROUP_LOCKED ·
// khoá lạ INPUT_NOT_ALLOWED · thiếu `version`/rỗng/sai kiểu INVALID_INPUT · phạm vi lạ/chỉ đọc/giá trị lạ SCOPE_* ·
// việc "Chỉ Chủ" BR-PQ-32 · CAS `version` (409 GROUP_CHANGED) · `requires` · PO-Q1 (bật Xem khách hàng mà Khách hàng = Không xem → 400) ·
// mở rộng dữ liệu khách mà thiếu xác nhận → 400 CUSTOMER_DATA_WIDENING_UNCONFIRMED kèm `impact`. Tất cả hoặc không gì cả;
// không có thay đổi thật thì 200 và KHÔNG tăng `version`. Câu lỗi là xấp xỉ câu BE (UI hiện nguyên văn `detail` của BE thật).
// Số "dòng mất quyền xem" của bản xem trước là SỐ GIẢ cố định (mock không có chứng từ): 3 phiếu nhập, 2 dòng loại khác.
// LƯU Ý: đổi việc ở đây KHÔNG đổi quyền khi đăng nhập mock (bảng quyền mock ở features/auth, không sửa ở lô này).
// Kho tạm: sessionStorage (chỉ khoá việc → true/false, mã đối tượng → mã giá trị, số phiên bản; KHÔNG có dữ liệu khách).
// Công cụ thử: window.__caveMock.resetGroupCaps() · window.__caveMock.bumpGroupVersion(code) (giả lập người khác vừa lưu → 409).

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
import { SCOPE_BY_KEY, buildPreview, describeRows, rankOf, scopeEventLabel, valuesOf, type PreviewGroup } from "./mockScopes";
import type { CapabilityChanges, CapabilityState, GroupDetail, GroupMember, GroupSummary, RegistryItem, ScopeChanges, ScopePreview } from "./types";

const S_SALES = "Bán hàng";
const S_STOCK = "Hàng hoá & kho";
const S_ACC = "Kế toán";
const S_WEB = "Website";
const S_ADMIN = "Quản trị";

/** Chép registry BE (26 việc). `groups` = nhóm đang bật việc theo mặc định (việc Chỉ Chủ chỉ có nhóm Chủ). */
const REGISTRY: { item: RegistryItem; groups: string[] }[] = [
  { item: { key: "view_orders", label: "Xem đơn", section: S_SALES, owner_only: false, requires: [] }, groups: ["manager", "warehouse_staff", "delivery_staff", "customer_service"] },
  { item: { key: "view_customers", label: "Xem khách hàng", section: S_SALES, owner_only: false, requires: [] }, groups: ["manager"] },
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

const OVERRIDE_KEY = "cave_erp_mock_group_caps";
const EVENTS_KEY = "cave_erp_mock_group_events";
const SCOPES_KEY = "cave_erp_mock_group_scopes";
const VERSIONS_KEY = "cave_erp_mock_group_versions";

type Overrides = Record<string, Record<string, boolean>>;
type ScopeOverrides = Record<string, Record<string, string>>;
type Versions = Record<string, number>;
type StoredEvent = { group: string; at: string; label: string; actor: string; kind?: string };

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
      window.sessionStorage.removeItem(SCOPES_KEY);
      window.sessionStorage.removeItem(VERSIONS_KEY);
      return "Đã đặt lại bảng quyền nhóm về mặc định";
    },
    /** Giả lập người khác vừa lưu nhóm: tăng `version` mà không đổi dữ liệu (để thử 409 GROUP_CHANGED). */
    bumpGroupVersion: (code: string) => {
      const versions = readJson<Versions>(VERSIONS_KEY, {});
      versions[code] = (versions[code] ?? 1) + 1;
      writeJson(VERSIONS_KEY, versions);
      return `Phiên bản nhóm ${code} = ${versions[code]}`;
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

type Store = { caps: Overrides; scopes: ScopeOverrides; events: StoredEvent[]; versions: Versions };

function readStore(): Store {
  return {
    caps: readJson<Overrides>(OVERRIDE_KEY, {}),
    scopes: readJson<ScopeOverrides>(SCOPES_KEY, {}),
    events: readJson<StoredEvent[]>(EVENTS_KEY, []),
    versions: readJson<Versions>(VERSIONS_KEY, {}),
  };
}

const versionOf = (group: string, store: Store): string => String(store.versions[group] ?? 1);

function lastChange(group: string, events: StoredEvent[]) {
  const mine = events.filter((e) => e.group === group).sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0];
  return mine ? { at: mine.at, by: mine.actor } : { at: null, by: null };
}

function summary(group: string, users: MockUser[], store: Store): GroupSummary {
  const caps = capabilitiesOf(group, store.caps);
  const members = users.filter((u) => u.is_active && u.groups.includes(group));
  const last = lastChange(group, store.events);
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
    version: versionOf(group, store),
    data_scope_values: valuesOf(group, store.scopes[group]),
  };
}

function detail(group: string, users: MockUser[], store: Store): GroupDetail {
  const base = summary(group, users, store);
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
  const timeline = store.events
    .filter((e) => e.group === group)
    .map((e) => ({ at: e.at, kind: e.kind ?? "capability", label: e.label, doc: "group", actor: { kind: "user" as const, display: e.actor } }));
  if (group === ROLE.owner || group === ROLE.manager) {
    timeline.push({ at: ago(30), kind: "capability", label: "Tạo nhóm quyền", doc: "group", actor: { kind: "user" as const, display: "Hệ thống" } });
  }
  return {
    ...base,
    members,
    registry: ITEMS,
    data_scopes: describeRows(group, base.capabilities, base.data_scope_values, labelOf),
    timeline: timeline as GroupDetail["timeline"],
  };
}

function fail(status: number, code: string, message: string, extra?: Record<string, unknown>): MockResponse {
  return { status, body: { detail: message, code, ...extra } };
}

function labelOf(key: string): string {
  return ITEMS.find((i) => i.key === key)?.label ?? key;
}

const BODY_KEYS = ["version", "capabilities", "scopes", "confirm_customer_data_widening"];

type Parsed = { caps: CapabilityChanges; scopes: ScopeChanges; version: unknown; confirm: boolean };

/** Kiểm thân PUT/POST theo 02b §2.3 bước 4–7 (lỗi đầu tiên thắng). `needVersion` false với xem trước. */
function parseBody(body: unknown, needVersion: boolean): Parsed | MockResponse {
  const obj = body && typeof body === "object" && !Array.isArray(body) ? (body as Record<string, unknown>) : null;
  if (!obj) return fail(400, "INVALID_INPUT", "Thân yêu cầu phải là một đối tượng.");
  for (const key of Object.keys(obj)) {
    if (!BODY_KEYS.includes(key) || (!needVersion && key === "version")) return fail(400, "INPUT_NOT_ALLOWED", `Không nhận trường ${key}.`);
  }
  const caps = obj.capabilities ?? {};
  const scopes = obj.scopes ?? {};
  const isMap = (v: unknown) => !!v && typeof v === "object" && !Array.isArray(v);
  if (!isMap(caps) || !isMap(scopes)) return fail(400, "INVALID_INPUT", "Việc và phạm vi phải gửi dạng danh sách khoá và giá trị.");
  const capMap = caps as Record<string, unknown>;
  const scopeMap = scopes as Record<string, unknown>;
  for (const key of Object.keys(capMap)) {
    if (!ITEMS.some((i) => i.key === key)) return fail(400, "INPUT_NOT_ALLOWED", `Việc không có trong danh sách: ${key}.`);
  }
  if (needVersion && (typeof obj.version !== "string" || !obj.version)) return fail(400, "INVALID_INPUT", "Thiếu phiên bản (version) của nhóm.");
  if (obj.confirm_customer_data_widening !== undefined && typeof obj.confirm_customer_data_widening !== "boolean") {
    return fail(400, "INVALID_INPUT", "Xác nhận phải là đúng hoặc sai.");
  }
  if (Object.keys(capMap).length === 0 && Object.keys(scopeMap).length === 0) return fail(400, "INVALID_INPUT", "Cần gửi ít nhất một việc hoặc một phạm vi để đổi.");
  for (const key of Object.keys(capMap)) {
    if (typeof capMap[key] !== "boolean") return fail(400, "INVALID_INPUT", `Giá trị của “${labelOf(key)}” phải là bật hoặc tắt.`);
  }
  for (const [key, value] of Object.entries(scopeMap)) {
    const def = SCOPE_BY_KEY[key];
    if (!def) return fail(400, "SCOPE_OBJECT_UNKNOWN", `Không có đối tượng phạm vi “${key}”.`);
    if (def.read_only) return fail(400, "SCOPE_READ_ONLY", `“${def.label}” chỉ để xem, không đổi được ở đây.`);
    if (typeof value !== "string" || rankOf(def, value) < 0) return fail(400, "SCOPE_VALUE_INVALID", `Giá trị phạm vi của “${def.label}” không hợp lệ.`);
  }
  for (const [key, value] of Object.entries(capMap)) {
    const item = ITEMS.find((i) => i.key === key) as RegistryItem;
    if (value && item.owner_only) return fail(400, "BR-PQ-32", `“${item.label}” chỉ nhóm Chủ được bật, không cấp cho nhóm khác.`);
  }
  return { caps: capMap as CapabilityChanges, scopes: scopeMap as ScopeChanges, version: obj.version, confirm: obj.confirm_customer_data_widening === true };
}

const isFail = (v: Parsed | MockResponse): v is MockResponse => "status" in v;

function applyCaps(group: string, caps: CapabilityChanges, base: Overrides): Overrides {
  return { ...base, [group]: { ...(base[group] ?? {}), ...caps } };
}

function previewGroup(group: string, users: MockUser[], caps: Overrides, scopes: ScopeOverrides): PreviewGroup {
  return {
    code: group,
    states: capabilitiesOf(group, caps),
    values: valuesOf(group, scopes[group]),
    members: users.filter((u) => u.is_active && u.groups.includes(group)).map((u) => ({ id: u.id, display_name: u.display_name || u.username })),
  };
}

/** Xem trước ảnh hưởng của bản (việc + phạm vi) lên nhóm `group` (02b §2.4). Không ghi gì. */
function impactOf(group: string, users: MockUser[], store: Store, parsed: Parsed): ScopePreview {
  const nextCaps = applyCaps(group, parsed.caps, store.caps);
  const nextScopes: ScopeOverrides = { ...store.scopes, [group]: { ...(store.scopes[group] ?? {}), ...parsed.scopes } };
  const before = previewGroup(group, users, store.caps, store.scopes);
  const after = previewGroup(group, users, nextCaps, nextScopes);
  const others = GROUP_CODES.filter((g) => g !== group).map((g) => previewGroup(g, users, store.caps, store.scopes));
  return buildPreview(before, after, others);
}

/** Kiểm trạng thái cuối (bước 9, 10): `requires` và PO-Q1. */
function checkFinalState(group: string, nextCaps: Overrides, nextScopes: ScopeOverrides): MockResponse | null {
  for (const item of ITEMS) {
    if (stateOf(group, item.key, nextCaps) !== "on") continue;
    for (const need of item.requires) {
      if (stateOf(group, need, nextCaps) !== "on") {
        return fail(400, "CAPABILITY_REQUIRES", `“${item.label}” cần bật cả “${labelOf(need)}”. Hãy đổi hai việc cùng lúc.`);
      }
    }
  }
  if (stateOf(group, "view_customers", nextCaps) === "on" && valuesOf(group, nextScopes[group]).customers === "none") {
    return fail(400, "SCOPE_VALUE_INVALID", "Bật Xem khách hàng thì chọn phạm vi Khách hàng khác Không xem.");
  }
  return null;
}

function gate(viewer: MockUser, group: string): MockResponse | null {
  if (!isOwnerViewer(viewer)) return fail(403, "OWNER_ONLY", "Chỉ Chủ mới đổi được việc và phạm vi của nhóm.");
  if (!(GROUP_CODES as readonly string[]).includes(group)) return fail(404, "GROUP_NOT_FOUND", "Không tìm thấy nhóm này.");
  if (group === ROLE.owner) return fail(400, "GROUP_LOCKED", "Nhóm Chủ luôn có đủ quyền, không sửa được.");
  return null;
}

function put(viewer: MockUser, group: string, body: unknown, users: MockUser[]): MockResponse {
  const blocked = gate(viewer, group);
  if (blocked) return blocked;
  const parsed = parseBody(body, true);
  if (isFail(parsed)) return parsed;
  const store = readStore();
  // Bước 8: so `version` (CAS). Người khác vừa lưu → 409, không đổi gì.
  if (parsed.version !== versionOf(group, store)) {
    return fail(409, "GROUP_CHANGED", "Nhóm này vừa được người khác đổi. Tải lại để xem bản mới.");
  }
  const nextCaps = applyCaps(group, parsed.caps, store.caps);
  const nextScopes: ScopeOverrides = { ...store.scopes, [group]: { ...(store.scopes[group] ?? {}), ...parsed.scopes } };
  const problem = checkFinalState(group, nextCaps, nextScopes);
  if (problem) return problem;
  const impact = impactOf(group, users, store, parsed);
  if (impact.widens_customer_data && !parsed.confirm) {
    return fail(400, "CUSTOMER_DATA_WIDENING_UNCONFIRMED", "Thay đổi này cho thêm người xem dữ liệu khách. Hãy xác nhận trước khi lưu.", { impact });
  }
  // Bước 12: áp. Chỉ ghi dòng thật sự đổi; không có gì đổi thì 200, không sự kiện, không tăng version.
  const events = [...store.events];
  const at = new Date().toISOString();
  let changed = false;
  for (const [key, value] of Object.entries(parsed.caps)) {
    const item = ITEMS.find((i) => i.key === key) as RegistryItem;
    if (stateOf(group, key, store.caps) !== (value ? "on" : "off")) {
      events.push({ group, at, label: `${value ? "Bật" : "Tắt"} “${item.label}”`, actor: viewer.username });
      changed = true;
    }
  }
  const beforeValues = valuesOf(group, store.scopes[group]);
  for (const [key, value] of Object.entries(parsed.scopes)) {
    if (beforeValues[key] !== value) {
      events.push({ group, at, kind: "change_group_data_scopes", label: scopeEventLabel(key, beforeValues[key], value), actor: viewer.username });
      changed = true;
    }
  }
  const versions = { ...store.versions };
  if (changed) {
    versions[group] = (store.versions[group] ?? 1) + 1;
    writeJson(OVERRIDE_KEY, nextCaps);
    writeJson(SCOPES_KEY, nextScopes);
    writeJson(EVENTS_KEY, events);
    writeJson(VERSIONS_KEY, versions);
  }
  return { status: 200, body: detail(group, users, { caps: nextCaps, scopes: nextScopes, events, versions }) };
}

function preview(viewer: MockUser, group: string, body: unknown, users: MockUser[]): MockResponse {
  const blocked = gate(viewer, group);
  if (blocked) return blocked;
  const parsed = parseBody(body, false);
  if (isFail(parsed)) return parsed;
  const store = readStore();
  const problem = checkFinalState(group, applyCaps(group, parsed.caps, store.caps), { ...store.scopes, [group]: { ...(store.scopes[group] ?? {}), ...parsed.scopes } });
  if (problem) return problem;
  return { status: 200, body: impactOf(group, users, store, parsed) };
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
  const store = readStore();

  if (parts.length === 0) {
    if (req.method !== "GET") return fail(405, "METHOD_NOT_ALLOWED", `Không dùng được phương thức ${req.method} ở đây.`);
    return { status: 200, body: GROUP_CODES.map((g) => summary(g, users, store)) };
  }
  const code = decodeURIComponent(parts[0]);
  if (!(GROUP_CODES as readonly string[]).includes(code)) return fail(404, "GROUP_NOT_FOUND", "Không tìm thấy nhóm này.");
  if (parts.length === 1 && req.method === "GET") return { status: 200, body: detail(code, users, store) };
  if (parts[1] === "capabilities" && req.method === "PUT") return put(viewer, code, req.body, users);
  if (parts[1] === "permissions-preview" && req.method === "POST") return preview(viewer, code, req.body, users);
  return fail(404, "NOT_FOUND", "Không tìm thấy.");
}
