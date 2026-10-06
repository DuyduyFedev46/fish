// Phần THUẦN của mock phạm vi dữ liệu (PV-02 contract, PV-09): danh mục D1..D8 chép từ BE `accounts/data_scopes/catalog.py`,
// dựng 8 dòng `data_scopes`, đánh giá "mở rộng dữ liệu khách" (02b §2.5) và dựng kết quả xem trước. Không đọc storage, không React
// → vitest được. Chỉ mock.ts dùng. Không có dữ liệu khách: chỉ mã đối tượng, mã giá trị, tên nhân viên.

import { ROLE } from "@/shared/lib/roles";
import type { CapabilityState, DataScopeRow, ScopeOption, ScopePreview } from "./types";

export type ScopeObjectDef = {
  key: string;
  label: string;
  customer_data: boolean;
  options: ScopeOption[];
  /** Mã việc ở registry mà tắt thì ô mờ; null = quyền ngoài registry (hoặc việc chưa có tới Lô 3). */
  gate_capability: string | null;
  /** Dùng trong "Nhóm không có quyền xem …" khi không có việc gốc ở registry. */
  gate_label: string;
  /** Mặc định theo nhóm (khớp migration BE `0015`). */
  defaults: Record<string, string>;
  read_only: boolean;
  /** Câu "N người … sẽ thấy tên, SĐT, địa chỉ khách <cụm>". */
  phrase: string;
  /** Danh từ cho dòng "đang làm dở" khi thu hẹp. */
  noun: string;
};

const opt = (value: string, label: string, rank: number): ScopeOption => ({ value, label, rank });
const dflt = (manager: string, warehouse: string, delivery: string, service: string): Record<string, string> => ({
  [ROLE.manager]: manager,
  [ROLE.warehouseStaff]: warehouse,
  [ROLE.deliveryStaff]: delivery,
  [ROLE.customerService]: service,
});

export const SCOPE_OBJECTS: ScopeObjectDef[] = [
  {
    key: "orders",
    label: "Đơn hàng",
    customer_data: true,
    options: [
      opt("assigned_deliveries", "Đơn có phiếu giao gán cho tôi", 0),
      opt("assigned_or_confirmation", "Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận", 1),
      opt("all", "Tất cả đơn", 2),
    ],
    gate_capability: "view_orders",
    gate_label: "đơn hàng",
    defaults: dflt("all", "all", "assigned_deliveries", "assigned_or_confirmation"),
    read_only: false,
    phrase: "của mọi đơn",
    noun: "đơn",
  },
  {
    key: "invoices",
    label: "Hoá đơn bán",
    customer_data: true,
    options: [],
    gate_capability: null, // V1 `view_sales_invoices` chưa có tới Lô 3 (BE trả null)
    gate_label: "hoá đơn bán",
    defaults: {},
    read_only: true,
    phrase: "trên hoá đơn bán",
    noun: "hoá đơn",
  },
  {
    key: "deliveries",
    label: "Phiếu giao",
    customer_data: true,
    options: [opt("assigned", "Phiếu gán cho tôi", 0), opt("all", "Tất cả phiếu", 1)],
    gate_capability: null,
    gate_label: "phiếu giao",
    defaults: dflt("all", "all", "assigned", "assigned"),
    read_only: false,
    phrase: "của mọi phiếu giao",
    noun: "phiếu giao",
  },
  {
    key: "confirmation",
    label: "Gọi xác nhận",
    customer_data: true,
    options: [opt("pending_or_called_recently", "Phiếu đang chờ gọi hoặc tôi đã gọi trong N ngày", 0), opt("all_pending", "Mọi phiếu chờ gọi", 1)],
    gate_capability: "confirm_calls",
    gate_label: "gọi xác nhận",
    defaults: dflt("all_pending", "all_pending", "pending_or_called_recently", "pending_or_called_recently"),
    read_only: false,
    phrase: "của mọi phiếu chờ gọi",
    noun: "việc gọi",
  },
  {
    key: "returns",
    label: "Hàng hoàn về kho",
    customer_data: true,
    options: [opt("assigned_deliveries", "Phiếu của phiếu giao gán cho tôi", 0), opt("all", "Tất cả phiếu", 1)],
    gate_capability: null,
    gate_label: "hàng hoàn về kho",
    defaults: dflt("all", "all", "assigned_deliveries", "assigned_deliveries"),
    read_only: false,
    phrase: "của mọi phiếu hàng hoàn",
    noun: "phiếu hàng hoàn",
  },
  {
    key: "receipts",
    label: "Phiếu nhập",
    customer_data: false,
    options: [opt("created_by_me_today", "Do tôi tạo trong ngày", 0), opt("created_by_me", "Do tôi tạo", 1), opt("all", "Tất cả phiếu", 2)],
    gate_capability: "receive",
    gate_label: "phiếu nhập",
    defaults: dflt("all", "all", "all", "all"),
    read_only: false,
    phrase: "",
    noun: "phiếu nhập",
  },
  {
    key: "customers",
    label: "Khách hàng",
    customer_data: true,
    options: [opt("none", "Không xem", 0), opt("assigned_deliveries", "Khách của phiếu giao gán cho tôi (trong cửa sổ)", 1), opt("all", "Tất cả khách", 2)],
    gate_capability: "view_customers",
    gate_label: "khách hàng",
    defaults: dflt("all", "none", "assigned_deliveries", "none"),
    read_only: false,
    phrase: "của mọi khách",
    noun: "khách",
  },
  {
    key: "audit_log",
    label: "Nhật ký hoạt động",
    customer_data: false,
    options: [],
    gate_capability: "view_audit",
    gate_label: "nhật ký hoạt động",
    defaults: {},
    read_only: true,
    phrase: "",
    noun: "dòng nhật ký",
  },
];

