// Module overview (S8) đọc TOÀN BỘ response /api/dashboard/summary/ (contract ở shared/lib/dashboardSummary.ts).
import type { DashboardSummary } from "@/shared/lib/dashboardSummary";

export type OverviewData = DashboardSummary;
export type { DashboardBatch, ExpiryAlert, RecentOrder } from "@/shared/lib/dashboardSummary";

export type DashboardAttentionData = {
  cskh_queue_waiting?: number;
  cskh_escalated?: number;
  cskh_auto_cancel_blocked?: number;
  refund_calls_open?: number;
  labels_not_printed?: number;
  labels_to_void?: number;
};

