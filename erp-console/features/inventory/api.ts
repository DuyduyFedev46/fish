// API module inventory (S8). Tạm đọc tồn theo lô + sổ kho từ GET /api/dashboard/summary/ (y như bản HTML cũ).
// P8 Lô 5: lô Quá hạn còn tồn (SR-15/SR-16) — danh sách lọc theo trạng thái + Đã huỷ phần tồn / Đã trả NCC / Chốt lô.
import { apiFetch, type Paginated } from "@/shared/lib/http";
import { DASHBOARD_SUMMARY_PATH, fefoOrder, type BatchStatus } from "@/shared/lib/dashboardSummary";
import { matches } from "@/shared/lib/search";
import {
  mockBatchAction,
  mockBatchList,
  mockInventory,
  mockReturnToSupplier,
} from "./mock";
import type {
  ActivityData,
  BatchActionResult,
  BatchApiRow,
  BatchRow,
  InventoryData,
  ReturnToSupplierInput,
  ReturnToSupplierResult,
} from "./types";


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
  return fefoOrder(rows.filter((b) => matches(q, b.batch_id, b.item, b.supplier, b.warehouse, b.status_label)));
}

// ---- Danh sách lô lọc theo trạng thái (link từ thẻ "Lô quá hạn còn tồn" ở Tổng quan) ----

/** Nhãn trạng thái lô dự phòng (BE `get_status_display`) khi response không kèm `status_label`; cũng dùng cho tiêu đề chế độ lọc. */
const BATCH_STATUS_LABEL: Record<string, string> = {
  DRAFT: "Nháp",
  SELLING: "Đang bán",
  NEAR_EXPIRY: "Cận hạn",
  SOLD_OUT: "Hết hàng",
  EXPIRED: "Quá hạn",
  CANCELLED: "Đã huỷ",
  CLOSED: "Đã chốt",
};

export function batchStatusLabel(status: string): string {
  return BATCH_STATUS_LABEL[status] || status;
}

export function batchesByStatusKey(userId: number, status: string): string {
  return `GET /api/inventory/batches/?status=${status}#${userId}`;
}

/**
 * GET /api/inventory/batches/?status=…[&has_stock=1] — DANH SÁCH PHÂN TRANG DRF ({count,next,previous,results}), chỉ lấy trang đầu (50 dòng).
 * BE trả sẵn `item_name`, `supplier_name`, `warehouse_name`, `status_label` (P8 Lô 7 / L5-1) nên bảng hiện đủ cột NCC/Kho.
 * Lô EXPIRED lọc còn tồn ngay ở BE bằng `has_stock=1` (khớp con số ở thẻ Cần chú ý `expired_batches_open`), FE không lọc lại.
 */
export async function getBatchesByStatus(
  status: string,
  viewer: { username: string; can_cost: boolean }
): Promise<InventoryData> {
  const qs = `status=${encodeURIComponent(status)}${status === "EXPIRED" ? "&has_stock=1" : ""}`;
  const res = await apiFetch<Paginated<BatchApiRow>>(`/api/inventory/batches/?${qs}`, {
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockBatchList : undefined,
  });
  const batches: BatchRow[] = res.results
    .map((b) => {
      const row: BatchRow = {
        batch_id: b.batch_id,
        item: b.item_name || b.item_code,
        warehouse: b.warehouse_name ?? "",
        supplier: b.supplier_name ?? "",
        qty_available: Number(b.qty_available),
        qty_reserved: Number(b.qty_reserved),
        received_date: b.received_date,
        expiry_date: b.expiry_date,
        status: b.status as BatchStatus,
        status_label: b.status_label || batchStatusLabel(b.status),
        near_expiry: false,
      };
      if (viewer.can_cost && b.landed_unit_cost != null) row.unit_cost = Number(b.landed_unit_cost);
      return row;
    });
  return { as_of: new Date().toISOString(), user: viewer, batches };
}

// ---- Thao tác lô quá hạn (chỉ Chủ: inventory.cancel_expired_batch) ----

/** Số kg → chuỗi thập phân 3 chữ số ("5" → "5.000") để gửi BE. */
export function decimalKg(n: number | string): string {
  return Number(n).toFixed(3);
}

/**
 * Xác nhận Đã huỷ phần tồn (DW-06 / BR-LO-03 / BR-LO-07) — WRITE_OFF toàn bộ tồn, ghi lỗ, lô → CANCELLED.
 * `confirmQty` = tồn ĐANG HIỂN THỊ: khác tồn thật → 400 BR-LO-07 "Tồn đã đổi (x kg) — tải lại." (SR-15-AC5).
 */
export function cancelExpiredBatch(batchId: number | string, confirmQty?: number | string): Promise<BatchActionResult> {
  return apiFetch<BatchActionResult>(`/api/inventory/batches/${batchId}/cancel-expired/`, {
    method: "POST",
    body: confirmQty === undefined ? undefined : { confirm_qty: decimalKg(confirmQty) },
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockBatchAction("cancel-expired", batchId, req) : undefined,
  });
}

/** Xác nhận Đã trả NCC (BR-MH-08, SR-16): xuất kho SUPPLIER_RETURN, lô vẫn EXPIRED. 400 → `ApiError.message` = `detail`. */
export function returnToSupplier(batchId: number | string, input: ReturnToSupplierInput): Promise<ReturnToSupplierResult> {
  return apiFetch<ReturnToSupplierResult>(`/api/inventory/batches/${batchId}/return-to-supplier/`, {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockReturnToSupplier(batchId, req) : undefined,
  });
}

/** Chốt lô (BR-LO-04): cần tồn = 0. */
export function closeBatch(batchId: number | string): Promise<BatchActionResult> {
  return apiFetch<BatchActionResult>(`/api/inventory/batches/${batchId}/close/`, {
    method: "POST",
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockBatchAction("close", batchId, req) : undefined,
  });
}
