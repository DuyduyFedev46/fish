import { apiFetch, type MockRequest } from "@/shared/lib/http";
import { todayInVietnam } from "@/shared/lib/format";
import type { AiDailyReport } from "../types";

export const mockDailyAiReport: AiDailyReport = {
  date: "2026-09-28",
  by_user: [
    {
      user_id: 1,
      display_name: "Duy (Chủ)",
      A: 5,
      B: 2,
      C_confirmed: 3,
      C_expired: 0,
      undone: 1,
      escalated: 0,
    },
    {
      user_id: 2,
      display_name: "Tuấn (Kho)",
      A: 12,
      B: 3,
      C_confirmed: 1,
      C_expired: 1,
      undone: 0,
      escalated: 1,
    },
    {
      user_id: 3,
      display_name: "Linh (Quản lý)",
      A: 8,
      B: 1,
      C_confirmed: 2,
      C_expired: 0,
      undone: 0,
      escalated: 0,
    },
  ],
  items: [
    {
      id: "rpt-1",
      command: "purchasing.purchasereceipt.nhap_lo",
      title: "Nhập lô mua tại cảng",
      level: "B",
      status: "DONE",
      owner_display: "Tuấn (Kho)",
      created_at: "2026-09-28T09:15:00+07:00",
      target: { type: "purchasereceipt", code: "PR-260928-01" },
      result_ref: { model: "purchasereceipt", id: 101 },
    },
    {
      id: "rpt-2",
      command: "inventory.batch.close",
      title: "Chốt lô cá",
      level: "C",
      status: "ESCALATED",
      owner_display: "Tuấn (Kho)",
      created_at: "2026-09-28T10:30:00+07:00",
      target: { type: "batch", code: "CA01-260928-AB" },
      result_ref: null,
    },
    {
      id: "rpt-3",
      command: "purchasing.purchasereceipt.nhap_lo",
      title: "Nhập lô mua tại cảng",
      level: "B",
      status: "UNDONE",
      owner_display: "Duy (Chủ)",
      created_at: "2026-09-28T14:20:00+07:00",
      target: { type: "purchasereceipt", code: "PR-260928-02" },
      result_ref: { model: "purchasereceipt", id: 102 },
    },
  ],
};

export async function fetchDailyAiReport(
  dateStr?: string,
  signal?: AbortSignal
): Promise<AiDailyReport> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const qs = dateStr ? `?date=${encodeURIComponent(dateStr)}` : "";

  return apiFetch<AiDailyReport>(`/api/ai/report/daily/${qs}`, {
    signal,
    mock: isMock
      ? (_req: MockRequest) => {
          return {
            status: 200,
            body: {
              ...mockDailyAiReport,
              date: dateStr || todayInVietnam(),
            },
          };
        }
      : undefined,
  });
}
