// Dựng bảng `caps` gửi lên PUT /api/ai/policy/ khi Chủ sửa trần lệnh Nhập lô (P8b Lô 4b).
// Luôn ghi bằng id MỚI; khoá cũ của cùng lệnh (nếu BE còn trả) bị bỏ để không có hai khoá cho một lệnh. Lệnh khác giữ nguyên.

import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import { findByCommand, isSameCommand } from "../legacyIds";
import type { PolicyCaps } from "../types";

export type ReceiveBatchesCap = { kg: string | null; vnd: string | null; daily: number | null };

export function buildCapsForSave(
  caps: Readonly<PolicyCaps> | null | undefined,
  next: ReceiveBatchesCap
): PolicyCaps {
  const existing = findByCommand(caps, RECEIVE_BATCHES_COMMAND_ID);
  const others = Object.fromEntries(Object.entries(caps ?? {}).filter(([key]) => !isSameCommand(key, RECEIVE_BATCHES_COMMAND_ID)));
  return { ...others, [RECEIVE_BATCHES_COMMAND_ID]: { ...(existing?.value ?? {}), ...next } };
}
