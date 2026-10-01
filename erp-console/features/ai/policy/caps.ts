// Dựng bảng `caps` gửi lên PUT /api/ai/policy/ khi Chủ sửa trần lệnh Nhập lô (P8b Lô 4b, 5).
// Ghi bằng id `RECEIVE_BATCHES_COMMAND_ID`; lệnh khác giữ nguyên. Giá trị phụ (vd `max_level`) lấy từ chính khoá đó.

import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import type { PolicyCaps } from "../types";

export type ReceiveBatchesCap = { kg: string | null; vnd: string | null; daily: number | null };

export function buildCapsForSave(
  caps: Readonly<PolicyCaps> | null | undefined,
  next: ReceiveBatchesCap
): PolicyCaps {
  return { ...(caps ?? {}), [RECEIVE_BATCHES_COMMAND_ID]: { ...(caps?.[RECEIVE_BATCHES_COMMAND_ID] ?? {}), ...next } };
}
