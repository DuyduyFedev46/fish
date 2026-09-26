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

  // ---- S11 POST /api/sales/orders/{id}/confirm-payment (contract THỰC TẾ BE L7, 03-dev-notes.md "Lô L7 — S10, S11 (BE)") ----
  TT_TXN_REQUIRED: { status: 400, code: "BR-TT-08", detail: "Thiếu mã giao dịch ngân hàng." },
  TT_AMOUNT_INVALID: { status: 400, code: "BR-TT-08", detail: "Số tiền phải là số lớn hơn 0." },
  /** L8 bổ sung tiền (Duy 2026-09-26): sau làm tròn 0,01 mà 0 < số < 1đ. */
  TT_AMOUNT_MIN: { status: 400, code: "BR-TT-08", detail: "Số tiền tối thiểu 1đ." },
  TT_TXN_TOO_LONG: { status: 400, code: "BR-TT-08", detail: "Mã giao dịch ngân hàng dài quá 100 ký tự." },
  TT_WRONG_STATUS: { status: 400, code: "BR-TT-08", detail: "Đơn không ở trạng thái Giữ chỗ/Tự huỷ." },
  TT_TXN_OTHER: {
    status: 400,
    code: "BR-TT-03",
    detail: "Mã giao dịch này đã được ghi nhận cho giao dịch khác, không dùng lại (BR-TT-03).",
  },
  // ---- S12 POST /api/sales/payments/{id}/resolve — contract THỰC TẾ BE L8 (03-dev-notes.md "Lô L8 — S12, S13 (BE)") ----
  TT_NOT_ENOUGH: { status: 400, code: "BR-TT-09", detail: "Tổng tiền đã nhận {paid} < tổng đơn {total}." },
  TT_ORDER_CANCELLED: { status: 400, code: "BR-TT-05", detail: "Đơn đã tự huỷ, chỉ còn cách hoàn tiền." },
  /** BE ghi "Đơn đã huỷ, …" — phần sau dấu phẩy chưa chép được nguyên văn, mock dùng cùng đuôi với câu tự huỷ. */
  TT_ORDER_CANCELLED_MANUAL: { status: 400, code: "BR-TT-05", detail: "Đơn đã huỷ, chỉ còn cách hoàn tiền." },
  TT_ALREADY_RESOLVED: { status: 400, code: "BR-TT-09", detail: "Giao dịch đã được xử lý, không xử lý lại." },
  TT_ACTION_INVALID: {
    status: 400,
    code: "BR-TT-09",
    detail: "Cách xử lý không hợp lệ: ATTACH_TO_ORDER hoặc CONFIRM_ORDER (hoàn tiền thì tạo phiếu hoàn).",
  },
  TT_ORDER_REQUIRED: { status: 400, code: "BR-TT-09", detail: "Thiếu hoặc sai order_id." },
  TT_ORDER_NOT_FOUND: { status: 400, code: "BR-TT-09", detail: "Không tìm thấy đơn để gắn." },
  TT_ATTACH_ONLY_UNMATCHED: { status: 400, code: "BR-TT-09", detail: "Chỉ gắn đơn cho giao dịch không khớp đơn." },
  TT_ORDER_NOT_BOOKED: { status: 400, code: "BR-TT-09", detail: "Đơn không ở trạng thái Giữ chỗ (đã thanh toán hoặc đang xử lý)." },
  TT_CONFIRM_NO_ORDER: { status: 400, code: "BR-TT-09", detail: "Giao dịch chưa gắn đơn — gắn đơn trước (ATTACH_TO_ORDER)." },
  TT_CONFIRM_ONLY_UNDERPAID: { status: 400, code: "BR-TT-09", detail: "Chỉ xác nhận đơn từ giao dịch thiếu tiền." },
  TT_CONFIRM_HAS_REFUND: { status: 400, code: "BR-TT-09", detail: "Giao dịch đang có phiếu hoàn — không dùng để xác nhận đơn." },
  // ---- S13 POST /api/sales/refunds/create/ (BE L8, nhánh payment_transaction — `create_refund_for_payment`) ----
  HT_OVER_REFUNDABLE: { status: 400, code: "BR-HT-04", detail: "Vượt số tiền còn được hoàn: tối đa {max}." },
  /** S15 nhánh sales_invoice (`create_invoice_refund`, câu viết lại ở BE L9 để khớp đúng chữ story). */
  HT_OVER_REFUNDABLE_INVOICE: { status: 400, code: "BR-HT-04", detail: "Vượt số đã thu: còn được hoàn tối đa {max}." },
  HT_AMOUNT_INVALID: { status: 400, code: "BR-HT-04", detail: "Số tiền hoàn phải lớn hơn 0." },
  HT_AMOUNT_MIN: { status: 400, code: "BR-HT-04", detail: "Số tiền hoàn tối thiểu 1đ." },
  HT_ONE_SOURCE: { status: 400, code: "BR-HT-01", detail: "Chỉ gửi một trong hai: sales_invoice hoặc payment_transaction." },
  HT_NO_SOURCE: { status: 400, code: "BR-HT-01", detail: "Thiếu sales_invoice hoặc payment_transaction." },
  HT_TXN_MATCHED: { status: 400, code: "BR-HT-01", detail: "Giao dịch đã khớp hoá đơn — lập phiếu hoàn từ hoá đơn." },
  HT_TXN_NOT_FOUND: { status: 400, code: "BR-HT-01", detail: "Giao dịch không tồn tại." },
  HT_REQUEST_ID_INVALID: { status: 400, code: "BR-HT-01", detail: "request_id phải là UUID." },
  HT_REQUEST_ID_USED: { status: 400, code: "BR-HT-01", detail: "request_id đã dùng cho phiếu hoàn khác." },
  HT_TXN_RESOLVED: { status: 400, code: "BR-TT-09", detail: "Giao dịch đã được xử lý, không lập phiếu hoàn." },
  // ---- S10 GET /api/sales/orders/ — tham số lọc sai ----
  INVALID_FILTER: { status: 400, code: "INVALID_FILTER", detail: "Tham số {param} phải là ngày dạng YYYY-MM-DD." },

  // ---- S14 POST /api/sales/orders/{id}/cancel/ (contract THỰC TẾ BE L9, 03-dev-notes.md "Lô L9 — S14, S15, S16 (BE)") ----
  GH_CANCEL_DELIVERING: {
    status: 400,
    code: "BR-GH-07",
    detail: "Phiếu giao đang Đang giao — báo giao thất bại trước khi huỷ.",
  },
  GH_CANCEL_COMPLETED: {
    status: 400,
    code: "BR-GH-05",
    detail: "Đơn đã giao hoàn tất — chỉ còn cách lập phiếu hoàn.",
  },
  HT_CANCEL_REASON_INVALID: { status: 400, code: "BR-HT-05", detail: "Lý do huỷ không hợp lệ." },
  HT_CANCEL_NOTE_REQUIRED: {
    status: 400,
    code: "BR-HT-05",
    detail: "Bắt buộc nhập ghi chú khi chọn lý do khác (OTHER).",
  },
  /** Không nằm trong 8 test S14 của BE (available_actions đã ẩn nút "cancel" ở các trạng thái này) — FE chỉ
   * dùng làm lưới an toàn khi có ai gọi thẳng API ngoài luồng nút. */
  HT_CANCEL_INVALID_STATUS: { status: 400, code: "BR-HT-05", detail: "Chỉ huỷ được đơn đã thanh toán, chưa giao xong." },

  // ---- S16 POST /api/sales/refunds/{id}/confirm/ | mark-failed/ | retry/ (contract THỰC TẾ BE L9) ----
  HT_CONFIRM_TXN_REQUIRED: {
    status: 400,
    code: "BR-HT-03",
    detail: "Bắt buộc nhập mã giao dịch chuyển khoản (BR-HT-03).",
  },
  /** REFUNDED chặn cả 3 action (điểm không quay lui). */
  HT_ALREADY_DONE: { status: 400, code: "BR-HT-09", detail: "Phiếu đã hoàn, không đổi trạng thái được." },
  HT_MARK_FAILED_WRONG_STATUS: {
    status: 400,
    code: "BR-HT-09",
    detail: "Chỉ báo thất bại được khi phiếu đang Chờ hoàn.",
  },
  HT_RETRY_WRONG_STATUS: { status: 400, code: "BR-HT-09", detail: "Chỉ thử lại được khi phiếu đang Thất bại." },
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
