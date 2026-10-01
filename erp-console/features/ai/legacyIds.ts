// Lớp chuẩn hoá id lệnh AI, nhóm lệnh, mức nhạy cảm (P8b Lô 3).
// Từ Lô 4 BE trả tên tiếng Anh (`…receive_batches`, `purchasing`, `high`…). Trong lúc hai phía deploy lệch nhau, FE nhận CẢ tên cũ và
// tên mới rồi đổi về giá trị nội bộ hiện tại (./commandGroups.ts) khi ĐỌC / SO SÁNH / HIỂN THỊ.
// Không ghi đè id trong dữ liệu BE trả về: lệnh gọi lại BE (URL `/call/`, khoá `caps`/`overrides`) dùng đúng chuỗi BE đã đưa,
// nên dù BE ở phía nào của Lô 4 thì request vẫn khớp. Gỡ tên cũ ở Lô 5 (phiên bản AI cũ được ghim vẫn có thể còn khoá cũ).

import { normalizeRoles } from "@/shared/lib/roles";
import { COMMAND_GROUP, RECEIVE_BATCHES_COMMAND_ID, SENSITIVITY, type AiCommandGroup, type AiSensitivity } from "./commandGroups";
import type { AiCommandDescriptor, AiCommandsIndexResponse, AiPolicy, MyConfig } from "./types";

/** Id lệnh (cũ và mới) → id nội bộ hiện tại. */
export const LEGACY_COMMAND_IDS: ReadonlyMap<string, string> = new Map<string, string>([
  ["purchasing.purchasereceipt.nhap_lo", RECEIVE_BATCHES_COMMAND_ID],
  ["purchasing.purchasereceipt.receive_batches", RECEIVE_BATCHES_COMMAND_ID],
]);

/** Nhóm lệnh (cũ và mới) → giá trị nội bộ hiện tại. */
export const LEGACY_COMMAND_GROUPS: ReadonlyMap<string, string> = new Map<string, string>([
  ["thu_mua", COMMAND_GROUP.purchasing],
  ["purchasing", COMMAND_GROUP.purchasing],
  ["ban_hang", COMMAND_GROUP.sales],
  ["sales", COMMAND_GROUP.sales],
  ["cskh", COMMAND_GROUP.customerService],
  ["customer_service", COMMAND_GROUP.customerService],
]);

/** Mức nhạy cảm (cũ và mới) → giá trị nội bộ hiện tại. */
export const LEGACY_SENSITIVITIES: ReadonlyMap<string, string> = new Map<string, string>([
  ["cao", SENSITIVITY.high],
  ["high", SENSITIVITY.high],
  ["trung_binh", SENSITIVITY.medium],
  ["medium", SENSITIVITY.medium],
  ["thap", SENSITIVITY.low],
  ["low", SENSITIVITY.low],
]);

export function normalizeCommandId(id: string): string {
  return LEGACY_COMMAND_IDS.get(id) ?? id;
}

export function normalizeAiGroup(group: string): string {
  return LEGACY_COMMAND_GROUPS.get(group) ?? group;
}

export function normalizeSensitivity(sensitivity: string): string {
  return LEGACY_SENSITIVITIES.get(sensitivity) ?? sensitivity;
}

/** Hai id cùng chỉ một lệnh (so sánh sau khi chuẩn hoá). */
export function isSameCommand(a: string, b: string): boolean {
  return normalizeCommandId(a) === normalizeCommandId(b);
}

/**
 * Tìm mục của lệnh `commandId` trong một bảng khoá theo id lệnh (`caps`, `overrides`, `limits`), khoá là tên cũ hay mới đều được.
 * Trả cả khoá thật để ghi ngược lại đúng khoá BE đang dùng (không tạo khoá thứ hai).
 */
export function findByCommand<T>(
  table: Readonly<Record<string, T>> | null | undefined,
  commandId: string
): { key: string; value: T } | undefined {
  if (!table) return undefined;
  for (const key of Object.keys(table)) {
    if (isSameCommand(key, commandId)) return { key, value: table[key] };
  }
  return undefined;
}

// ---- Chuẩn hoá ở biên API. Chỉ đổi trường dùng để SO SÁNH/HIỂN THỊ (group, sensitivity, groups của người dùng);
// id lệnh và khoá `caps`/`overrides` giữ nguyên như BE trả để gửi ngược lại không lệch. ----

export function normalizeIndexResponse(res: AiCommandsIndexResponse): AiCommandsIndexResponse {
  return {
    ...res,
    commands: (res.commands ?? []).map((c) => ({ ...c, group: normalizeAiGroup(c.group) as AiCommandGroup })),
  };
}

export function normalizeDescriptor(desc: AiCommandDescriptor): AiCommandDescriptor {
  return { ...desc, sensitivity: normalizeSensitivity(desc.sensitivity) as AiSensitivity };
}

export function normalizeMyConfig(cfg: MyConfig): MyConfig {
  return {
    ...cfg,
    groups: (cfg.groups ?? []).map((g) => ({ ...g, group: normalizeAiGroup(g.group) as AiCommandGroup })),
  };
}

export function normalizeAiPolicy(policy: AiPolicy): AiPolicy {
  return {
    ...policy,
    users: (policy.users ?? []).map((u) => ({ ...u, groups: normalizeRoles(u.groups ?? []) })),
  };
}
