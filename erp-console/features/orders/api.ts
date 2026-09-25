// API module orders — S10 (danh sách + chi tiết đơn) và S11 (Chủ xác nhận thanh toán tay), contract ở 02-stories.md.
// Danh sách/chi tiết cần sales.view_salesorder (NV giao chỉ thấy đơn của phiếu mình, ngoài phạm vi → 404, S5).
// Xác nhận tay cần sales.confirm_payment_manual; nút chỉ hiện khi `available_actions` có "confirm_payment".

import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockOrdersApi } from "./mock";
import type {
  ConfirmPaymentInput,
  ConfirmPaymentResult,
  OrderDetail,
  OrderListItem,
  OrderListParams,
} from "./types";

const BASE = "/api/sales/orders/";

/** Chuỗi query theo đúng tên tham số contract; bỏ tham số rỗng. */
export function orderListQuery(params: OrderListParams, page: number): string {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.date_from) qs.set("date_from", params.date_from);
  if (params.date_to) qs.set("date_to", params.date_to);
  if (params.q.trim()) qs.set("q", params.q.trim());
  if (page > 1) qs.set("page", String(page));
  const s = qs.toString();
  return s ? `?${s}` : "";
}

/** GET /api/sales/orders/?status=&date_from=&date_to=&q=&page= — 20 dòng/trang. */
export function listOrders(params: OrderListParams, page = 1, signal?: AbortSignal): Promise<Paginated<OrderListItem>> {
  return apiFetch<Paginated<OrderListItem>>(BASE + orderListQuery(params, page), {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockOrdersApi : undefined,
  });
}

/** GET /api/sales/orders/{id}/ */
export function getOrder(id: number, signal?: AbortSignal): Promise<OrderDetail> {
  return apiFetch<OrderDetail>(`${BASE}${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockOrdersApi : undefined,
  });
}

/**
 * POST /api/sales/orders/{id}/confirm-payment/ — contract S11 viết không có "/" cuối, nhưng router DRF của BE
 * (DefaultRouter) sinh URL có "/" cuối như mọi action khác → FE gọi có "/" (ghi ở 03-dev-notes.md, L7 FE).
 */
export function confirmPayment(id: number, input: ConfirmPaymentInput): Promise<ConfirmPaymentResult> {
  return apiFetch<ConfirmPaymentResult>(`${BASE}${id}/confirm-payment/`, {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockOrdersApi : undefined,
  });
}
