// API module orders — S10 (danh sách + chi tiết đơn) và S11 (Chủ xác nhận thanh toán tay), contract ở 02-stories.md.
// Danh sách/chi tiết cần sales.view_salesorder (NV giao chỉ thấy đơn của phiếu mình, ngoài phạm vi → 404, S5).
// Xác nhận tay cần sales.confirm_payment_manual; nút chỉ hiện khi `available_actions` có "confirm_payment".
// S12 (hàng chờ thanh toán lệch) + S13 (phiếu hoàn cho khoản không có hoá đơn): chỉ Chủ (sales.confirm_payment_manual;
// S13 thêm sales.create_refund). Nút trên từng khoản theo `available_actions` của khoản đó.

import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockOrdersApi, mockPaymentsApi, mockRefundQueueApi, mockRefundsApi } from "./mock";
import type {
  CancelOrderInput,
  CancelOrderResult,
  ConfirmPaymentInput,
  ConfirmPaymentResult,
  ConfirmRefundInput,
  ConfirmRefundResult,
  CreateRefundInput,
  CreateRefundResult,
  MarkRefundFailedInput,
  MarkRefundFailedResult,
  OrderDetail,
  OrderListItem,
  OrderListParams,
  PaymentQueueItem,
  PaymentQueueParams,
  RefundQueueItem,
  ResolveInput,
  ResolveResult,
  RetryRefundResult,
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

/** POST /api/sales/orders/{id}/cancel/ (S14) — nút chỉ hiện khi `available_actions` có "cancel". */
export function cancelOrder(id: number, input: CancelOrderInput): Promise<CancelOrderResult> {
  return apiFetch<CancelOrderResult>(`${BASE}${id}/cancel/`, {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockOrdersApi : undefined,
  });
}

// ---------------------------------------------------------------------------------------------------------------------
// S12 — hàng chờ thanh toán lệch

const PAYMENTS = "/api/sales/payments/";

/** Chuỗi query hàng chờ (BE L8: `resolution_status`, `match_status`, `page`). */
export function paymentQueueQuery(params: PaymentQueueParams, page: number): string {
  const qs = new URLSearchParams();
  qs.set("resolution_status", params.resolution_status);
  if (params.match_status) qs.set("match_status", params.match_status);
  if (page > 1) qs.set("page", String(page));
  return `?${qs.toString()}`;
}

/** GET /api/sales/payments/?resolution_status=OPEN&match_status=&page= — 20 dòng/trang. */
export function listPaymentQueue(params: PaymentQueueParams, page = 1, signal?: AbortSignal): Promise<Paginated<PaymentQueueItem>> {
  return apiFetch<Paginated<PaymentQueueItem>>(PAYMENTS + paymentQueueQuery(params, page), {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockPaymentsApi : undefined,
  });
}

/**
 * GET /api/sales/payments/{id}/ — một khoản (để tải lại tấm chi tiết sau thao tác, lấy `available_actions` mới).
 * BE L8: cùng hình một dòng danh sách. Lỗi → FE sửa tại chỗ theo response của thao tác.
 */
export function getPayment(id: number, signal?: AbortSignal): Promise<PaymentQueueItem> {
  return apiFetch<PaymentQueueItem>(`${PAYMENTS}${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockPaymentsApi : undefined,
  });
}

/**
 * POST /api/sales/payments/{id}/resolve/ — ATTACH_TO_ORDER {order_id, note} hoặc CONFIRM_ORDER {note}.
 * BE nhận cả hai dạng có/không "/" cuối; FE gọi có "/" như confirm-payment.
 */
export function resolvePayment(id: number, input: ResolveInput): Promise<ResolveResult> {
  return apiFetch<ResolveResult>(`${PAYMENTS}${id}/resolve/`, {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockPaymentsApi : undefined,
  });
}

// ---------------------------------------------------------------------------------------------------------------------
// S13 — phiếu hoàn cho khoản tiền không có hoá đơn

/** POST /api/sales/refunds/create/ {payment_transaction, amount, reason, request_id} → 201 phiếu PENDING (200 + duplicate khi trùng request_id). */
export function createRefund(input: CreateRefundInput): Promise<CreateRefundResult> {
  return apiFetch<CreateRefundResult>("/api/sales/refunds/create/", {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockRefundsApi : undefined,
  });
}

// ---------------------------------------------------------------------------------------------------------------------
// S16 — phiếu hoàn chờ chuyển: danh sách + xác nhận / báo thất bại / thử lại

const REFUNDS = "/api/sales/refunds/";

/** GET /api/sales/refunds/?status=PENDING,FAILED&page= — cần sales.view_refund (Chủ, Quản lý). */
export function listRefundQueue(_params: Record<string, never>, page = 1, signal?: AbortSignal): Promise<Paginated<RefundQueueItem>> {
  const qs = new URLSearchParams({ status: "PENDING,FAILED" });
  if (page > 1) qs.set("page", String(page));
  return apiFetch<Paginated<RefundQueueItem>>(`${REFUNDS}?${qs.toString()}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockRefundQueueApi : undefined,
  });
}

/** POST /api/sales/refunds/{id}/confirm/ {bank_txn_ref} → 200 REFUNDED. Cần sales.confirm_refund (chỉ Chủ). */
export function confirmRefund(id: number, input: ConfirmRefundInput): Promise<ConfirmRefundResult> {
  return apiFetch<ConfirmRefundResult>(`${REFUNDS}${id}/confirm/`, {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockRefundQueueApi : undefined,
  });
}

/** POST /api/sales/refunds/{id}/mark-failed/ {reason} → 200 FAILED. */
export function markRefundFailed(id: number, input: MarkRefundFailedInput): Promise<MarkRefundFailedResult> {
  return apiFetch<MarkRefundFailedResult>(`${REFUNDS}${id}/mark-failed/`, {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockRefundQueueApi : undefined,
  });
}

/** POST /api/sales/refunds/{id}/retry/ {} → 200 PENDING (quay lại Chờ hoàn). */
export function retryRefund(id: number): Promise<RetryRefundResult> {
  return apiFetch<RetryRefundResult>(`${REFUNDS}${id}/retry/`, {
    method: "POST",
    body: {},
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockRefundQueueApi : undefined,
  });
}
