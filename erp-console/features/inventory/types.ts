// Module inventory (S8): phần của /api/dashboard/summary/ mà màn Kho & lô và tab Hoạt động đọc.
// S25 sẽ đổi sang danh sách lô riêng (GET /api/batches/, cần inventory.view_batch).
import type { DashboardSummary } from "@/shared/lib/dashboardSummary";

export type InventoryData = Pick<DashboardSummary, "as_of" | "user" | "batches">;
export type ActivityData = Pick<DashboardSummary, "activity">;
export type { DashboardBatch as BatchRow, LedgerActivity } from "@/shared/lib/dashboardSummary";
