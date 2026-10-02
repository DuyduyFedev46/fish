import { apiFetch, type Paginated } from "@/shared/lib/http";
import type { GuidanceData } from "@/features/guidance/types";
import {
  mockCancelPurchaseReceipt,
  mockListSuppliers,
  mockReceiptDetail,
  mockReceiptGuidance,
  mockReceiptList,
  mockSubmitReceipt,
  mockSubmitReceiveBatches,
} from "./mock";
import type {
  CancelPurchaseReceiptResponse,
  ReceiptDetail,
  ReceiptListParams,
  ReceiptRow,
  ReceiveBatchesPayload,
  ReceiveBatchesResponse,
  SubmitReceiptResponse,
  Supplier,
} from "./types";

// Điều kiện mock viết thẳng tại mỗi lời gọi để bản build thật loại bỏ dữ liệu mẫu (check-no-mock).

/** Danh sách nhà cung cấp (50 dòng/trang), gom hết các trang để ô chọn không bị cụt. */
export async function fetchSuppliers(signal?: AbortSignal): Promise<Supplier[]> {
  const all: Supplier[] = [];
  for (let page = 1; page <= 20; page += 1) {
    const res = await apiFetch<Paginated<Supplier>>(`/api/purchasing/suppliers/${page > 1 ? `?page=${page}` : ""}`, {
      signal,
      mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockListSuppliers : undefined,
    });
    all.push(...(res.results || []));
    if (!res.next) break;
  }
  return all;
}

export async function submitReceiveBatches(
  payload: ReceiveBatchesPayload,
  signal?: AbortSignal
): Promise<ReceiveBatchesResponse> {
  return apiFetch<ReceiveBatchesResponse>("/api/purchasing/receipts/receive-batches/", {
    method: "POST",
    body: payload,
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockSubmitReceiveBatches : undefined,
  });
}

export async function cancelPurchaseReceipt(
  receiptId: number,
  signal?: AbortSignal
): Promise<CancelPurchaseReceiptResponse> {
  return apiFetch<CancelPurchaseReceiptResponse>(`/api/purchasing/receipts/${receiptId}/cancel/`, {
    method: "POST",
    body: {},
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockCancelPurchaseReceipt : undefined,
  });
}

function receiptQuery(params: ReceiptListParams, page: number): string {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  if (params.supplier) q.set("supplier", params.supplier);
  if (params.date_from) q.set("date_from", params.date_from);
  if (params.date_to) q.set("date_to", params.date_to);
  if (params.has_invoice) q.set("has_invoice", params.has_invoice);
  if (page > 1) q.set("page", String(page));
  const text = q.toString();
  return text ? `?${text}` : "";
}

/** GET /api/purchasing/receipts/ (R10): 20 phiếu/trang. `purchase_amount` chỉ có khi người xem có view_costprice. */
export function fetchReceipts(params: ReceiptListParams, page: number, signal?: AbortSignal): Promise<Paginated<ReceiptRow>> {
  return apiFetch<Paginated<ReceiptRow>>(`/api/purchasing/receipts/${receiptQuery(params, page)}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockReceiptList : undefined,
  });
}

/** GET /api/purchasing/receipts/{id}/ (R10): dòng nhập, hoá đơn (theo quyền), chi phí phụ (chỉ Chủ). */
export function fetchReceipt(id: number, signal?: AbortSignal): Promise<ReceiptDetail> {
  return apiFetch<ReceiptDetail>(`/api/purchasing/receipts/${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockReceiptDetail : undefined,
  });
}

/** POST /api/purchasing/receipts/{id}/submit/: ghi nhận phiếu Nháp, sinh lô. */
export function submitReceipt(id: number): Promise<SubmitReceiptResponse> {
  return apiFetch<SubmitReceiptResponse>(`/api/purchasing/receipts/${id}/submit/`, {
    method: "POST",
    body: {},
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockSubmitReceipt : undefined,
  });
}

/** GET /api/guidance/receipt/{id}/: chỉ có dòng thời gian (không có trạng thái, không có bước tiếp theo). */
export function fetchReceiptGuidance(id: number, signal?: AbortSignal): Promise<GuidanceData> {
  return apiFetch<GuidanceData>(`/api/guidance/receipt/${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockReceiptGuidance : undefined,
  });
}
