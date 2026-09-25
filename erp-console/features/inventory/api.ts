// API module inventory (S8). Tạm đọc tồn theo lô + sổ kho từ GET /api/dashboard/summary/ (y như bản HTML cũ).
import { apiFetch } from "@/shared/lib/http";
import { DASHBOARD_SUMMARY_PATH } from "@/shared/lib/dashboardSummary";
import { matches } from "@/shared/lib/search";
import { mockInventory } from "./mock";
import type { ActivityData, BatchRow, InventoryData } from "./types";

export function getInventory(): Promise<InventoryData> {
  return apiFetch<InventoryData>(DASHBOARD_SUMMARY_PATH, {
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockInventory : undefined,
  });
}

/** 8 dòng sổ kho mới nhất cho tab "Hoạt động" (cùng request, dùng chung cache). */
export function getActivity(): Promise<ActivityData> {
  return apiFetch<ActivityData>(DASHBOARD_SUMMARY_PATH, {
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockInventory : undefined,
  });
}

/** Lọc như bản cũ: mã lô, mặt hàng, NCC, kho, trạng thái. */
export function filterBatches(rows: BatchRow[], q: string): BatchRow[] {
  return rows.filter((b) => matches(q, b.batch_id, b.item, b.supplier, b.warehouse, b.status_label));
}
