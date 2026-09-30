// Module inventory (S8): phần của /api/dashboard/summary/ mà màn Kho & lô và tab Hoạt động đọc.
// S25 sẽ đổi sang danh sách lô riêng (GET /api/batches/, cần inventory.view_batch).
import type { DashboardSummary } from "@/shared/lib/dashboardSummary";

export type InventoryData = Pick<DashboardSummary, "as_of" | "user" | "batches">;
export type ActivityData = Pick<DashboardSummary, "activity">;
export type { DashboardBatch as BatchRow, LedgerActivity } from "@/shared/lib/dashboardSummary";

// ---- Lô quá hạn còn tồn (P8 Lô 5, SR-15/SR-16, 02b §5.4) ----

/** Body POST /api/inventory/batches/<id>/return-to-supplier/. `qty`/`supplier_refund_amount` là chuỗi thập phân. */
export type ReturnToSupplierInput = {
  qty: string;
  supplier_refund_amount: string;
  note: string;
  /** UUID sinh khi mở form — gửi lại cùng mã (bấm đúp, mạng chập chờn) thì BE trả bản ghi cũ, không trừ tồn lần 2. */
  request_id: string;
};

/** 200 của return-to-supplier. KHÔNG có số tiền NCC hoàn (nhạy cảm) — FE cũng không hiện lại sau khi lưu. */
export type ReturnToSupplierResult = {
  batch_id: string;
  status: string;
  qty_available: string;
  returned_qty: string;
  return_id: number;
};

/** Phần FE dùng của BatchSerializer (response cancel-expired / close, dòng của GET /api/inventory/batches/). */
export type BatchApiRow = {
  id: number;
  batch_id: string;
  item: number;
  item_code: string;
  /** Khoá tên (P8 Lô 7 / L5-1) của danh sách GET /api/inventory/batches/. Thiếu ở BE cũ → FE lùi về `item_code` / bỏ trống. */
  item_name?: string;
  supplier: number;
  supplier_name?: string;
  warehouse: number;
  warehouse_name?: string;
  status_label?: string;
  received_date: string;
  expiry_date: string;
  qty_available: string;
  qty_reserved: string;
  status: string;
  /** Chỉ có khi người xem có inventory.view_costprice. */
  landed_unit_cost?: string;
};

export type BatchActionResult = Pick<BatchApiRow, "id" | "batch_id" | "status"> & { qty_available?: string };
