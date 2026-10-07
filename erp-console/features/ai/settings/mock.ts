// Mock "AI của tôi" — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Mô phỏng NGỮ NGHĨA của BE thật (`backend/apps/ai/settings/services.py`), không chỉ hình dạng:
//  - PUT thay THẾ toàn bộ `group_levels`, `overrides`, `limits` (vắng khoá = rỗng), nên FE không gửi `groups` là mất cấu hình nhóm.
//  - `limits` của lệnh trả PHẲNG `{kg, vnd}` (chuỗi), không có trần của Chủ; `null` khi chưa đặt. `supports_limits` báo lệnh có khai ngưỡng.
//  - Kiểm tương tự BE: cần xác nhận trách nhiệm (BR-AI-14), phiên bản cũ 409, mức/lệnh không hợp lệ 400 (BR-AI-19).
// Dữ liệu GIẢ, không chứa tên/SĐT/địa chỉ.

import type { MockResponse } from "@/shared/lib/http";
import { aiEnabled } from "../mock";
import { COMMAND_GROUP, RECEIVE_BATCHES_COMMAND_ID, type AiCommandGroup } from "../commandGroups";
import type { AiCommandKind, AiCommandLevel, MyConfig, MyConfigCommandItem, MyConfigGroup } from "../types";

type MockSpec = { id: string; title: string; kind: AiCommandKind; group: AiCommandGroup; maxLevel: AiCommandLevel; redZone: boolean };

const SPECS: MockSpec[] = [
  { id: "inventory.batch.list", title: "Xem tồn kho theo lô", kind: "read", group: COMMAND_GROUP.purchasing, maxLevel: "A", redZone: false },
  { id: "purchasing.purchasereceipt.submit", title: "Gửi phiếu nhập kho", kind: "write", group: COMMAND_GROUP.purchasing, maxLevel: "C", redZone: false },
  // Tên lệnh do registry BE tự sinh (chưa có tên viết tay): FE phải đổi sang tiếng Việt (commandLabels.ts, Lô 15 QA).
  { id: "inventory.batch.create", title: "Tạo mới batch", kind: "write", group: COMMAND_GROUP.purchasing, maxLevel: "C", redZone: false },
  { id: RECEIVE_BATCHES_COMMAND_ID, title: "Nhập lô mua tại cảng", kind: "write", group: COMMAND_GROUP.purchasing, maxLevel: "B", redZone: false },
  { id: "sales.salesorder.list", title: "Xem danh sách đơn bán", kind: "read", group: COMMAND_GROUP.sales, maxLevel: "A", redZone: false },
  { id: "sales.salesorder.confirm_payment", title: "Xác nhận thanh toán tay", kind: "write", group: COMMAND_GROUP.sales, maxLevel: "B", redZone: true },
  { id: "confirmation.queue.list", title: "Xem hàng đợi xác nhận đơn", kind: "read", group: COMMAND_GROUP.customerService, maxLevel: "A", redZone: false },
];

const GROUP_LABELS: Array<[AiCommandGroup, string]> = [
  [COMMAND_GROUP.purchasing, "Thu mua"],
  [COMMAND_GROUP.sales, "Bán hàng"],
  [COMMAND_GROUP.customerService, "Chăm sóc khách hàng"],
];

const WRITE_CHOICES: AiCommandLevel[] = ["OFF", "C", "B"];
const READ_LEVELS = new Set(["OFF", "A"]);
const WRITE_LEVELS = new Set(["OFF", "C", "B"]);

type Stored = {
  version: number;
  updated_at: string;
  killed: boolean;
  group_levels: Record<string, { read?: string; write?: string }>;
  overrides: Record<string, string>;
  limits: Record<string, { kg?: string; vnd?: string }>;
};

const state: Stored = {
  version: 1,
  updated_at: new Date().toISOString(),
  killed: false,
  group_levels: {},
  overrides: {},
  limits: { [RECEIVE_BATCHES_COMMAND_ID]: { kg: "60", vnd: "6000000" } },
};

function commandItem(spec: MockSpec): MyConfigCommandItem {
  const groupCfg = state.group_levels[spec.group] ?? {};
  const isRead = spec.kind === "read";
  let level: AiCommandLevel;
  let source: MyConfigCommandItem["source"];
  if (spec.id in state.overrides) {
    level = state.overrides[spec.id] as AiCommandLevel;
    source = "override";
  } else if (isRead ? groupCfg.read !== undefined : groupCfg.write !== undefined) {
    level = (isRead ? groupCfg.read : groupCfg.write) as AiCommandLevel;
    source = "group";
  } else {
    level = isRead ? "A" : "C";
    source = "default";
  }
  return {
    id: spec.id,
    title: spec.title,
    kind: spec.kind,
    level,
    source,
    choices: isRead ? ["OFF", "A"] : spec.redZone ? ["OFF", "C"] : [...WRITE_CHOICES],
    max_level: isRead ? "A" : spec.redZone ? "C" : spec.maxLevel,
    locked_reason: !isRead && spec.redZone ? { code: "BR-AI-18", text: "Chủ chưa mở việc nhạy cảm này" } : null,
    red_zone: !isRead && spec.redZone,
    limits: isRead ? null : state.limits[spec.id] ?? null,
    supports_limits: !isRead && spec.id === RECEIVE_BATCHES_COMMAND_ID,
  };
}

