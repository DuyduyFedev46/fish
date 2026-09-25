// API module orders (S8). Tạm đọc 8 đơn gần nhất từ GET /api/dashboard/summary/ (y như bản HTML cũ).
import { apiFetch } from "@/shared/lib/http";
import { DASHBOARD_SUMMARY_PATH } from "@/shared/lib/dashboardSummary";
import { matches } from "@/shared/lib/search";
import { mockOrders } from "./mock";
import type { OrderRow, OrdersData } from "./types";

export function getOrders(): Promise<OrdersData> {
  return apiFetch<OrdersData>(DASHBOARD_SUMMARY_PATH, {
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockOrders : undefined,
  });
}

/** Lọc như bản cũ: mã đơn, khách, trạng thái, 4 số cuối SĐT. */
export function filterOrders(rows: OrderRow[], q: string): OrderRow[] {
  return rows.filter((o) => matches(q, o.code, o.customer, o.status_label, o.phone_last4));
}
