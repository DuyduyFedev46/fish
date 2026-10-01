// Quản lý chỉ mục và mô tả lệnh AI phía FE (DW-09, 02b §5.1, §6.2).
// Bất biến: chỉ mục lưu trong RAM JS, không lưu vào localStorage hay URL (DW-09-AC7).
// Tải lại khi index_version đổi (DW-09-AC6).

import { apiFetch } from "@/shared/lib/http";
import type { AiCommandDescriptor, AiCommandsIndexResponse } from "../types";

let cachedIndex: AiCommandsIndexResponse | null = null;
const cachedDescriptors = new Map<string, AiCommandDescriptor>();

/** Xoá bộ nhớ đệm chỉ mục (dùng cho test hoặc khi đăng xuất). */
export function clearIndexCache(): void {
  cachedIndex = null;
  cachedDescriptors.clear();
}

/** Lấy chỉ mục đang có trong RAM. */
export function getCachedIndex(): AiCommandsIndexResponse | null {
  return cachedIndex;
}

/**
 * Tải chỉ mục lệnh AI từ BE (/api/ai/commands/index/).
 * Lưu vào bộ nhớ RAM; tự làm mới nếu index_version thay đổi.
 * Ném lỗi mã "AI_DISABLED" nếu BE trả 410.
 */
export async function fetchCommandIndex(force = false, signal?: AbortSignal): Promise<AiCommandsIndexResponse> {
  if (!force && cachedIndex) {
    return cachedIndex;
  }

  const res = await apiFetch<AiCommandsIndexResponse>("/api/ai/commands/index/", { signal });

  if (cachedIndex && cachedIndex.index_version !== res.index_version) {
    cachedDescriptors.clear();
  }

  cachedIndex = res;
  return res;
}

/**
 * Tải chi tiết mô tả lệnh (schema, output_fields) từ BE (/api/ai/commands/<id>/).
 */
export async function fetchCommandDescriptor(
  commandId: string,
  signal?: AbortSignal
): Promise<AiCommandDescriptor> {
  const cached = cachedDescriptors.get(commandId);
  if (cached) return cached;

  const desc = await apiFetch<AiCommandDescriptor>(`/api/ai/commands/${encodeURIComponent(commandId)}/`, { signal });

  cachedDescriptors.set(commandId, desc);
  return desc;
}
