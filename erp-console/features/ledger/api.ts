// API Sổ nhập xuất (R6): GET /api/inventory/ledger/ — chỉ đọc, mới nhất trước, 20 dòng/trang. Không có hàm ghi, sửa, xoá.
import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockLedgerList } from "./mock";
import type { LedgerEntry, LedgerParams } from "./types";

/** Bỏ khoá rỗng để URL ngắn; chỉ chứa mã lô, id kho, loại và ngày, không có dữ liệu cá nhân. */
export function ledgerQuery(params: Partial<LedgerParams>, page: number): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) q.set(k, v);
  if (page > 1) q.set("page", String(page));
  const text = q.toString();
  return text ? `?${text}` : "";
}

export function fetchLedger(params: Partial<LedgerParams>, page: number, signal?: AbortSignal): Promise<Paginated<LedgerEntry>> {
  return apiFetch<Paginated<LedgerEntry>>(`/api/inventory/ledger/${ledgerQuery(params, page)}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockLedgerList : undefined,
  });
}
