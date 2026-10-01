// Mức tự chủ hiệu lực, ô ngưỡng và câu báo lỗi của màn "AI của tôi" (QA lần 1: B1, B2 của lô lưu cài đặt AI).
// Thuần hàm, không React, để vừa vẽ màn vừa dựng thân PUT bằng cùng một quy tắc.

import { ApiError } from "@/shared/lib/http";
import { isSameCommand } from "../legacyIds";
import type { AiCommandLevel, MyConfig, MyConfigCommandItem } from "../types";
import type { MyConfigSavePayload } from "./payload";

export type LimitField = "kg" | "vnd";

/** Mọi lệnh trong mọi nhóm của cấu hình (để tra tên lệnh theo id). */
function allCommands(config: MyConfig): MyConfigCommandItem[] {
  return config.groups.flatMap((group) => group.commands);
}

/**
 * Lệnh ghi này có được ở mức B không? Khớp các điều kiện BE từ chối override B (`update_user_config`):
 * môi trường không cho B (BR-AI-27), vùng đỏ Chủ chưa mở hoặc lệnh bị khoá (`locked_reason`, BR-AI-18), trần lệnh thấp hơn B.
 * Lệnh đọc không có mức B.
 */
export function canKeepLevelB(config: MyConfig, cmd: MyConfigCommandItem): boolean {
  if (cmd.kind === "read") return false;
  const envAllowsB = Boolean(config.write_levels_allowed?.includes("B"));
  return envAllowsB && cmd.max_level === "B" && !cmd.locked_reason;
}

/**
 * Mức hiệu lực để HIỂN THỊ và để GỬI: mức B mà lệnh không còn giữ được thì quy về C (mức nháp, đúng với cách BE chặn trần ở C),
 * không để ô chọn rơi về "Tắt (OFF)" vì thiếu lựa chọn B (người dùng hiểu sai là AI đang tắt).
 */
export function displayLevel(config: MyConfig, cmd: MyConfigCommandItem, selected: string): string {
  if (selected === "B" && !canKeepLevelB(config, cmd)) return "C";
  return selected;
}

/**
 * Danh sách mức cho ô chọn. Lệnh ghi: OFF, C; thêm B khi lệnh được chọn B (không phải vùng đỏ), hoặc khi mức đang chọn
 * đã là B và còn giữ được (vùng đỏ Chủ đã mở) để ô hiện đúng mức đang có thay vì OFF.
 */
export function commandChoices(config: MyConfig, cmd: MyConfigCommandItem, selected: string): AiCommandLevel[] {
  if (cmd.kind === "read") return cmd.choices || ["OFF", "A"];
  const choices: AiCommandLevel[] = ["OFF", "C"];
  if (canKeepLevelB(config, cmd) && (!cmd.red_zone || selected === "B")) choices.push("B");
  return choices;
}

/** Các ô ngưỡng cần vẽ cho lệnh. Có cờ `supports_limits` thì theo cờ (đủ kg và vnd); chưa có cờ thì theo khoá `limits` đang có. */
export function limitFieldsOf(cmd: MyConfigCommandItem): LimitField[] {
  if (cmd.supports_limits === true) return ["kg", "vnd"];
  if (cmd.supports_limits === false || !cmd.limits) return [];
  return (["kg", "vnd"] as const).filter((field) => field in (cmd.limits as object));
}

function commandTitle(config: MyConfig, id: string): string {
  return allCommands(config).find((cmd) => isSameCommand(cmd.id, id))?.title ?? id;
}

function errorKeyLabel(config: MyConfig, key: string): string {
  const groupKey = /^groups\.([^.]+)\.(read|write)$/.exec(key);
  if (groupKey) {
    const label = config.groups.find((group) => group.group === groupKey[1])?.label ?? groupKey[1];
    return groupKey[2] === "read" ? `Nhóm ${label} (mức đọc)` : `Nhóm ${label} (mức ghi)`;
  }
  return commandTitle(config, key);
}

/**
 * Câu báo lỗi khi lưu "AI của tôi". BR-AI-19 BE kèm `errors` (khoá = id lệnh hoặc `groups.<nhóm>.<read|write>`) thì nêu từng
 * lệnh/nhóm sai và lý do. BR-AI-27 BE không nêu lệnh, nên liệt kê các lệnh trong thân đã gửi đang ở mức B để người dùng biết chỗ sửa.
 */
export function describeSaveError(err: unknown, config: MyConfig, sent: MyConfigSavePayload | null): string {
  if (!(err instanceof Error)) return "Lỗi khi lưu cấu hình.";
  if (!(err instanceof ApiError)) return err.message;
  if (err.code === "BR-AI-19") {
    const errors = (err.details as { errors?: unknown } | undefined)?.errors;
    if (errors && typeof errors === "object") {
      const entries = Object.entries(errors as Record<string, unknown>);
      const lines = entries.map(([key, reason]) => `${errorKeyLabel(config, key)}: ${String(reason)}`);
      // Chỉ một lỗi và câu chung của BE chính là lý do đó: không nhắc lại hai lần.
      if (entries.length === 1 && err.message === String(entries[0][1])) return `${lines[0]}.`;
      if (lines.length > 0) return `${err.message} ${lines.join("; ")}.`;
    }
  }
  if (err.code === "BR-AI-27" && sent) {
    const titles = Object.entries(sent.overrides)
      .filter(([, level]) => level === "B")
      .map(([id]) => commandTitle(config, id));
    if (titles.length > 0) return `${err.message} Lệnh đang đặt mức B: ${titles.join(", ")}. Đổi sang mức C rồi lưu lại.`;
  }
  return err.message;
}
