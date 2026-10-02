// Lớp gọi API Kiểm kê (ED-28). Contract thật: backend/apps/inventory/stocktake/api.py.
//   GET  /api/inventory/reconciliations/?status=&warehouse=&page=   danh sách (phân trang DRF)
//   GET  /api/inventory/reconciliations/<id>/                       chi tiết (kèm `lines`, `available_actions`, `approve_blocked_reason`)
//   POST /api/inventory/reconciliations/                            lập phiếu {count_date, note, lines?}
//   PATCH /api/inventory/reconciliations/<id>/                      sửa ngày / ghi chú
//   POST /api/inventory/reconciliations/<id>/lines/                 thay TOÀN BỘ dòng {expected_updated_at, lines} (409 STALE_STATE khi lệch)
//   POST /api/inventory/reconciliations/<id>/submit/                gửi duyệt (Nháp → Chờ duyệt; phiếu rỗng 400 RECON_EMPTY)
//   POST /api/inventory/reconciliations/<id>/return-to-draft/       trả về nháp (Chờ duyệt → Nháp)
//   POST /api/inventory/reconciliations/<id>/approve/               duyệt và cân đối tồn (chỉ phiếu Chờ duyệt; không còn chặn người nhập số tự duyệt)
// Mỗi hàm nối mock qua `process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined` ghi thẳng tại chỗ
// (ghi qua biến trung gian sẽ làm mock lọt vào bản build thật; scripts/check-no-mock.mjs bắt lỗi này).
import type { GuidanceData } from "@/features/guidance/types";
import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockStocktakeApi } from "./mock";
import type {
  BatchOption,
  StocktakeCreateInput,
  StocktakeDetail,
  StocktakeLineInput,
  StocktakeListItem,
  WarehouseOption,
} from "./types";

const BASE = "/api/inventory/reconciliations/";
/** Chặn vòng lặp tải lô: 20 trang × 50 dòng; BE cũng giới hạn 500 dòng mỗi phiếu. */
const MAX_BATCH_PAGES = 20;

export function fetchStocktakes(
  params: { status?: string; warehouse?: string; page?: number },
  signal?: AbortSignal,
): Promise<Paginated<StocktakeListItem>> {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  if (params.warehouse) q.set("warehouse", params.warehouse);
  if (params.page && params.page > 1) q.set("page", String(params.page));
  const qs = q.toString();
  return apiFetch<Paginated<StocktakeListItem>>(`${BASE}${qs ? `?${qs}` : ""}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined,
  });
}

export function fetchStocktake(id: number, signal?: AbortSignal): Promise<StocktakeDetail> {
  return apiFetch<StocktakeDetail>(`${BASE}${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined,
  });
}

export function createStocktake(input: StocktakeCreateInput): Promise<StocktakeDetail> {
  return apiFetch<StocktakeDetail>(BASE, {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined,
  });
}

/** Sửa ngày kiểm kê / ghi chú của phiếu chờ duyệt. Dòng số đếm KHÔNG sửa ở đây (BE trả 400 RECON_USE_LINES_ENDPOINT). */
export function updateStocktakeHeader(id: number, changes: { count_date?: string; note?: string }): Promise<StocktakeDetail> {
  return apiFetch<StocktakeDetail>(`${BASE}${id}/`, {
    method: "PATCH",
    body: changes,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined,
  });
}

/** Thay toàn bộ dòng. `expectedUpdatedAt` = `updated_at` đang giữ; lệch → 409 STALE_STATE (kèm updated_at, updated_by_name). */
export function replaceStocktakeLines(id: number, expectedUpdatedAt: string, lines: StocktakeLineInput[]): Promise<StocktakeDetail> {
  return apiFetch<StocktakeDetail>(`${BASE}${id}/lines/`, {
    method: "POST",
    body: { expected_updated_at: expectedUpdatedAt, lines },
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined,
  });
}

/** Gửi duyệt: Nháp → Chờ duyệt. Từ đó không sửa số đếm được, chỉ duyệt hoặc trả về nháp. */
export function submitStocktake(id: number): Promise<StocktakeDetail> {
  return apiFetch<StocktakeDetail>(`${BASE}${id}/submit/`, {
    method: "POST",
    body: {},
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined,
  });
}

/** Trả phiếu Chờ duyệt về Nháp để sửa số đếm. Phiếu không ở Chờ duyệt → 400 RECON_NOT_SUBMITTED. */
export function returnStocktakeToDraft(id: number): Promise<StocktakeDetail> {
  return apiFetch<StocktakeDetail>(`${BASE}${id}/return-to-draft/`, {
    method: "POST",
    body: {},
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined,
  });
}

export function approveStocktake(id: number): Promise<StocktakeDetail> {
  return apiFetch<StocktakeDetail>(`${BASE}${id}/approve/`, {
    method: "POST",
    body: {},
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined,
  });
}

/** Dòng thời gian của phiếu: guidance loại `stocktake` (R2, chỉ có dòng thời gian). */
export function fetchStocktakeTimeline(id: number, signal?: AbortSignal): Promise<GuidanceData> {
  return apiFetch<GuidanceData>(`/api/guidance/stocktake/${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined,
  });
}

type WarehouseRow = { id: number; name: string; is_group?: boolean };

/** Kho để chọn. Bỏ "nhóm kho" (không chứa lô trực tiếp). */
export async function fetchWarehouses(signal?: AbortSignal): Promise<WarehouseOption[]> {
  const res = await apiFetch<Paginated<WarehouseRow> | WarehouseRow[]>("/api/inventory/warehouses/", {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined,
  });
  const rows = Array.isArray(res) ? res : res.results;
  return rows.filter((w) => !w.is_group).map((w) => ({ id: w.id, name: w.name }));
}

type BatchRow = {
  id: number;
  batch_id: string;
  item_name?: string;
  item_code?: string;
  warehouse: number;
  warehouse_name?: string;
  qty_available: string;
};

/**
 * Lô còn tồn của một kho (`?warehouse=&has_stock=1`), đi hết các trang. Kho chỉ là bộ lọc: phiếu kiểm kê tính theo LÔ.
 * Chỉ giữ các trường kg; KHÔNG đọc giá vốn dù BE có trả cho Chủ.
 */
export async function fetchStockBatches(warehouseId: number, signal?: AbortSignal): Promise<BatchOption[]> {
  const out: BatchOption[] = [];
  for (let page = 1; page <= MAX_BATCH_PAGES; page++) {
    const res = await apiFetch<Paginated<BatchRow>>(
      `/api/inventory/batches/?warehouse=${warehouseId}&has_stock=1${page > 1 ? `&page=${page}` : ""}`,
      { signal, mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStocktakeApi : undefined },
    );
    for (const b of res.results) {
      out.push({
        id: b.id,
        batch_id: b.batch_id,
        item_name: b.item_name || b.item_code || "",
        warehouse: b.warehouse,
        warehouse_name: b.warehouse_name ?? "",
        qty_available: b.qty_available,
      });
    }
    if (!res.next) break;
  }
  return out;
}
