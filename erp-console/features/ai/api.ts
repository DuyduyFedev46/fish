// API module AI — endpoint S05 status (nhật ký S03 đã chuyển sang features/audit).
// BOUNDARY (C.2): file này KHÔNG được import gì từ runtime/ · voice/ · chat/ — chỉ gọi HTTP qua shared/lib/http.

import { apiFetch } from "@/shared/lib/http";
import { publishAiEnabled, type AiGateOwner } from "./gate-state";
import { mockStatus } from "./mock";
import type { AiStatus } from "./types";

/** GET /api/ai/status/ — luôn 200 kể cả AI tắt; lỗi mạng → gate coi như tắt (S05-AC5 fail-closed). */
export async function getAiStatus(signal?: AbortSignal, owner?: AiGateOwner): Promise<AiStatus> {
  try {
    const st = await apiFetch<AiStatus>("/api/ai/status/", {
      signal,
      mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStatus : undefined,
    });
    publishAiEnabled(st.ai_enabled, owner); // SR-20: màn nghiệp vụ đọc kết quả này qua gate-state, không tự gọi status
    return st;
  } catch (err) {
    if (!signal?.aborted) publishAiEnabled(false, owner); // lỗi mạng → coi như tắt (fail-closed)
    throw err;
  }
}
