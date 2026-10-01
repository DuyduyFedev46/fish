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
  /**
   * Phần còn lại của thân lỗi BE ngoài `detail` và `code` (BE trải `details` dạng object ra ngang hàng, vd BR-AI-19 trả
   * `{ errors: { <id lệnh>: "lý do" }, detail, code }` thì đây là `{ errors: {...} }`), để màn nêu rõ chỗ sai. Không bắt buộc.
   */
  details?: unknown;
  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
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

/**
 * Thân yêu cầu như BE thấy: `apiFetch` TỰ `JSON.stringify` object, nên người gọi truyền object, KHÔNG truyền chuỗi JSON
 * (chuỗi bị mã hoá lần hai, DRF trả 400 `Expected a dictionary, but got str`). FormData đi nguyên.
 */
function mockWireBody(body: unknown): { ok: true; body: unknown } | { ok: false } {
  if (body === undefined || (typeof FormData !== "undefined" && body instanceof FormData)) return { ok: true, body };
  const parsed: unknown = JSON.parse(JSON.stringify(body));
  if (typeof parsed === "string") return { ok: false };
  return { ok: true, body: parsed };
}

async function sendMock(path: string, init: ApiInit, token: string | null): Promise<MockResponse> {
  const method = init.method || "GET";
  mockRequestLog.push(`${method} ${path}`);
  mockPending += 1;
  try {
    await new Promise((r) => setTimeout(r, 250));
    // Mock đọc thân sau một vòng JSON y như trên dây; thân là chuỗi (mã hoá hai lần) thì trả 400 như BE thật.
    const wire = mockWireBody(init.body);
    if (!wire.ok) {
      return { status: 400, body: { non_field_errors: ["Invalid data. Expected a dictionary, but got str."] } };
    }
    const req: MockRequest = { method, path, body: wire.body, token };
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
  // Tải ảnh (A2, 02-stories.md): body là FormData (multipart) — KHÔNG tự đặt Content-Type, để trình duyệt
  // tự gắn boundary; KHÔNG JSON.stringify (mất tệp nhị phân).
  const isForm = typeof FormData !== "undefined" && init.body instanceof FormData;
  if (init.body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Token ${token}`;
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: init.method || "GET",
      headers,
      body: init.body !== undefined ? (isForm ? (init.body as FormData) : JSON.stringify(init.body)) : undefined,
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

function detailOf(body: unknown): { detail?: string; code?: string; details?: unknown } {
  if (body && typeof body === "object") {
    const { detail, code, ...rest } = body as Record<string, unknown>;
    return {
      detail: typeof detail === "string" ? detail : undefined,
      code: typeof code === "string" ? code : undefined,
      details: Object.keys(rest).length > 0 ? rest : undefined,
    };
  }
  return {};
}

export async function apiFetch<T>(path: string, init: ApiInit = {}): Promise<T> {
  const token = init.auth === false ? null : getToken();
  const { status, body } = USE_MOCK ? await sendMock(path, init, token) : await sendReal(path, init, token);

  if (status >= 200 && status < 300) return (status === 204 ? undefined : body) as T;

  const { detail, code, details } = detailOf(body);
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
  if (status === 400) throw new ApiError(detail || MSG.badRequest, 400, code, details);
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

export type ApiUploadInit = {
  auth?: boolean;
  onProgress?: (percent: number) => void;
  mock?: MockHandler;
};

/**
 * Tải tệp lên server qua multipart/form-data kèm theo dõi tiến trình upload (CMS-05).
 * Dùng XMLHttpRequest.upload.onprogress để báo % tiến trình cho UI.
 */
export async function apiUpload<T>(path: string, formData: FormData, init: ApiUploadInit = {}): Promise<T> {
  const token = init.auth === false ? null : getToken();

  if (USE_MOCK) {
    if (init.onProgress) {
      init.onProgress(50);
      await new Promise((r) => setTimeout(r, 100));
      init.onProgress(100);
    }
    const mockRes = await sendMock(path, { method: "POST", body: formData, mock: init.mock }, token);
    const { status, body } = mockRes;
    if (status >= 200 && status < 300) return (status === 204 ? undefined : body) as T;
    const { detail, code } = detailOf(body);
    if (status === 401) {
      if (token && onUnauthorized) onUnauthorized();
      throw new ApiError(detail || MSG.unauthorized, 401, code);
    }
    if (status === 403) {
      if (onForbidden) onForbidden(code, `POST ${path}`);
      throw new ApiError(detail || MSG.forbidden, 403, code);
    }
    if (status === 404) throw new ApiError(detail || MSG.notFound, 404, code);
    if (status === 400) throw new ApiError(detail || MSG.badRequest, 400, code);
    throw new ApiError(detail || MSG.server(status), status, code);
  }

  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${path}`);
    xhr.setRequestHeader("Accept", "application/json");
    if (token) xhr.setRequestHeader("Authorization", `Token ${token}`);

    if (xhr.upload && init.onProgress) {
      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable) {
          const percent = Math.round((evt.loaded / evt.total) * 100);
          init.onProgress!(percent);
        }
      };
    }

    xhr.onload = () => {
      let body: unknown = null;
      if (xhr.status !== 204) {
        try {
          body = JSON.parse(xhr.responseText);
        } catch {
          body = null;
        }
      }
      const { status } = xhr;
      if (status >= 200 && status < 300) {
        return resolve((status === 204 ? undefined : body) as T);
      }
      const { detail, code } = detailOf(body);
      if (status === 401) {
        if (token && onUnauthorized) onUnauthorized();
        return reject(new ApiError(detail || MSG.unauthorized, 401, code));
      }
      if (status === 403) {
        if (onForbidden) onForbidden(code, `POST ${path}`);
        return reject(new ApiError(detail || MSG.forbidden, 403, code));
      }
      if (status === 404) return reject(new ApiError(detail || MSG.notFound, 404, code));
      if (status === 400) return reject(new ApiError(detail || MSG.badRequest, 400, code));
      return reject(new ApiError(detail || MSG.server(status), status, code));
    };

    xhr.onerror = () => {
      reject(new ApiError(MSG.network, 0));
    };

    xhr.send(formData);
  });
}

