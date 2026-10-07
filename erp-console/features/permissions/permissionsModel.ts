// Luật thuần của màn Phân quyền (ED-40): gom việc theo khu, kiểu ô, kế hoạch bật/tắt một việc (cặp `requires` đổi cùng lúc,
// cách hoàn tác), cảnh báo trước khi tắt việc làm hỏng màn của nhóm. KHÔNG gọi API, KHÔNG React → vitest được.
// Luật quyết định cuối cùng vẫn ở BE (`set_group_capabilities`): FE chỉ dựng đúng yêu cầu và hiện đúng ô.

import { ROLE } from "@/shared/lib/roles";
import type { CapabilityChanges, CapabilityState, DataScopeRow, GroupSaveBody, RegistryItem, ScopeChanges } from "./types";

/** Thứ tự các khu trong ma trận (02b §3 B4); khu lạ BE thêm sau này đứng cuối. */
export const SECTION_ORDER = ["Bán hàng", "Hàng hoá & kho", "Kế toán", "Website", "Quản trị"] as const;

export type Section = { name: string; items: RegistryItem[] };

/** Gom registry theo khu, giữ thứ tự việc BE trả; khu theo `SECTION_ORDER`. */
/** Việc thuộc phần AI: ẩn khỏi ma trận khi giao diện AI tắt (W39). BE đã ẩn khi `AI_ENABLED` tắt; đây là lớp phòng khi BE bật mà giao diện tắt. */
export const AI_CAPABILITY_KEYS: readonly string[] = ["ai_policy"];
export function visibleRegistry(registry: RegistryItem[], aiOn: boolean): RegistryItem[] {
  return aiOn ? registry : registry.filter((r) => !AI_CAPABILITY_KEYS.includes(r.key));
}

export function sectionsOf(registry: RegistryItem[]): Section[] {
  const byName = new Map<string, RegistryItem[]>();
  for (const item of registry) {
    const list = byName.get(item.section) ?? [];
    list.push(item);
    byName.set(item.section, list);
  }
  const rank = (name: string) => {
    const at = (SECTION_ORDER as readonly string[]).indexOf(name);
    return at < 0 ? SECTION_ORDER.length : at;
  };
  return Array.from(byName, ([name, items]) => ({ name, items })).sort((a, b) => rank(a.name) - rank(b.name));
}

/**
 * Chip phạm vi cạnh một việc (W3h, W3i): lấy từ `data_scope_values` BE trả, KHÔNG còn bảng hằng số theo nhóm (PV-11).
 * Mỗi việc gắn với một đối tượng phạm vi; chip chỉ hiện khi việc đang bật và giá trị thuộc họ "được gán".
 */
const SCOPE_OF_CAPABILITY: Record<string, string> = {
  view_orders: "orders",
  deliver: "deliveries",
  view_customers: "customers",
};
const NARROW_VALUES: Record<string, readonly string[]> = {
  orders: ["assigned_deliveries", "assigned_or_confirmation"],
  deliveries: ["assigned"],
  customers: ["assigned_deliveries"],
};

/** Chip "Được gán" khi việc `key` đang bật và phạm vi của nhóm hẹp (vd NV giao: đơn gán cho mình). */
export function isAssignedOnly(values: Record<string, string> | undefined, key: string): boolean {
  const scopeKey = SCOPE_OF_CAPABILITY[key];
  if (!scopeKey || !values) return false;
  return (NARROW_VALUES[scopeKey] ?? []).includes(values[scopeKey]);
}

/**
 * "Xem khách hàng" bật mà phạm vi Khách hàng là Tất cả → chip cảnh báo "Tất cả khách" (quyết định #13, bất biến 9).
 * `values` thiếu (BE cũ) → coi bật = Tất cả khách như trước.
 */
export function showsAllCustomers(values: Record<string, string> | undefined, on: boolean): boolean {
  if (!on) return false;
  return values?.customers === undefined ? true : values.customers === "all";
}

