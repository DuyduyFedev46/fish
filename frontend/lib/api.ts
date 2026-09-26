// API client cho Shop API công khai (xem doc/BUILD-PLAN.md — "Shop API (công khai)").
// Khi NEXT_PUBLIC_USE_MOCK=1, mọi hàm trả dữ liệu mock (lib/mock.ts) thay vì gọi mạng —
// cho phép /shop chạy được ngay cả khi backend Django chưa lên.

import {
  ApiError,
  type CatalogItem,
  type CatalogItemDetail,
  type CreateOrderPayload,
  type CreateOrderResponse,
  type OrderStatus,
  type PaymentCheckoutSession,
  type WireCreateOrderResponse,
  type WireOrderStatus,
} from "./types";
import {
  mockCreateOrder,
  mockGetCatalog,
  mockGetCatalogItem,
  mockGetOrderStatus,
  mockStartCheckoutSession,
} from "./mock";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "1";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  if (res.status === 404) {
    throw new ApiError("Không tìm thấy", 404);
  }

  if (!res.ok) {
    let detail = `Lỗi máy chủ (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore parse error, keep default message
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) {
    return undefined as unknown as T;
  }

  return res.json() as Promise<T>;
}

export async function getCatalog(): Promise<CatalogItem[]> {
  if (USE_MOCK) return mockGetCatalog();
  return apiFetch<CatalogItem[]>("/api/shop/catalog/");
}

export async function getCatalogItem(itemCode: string): Promise<CatalogItemDetail | null> {
  if (USE_MOCK) return mockGetCatalogItem(itemCode);
  try {
    return await apiFetch<CatalogItemDetail>(
      `/api/shop/catalog/${encodeURIComponent(itemCode)}/`
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

// Trạng thái coi là "đã thanh toán" cho mục đích hiển thị (BR-TT-12). PAID là trạng thái cũ
// ít dùng (lõi hiện đi thẳng BOOKED -> PROCESSING khi IPN khớp, theo P3) — vẫn liệt vào đây
// phòng khi có nơi khác set PAID.
const PAID_STATUSES = new Set(["PAID", "PROCESSING", "COMPLETED"]);

function mapOrderStatus(wire: WireOrderStatus): OrderStatus {
  return {
    order_code: wire.order_code,
    status: wire.status,
    status_label: wire.status_label,
    total_amount: Number(wire.total_amount),
    lines: wire.lines.map((l) => ({
      item_code: l.item_code,
      name: l.name || l.item_code,
      qty: Number(l.qty),
      line_total: Number(l.amount),
    })),
    is_paid: PAID_STATUSES.has(wire.status),
    is_expired: wire.status === "AUTO_CANCELLED",
    ...(wire.booked_expires_at ? { booked_expires_at: wire.booked_expires_at } : {}),
    delivery: wire.delivery ? { status: wire.delivery.status } : undefined,
  };
}

function mapCreateOrderResponse(wire: WireCreateOrderResponse): CreateOrderResponse {
  return {
    order_code: wire.order_code,
    total_amount: Number(wire.total_amount),
    booked_expires_at: wire.booked_expires_at,
  };
}

export async function createOrder(
  payload: CreateOrderPayload
): Promise<CreateOrderResponse> {
  if (USE_MOCK) return mapCreateOrderResponse(await mockCreateOrder(payload));
  const wire = await apiFetch<WireCreateOrderResponse>("/api/shop/orders/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return mapCreateOrderResponse(wire);
}

export async function getOrderStatus(
  orderCode: string,
  phoneLast4: string
): Promise<OrderStatus | null> {
  if (USE_MOCK) {
    const wire = await mockGetOrderStatus(orderCode, phoneLast4);
    return wire ? mapOrderStatus(wire) : null;
  }
  try {
    const wire = await apiFetch<WireOrderStatus>(
      `/api/shop/orders/${encodeURIComponent(orderCode)}/?phone_last4=${encodeURIComponent(
        phoneLast4
      )}`
    );
    return mapOrderStatus(wire);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

// Lập bộ tham số thanh toán cổng SePay cho một đơn Giữ chỗ (P1, BE — endpoint thật `POST
// /api/shop/orders/<order_code>/checkout/`). Dùng cho cả lần đầu ("Thanh toán bằng VietQR")
// lẫn thanh toán lại (P1-AC5). Không cần gửi số điện thoại: chỉ đơn `BOOKED` còn TTL mới lập
// được, không lộ thông tin khách (P1-AC6). Trả nguyên `fields` (mảng có thứ tự, BR-TT-13) —
// xem `features/checkout/gateway.ts` để biết cách dùng.
export async function startCheckoutSession(
  orderCode: string
): Promise<PaymentCheckoutSession> {
  if (USE_MOCK) return mockStartCheckoutSession(orderCode);
  return apiFetch<PaymentCheckoutSession>(
    `/api/shop/orders/${encodeURIComponent(orderCode)}/checkout/`,
    { method: "POST" }
  );
}

export { ApiError };
export * from "./types";
