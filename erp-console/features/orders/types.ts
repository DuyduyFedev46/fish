// Module orders (S8): phần của /api/dashboard/summary/ mà màn Đơn đọc.
// S10 sẽ đổi sang GET /api/orders/ (danh sách đầy đủ, phân trang, cần sales.view_salesorder).
import type { DashboardSummary } from "@/shared/lib/dashboardSummary";

export type OrdersData = Pick<DashboardSummary, "as_of" | "kpis" | "recent_orders">;
export type { RecentOrder as OrderRow } from "@/shared/lib/dashboardSummary";