export function mockGetMyConfig(): MyConfig {
  const groups: MyConfigGroup[] = GROUP_LABELS.map(([group, label]) => {
    const cfg = state.group_levels[group] ?? {};
    return {
      group,
      label,
      read_level: (cfg.read ?? "A") as AiCommandLevel,
      write_level: (cfg.write ?? "C") as AiCommandLevel,
      commands: SPECS.filter((s) => s.group === group).map(commandItem),
    };
  });
  return {
    ai_enabled: aiEnabled(),
    version: state.version,
    killed: state.killed,
    updated_at: state.updated_at,
    global_mode: "on",
    write_levels_allowed: [...WRITE_CHOICES],
    groups,
  };
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

// BE trải `details` (object) ra ngang hàng `detail`/`code` (`apps/common/api.py: exception_handler`).
function fail(status: number, detail: string, code: string, details?: Record<string, unknown>): MockResponse {
  return { status, body: { ...(details ?? {}), detail, code } };
}

/** PUT /api/ai/my-config/ — `body` là thân đã qua JSON (xem `sendMock` ở shared/lib/http.ts). */
export function mockUpdateMyConfig(body: unknown): MockResponse {
  const b = isRecord(body) ? body : {};
  if (typeof b.base_version !== "number" || typeof b.acknowledge_responsibility !== "boolean") {
    return { status: 400, body: { non_field_errors: ["Invalid data."] } };
  }
  if (!b.acknowledge_responsibility) return fail(400, "Bạn phải xác nhận chịu trách nhiệm cho cấu hình AI.", "BR-AI-14");
  if (b.base_version !== state.version) return fail(409, "Cấu hình đã thay đổi ở phiên khác.", "AI_CONFIG_CONFLICT", { current_version: state.version });

  // Vắng khoá = rỗng (DictField default=dict ở BE), KHÔNG phải giữ nguyên.
  const groups = isRecord(b.groups) ? b.groups : {};
  const overrides = isRecord(b.overrides) ? b.overrides : {};
  const limits = isRecord(b.limits) ? b.limits : {};

  const errors: Record<string, string> = {};
  for (const [id, level] of Object.entries(overrides)) {
    const spec = SPECS.find((s) => s.id === id);
    if (!spec) errors[id] = "Lệnh ngoài quyền của bạn";
    else if (spec.kind === "read" ? !READ_LEVELS.has(String(level)) : !WRITE_LEVELS.has(String(level))) errors[id] = "Mức không hợp lệ";
    else if (spec.redZone && level === "B") errors[id] = "Chủ chưa mở việc nhạy cảm này";
  }
  for (const [group, cfg] of Object.entries(groups)) {
    if (!isRecord(cfg)) continue;
    if (cfg.read && !READ_LEVELS.has(String(cfg.read))) errors[`groups.${group}.read`] = "Mức đọc không hợp lệ";
    if (cfg.write && !WRITE_LEVELS.has(String(cfg.write))) errors[`groups.${group}.write`] = "Mức ghi không hợp lệ";
  }
  for (const [id, lim] of Object.entries(limits)) {
    if (!isRecord(lim)) continue;
    for (const field of ["kg", "vnd"] as const) {
      if (!(field in lim) || lim[field] === null) continue;
      const text = String(lim[field]);
      if (text.trim() === "" || Number.isNaN(Number(text))) errors[id] = `Giá trị giới hạn ${field} không hợp lệ`;
    }
  }
  if (Object.keys(errors).length > 0) {
    const detail = Object.keys(errors).length === 1 ? Object.values(errors)[0] : "Dữ liệu cấu hình không hợp lệ.";
    return fail(400, detail, "BR-AI-19", { errors });
  }

  state.version += 1;
  state.updated_at = new Date().toISOString();
  state.group_levels = groups as Stored["group_levels"];
  state.overrides = overrides as Stored["overrides"];
  state.limits = limits as Stored["limits"];
  return { status: 200, body: mockGetMyConfig() };
}

/** POST /api/ai/my-config/kill/ */
export function mockKillMyConfig(body: unknown): MockResponse {
  const killed = isRecord(body) ? body.killed : undefined;
  if (typeof killed !== "boolean") return { status: 400, body: { killed: ["This field is required."] } };
  state.version += 1;
  state.updated_at = new Date().toISOString();
  state.killed = killed;
  return { status: 200, body: { version: state.version, killed } };
}
