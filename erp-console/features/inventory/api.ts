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

/** Nhãn trạng thái lô (BE `get_status_display`); danh sách GET /api/inventory/batches/ không kèm `status_label`. */
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
 * GET /api/inventory/batches/?status=… — DANH SÁCH PHÂN TRANG DRF ({count,next,previous,results}), chỉ lấy trang đầu (50 dòng).
 * BatchSerializer trả `item`/`supplier`/`warehouse` là id (không có tên) nên mặt hàng hiện bằng `item_code`, cột NCC/Kho bỏ.
 * Lô EXPIRED chỉ giữ lô còn tồn (khớp con số ở thẻ Cần chú ý `expired_batches_open`).
 */
export async function getBatchesByStatus(
  status: string,
  viewer: { username: string; can_cost: boolean }
): Promise<InventoryData> {
  const res = await apiFetch<Paginated<BatchApiRow>>(`/api/inventory/batches/?status=${encodeURIComponent(status)}`, {
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockBatchList : undefined,
  });
  const batches: BatchRow[] = res.results
    .filter((b) => status !== "EXPIRED" || Number(b.qty_available) > 0)
    .map((b) => {
      const row: BatchRow = {
        batch_id: b.batch_id,
        item: b.item_code,
        warehouse: "",
        supplier: "",
        qty_available: Number(b.qty_available),
        qty_reserved: Number(b.qty_reserved),
        received_date: b.received_date,
        expiry_date: b.expiry_date,
        status: b.status as BatchStatus,
        status_label: batchStatusLabel(b.status),
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
