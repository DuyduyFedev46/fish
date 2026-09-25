// Bảng mã lỗi + thông điệp của BACKEND, dùng cho mock — CHỈ import từ features/*/mock.ts (bản build thật không chứa).
// Chép NGUYÊN VĂN từ contract thực tế trong 03-dev-notes.md: "Lô L5 — S41, S42" (bảng lỗi /api/staff/) và
// "Lô L6 — S46, S47" (change-password), "Lô L6b (BE)" (S48), cùng lỗi chung DRF (401/403/404/405). BE đổi câu nào thì sửa MỘT dòng ở đây.
// Mock trả `{code, detail}` đúng như BE; UI hiện nguyên văn `detail`, không tự viết lại.
// E2E đọc câu mong đợi qua window.__caveMock.beDetail(key, params) / .pwProblems / .msg (thông điệp FE, shared/lib/messages.ts)
// — không gõ lại chuỗi trong kịch bản.

import type { MockResponse } from "./http";
import { MSG } from "./messages";

type Entry = { status: number; code?: string; detail: string };

export const BE_ERRORS = {
  // ---- Chung (DRF + exception_handler BE) ----
  UNAUTHORIZED: { status: 401, detail: "Thông tin xác thực không hợp lệ." },
  DRF_FORBIDDEN: { status: 403, detail: "Bạn không được cấp quyền để thực hiện hành động này." },
  NOT_FOUND: { status: 404, detail: "Không tìm thấy." },
  METHOD_NOT_ALLOWED: { status: 405, detail: 'Phương thức "{method}" không được chấp nhận.' },

  // ---- /api/staff/ (BE L5) ----
  FIELD_NOT_ALLOWED: { status: 400, code: "BR-PQ-08", detail: "Trường không được phép: {fields}." },
  PHONE_REQUIRED: { status: 400, code: "BR-PQ-08", detail: "Số điện thoại là bắt buộc." },
  USERNAME_EXISTS: { status: 400, code: "BR-PQ-08", detail: "Tên đăng nhập đã tồn tại." },
  USERNAME_REQUIRED: { status: 400, code: "BR-PQ-08", detail: "Tên đăng nhập là bắt buộc." },
  USERNAME_INVALID: {
    status: 400,
    code: "BR-PQ-08",
    detail: "Tên đăng nhập chỉ gồm chữ, số và @ . + - _ (không dấu cách).",
  },
  PASSWORD_REQUIRED: { status: 400, code: "BR-PQ-08", detail: "Mật khẩu là bắt buộc." },
  /** `detail` = các câu của Django validator nối bằng dấu cách (xem PW_*). */
  PASSWORD_WEAK: { status: 400, code: "BR-PQ-08", detail: "{problems}" },
  GROUPS_NOT_ARRAY: { status: 400, code: "BR-PQ-08", detail: "Danh sách nhóm phải là mảng tên nhóm." },
  GROUP_UNKNOWN: { status: 400, code: "BR-PQ-08", detail: "Nhóm không tồn tại: {groups}. Chỉ dùng: {valid}." },
  SELF_GROUPS: { status: 400, code: "BR-PQ-17", detail: "Không thể tự đổi nhóm của chính mình." },
  SELF_DEACTIVATE: { status: 400, code: "BR-PQ-17", detail: "Không thể tự cho nghỉ chính mình." },
  SELF_RESET: {
    status: 400,
    code: "BR-PQ-17",
    detail: "Không tự đặt lại mật khẩu của mình ở đây — dùng Đổi mật khẩu.",
  },
  CHU_GROUP_ONLY: { status: 403, code: "BR-PQ-17", detail: "Chỉ Chủ mới gán hoặc bỏ nhóm Chủ." },
  CHU_ACCOUNT_ONLY: { status: 403, code: "BR-PQ-17", detail: "Chỉ Chủ mới thao tác trên tài khoản Chủ." },
  SUPERUSER_ONLY: { status: 403, code: "BR-PQ-17", detail: "Chỉ superuser mới thao tác trên tài khoản superuser." },
  LAST_CHU_GROUP: { status: 400, code: "BR-PQ-18", detail: "Phải còn ít nhất một Chủ đang làm." },
  LAST_CHU_DEACTIVATE: { status: 400, code: "BR-PQ-18", detail: "Không thể cho nghỉ Chủ cuối cùng." },
  DELIVERING_LEFT: {
    status: 400,
    code: "BR-GH-08",
    detail: "Còn {count} phiếu Đang giao ({notes}) — xử lý trước khi cho nghỉ.",
  },
  ALREADY_INACTIVE: { status: 400, code: "BR-PQ-01", detail: "Tài khoản này đã nghỉ." },
  ALREADY_ACTIVE: { status: 400, code: "BR-PQ-01", detail: "Tài khoản này đang làm." },

  // ---- /api/auth/change-password/ (BE L6) ----
  CP_FIELD_NOT_ALLOWED: {
    status: 400,
    code: "BR-PQ-17",
    detail: "Trường không được phép: {fields}. Chỉ đổi được mật khẩu của chính bạn.",
  },
  AUTH_OLD_PASSWORD: { status: 400, code: "AUTH_OLD_PASSWORD", detail: "Mật khẩu hiện tại không đúng." },
  AUTH_NEW_REQUIRED: { status: 400, code: "AUTH_WEAK_PASSWORD", detail: "Mật khẩu mới là bắt buộc." },
  AUTH_WEAK_PASSWORD: { status: 400, code: "AUTH_WEAK_PASSWORD", detail: "{problems}" },

  // ---- S48 / BR-PQ-19 (BE L6b): còn mật khẩu tạm → mọi API bị chặn trừ auth/token, auth/me, auth/logout,
  // auth/change-password ----
  AUTH_MUST_CHANGE_PASSWORD: {
    status: 403,
    code: "AUTH_MUST_CHANGE_PASSWORD",
    detail: "Bạn cần đặt mật khẩu mới trước khi dùng hệ thống (BR-PQ-19).",
  },
} satisfies Record<string, Entry>;