/** Người được ghi phân quyền (BE: Chủ HOẶC superuser; Duy chốt 06/10: FE mở cho superuser, không chặn chặt hơn BE). */
const OWNER_ONLY_PERMS = [
  "sales.confirm_payment_manual",
  "sales.confirm_refund",
  "accounts.manage_staff",
  "ai.manage_ai_policy",
  "inventory.close_batch",
];
export function isGroupWriter(me: { groups: string[]; permissions: string[]; is_superuser?: boolean } | null | undefined): boolean {
  if (!me) return false;
  if (me.groups.includes(ROLE.owner) || me.is_superuser === true) return true;
  // `/api/auth/me/` chưa trả `is_superuser`: superuser có MỌI permission nên có đủ các quyền chỉ-Chủ. Nếu sai, BE vẫn trả 403 và UI hiện nguyên văn.
  return OWNER_ONLY_PERMS.every((p) => me.permissions.includes(p));
}

/** Việc "Xem khách hàng": bật = nhóm xem được MỌI khách (quyết định #13, bất biến 9) → ô phải ghi rõ "Tất cả khách". */
export const CUSTOMERS_KEY = "view_customers";

/** Nhãn hiện trong ô/dòng khi nhóm xem được mọi khách (trùng `SCOPE_ALL_CUSTOMERS` của BE). */
export const ALL_CUSTOMERS_LABEL = "Tất cả khách";

export type CellMode =
  /** Cột nhóm Chủ: luôn đủ quyền, không sửa. */
  | "owner"
  /** Việc "Chỉ Chủ" đang tắt ở nhóm khác: khoá, không bật được. */
  | "locked"
  | "on"
  | "off"
  /** Nhóm có một phần quyền của việc: hiện như tắt kèm cảnh báo, bấm = bật đủ. */
  | "partial";

export function cellMode(item: RegistryItem, groupCode: string, state: CapabilityState | undefined): CellMode {
  if (groupCode === ROLE.owner) return "owner";
  const s = state ?? "off";
  if (item.owner_only && s === "off") return "locked";
  return s;
}

/** Bấm vào ô này có đổi được không (chưa tính quyền người xem và việc đang gửi). */
export function isToggleable(mode: CellMode): boolean {
  return mode === "on" || mode === "off" || mode === "partial";
}

export type TogglePlan = {
  /** Body gửi BE. Gồm cả việc đi kèm (`requires`) để BE nhận cặp cùng lúc. */
  changes: CapabilityChanges;
  /** Body hoàn tác (đưa mọi việc đã đổi về như cũ); null nếu không đưa về đúng cũ được (có việc đang "partial"). */
  undo: CapabilityChanges | null;
  /** Các việc ĐI KÈM bị đổi theo (không gồm việc người dùng bấm). */
  alsoChanged: string[];
  /** Giá trị mới của việc người dùng bấm. */
  wanted: boolean;
};

/**
 * Bấm một ô → body gửi BE. Đang bật → tắt; đang tắt hoặc một phần → bật đủ.
 * Bật việc cần việc gốc (`requires`) đang chưa bật → bật luôn việc gốc. Tắt việc gốc mà có việc phụ thuộc đang bật/một phần → tắt luôn việc phụ thuộc.
 * (BE đòi hai bên đổi cùng một yêu cầu, nếu không trả 400 `CAPABILITY_REQUIRES`.)
 */
export function planToggle(registry: RegistryItem[], states: Record<string, CapabilityState>, key: string): TogglePlan | null {
  const item = registry.find((r) => r.key === key);
  if (!item) return null;
  const wanted = (states[key] ?? "off") !== "on";
  const changes: CapabilityChanges = { [key]: wanted };
  const alsoChanged: string[] = [];
  if (wanted) {
    for (const need of item.requires) {
      if ((states[need] ?? "off") !== "on") {
        changes[need] = true;
        alsoChanged.push(need);
      }
    }
  } else {
    for (const other of registry) {
      if (other.requires.includes(key) && (states[other.key] ?? "off") !== "off") {
        changes[other.key] = false;
        alsoChanged.push(other.key);
      }
    }
  }
  let undo: CapabilityChanges | null = {};
  for (const k of Object.keys(changes)) {
    const before = states[k] ?? "off";
    if (before === "partial") {
      undo = null;
      break;
    }
    undo[k] = before === "on";
  }
  return { changes, undo, alsoChanged, wanted };
}

/** Trạng thái sau khi áp `changes` (dùng để vẽ ngay trước khi BE trả lời, và để hoàn lại khi lỗi). */
export function applyChanges(states: Record<string, CapabilityState>, changes: CapabilityChanges): Record<string, CapabilityState> {
  const next = { ...states };
  for (const [k, on] of Object.entries(changes)) next[k] = on ? "on" : "off";
  return next;
}

