// Lớp gọi API Tiếp theo · Đã làm (02b §6.7, DW-03).

import { apiFetch } from "@/shared/lib/http";
import { mockGuidanceApi } from "./mock";
import type { GuidanceData } from "./types";

export function getGuidance(
  docType: string,
  docId: string | number,
  signal?: AbortSignal
): Promise<GuidanceData> {
  return apiFetch<GuidanceData>(`/api/guidance/${docType}/${docId}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockGuidanceApi : undefined,
  });
}
