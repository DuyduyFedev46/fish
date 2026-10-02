// API module Nhà cung cấp (ED-22, Lô 11) — contract BE Lô 11 (B3): 03-dev-notes.md "Lô 11 — BE".
//   GET   /api/purchasing/suppliers/?q=&supplier_type=&is_active=&page=   (50 dòng/trang)
//   GET   /api/purchasing/suppliers/{id}/        POST /suppliers/        PATCH /suppliers/{id}/
//   GET   /api/purchasing/receipts/?supplier=<id>&page=      (R10, 20 dòng/trang)
//   GET   /api/inventory/batches/?supplier=<id>&has_stock=1  (R5)
//   GET   /api/guidance/supplier/{id}/           (chỉ dùng `timeline`)
// KHÔNG có DELETE/PUT (BE trả 405): "Ngừng hợp tác" = PATCH is_active=false, bật lại = PATCH is_active=true.
// Từ khoá và số điện thoại chỉ đi vào query/thân của request, không bao giờ vào URL trang hay storage.
// Không sửa features/purchasing/**: hàm lấy danh sách cho form Nhập lô ở đó là việc của Lô 10.

import { apiFetch, type Paginated } from "@/shared/lib/http";
import type { GuidanceData } from "@/features/guidance/types";
import { mockSuppliersApi } from "./mock";
import type { Supplier, SupplierBatchRow, SupplierInput, SupplierListParams, SupplierPatch, SupplierReceiptRow } from "./types";

const BASE = "/api/purchasing/suppliers/";

/** Chuỗi query theo đúng tên tham số contract; bỏ tham số rỗng. */
export function supplierListQuery(params: SupplierListParams, page: number): string {
  const qs = new URLSearchParams();
  if (params.q.trim()) qs.set("q", params.q.trim());
  if (params.type) qs.set("supplier_type", params.type);
  if (params.active) qs.set("is_active", params.active);
  if (page > 1) qs.set("page", String(page));
  const text = qs.toString();
  return text ? `?${text}` : "";
}

/** GET /api/purchasing/suppliers/ — 50 dòng/trang, sắp xếp tên rồi id. */
export function listSuppliers(params: SupplierListParams, page = 1, signal?: AbortSignal): Promise<Paginated<Supplier>> {
  return apiFetch<Paginated<Supplier>>(BASE + supplierListQuery(params, page), {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockSuppliersApi : undefined,
  });
}

/** GET /api/purchasing/suppliers/{id}/ — cùng shape dòng danh sách, không kèm phiếu hay lô. */
export function getSupplier(id: number, signal?: AbortSignal): Promise<Supplier> {
  return apiFetch<Supplier>(`${BASE}${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockSuppliersApi : undefined,
  });
}

/** POST /api/purchasing/suppliers/ → 201. Tên trùng: 400 `{name:[…]}` hoặc `{detail, code:"SUPPLIER_NAME_TAKEN"}`. */
export function createSupplier(input: SupplierInput): Promise<Supplier> {
  return apiFetch<Supplier>(BASE, {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockSuppliersApi : undefined,
  });
}

/** PATCH /api/purchasing/suppliers/{id}/ — chỉ trường đổi. Các số tính toán (phiếu, tổng tiền) là chỉ đọc. Trả thân mới. */
export function updateSupplier(id: number, patch: SupplierPatch): Promise<Supplier> {
  return apiFetch<Supplier>(`${BASE}${id}/`, {
    method: "PATCH",
    body: patch,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockSuppliersApi : undefined,
  });
}

/** Ngừng hợp tác / bật lại: cùng một PATCH, chỉ đổi `is_active`. */
export function setSupplierActive(id: number, active: boolean): Promise<Supplier> {
  return updateSupplier(id, { is_active: active });
}

/** GET /api/purchasing/receipts/?supplier=<id>&page= (R10, cần purchasing.view_purchasereceipt). 20 dòng/trang, mới nhất trước. */
export function listSupplierReceipts(supplierId: number, page = 1, signal?: AbortSignal): Promise<Paginated<SupplierReceiptRow>> {
  const qs = new URLSearchParams({ supplier: String(supplierId) });
  if (page > 1) qs.set("page", String(page));
  return apiFetch<Paginated<SupplierReceiptRow>>(`/api/purchasing/receipts/?${qs.toString()}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockSuppliersApi : undefined,
  });
}

/** GET /api/inventory/batches/?supplier=<id>&has_stock=1 (R5, cần inventory.view_batch). Chỉ trang đầu (50 lô). */
export function listSupplierBatches(supplierId: number, signal?: AbortSignal): Promise<Paginated<SupplierBatchRow>> {
  return apiFetch<Paginated<SupplierBatchRow>>(`/api/inventory/batches/?supplier=${supplierId}&has_stock=1`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockSuppliersApi : undefined,
  });
}

/** GET /api/guidance/supplier/{id}/ — dòng thời gian của nhà cung cấp (cùng quyền xem). Chỉ dùng `timeline`. */
export function getSupplierTimeline(id: number, signal?: AbortSignal): Promise<GuidanceData> {
  return apiFetch<GuidanceData>(`/api/guidance/supplier/${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockSuppliersApi : undefined,
  });
}