/** Việc mà tắt đi sẽ làm hỏng cả màn của nhóm → hỏi lại trước khi gửi. Trả câu hậu quả, hoặc null nếu tắt thoải mái. */
const BREAKING_OFF: Record<string, string> = {
  view_orders: "Người trong nhóm sẽ không mở được danh sách và chi tiết đơn nữa, nên nhiều màn sẽ trống hoặc báo không có quyền.",
  deliver: "Người trong nhóm sẽ không nhận phiếu, giao hàng hay báo kết quả giao được nữa. Việc soạn hàng, in tem tắt theo.",
  view_audit: "Người trong nhóm sẽ không xem được nhật ký hoạt động nữa.",
};

export function breakingWarning(key: string, wanted: boolean, memberCount: number): string | null {
  if (wanted) return null;
  const base = BREAKING_OFF[key];
  if (!base) return null;
  return memberCount > 0 ? `${base} Hiện có ${memberCount} người trong nhóm.` : base;
}

/** Thông báo sau khi lưu: nói đúng việc, nêu cả việc đi kèm nếu có. */
export function toggleMessage(item: RegistryItem, groupLabel: string, plan: TogglePlan, labelOf: (key: string) => string): string {
  const verb = plan.wanted ? "Đã bật" : "Đã tắt";
  const extra = plan.alsoChanged.length ? ` (kèm ${plan.alsoChanged.map(labelOf).join(", ")})` : "";
  return `${verb} “${item.label}” cho ${groupLabel}${extra}.`;
}

