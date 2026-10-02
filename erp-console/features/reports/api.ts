// API Báo cáo lãi lỗ (ED-32). Chỉ Chủ (reports.view_profitreport); vai khác nhận 403 → màn "Không có quyền".
// Điều kiện mock viết thẳng tại chỗ dùng để bản build thật loại bỏ dữ liệu mẫu (check-no-mock).
import { apiFetch, type Paginated } from "@/shared/lib/http";
import { toDecimalString } from "./decimal";
import { mockBatchReport, mockPeriodReport } from "./mock";
import type { BatchReportParams, BatchReportRow, PeriodReport } from "./types";

// BE trả tiền và kg của hai endpoint báo cáo dạng JSON number (DRF đổi Decimal thành float). Cả app giữ chúng dạng
// chuỗi thập phân (cộng trừ bằng BigInt), nên chuẩn hoá ngay ở đây; nhận cả number lẫn string.
const PERIOD_DECIMAL_FIELDS = ["revenue", "cogs", "credit_notes", "cogs_reversed", "refunds", "profit"] as const;
const BATCH_DECIMAL_FIELDS = [
  "qty_received", "qty_sold", "landed_unit_cost", "revenue", "reversed_qty", "reversed_revenue", "purchase_cost", "allocated_cost",
  "shrinkage_qty", "shrinkage_cost", "damage_qty", "damage_cost", "expired_qty", "expired_cost", "supplier_return_qty",
  "supplier_refund_amount", "total_cost", "profit",
] as const;

function withDecimalStrings<T extends object>(raw: unknown, fields: readonly (keyof T)[]): T {
  const out = { ...(raw as T) };
  for (const f of fields) out[f] = toDecimalString(out[f] as string | number | null | undefined) as T[keyof T];
  return out;
}

export const normalizePeriodReport = (raw: unknown): PeriodReport => withDecimalStrings<PeriodReport>(raw, PERIOD_DECIMAL_FIELDS);
export const normalizeBatchRow = (raw: unknown): Omit<BatchReportRow, "id"> =>
  withDecimalStrings<Omit<BatchReportRow, "id">>(raw, BATCH_DECIMAL_FIELDS);

/** GET /api/reports/period/?year=&month=: doanh thu, giá vốn, hoàn tiền, lãi/lỗ của một tháng (giờ VN). */
export function fetchPeriodReport(year: number, month: number, signal?: AbortSignal): Promise<PeriodReport> {
  return apiFetch<unknown>(`/api/reports/period/?year=${year}&month=${month}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockPeriodReport : undefined,
  }).then(normalizePeriodReport);
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
  const result = await apiFetch<Paginated<unknown>>(`/api/reports/batches/${text ? `?${text}` : ""}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockBatchReport : undefined,
  });
  const offset = (page - 1) * 20;
  return { ...result, results: result.results.map((r, i) => ({ ...normalizeBatchRow(r), id: offset + i + 1 })) };
}
