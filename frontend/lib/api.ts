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
} from "./types";
import {
  mockCreateOrder,
  mockGetCatalog,
  mockGetCatalogItem,
  mockGetOrderStatus,
} from "./mock";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "1";

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

export async function createOrder(
  payload: CreateOrderPayload
): Promise<CreateOrderResponse> {
  if (USE_MOCK) return mockCreateOrder(payload);
  return apiFetch<CreateOrderResponse>("/api/shop/orders/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getOrderStatus(
  orderCode: string,
  phoneLast4: string
): Promise<OrderStatus | null> {
  if (USE_MOCK) return mockGetOrderStatus(orderCode, phoneLast4);
  try {
    return await apiFetch<OrderStatus>(
      `/api/shop/orders/${encodeURIComponent(orderCode)}/?phone_last4=${encodeURIComponent(
        phoneLast4
      )}`
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export { ApiError };
export * from "./types";
