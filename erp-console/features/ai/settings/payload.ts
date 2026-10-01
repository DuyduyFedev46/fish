// Dựng thân `PUT /api/ai/my-config/` từ cấu hình đang xem (SR-AIS-02, SR-AIS-03).
//
// Ngữ nghĩa BE (`backend/apps/ai/settings/services.py: update_user_config`): mỗi lần lưu tạo MỘT phiên bản mới có
// `group_levels = groups`, `overrides = overrides`, `limits = limits` — THAY THẾ toàn bộ, khoá vắng = rỗng (không phải "giữ nguyên").
// Vì vậy thân gửi đi phải mang đủ cả ba; thiếu `groups` thì BE đặt lại mọi nhóm về mặc định và lệnh đang OFF trở thành C/A (nới quyền).

import type { AiCommandLevel, MyCommandLimits, MyConfig } from "../types";
import { displayLevel } from "./levels";

export type LimitInputs = Record<string, { kg?: string; vnd?: string }>;

export type MyConfigForm = {
  /** id lệnh → mức đang chọn (mọi lệnh có `source: "override"` cộng các lệnh vừa đổi). */
  overrides: Record<string, string>;
  /** id lệnh → nội dung ô nhập ngưỡng (chuỗi, rỗng = để trống). */
  limits: LimitInputs;
};

export type MyConfigSavePayload = {
  base_version: number;
  groups: Record<string, { read: string; write: string }>;
  overrides: Record<string, string>;
  limits: Record<string, { kg?: string; vnd?: string }>;
  acknowledge_responsibility: boolean;
};

/** Giá trị các ô ngưỡng từ `limits` phẳng của BE; chưa đặt thì ô rỗng. */
export function readLimitInputs(limits: MyCommandLimits | null | undefined): { kg: string; vnd: string } {
  return { kg: limits?.kg != null ? String(limits.kg) : "", vnd: limits?.vnd != null ? String(limits.vnd) : "" };
}

/** Ngưỡng gửi đi: ô để trống thì KHÔNG gửi khoá (gửi "" là BE báo 400); lệnh trống cả hai thì bỏ hẳn. */
export function buildLimitsForSave(inputs: LimitInputs): Record<string, { kg?: string; vnd?: string }> {
  const out: Record<string, { kg?: string; vnd?: string }> = {};
  for (const [id, fields] of Object.entries(inputs)) {
    const kg = fields.kg?.trim();
    const vnd = fields.vnd?.trim();
    if (!kg && !vnd) continue;
    out[id] = { ...(kg ? { kg } : {}), ...(vnd ? { vnd } : {}) };
  }
  return out;
}

/**
 * `groups` gửi lại đúng mức nhóm đang có (`read_level`, `write_level` BE đã gộp với mặc định A/C nên nhóm chưa cấu hình
 * gửi lại đúng mặc định, mức hiệu lực không đổi). Mức ghi B mà môi trường không cho B được hạ về C để BE không từ chối cả lần lưu;
 * mức hiệu lực vẫn bị trần môi trường chặn ở C nên không đổi.
 */
export function buildGroupsForSave(config: MyConfig): Record<string, { read: string; write: string }> {
  const allowed: AiCommandLevel[] = config.write_levels_allowed ?? ["OFF", "C"];
  const out: Record<string, { read: string; write: string }> = {};
  for (const group of config.groups) {
    out[group.group] = {
      read: group.read_level,
      write: allowed.includes(group.write_level) ? group.write_level : "C",
    };
  }
  return out;
}

/**
 * `overrides` gửi đi: mức B mà môi trường không cho B (BR-AI-27), vùng đỏ chưa mở hoặc trần lệnh thấp hơn B bị hạ về C, giống
 * `buildGroupsForSave`, để một override cũ không làm BE từ chối cả lần lưu (người dùng kẹt, không lưu được gì). Mức hiệu lực
 * không đổi vì trần vẫn chặn ở C. Id không có trong cấu hình (lệnh ngoài quyền) gửi nguyên.
 */
export function buildOverridesForSave(config: MyConfig, overrides: Record<string, string>): Record<string, string> {
  const commands = new Map(config.groups.flatMap((group) => group.commands).map((cmd) => [cmd.id, cmd] as const));
  const out: Record<string, string> = {};
  for (const [id, level] of Object.entries(overrides)) {
    const cmd = commands.get(id);
    out[id] = cmd ? displayLevel(config, cmd, level) : level;
  }
  return out;
}

export function buildMyConfigPayload(config: MyConfig, form: MyConfigForm): MyConfigSavePayload {
  return {
    base_version: config.version,
    groups: buildGroupsForSave(config),
    overrides: buildOverridesForSave(config, form.overrides),
    limits: buildLimitsForSave(form.limits),
    acknowledge_responsibility: true,
  };
}
