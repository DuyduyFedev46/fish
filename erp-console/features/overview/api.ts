// API module overview (S8). Endpoint: GET /api/dashboard/summary/ — BE đòi reports.view_dashboard (S6).
import { apiFetch } from "@/shared/lib/http";
import { DASHBOARD_SUMMARY_PATH, fefoOrder } from "@/shared/lib/dashboardSummary";
import { matches } from "@/shared/lib/search";
import { mockAttention, mockOverview } from "./mock";
import type { DashboardAttentionData, DashboardBatch, OverviewData, RecentOrder } from "./types";

export function getOverview(): Promise<OverviewData> {
  return apiFetch<OverviewData>(DASHBOARD_SUMMARY_PATH, {
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockOverview : undefined,
  });
}

export function getDashboardAttention(signal?: AbortSignal): Promise<DashboardAttentionData> {
  return apiFetch<DashboardAttentionData>("/api/dashboard/attention/", {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockAttention : undefined,
  });
}


/** Lọc: mã đơn, trạng thái (SR-17: bảng đơn không còn tên khách, bất biến 9). */
export function filterRecentOrders(rows: RecentOrder[], q: string): RecentOrder[] {
  return rows.filter((o) => matches(q, o.code, o.status_label));
}

/** Lọc như bản cũ: mã lô, mặt hàng, kho, trạng thái. */
export function filterBatches(rows: DashboardBatch[], q: string): DashboardBatch[] {
  return fefoOrder(rows.filter((b) => matches(q, b.batch_id, b.item, b.warehouse, b.status_label)));
}

/** Đọc 3 số liệu Gọi xác nhận từ khoá `confirmation_*` (P8b Lô 5: BE đã bỏ khoá cũ `cskh_*`, FE không đọc nữa). */
export function readConfirmationCounts(data: DashboardAttentionData): {
  queueWaiting: number | undefined;
  escalated: number | undefined;
  autoCancelBlocked: number | undefined;
} {
  return {
    queueWaiting: data.confirmation_queue_waiting,
    escalated: data.confirmation_escalated,
    autoCancelBlocked: data.confirmation_auto_cancel_blocked,
  };
}