export const SCOPE_BY_KEY: Record<string, ScopeObjectDef> = Object.fromEntries(SCOPE_OBJECTS.map((o) => [o.key, o]));
/** 6 đối tượng sửa được (D2, D8 chỉ đọc). */
export const STORED_KEYS = SCOPE_OBJECTS.filter((o) => !o.read_only).map((o) => o.key);

const OWNER_NOTE = "Chủ luôn thấy tất cả";

export function widestValue(obj: ScopeObjectDef): string {
  return [...obj.options].sort((a, b) => b.rank - a.rank)[0].value;
}
function narrowestValue(obj: ScopeObjectDef): string {
  return [...obj.options].sort((a, b) => a.rank - b.rank)[0].value;
}
/** Rank của giá trị, hoặc -1 nếu không thuộc lựa chọn. */
export function rankOf(obj: ScopeObjectDef, value: string): number {
  return obj.options.find((o) => o.value === value)?.rank ?? -1;
}

/** Giá trị phạm vi của 6 đối tượng sửa được: Chủ rộng nhất; nhóm khác = mặc định BE đè bằng `overrides`; hỏng → hẹp nhất. */
export function valuesOf(group: string, overrides: Record<string, string> | undefined): Record<string, string> {
  const out: Record<string, string> = {};
  for (const key of STORED_KEYS) {
    const obj = SCOPE_BY_KEY[key];
    if (group === ROLE.owner) {
      out[key] = widestValue(obj);
      continue;
    }
    const stored = overrides?.[key] ?? obj.defaults[group];
    out[key] = stored !== undefined && rankOf(obj, stored) >= 0 ? stored : narrowestValue(obj);
  }
  return out;
}

/** Quyền Tầng 1 của nhóm mà mock chép từ migration BE (ngoài registry nên Chủ không đổi ở màn này). */
const HAS_INVOICE_VIEW = [ROLE.manager, ROLE.warehouseStaff];
const HAS_CUSTOMER_VIEW = [ROLE.manager, ROLE.deliveryStaff];
const NO_DELIVERY_VIEW = [ROLE.customerService];

/** Nhóm có đủ điều kiện xem đối tượng `obj` (BE `_eligible`: có ít nhất một permission cổng). */
export function isEligible(obj: ScopeObjectDef, group: string, states: Record<string, CapabilityState>): boolean {
  if (group === ROLE.owner) return true;
  switch (obj.key) {
    case "invoices":
      return HAS_INVOICE_VIEW.includes(group as never);
    case "deliveries":
    case "returns":
      return !NO_DELIVERY_VIEW.includes(group as never);
    case "customers":
      // Quản lý và NV giao có `sales.view_customer` (Tầng 1, ngoài registry, migration 0002/0012) nên đủ điều kiện, không bao giờ mờ.
      return states.view_customers === "on" || HAS_CUSTOMER_VIEW.includes(group as never);
    default:
      return obj.gate_capability !== null && states[obj.gate_capability] === "on";
  }
}

export function describeRows(group: string, states: Record<string, CapabilityState>, values: Record<string, string>, labelOfCapability: (key: string) => string): DataScopeRow[] {
  const owner = group === ROLE.owner;
  return SCOPE_OBJECTS.map((obj) => {
    const eligible = isEligible(obj, group, states);
    let value: string;
    if (obj.key === "invoices") value = "follows_orders";
    else if (obj.key === "audit_log") value = owner || eligible ? "all" : "none";
    else value = values[obj.key];
    let reason: string | null = null;
    if (!owner && !eligible) {
      reason = obj.gate_capability !== null ? `Không xem — bật việc "${labelOfCapability(obj.gate_capability)}" trước` : `Nhóm không có quyền xem ${obj.gate_label}`;
    }
    return {
      key: obj.key,
      label: obj.label,
      value,
      editable: !owner && !obj.read_only,
      customer_data: obj.customer_data,
      gate_capability: obj.gate_capability,
      inactive_reason: reason,
      note: owner ? OWNER_NOTE : obj.key === "invoices" ? "Theo Đơn hàng" : null,
      options: obj.read_only ? [] : [...obj.options].sort((a, b) => a.rank - b.rank),
    };
  });
}