/** Bỏ dấu, hạ chữ thường: gõ "ban hang" vẫn ra "Bán hàng". */
export function foldText(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

/** Ô tìm của ma trận: khớp nhãn việc, khoá việc hoặc tên khu (không dấu cũng được). Từ khoá trống = hiện hết. */
export function matchesTask(item: RegistryItem, q: string): boolean {
  const needle = foldText(q.trim());
  if (!needle) return true;
  return [item.label, item.key, item.section].some((t) => foldText(t).includes(needle));
}

/** Tên nhóm cho cột/tiêu đề: nhãn BE, thiếu thì mã. */
export function labelOfGroup(code: string, labels: Record<string, string>): string {
  return labels[code] ?? code;
}

/** Địa chỉ trang chi tiết nhóm; chỉ mang mã nhóm hệ thống. */
export function groupHref(code: string): string {
  return `/permissions/detail/?group=${encodeURIComponent(code)}`;
}

/** Mã nhóm trong query `?group=` hợp lệ: chữ thường, số, gạch dưới (không bao giờ có tên người). */
export function parseGroupCode(search: string): string | null {
  const raw = new URLSearchParams(search).get("group");
  return raw && /^[a-z][a-z0-9_]{0,40}$/.test(raw) ? raw : null;
}

// ---- Bản nháp của W3i (PV-11): việc và phạm vi đổi trong bộ nhớ, bấm "Lưu thay đổi" mới gửi MỘT PUT ----

export type Draft = { capabilities: CapabilityChanges; scopes: ScopeChanges };
export const EMPTY_DRAFT: Draft = { capabilities: {}, scopes: {} };

export function draftSize(d: Draft): number {
  return Object.keys(d.capabilities).length + Object.keys(d.scopes).length;
}

/** Bỏ khoá trùng giá trị đang lưu (đổi qua đổi lại về như cũ thì không còn là thay đổi). */
export function cleanDraft(d: Draft, states: Record<string, CapabilityState>, values: Record<string, string>): Draft {
  const capabilities: CapabilityChanges = {};
  for (const [k, on] of Object.entries(d.capabilities)) {
    const before = states[k] ?? "off";
    if (before === "partial" || (before === "on") !== on) capabilities[k] = on;
  }
  const scopes: ScopeChanges = {};
  for (const [k, v] of Object.entries(d.scopes)) if (values[k] !== v) scopes[k] = v;
  return { capabilities, scopes };
}

export function effectiveValues(values: Record<string, string>, d: Draft): Record<string, string> {
  return { ...values, ...d.scopes };
}

/**
 * Bấm một việc trong bản nháp: dùng `planToggle` (cặp `requires` đổi cùng lúc) trên trạng thái đã cộng bản nháp.
 * PO-Q1: bật "Xem khách hàng" khi phạm vi Khách hàng đang "Không xem" → bản nháp tự đặt Khách hàng = Tất cả (BE không nhận trạng thái bật + Không xem).
 */
export function toggleInDraft(
  registry: RegistryItem[],
  states: Record<string, CapabilityState>,
  values: Record<string, string>,
  d: Draft,
  key: string,
): { draft: Draft; plan: TogglePlan } | null {
  const plan = planToggle(registry, applyChanges(states, d.capabilities), key);
  if (!plan) return null;
  const capabilities = { ...d.capabilities, ...plan.changes };
  const scopes = { ...d.scopes };
  if (plan.changes[CUSTOMERS_KEY] === true && effectiveValues(values, d).customers === "none") scopes.customers = "all";
  if (plan.changes[CUSTOMERS_KEY] === false && values.customers === "none") delete scopes.customers;
  return { draft: cleanDraft({ capabilities, scopes }, states, values), plan };
}

/** Đổi một ô phạm vi trong bản nháp. */
export function setScopeInDraft(states: Record<string, CapabilityState>, values: Record<string, string>, d: Draft, key: string, value: string): Draft {
  return cleanDraft({ capabilities: d.capabilities, scopes: { ...d.scopes, [key]: value } }, states, values);
}

/** Ô phạm vi mờ? Mờ khi BE báo `inactive_reason` và việc gốc CHƯA bật trong bản nháp (PV-11-AC2, AC3). */
export function isScopeInactive(row: DataScopeRow, states: Record<string, CapabilityState>, d: Draft): boolean {
  if (row.inactive_reason == null) return false;
  if (row.gate_capability && applyChanges(states, d.capabilities)[row.gate_capability] === "on") return false;
  return true;
}

/** Chữ hiện cho một giá trị phạm vi: nhãn lựa chọn của BE, hoặc chữ cố định cho dòng chỉ đọc. */
export function scopeValueLabel(row: DataScopeRow, value: string): string {
  const option = row.options.find((o) => o.value === value);
  if (option) return option.label;
  if (value === "follows_orders") return "Theo Đơn hàng";
  if (value === "all") return "Tất cả";
  if (value === "none") return "Không xem";
  return value;
}

/** Lỗi chặn lưu ở FE (BE cũng chặn): "Xem khách hàng" bật mà Khách hàng = Không xem (PO-Q1). Null = hợp lệ. */
export function draftProblem(groupCode: string, states: Record<string, CapabilityState>, values: Record<string, string>, d: Draft): string | null {
  if (groupCode === ROLE.owner || draftSize(d) === 0) return null;
  const on = applyChanges(states, d.capabilities)[CUSTOMERS_KEY] === "on";
  if (on && effectiveValues(values, d).customers === "none") return "Bật Xem khách hàng thì chọn phạm vi Khách hàng khác Không xem.";
  return null;
}

/** Thân PUT từ bản nháp: chỉ khoá đã đổi, kèm `version` của lần GET gần nhất (PV-10-AC8). */
export function saveBodyOf(version: string, d: Draft, confirm: boolean): GroupSaveBody {
  const body: GroupSaveBody = { version };
  if (Object.keys(d.capabilities).length) body.capabilities = d.capabilities;
  if (Object.keys(d.scopes).length) body.scopes = d.scopes;
  if (confirm) body.confirm_customer_data_widening = true;
  return body;
}

/** Các câu "tắt việc làm hỏng màn" của bản nháp (hỏi lại một lần lúc Lưu, thay cho hộp hỏi lúc bấm). */
export function breakingWarnings(registry: RegistryItem[], states: Record<string, CapabilityState>, d: Draft, memberCount: number): { key: string; text: string }[] {
  const out: { key: string; text: string }[] = [];
  for (const [key, on] of Object.entries(d.capabilities)) {
    if (on || (states[key] ?? "off") === "off") continue;
    const text = breakingWarning(key, false, memberCount);
    const item = registry.find((r) => r.key === key);
    if (text && item) out.push({ key, text: `Tắt “${item.label}”: ${text}` });
  }
  return out;
}
