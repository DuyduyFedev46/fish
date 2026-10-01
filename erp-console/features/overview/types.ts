// Module overview (S8) đọc TOÀN BỘ response /api/dashboard/summary/ (contract ở shared/lib/dashboardSummary.ts).
import type { DashboardSummary } from "@/shared/lib/dashboardSummary";

export type OverviewData = DashboardSummary;
export type { DashboardBatch, ExpiryAlert, RecentOrder } from "@/shared/lib/dashboardSummary";

export type DashboardAttentionData = {
  confirmation_queue_waiting?: number;
  confirmation_escalated?: number;
  confirmation_auto_cancel_blocked?: number;
  refund_calls_open?: number;
  labels_not_printed?: number;
  labels_to_void?: number;
  /** P8 Lô 5 (BR-LO-07): số lô Quá hạn còn tồn. Chỉ có khi người xem có inventory.cancel_expired_batch (Chủ). */
  expired_batches_open?: number;
};

