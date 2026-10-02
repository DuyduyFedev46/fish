// API "Báo cáo AI cuối ngày" (ED-42 / W4d): GET /api/ai/report/daily/?date=YYYY-MM-DD (chỉ Chủ). Mock ở ./mock.ts.

import { apiFetch } from "@/shared/lib/http";
import type { AiDailyReport } from "../types";
import { mockDailyReport } from "./mock";

export async function fetchDailyAiReport(dateStr?: string, signal?: AbortSignal): Promise<AiDailyReport> {
  const qs = dateStr ? `?date=${encodeURIComponent(dateStr)}` : "";
  return apiFetch<AiDailyReport>(`/api/ai/report/daily/${qs}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockDailyReport : undefined,
  });
}
