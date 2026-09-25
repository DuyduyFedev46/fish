// Lớp gọi API dùng chung cho mọi module. Module KHÔNG gọi fetch trực tiếp.
//
//   apiFetch<T>(path, { method, body, mock })
//
// - Tự gắn `Authorization: Token <token>` (token DRF từ POST /api/auth/token/).
// - NEXT_PUBLIC_USE_MOCK=1: không gọi mạng mà chạy hàm `mock` do module truyền vào
//   (mỗi module giữ mock của mình trong features/<x>/mock.ts). Kết quả mock đi qua CÙNG
//   nhánh xử lý status bên dưới, nên hết phiên (401) / thiếu quyền (403) chạy y như thật.
// - Lỗi → ApiError(detail tiếng Việt, status, code). FE hiện `message`, logic chỉ dựa vào `code`.
// - Backend mới là lớp chặn quyền thật; console chỉ ẩn cho gọn (BR-PQ-12).

import { getToken } from "./token";
import { MSG } from "./messages";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "1";

/** Lỗi API. `code` = mã BR/mã lỗi BE trả (vd "BR-GH-07", "AUTH_OLD_PASSWORD"). */
export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/** Danh sách phân trang DRF, 20 dòng/trang, `?page=`. */
export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export type MockRequest = { method: HttpMethod; path: string; body?: unknown; token: string | null };
export type MockResponse = { status: number; body: unknown };
export type MockHandler = (req: MockRequest) => MockResponse | Promise<MockResponse>;

export type ApiInit = {
  method?: HttpMethod;
  body?: unknown;
  /** false = không gửi token (đăng nhập). Mặc định true. */
  auth?: boolean;
  signal?: AbortSignal;
  /** Bản mock của request này — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1. */
  mock?: MockHandler;
};

// ---- Handler toàn cục (features/auth đăng ký) ----
type Handler = () => void;
/**
 * Nhận `code` của 403 (vd "AUTH_MUST_CHANGE_PASSWORD" — S48) để phân biệt với 403 thiếu quyền, và `request`
 * ("METHOD path") để bên nhận không tải lại `me` lặp lại cho cùng một request cứ 403 mãi khi quyền không đổi.
 */
type ForbiddenHandler = (code: string | undefined, request: string) => void;
let onUnauthorized: Handler | null = null;
let onForbidden: ForbiddenHandler | null = null;

/** 401 khi đã gửi token → về màn đăng nhập (giữ nháp). */
export function setUnauthorizedHandler(fn: Handler | null): void {
  onUnauthorized = fn;
}
/** 403 → tải lại quyền (`me`), vì quyền có thể vừa đổi (S47). */
export function setForbiddenHandler(fn: ForbiddenHandler | null): void {
  onForbidden = fn;
}

// ---- Cổng chung của mock (chỉ chế độ mock): mô phỏng lớp chặn chung của BE chạy TRƯỚC mọi endpoint ----
// Vd S48: BE chặn mọi API nghiệp vụ bằng 403 AUTH_MUST_CHANGE_PASSWORD khi người dùng còn mật khẩu tạm.
// features/auth/mock.ts đăng ký; trả null = cho qua. Bản build thật không có ai đăng ký nên không chạy.
type MockGate = (req: MockRequest) => MockResponse | null;
let mockGate: MockGate | null = null;
export function setMockGate(fn: MockGate | null): void {
  mockGate = fn;
}

// ---- Log request ở chế độ mock (kiểm "không gọi API nào" — S7-AC3) ----
export const mockRequestLog: string[] = [];
/** Số request mock đang chờ trả lời — e2e chờ về 0 trước khi đổi dữ liệu mock (tránh đua với request đang bay). */
let mockPending = 0;
if (USE_MOCK && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    log: mockRequestLog,
    clearLog: () => {
      mockRequestLog.length = 0;
    },
    pending: () => mockPending,
  };
}

async function sendMock(path: string, init: ApiInit, token: string | null): Promise<MockResponse> {
  const method = init.method || "GET";
  mockRequestLog.push(`${method} ${path}`);
  mockPending += 1;
  try {
    await new Promise((r) => setTimeout(r, 250));
    const req: MockRequest = { method, path, body: init.body, token };
    const blocked = mockGate ? mockGate(req) : null;
    if (blocked) return blocked;
    if (!init.mock) {
      return { status: 404, body: { detail: `Mock chưa có endpoint ${method} ${path}.` } };
    }
    return init.mock(req);
  } finally {
    mockPending -= 1;
  }
}

async function sendReal(path: string, init: ApiInit, token: string | null): Promise<MockResponse> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Token ${token}`;
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: init.method || "GET",
      headers,
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      cache: "no-store",
      signal: init.signal,
    });
  } catch (err) {
    if ((err as Error)?.name === "AbortError") throw err;
    throw new ApiError(MSG.network, 0);
  }
  let body: unknown = null;
  if (res.status !== 204) {
    try {
      body = await res.json();
    } catch {
      body = null;
    }
  }
  return { status: res.status, body };
}

function detailOf(body: unknown): { detail?: string; code?: string } {
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    return {
      detail: typeof b.detail === "string" ? b.detail : undefined,
      code: typeof b.code === "string" ? b.code : undefined,
    };
  }
  return {};
}

export async function apiFetch<T>(path: string, init: ApiInit = {}): Promise<T> {
  const token = init.auth === false ? null : getToken();
  const { status, body } = USE_MOCK ? await sendMock(path, init, token) : await sendReal(path, init, token);

  if (status >= 200 && status < 300) return (status === 204 ? undefined : body) as T;

  const { detail, code } = detailOf(body);
  if (status === 401) {
    if (token && onUnauthorized) onUnauthorized();
    throw new ApiError(detail || MSG.unauthorized, 401, code);
  }
  if (status === 403) {
    if (onForbidden) onForbidden(code, `${init.method || "GET"} ${path}`);
    throw new ApiError(detail || MSG.forbidden, 403, code);
  }
  if (status === 404) {
    // BR-PQ-12: ngoài phạm vi dòng cũng 404 — không tiết lộ bản ghi có tồn tại.
    throw new ApiError(detail || MSG.notFound, 404, code);
  }
  if (status === 400) throw new ApiError(detail || MSG.badRequest, 400, code);
  throw new ApiError(detail || MSG.server(status), status, code);
}

/**
 * Câu báo lỗi khi TẢI dữ liệu cho màn: lỗi máy chủ (5xx) → "Không tải được dữ liệu, thử lại." (S8-AC4);
 * mất mạng / thiếu quyền / không tìm thấy → thông điệp cụ thể của ApiError.
 */
export function loadErrorText(err: unknown): string {
  if (err instanceof ApiError && (err.status === 0 || err.status === 403 || err.status === 404)) return err.message;
  return MSG.loadFailed;
}