/**
 * Rank HIỆU LỰC của một giá trị (02b §2.5, luật H1): D7 thiếu `sales.view_customer_list` (việc "Xem khách hàng" tắt) bị chặn trần
 * `assigned_deliveries` (rank 1), dù giá trị đã lưu là `all` (Q-7 giữ giá trị khi tắt việc).
 */
export function effectiveRank(obj: ScopeObjectDef, value: string, states: Record<string, CapabilityState>): number {
  const rank = rankOf(obj, value);
  if (obj.key === "customers" && states.view_customers !== "on") return Math.min(rank, rankOf(obj, "assigned_deliveries"));
  return rank;
}

/** "Tầm với" của một nhóm với một đối tượng: cổng mở? rank bao nhiêu? (02b §2.5). */
export type Reach = { open: boolean; rank: number };

/** Mở rộng khi sau thay đổi cổng mở và rank lớn hơn rank trước (cổng đang đóng coi như rank 0, nên "vừa mở với rank 0" không tính). */
export function isWidening(before: Reach, after: Reach): boolean {
  if (!after.open) return false;
  const base = before.open ? before.rank : 0;
  return after.rank > base;
}

export type PreviewGroup = {
  code: string;
  states: Record<string, CapabilityState>;
  values: Record<string, string>;
  /** Thành viên ĐANG LÀM. */
  members: { id: number; display_name: string }[];
};

/**
 * Xem trước (02b §2.4). `before`/`after` = nhóm đang sửa trước và sau thay đổi; `others` = các nhóm còn lại (để tìm người kiêm nhiệm).
 * Chỉ xét đối tượng có dữ liệu khách để quyết `widens_customer_data`; thu hẹp xét mọi đối tượng sửa được.
 */
export function buildPreview(before: PreviewGroup, after: PreviewGroup, others: PreviewGroup[]): ScopePreview {
  const widened: ScopePreview["widened"] = [];
  const narrowed: ScopePreview["narrowed"] = [];
  const widenedObjects: ScopeObjectDef[] = [];
  const changedKeys: string[] = [];
  for (const key of STORED_KEYS) {
    const obj = SCOPE_BY_KEY[key];
    const reachBefore: Reach = { open: isEligible(obj, before.code, before.states), rank: effectiveRank(obj, before.values[key], before.states) };
    const reachAfter: Reach = { open: isEligible(obj, after.code, after.states), rank: effectiveRank(obj, after.values[key], after.states) };
    const changed = before.values[key] !== after.values[key];
    if (changed) changedKeys.push(key);
    if (obj.customer_data && isWidening(reachBefore, reachAfter)) {
      widened.push({ key, from: before.values[key], to: after.values[key] });
      widenedObjects.push(obj);
    }
    if (changed && reachAfter.rank < reachBefore.rank) {
      narrowed.push({ key, from: before.values[key], to: after.values[key], rows_losing_access: after.members.length === 0 ? 0 : key === "receipts" ? 3 : 2 });
    }
  }
  const widens = widened.length > 0;
  const n = after.members.length;
  let message = "";
  if (widens) {
    if (n === 0) message = "Nhóm này chưa có ai đang làm nên chưa người nào thấy thêm.";
    else if (widenedObjects.length === 1) message = `${n} người trong nhóm sẽ thấy tên, SĐT, địa chỉ khách ${widenedObjects[0].phrase}.`;
    else message = `${n} người trong nhóm sẽ thấy tên, SĐT, địa chỉ khách ở: ${widenedObjects.map((o) => o.label).join(", ")}.`;
  }
  const wider: ScopePreview["already_wider_elsewhere"] = [];
  for (const key of changedKeys) {
    const obj = SCOPE_BY_KEY[key];
    const newRank = effectiveRank(obj, after.values[key], after.states);
    for (const member of after.members) {
      for (const other of others) {
        if (!other.members.some((m) => m.id === member.id)) continue;
        if (!isEligible(obj, other.code, other.states)) continue;
        if (effectiveRank(obj, other.values[key], other.states) > newRank && !wider.some((w) => w.id === member.id && w.key === key)) {
          wider.push({ id: member.id, display_name: member.display_name, via_group: other.code, key });
        }
      }
    }
  }
  return {
    widens_customer_data: widens,
    widened,
    affected_members: widens ? after.members : [],
    affected_count: widens ? n : 0,
    message,
    already_wider_elsewhere: wider,
    narrowed,
  };
}

/** Câu sự kiện dòng thời gian khi đổi phạm vi: "Đổi phạm vi Phiếu nhập: Tất cả phiếu → Do tôi tạo trong ngày". */
export function scopeEventLabel(key: string, from: string, to: string): string {
  const obj = SCOPE_BY_KEY[key];
  const text = (v: string) => obj.options.find((o) => o.value === v)?.label ?? v;
  return `Đổi phạm vi ${obj.label}: ${text(from)} → ${text(to)}`;
}
