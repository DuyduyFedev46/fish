// API module overview (S8). Endpoint: GET /api/dashboard/summary/ — BE đòi reports.view_dashboard (S6).
import { apiFetch } from "@/shared/lib/http";
import { DASHBOARD_SUMMARY_PATH, fefoOrder } from "@/shared/lib/dashboardSummary";
import { matches } from "@/shared/lib/search";
import { mockOverview } from "./mock";
import type { DashboardBatch, OverviewData, RecentOrder } from "./types";

export function getOverview(): Promise<OverviewData> {
  return apiFetch<OverviewData>(DASHBOARD_SUMMARY_PATH, {
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockOverview : undefined,
  });
}

/** Lọc như bản cũ: mã đơn, khách, trạng thái. */
export function filterRecentOrders(rows: RecentOrder[], q: string): RecentOrder[] {
  return rows.filter((o) => matches(q, o.code, o.customer, o.status_label));
}

/** Lọc như bản cũ: mã lô, mặt hàng, kho, trạng thái. */
export function filterBatches(rows: DashboardBatch[], q: string): DashboardBatch[] {
  return fefoOrder(rows.filter((b) => matches(q, b.batch_id, b.item, b.warehouse, b.status_label)));
}