export type BeErrorKey = keyof typeof BE_ERRORS;

/** Câu của Django AUTH_PASSWORD_VALIDATORS (LANGUAGE_CODE="vi") mà mock mô phỏng. */
export const PW_PROBLEMS = {
  PW_TOO_SHORT: "Mật khẩu quá ngắn. Nó phải chứa ít nhất 8 ký tự.",
  PW_COMMON: "Mật khẩu này quá phổ biến.",
  PW_NUMERIC: "Mật khẩu này hoàn toàn là số.",
  PW_SIMILAR: "Mật khẩu quá giống tên đăng nhập.",
} as const;

/** Lỗi DRF khi đăng nhập sai / tài khoản đã nghỉ (obtain_auth_token). */
export const LOGIN_BAD: MockResponse = {
  status: 400,
  body: { non_field_errors: ["Không thể đăng nhập với thông tin đã cung cấp."] },
};

function fill(template: string, params: Record<string, string | number> = {}): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => (k in params ? String(params[k]) : `{${k}}`));
}

/** `detail` của một lỗi BE, đã điền tham số. */
export function beDetail(key: BeErrorKey, params?: Record<string, string | number>): string {
  return fill(BE_ERRORS[key].detail, params);
}

/** Response mock đúng hình BE: `{detail}` (lỗi DRF) hoặc `{code, detail}` (lỗi nghiệp vụ). */
export function beError(key: BeErrorKey, params?: Record<string, string | number>): MockResponse {
  const e: Entry = BE_ERRORS[key];
  const detail = fill(e.detail, params);
  return { status: e.status, body: e.code ? { code: e.code, detail } : { detail } };
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = { ...(w.__caveMock || {}), beDetail, pwProblems: PW_PROBLEMS, msg: MSG };
}
