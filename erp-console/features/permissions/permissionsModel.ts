// Luật thuần của màn Phân quyền (ED-40): gom việc theo khu, kiểu ô, kế hoạch bật/tắt một việc (cặp `requires` đổi cùng lúc,
// cách hoàn tác), cảnh báo trước khi tắt việc làm hỏng màn của nhóm. KHÔNG gọi API, KHÔNG React → vitest được.
// Luật quyết định cuối cùng vẫn ở BE (`set_group_capabilities`): FE chỉ dựng đúng yêu cầu và hiện đúng ô.

import { ROLE } from "@/shared/lib/roles";
import type { CapabilityChanges, CapabilityState, RegistryItem } from "./types";

/** Thứ tự các khu trong ma trận (02b §3 B4); khu lạ BE thêm sau này đứng cuối. */
export const SECTION_ORDER = ["Bán hàng", "Hàng hoá & kho", "Kế toán", "Website", "Quản trị"] as const;

export type Section = { name: string; items: RegistryItem[] };

/** Gom registry theo khu, giữ thứ tự việc BE trả; khu theo `SECTION_ORDER`. */
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
 * Ô "Được gán" ở bảng ma trận (W3h, ED-40-AC1): nhân viên giao chỉ làm trên phiếu/đơn được gán cho mình. Bảng này chép
 * `GROUP_SCOPES` của BE (nhóm giao có phạm vi "Được gán"); danh sách nhóm KHÔNG kèm phạm vi nên FE giữ hằng số.
 */
export const ASSIGNED_ONLY: Record<string, readonly string[]> = {
  [ROLE.deliveryStaff]: ["view_orders", "deliver"],
};

export function isAssignedOnly(groupCode: string, key: string): boolean {
  return (ASSIGNED_ONLY[groupCode] ?? []).includes(key);
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
