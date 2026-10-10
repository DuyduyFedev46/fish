// API client cho Shop API công khai (contract: doc/features/2026-10-06-shop-giao-dien-moi/02b-tech-design.md §3).
// Khi NEXT_PUBLIC_USE_MOCK=1, mọi hàm trả dữ liệu mock (lib/mock.ts) thay vì gọi mạng —
// cho phép /shop chạy được ngay cả khi backend Django chưa lên.

import {
  ApiError,
  type CatalogItemDetail,
  type CatalogResponse,
  type CreateOrderPayload,
  type CreateOrderResponse,
  type OrderLookupInput,
  type OrderLookupResult,
  type PaymentCheckoutSession,
} from "./types";
// KHÔNG import tĩnh "./mock": bản build thật (USE_MOCK != "1") phải không mang seed mock.
// Mỗi nhánh mock dưới đây dùng điều kiện literal `process.env.NEXT_PUBLIC_USE_MOCK === "1"`
// tại chỗ + `await import("./mock")` động, để bundler cắt cả nhánh lẫn module (M5-1b;
// kiểm bằng `node scripts/check-no-mock.mjs`).

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "1";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  if (res.status === 404 || res.status === 410) {
    let detail = res.status === 410 ? "Bài này không còn trên web." : "Không tìm thấy";
    let code: string | undefined;
    let data: any;
    try {
      const body = await res.json();
      data = body;
      // DRF trả "Not found." (tiếng Anh) khi không có thông điệp riêng -> giữ câu tiếng Việt mặc định.
      if (body?.detail && body.detail !== "Not found.") detail = body.detail;
      if (body?.code) code = body.code;
    } catch {
      // ignore
    }
    throw new ApiError(detail, res.status, code, data);
  }

  if (!res.ok) {
    let detail = `Lỗi máy chủ (${res.status})`;
    let code: string | undefined;
    let data: any;
    try {
      const body = await res.json();
      data = body;
      if (body?.detail) detail = body.detail;
      if (body?.code) code = body.code;
    } catch {
      // ignore parse error, keep default message
    }
    throw new ApiError(detail, res.status, code, data);
  }

  if (res.status === 204) {
    return undefined as unknown as T;
  }

  return res.json() as Promise<T>;
}

// Catalog dùng chung cho trang chủ, header (menu nhóm) và các màn sau: giữ 30 giây để một lần
// xem trang chỉ tốn một request. Lỗi thì bỏ cache để lần "Thử lại" gọi lại thật.
const CATALOG_TTL_MS = 30 * 1000;
let catalogCache: { at: number; promise: Promise<CatalogResponse> } | null = null;

async function fetchCatalog(): Promise<CatalogResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockGetCatalog();
  }
  return apiFetch<CatalogResponse>("/api/shop/catalog/");
}

export function getCatalog(options?: { fresh?: boolean }): Promise<CatalogResponse> {
  const now = Date.now();
  if (!options?.fresh && catalogCache && now - catalogCache.at < CATALOG_TTL_MS) {
    return catalogCache.promise;
  }
  const promise = fetchCatalog();
  catalogCache = { at: now, promise };
  promise.catch(() => {
    if (catalogCache && catalogCache.promise === promise) catalogCache = null;
  });
  return promise;
}

export async function getCatalogItem(itemCode: string): Promise<CatalogItemDetail | null> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockGetCatalogItem(itemCode);
  }
  try {
    return await apiFetch<CatalogItemDetail>(
      `/api/shop/catalog/${encodeURIComponent(itemCode)}/`
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

// `getSiteInfo` nằm ở features/site/api.ts (một nguồn duy nhất, SR-23 F10).

/**
 * Tạo đơn (02b §3.3). Gửi lại cùng `client_request_id` thì máy chủ trả đơn đã có (HTTP 200), không giữ chỗ thêm.
 * Lỗi nghiệp vụ là `ApiError` có `code` (OUT_OF_STOCK, INVALID_QTY, VALIDATION, POLICY_CHANGED, SHOP_CLOSED,
 * VOUCHER_INVALID, throttled); lỗi mạng là lỗi không phải ApiError (fetch ném TypeError).
 * Không log `payload` (có tên, SĐT, địa chỉ khách).
 */
export async function createOrder(payload: CreateOrderPayload): Promise<CreateOrderResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockCreateOrder(payload);
  }
  return apiFetch<CreateOrderResponse>("/api/shop/orders/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Tra đơn bằng POST (02b §3.4): mã đơn + SĐT đầy đủ, hoặc mã đơn + mã tra đơn. SĐT chỉ nằm trong thân yêu cầu,
 * không bao giờ trên URL. 404 (sai mã, sai SĐT, token của đơn khác) -> `null`, một câu chung, không chỉ ra ô sai.
 * 401 `TOKEN_EXPIRED` và 429 để nguyên `ApiError` cho màn xử lý.
 */
export async function lookupOrder(input: OrderLookupInput): Promise<OrderLookupResult | null> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockLookupOrder(input);
  }
  try {
    return await apiFetch<OrderLookupResult>("/api/shop/orders/lookup/", {
      method: "POST",
      body: JSON.stringify(input.token ? { order_code: input.order_code, token: input.token } : input),
    });
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
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockStartCheckoutSession(orderCode);
  }
  return apiFetch<PaymentCheckoutSession>(
    `/api/shop/orders/${encodeURIComponent(orderCode)}/checkout/`,
    { method: "POST" }
  );
}

export { ApiError };
export * from "./types";
