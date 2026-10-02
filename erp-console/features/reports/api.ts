// API Báo cáo lãi lỗ (ED-32). Chỉ Chủ (reports.view_profitreport); vai khác nhận 403 → màn "Không có quyền".
// Điều kiện mock viết thẳng tại chỗ dùng để bản build thật loại bỏ dữ liệu mẫu (check-no-mock).
import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockBatchReport, mockPeriodReport } from "./mock";
import type { BatchReportParams, BatchReportRow, PeriodReport } from "./types";

/** GET /api/reports/period/?year=&month=: doanh thu, giá vốn, hoàn tiền, lãi/lỗ của một tháng (giờ VN). */
export function fetchPeriodReport(year: number, month: number, signal?: AbortSignal): Promise<PeriodReport> {
  return apiFetch<PeriodReport>(`/api/reports/period/?year=${year}&month=${month}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockPeriodReport : undefined,
  });
}

/**
 * GET /api/reports/batches/?month=YYYY-MM&state=closed|provisional&page=: lãi/lỗ từng lô có phát sinh trong tháng
 * (nhập, bán hoặc chốt trong tháng), 20 lô/trang. BE không trả khoá số nên FE gán `id` theo thứ tự để dùng usePagedList.
 */
export async function fetchBatchReport(params: BatchReportParams, page: number, signal?: AbortSignal): Promise<Paginated<BatchReportRow>> {
  const q = new URLSearchParams();
  if (params.month) q.set("month", params.month);
  if (params.state) q.set("state", params.state);
  if (page > 1) q.set("page", String(page));
  const text = q.toString();
  const result = await apiFetch<Paginated<Omit<BatchReportRow, "id">>>(`/api/reports/batches/${text ? `?${text}` : ""}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockBatchReport : undefined,
  });
  const offset = (page - 1) * 20;
  return { ...result, results: result.results.map((r, i) => ({ ...r, id: offset + i + 1 })) };
}
