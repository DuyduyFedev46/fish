// API module Khách hàng (ED-14) — contract BE Lô 6 (B2): 03-dev-notes.md "Lô 6 — BE (B2)".
// Danh bạ cần sales.view_customer_list (Chủ + Quản lý mặc định); sửa cần thêm sales.change_customer.
// KHÔNG gọi /api/sales/customers/ (endpoint cũ của CS-01, giữ nguyên cho luồng khác).
// Mọi tham số tìm kiếm đi vào query của request, không bao giờ vào URL trang hay storage.

import { apiFetch, type Paginated } from "@/shared/lib/http";
import type { GuidanceData } from "@/features/guidance/types";
import { mockCustomersApi, mockCustomerTimelineApi } from "./mock";
import type { CustomerDetail, CustomerListItem, CustomerListParams, CustomerPatch } from "./types";

const BASE = "/api/sales/customer-directory/";

/** Chuỗi query theo đúng tên tham số contract; bỏ tham số rỗng (mặc định `ordering` vẫn gửi để thứ tự không phụ thuộc BE). */
export function customerListQuery(params: CustomerListParams, page: number): string {
  const qs = new URLSearchParams();
  if (params.q.trim()) qs.set("q", params.q.trim());
  qs.set("ordering", params.ordering);
  if (page > 1) qs.set("page", String(page));
  return `?${qs.toString()}`;
}

/** GET /api/sales/customer-directory/?q=&ordering=&page= — 20 dòng/trang. */
export function listCustomers(params: CustomerListParams, page = 1, signal?: AbortSignal): Promise<Paginated<CustomerListItem>> {
  return apiFetch<Paginated<CustomerListItem>>(BASE + customerListQuery(params, page), {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockCustomersApi : undefined,
  });
}

/** GET /api/sales/customer-directory/{id}/ */
export function getCustomer(id: number, signal?: AbortSignal): Promise<CustomerDetail> {
  return apiFetch<CustomerDetail>(`${BASE}${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockCustomersApi : undefined,
  });
}

/**
 * PATCH /api/sales/customer-directory/{id}/ — chỉ `name`, `default_address`, `note` (chuỗi).
 * Gửi thêm khoá khác (kể cả `phone`) BE trả 400 INPUT_NOT_ALLOWED; hàm này không nhận khoá nào khác. Trả thân chi tiết mới.
 */
export function updateCustomer(id: number, patch: CustomerPatch): Promise<CustomerDetail> {
  return apiFetch<CustomerDetail>(`${BASE}${id}/`, {
    method: "PATCH",
    body: patch,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockCustomersApi : undefined,
  });
}

/** GET /api/guidance/customer/{id}/ — dòng thời gian của khách (cùng quyền xem danh bạ). Chỉ dùng `timeline`. */
export function getCustomerTimeline(id: number, signal?: AbortSignal): Promise<GuidanceData> {
  return apiFetch<GuidanceData>(`/api/guidance/customer/${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockCustomerTimelineApi : undefined,
  });
}
