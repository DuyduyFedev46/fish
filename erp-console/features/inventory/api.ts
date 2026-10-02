// API module inventory (Lô 7). Danh sách lô đọc từ R5 (GET /api/inventory/batches/), không còn đọc tạm dashboard/summary.
// Thao tác lô: mở bán (F1e), trả nhà cung cấp (F1g), huỷ phần tồn ghi lỗ (F1h), chốt lô (F1i).
import { apiFetch, type Paginated } from "@/shared/lib/http";
import {
  mockAddWarehouse,
  mockBatchAction,
  mockBatchDetail,
  mockBatchList,
  mockBatchProfit,
  mockOrdersByBatch,
  mockReturnToSupplier,
  mockStockEntries,
  mockWarehouses,
} from "./mock";
import type {
  BatchActionResult,
  BatchApiRow,
  BatchListParams,
  BatchProfitReport,
  OrderUsingBatch,
  ReturnToSupplierInput,
  ReturnToSupplierResult,
  StockEntry,
  StockEntryParams,
  Warehouse,
  WarehouseInput,
} from "./types";

// Điều kiện phải viết thẳng tại chỗ dùng để bản build thật loại bỏ dữ liệu mẫu (check-no-mock).
function query(entries: Record<string, string | number | boolean | undefined>, page = 1): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(entries)) if (v !== undefined && v !== "" && v !== false) q.set(k, v === true ? "1" : String(v));
  if (page > 1) q.set("page", String(page));
  const text = q.toString();
  return text ? `?${text}` : "";
}

// ---- Danh sách và chi tiết lô ----

/** Nhãn trạng thái lô khi lọc (khớp ENUMS.batchStatus). */
export function batchesPath(params: BatchListParams, page: number): string {
  return `/api/inventory/batches/${query({ status: params.status, warehouse: params.warehouse, has_stock: params.has_stock }, page)}`;
}

/** GET /api/inventory/batches/ (R5): 50 dòng/trang, thứ tự xuất theo hạn dùng sớm nhất. Không có tham số `search`. */
export function fetchBatches(params: BatchListParams, page: number, signal?: AbortSignal): Promise<Paginated<BatchApiRow>> {
  return apiFetch<Paginated<BatchApiRow>>(batchesPath(params, page), { signal, mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockBatchList : undefined });
}

/** Mọi lô (tối đa `maxPages` trang) để đổ ô chọn lô ở Sổ nhập xuất. */
export async function fetchBatchOptions(maxPages = 4): Promise<BatchApiRow[]> {
  const out: BatchApiRow[] = [];
  for (let page = 1; page <= maxPages; page += 1) {
    const res = await fetchBatches({ status: "", warehouse: "", has_stock: false }, page);
    out.push(...res.results);
    if (!res.next) break;
  }
  return out;
}

/** GET /api/inventory/batches/<id hoặc mã lô>/. 404 = không có lô; 403 = thiếu quyền. */
export function fetchBatch(idOrCode: number | string, signal?: AbortSignal): Promise<BatchApiRow> {
  return apiFetch<BatchApiRow>(`/api/inventory/batches/${encodeURIComponent(String(idOrCode))}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockBatchDetail : undefined,
  });
}

/** GET /api/sales/orders/?batch=<id lô> (R3). Chỉ đọc trang đầu: màn hiện "x / tổng" và nói rõ khi còn nữa. */
export function fetchOrdersByBatch(batchId: number, signal?: AbortSignal): Promise<Paginated<OrderUsingBatch>> {
  return apiFetch<Paginated<OrderUsingBatch>>(`/api/sales/orders/?batch=${batchId}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockOrdersByBatch : undefined,
  });
}

