// Module overview (S8) đọc TOÀN BỘ response /api/dashboard/summary/ (contract ở shared/lib/dashboardSummary.ts).
import type { DashboardSummary } from "@/shared/lib/dashboardSummary";

export type OverviewData = DashboardSummary;
export type { DashboardBatch, ExpiryAlert, RecentOrder } from "@/shared/lib/dashboardSummary";
