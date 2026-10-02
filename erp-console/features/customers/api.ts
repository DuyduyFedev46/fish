// API module Khách hàng (ED-14) — contract BE Lô 6 (B2): 03-dev-notes.md "Lô 6 — BE (B2)".
// Danh bạ cần sales.view_customer_list (Chủ + Quản lý mặc định); sửa cần thêm sales.change_customer.
// KHÔNG gọi /api/sales/customers/ (endpoint cũ của CS-01, giữ nguyên cho luồng khác).
// Từ khoá tìm (tên, số điện thoại) đi trong BODY của POST .../search/, không nằm trong URL hay log truy cập (Lô bổ sung A #11).

import { apiFetch, type Paginated } from "@/shared/lib/http";
import type { GuidanceData } from "@/features/guidance/types";
import { mockCustomersApi, mockCustomerTimelineApi } from "./mock";
import type { CustomerDetail, CustomerListItem, CustomerListParams, CustomerPatch } from "./types";

const BASE = "/api/sales/customer-directory/";

/** Thân POST search: `q` rỗng vẫn gửi (BE trả cả danh bạ); `ordering` luôn gửi để thứ tự không phụ thuộc mặc định của BE; `page` chỉ từ trang 2. */
export function customerSearchBody(params: CustomerListParams, page: number): { q: string; ordering: string; page?: number } {
  const body: { q: string; ordering: string; page?: number } = { q: params.q.trim(), ordering: params.ordering };
  if (page > 1) body.page = page;
  return body;
}

/** POST /api/sales/customer-directory/search/ — thân {q, ordering, page}; 20 dòng/trang. URL không có từ khoá. */
export function listCustomers(params: CustomerListParams, page = 1, signal?: AbortSignal): Promise<Paginated<CustomerListItem>> {
  return apiFetch<Paginated<CustomerListItem>>(`${BASE}search/`, {
    method: "POST",
    body: customerSearchBody(params, page),
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
 * PATCH /api/sales/customer-directory/{id}/ — `name`, `phone`, `default_address`, `note` (chuỗi).
 * `phone` BE chuẩn hoá về 0…; sai dạng → 400 INVALID_PHONE; trùng khách khác → 400 CUSTOMER_PHONE_TAKEN (không lặp lại số). Trả thân chi tiết mới.
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