/** GET /api/reports/batch/<mã lô>/: lãi lỗ lô. CHỈ gọi khi người xem có reports.view_profitreport. */
export function fetchBatchProfit(batchCode: string, signal?: AbortSignal): Promise<BatchProfitReport> {
  return apiFetch<BatchProfitReport>(`/api/reports/batch/${encodeURIComponent(batchCode)}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockBatchProfit : undefined,
  });
}

// ---- Thao tác lô ----

/** Số kg → chuỗi thập phân 3 chữ số ("5" → "5.000") để gửi máy chủ. */
export function decimalKg(n: number | string): string {
  return Number(n).toFixed(3);
}

/** F1e Mở bán lô: lô Nháp → Đang bán. Sai trạng thái → 400 BR-MH-05. */
export function publishBatch(batchId: number | string): Promise<BatchActionResult> {
  return apiFetch<BatchActionResult>(`/api/inventory/batches/${batchId}/publish/`, {
    method: "POST",
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockBatchAction("publish", batchId, req) : undefined,
  });
}

/**
 * F1h Huỷ phần tồn, ghi lỗ (BR-LO-03, BR-LO-07): xuất huỷ toàn bộ tồn, lô → Đã huỷ.
 * `confirmQty` = tồn ĐANG HIỂN THỊ: khác tồn thật → 400 BR-LO-07 "Tồn đã đổi (x kg) — tải lại.".
 */
export function cancelExpiredBatch(batchId: number | string, confirmQty?: number | string): Promise<BatchActionResult> {
  return apiFetch<BatchActionResult>(`/api/inventory/batches/${batchId}/cancel-expired/`, {
    method: "POST",
    body: confirmQty === undefined ? undefined : { confirm_qty: decimalKg(confirmQty) },
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockBatchAction("cancel-expired", batchId, req) : undefined,
  });
}

/** F1g Trả nhà cung cấp (BR-MH-08, SR-16): xuất kho SUPPLIER_RETURN, lô vẫn Quá hạn. 400 → `ApiError.message` = `detail`. */
export function returnToSupplier(batchId: number | string, input: ReturnToSupplierInput): Promise<ReturnToSupplierResult> {
  return apiFetch<ReturnToSupplierResult>(`/api/inventory/batches/${batchId}/return-to-supplier/`, {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockReturnToSupplier(batchId, req) : undefined,
  });
}

/** F1i Chốt lô (BR-LO-04): cần tồn = 0. */
export function closeBatch(batchId: number | string): Promise<BatchActionResult> {
  return apiFetch<BatchActionResult>(`/api/inventory/batches/${batchId}/close/`, {
    method: "POST",
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockBatchAction("close", batchId, req) : undefined,
  });
}

// ---- Kho (R7) và phiếu điều chỉnh tồn (R7b, chỉ đọc) ----

/** GET /api/inventory/warehouses/ (R7): 50 dòng/trang, theo tên. */
export function fetchWarehouses(page: number, signal?: AbortSignal): Promise<Paginated<Warehouse>> {
  return apiFetch<Paginated<Warehouse>>(`/api/inventory/warehouses/${query({}, page)}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockWarehouses : undefined,
  });
}

/** Mọi kho (số kho rất ít) để đổ ô chọn kho; tối đa 4 trang. */
export async function fetchAllWarehouses(): Promise<Warehouse[]> {
  const out: Warehouse[] = [];
  for (let page = 1; page <= 4; page += 1) {
    const res = await fetchWarehouses(page);
    out.push(...res.results);
    if (!res.next) break;
  }
  return out;
}

/** F3m Thêm kho — chỉ Chủ (inventory.add_warehouse). Lỗi: WAREHOUSE_NAME_REQUIRED / _TOO_LONG / _TAKEN, thông điệp nằm ở `ApiError.message`. */
export function addWarehouse(input: WarehouseInput): Promise<Warehouse> {
  return apiFetch<Warehouse>("/api/inventory/warehouses/", {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockAddWarehouse : undefined,
  });
}

/** GET /api/inventory/stock-entries/ (R7b): phiếu điều chỉnh tồn. CHỈ ĐỌC, không có hàm tạo (D-1). */
export function fetchStockEntries(params: StockEntryParams, page: number, signal?: AbortSignal): Promise<Paginated<StockEntry>> {
  return apiFetch<Paginated<StockEntry>>(`/api/inventory/stock-entries/${query({ ...params }, page)}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStockEntries : undefined,
  });
}
