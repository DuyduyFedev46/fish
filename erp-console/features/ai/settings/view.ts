// Phần THUẦN của màn "AI của tôi" (ED-08 / W4b): nhãn mức, mức nào bấm được, câu "Ghi chú" khoá, kiểm ô ngưỡng, đếm việc.
// Quy tắc mức vẫn ở ./levels.ts (commandChoices, displayLevel, canKeepLevelB) — file này chỉ dựng chữ và hình dáng để vẽ.

import { ENUMS } from "@/shared/lib/enums";
import type { AiCommandLevel, MyConfig, MyConfigCommandItem } from "../types";
import { canKeepLevelB, commandChoices, displayLevel, limitFieldsOf, type LimitField } from "./levels";
import type { LimitInputs } from "./payload";

/** Nhãn nút chọn mức: lấy tên trong bảng enum, thêm chữ cái mức cho A và B như bản thiết kế ("A · Tự đọc", "B · Tự ghi"). */
export function levelChoiceLabel(level: AiCommandLevel): string {
  const name = ENUMS.aiLevel[level].label;
  return level === "A" || level === "B" ? `${level} · ${name}` : name;
}

/** Các mức vẽ cho một lệnh (đủ, kể cả mức đang bị khoá để hiện ổ khoá), theo thứ tự Tắt → Tự đọc/Hỏi trước → Tự ghi. */
export function allLevelsOf(cmd: MyConfigCommandItem): AiCommandLevel[] {
  return cmd.kind === "read" ? ["OFF", "A"] : ["OFF", "C", "B"];
}

export type LevelChoice = { level: AiCommandLevel; label: string; selected: boolean; locked: boolean };

export function levelChoices(config: MyConfig, cmd: MyConfigCommandItem, selected: string): LevelChoice[] {
  const current = displayLevel(config, cmd, selected);
  const allowed = new Set(commandChoices(config, cmd, current));
  return allLevelsOf(cmd).map((level) => ({
    level,
    label: levelChoiceLabel(level),
    selected: level === current,
    locked: !allowed.has(level),
  }));
}

/** Câu ở cột "Ghi chú": rỗng khi không có gì cần nói. Ưu tiên lời của BE (`locked_reason.text`, đã là câu cho người dùng). */
export function lockNote(config: MyConfig, cmd: MyConfigCommandItem): string | null {
  if (cmd.kind === "read") return null;
  if (cmd.locked_reason?.text) return cmd.locked_reason.text;
  if (canKeepLevelB(config, cmd)) return null;
  if (cmd.red_zone) return "Chủ chưa cho phép.";
  if (cmd.max_level !== "B") return "Việc này không hoàn tác được nên luôn hỏi trước.";
  return "Hiện chỉ cho phép hỏi trước khi làm.";
}

/** Chú giải ba mức (không nêu số phút: BE không trả cho màn này). */
export const LEVEL_LEGEND: { name: string; meaning: string }[] = [
  { name: ENUMS.aiLevel.A.label, meaning: "Chỉ xem, không thay đổi gì." },
  { name: ENUMS.aiLevel.B.label, meaning: "Tự làm, bạn hoàn tác được trong thời gian ngắn." },
  { name: ENUMS.aiLevel.C.label, meaning: "Soạn sẵn rồi chờ bạn duyệt mới làm." },
];

/** Ô ngưỡng viết sai? Rỗng được (không đặt). Chỉ nhận số không âm, dấu chấm thập phân. */
export function limitProblem(value: string | undefined): string | null {
  const v = (value ?? "").trim();
  if (!v) return null;
  if (!/^\d+(\.\d+)?$/.test(v)) return "Nhập số, ví dụ 150.";
  return null;
}

/** Lỗi theo từng lệnh+ô (chỉ lệnh đang ở mức B mới có ô, nên chỉ kiểm các ô đang hiện). Khoá `${id}.${field}`. */
export function limitErrors(config: MyConfig, overrides: Record<string, string>, limits: LimitInputs): Record<string, string> {
  const out: Record<string, string> = {};
  for (const grp of config.groups) {
    for (const cmd of grp.commands) {
      if (displayLevel(config, cmd, overrides[cmd.id] || cmd.level) !== "B") continue;
      for (const field of limitFieldsOf(cmd)) {
        const problem = limitProblem(limits[cmd.id]?.[field]);
        if (problem) out[`${cmd.id}.${field}`] = problem;
      }
    }
  }
  return out;
}

export const LIMIT_UNIT: Record<LimitField, string> = { kg: "kg", vnd: "VNĐ" };
export const LIMIT_LABEL: Record<LimitField, string> = { kg: "Tối đa mỗi lần", vnd: "Giá trị tối đa mỗi lần" };

/** Có thay đổi so với bản đang lưu? So mức từng lệnh (kể cả ghi đè) và ô ngưỡng. */
export function isDirty(
  config: MyConfig,
  overrides: Record<string, string>,
  limits: LimitInputs,
  baseOverrides: Record<string, string>,
  baseLimits: LimitInputs,
): boolean {
  for (const grp of config.groups) {
    for (const cmd of grp.commands) {
      const now = overrides[cmd.id] ?? cmd.level;
      const was = baseOverrides[cmd.id] ?? cmd.level;
      if (now !== was) return true;
      for (const field of limitFieldsOf(cmd)) {
        if ((limits[cmd.id]?.[field] ?? "").trim() !== (baseLimits[cmd.id]?.[field] ?? "").trim()) return true;
      }
    }
  }
  return false;
}
