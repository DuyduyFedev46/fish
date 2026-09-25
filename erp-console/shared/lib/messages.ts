// MỘT chỗ cho mọi thông điệp lỗi / thông báo hệ thống do FE tự sinh (không phải của BE).
// Quy tắc:
// - Lỗi nghiệp vụ: FE hiện NGUYÊN VĂN `detail` BE trả; logic chỉ dựa vào `code` (quy ước 02-stories.md).
//   Câu trong file này CHỈ dùng khi BE không trả `detail` (mất mạng, 5xx, body rỗng) hoặc cho việc thuần giao diện.
// - Không viết chuỗi lỗi/thông báo tại chỗ trong component; thêm khoá mới vào đây rồi import.
// - Mã lỗi/thông điệp của BE (dùng cho mock) nằm ở shared/lib/beErrors.mock.ts, chép từ contract BE.

export const MSG = {
  // ---- Tầng gọi API (shared/lib/http.ts): dự phòng khi BE không trả `detail` ----
  network: "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.",
  unauthorized: "Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.",
  forbidden: "Bạn không có quyền thực hiện thao tác này.",
  notFound: "Không tìm thấy.",
  badRequest: "Dữ liệu gửi lên chưa hợp lệ.",
  server: (status: number) => `Lỗi máy chủ (${status}). Thử lại sau.`,
  /** S8-AC4: tải dữ liệu màn bị lỗi máy chủ. */
  loadFailed: "Không tải được dữ liệu, thử lại.",
  /** Lỗi không phải ApiError (lỗi lạ phía máy). */
  actionFailed: "Không thực hiện được. Thử lại.",

  // ---- Đăng nhập / phiên (features/auth) ----
  /** S7-AC4: gộp sai mật khẩu và tài khoản đã nghỉ (DRF trả cùng một lỗi 400). */
  loginFailed: "Sai tài khoản/mật khẩu hoặc tài khoản đã ngừng hoạt động.",
  meLoadFailed: "Không tải được thông tin tài khoản.",
  /** S7-AC6: bị đưa về đăng nhập vì 401. */
  sessionExpired: "Phiên đăng nhập đã hết. Đăng nhập lại để làm tiếp — nội dung đang gõ dở vẫn được giữ.",
  /** S47-AC3: 403 rồi tải lại `me` thấy quyền khác trước. */
  permChanged: "Quyền của bạn vừa thay đổi. Menu và nút đã cập nhật theo quyền mới.",
  /** S7-AC3: mở màn không có quyền. */
  noViewPermission: "Bạn không có quyền xem mục này",
  noViewPermissionHint: "Nếu cần dùng mục này, hãy nhờ Chủ vựa cấp quyền cho tài khoản của bạn.",
  /** UI5: nút gửi không bị tắt khi thiếu ô — bấm thì báo ngay tại ô còn trống (nói cách sửa). */
  needUsername: "Nhập tên tài khoản của bạn.",
  needPassword: "Nhập mật khẩu.",

  // ---- Mật khẩu (S46, S48) — kiểm tại máy, trước khi gọi BE ----
  /** S48-AC3: "Nhập lại" khác "Mật khẩu mới" → báo, KHÔNG gọi API. */
  passwordMismatch: "Hai mật khẩu không khớp.",
  /** UI5: ô mật khẩu còn trống khi bấm gửi. */
  needOldPassword: "Nhập mật khẩu hiện tại.",
  needNewPassword: "Nhập mật khẩu mới.",
  needAgainPassword: "Nhập lại mật khẩu mới để kiểm tra.",
  /** Cặp ô mật khẩu tạm của Chủ (features/staff PasswordField), `what` = nhãn viết thường, vd "mật khẩu mới". */
  needField: (what: string) => `Nhập ${what}.`,
  needFieldAgain: (what: string) => `Nhập lại ${what} để kiểm tra.`,
  /** Nút mắt của ô mật khẩu (S48-AC4) — chữ cho trình đọc màn hình. */
  pwShow: "Hiện mật khẩu",
  pwHide: "Ẩn mật khẩu",
  /** Gợi ý quy tắc (shared/lib/passwordRules.ts). */
  pwRulesTitle: "Mật khẩu cần:",
  pwRuleLength: (n: number) => `Ít nhất ${n} ký tự`,
  pwRuleNotNumeric: "Không toàn là số",
  pwRuleNotSimilar: "Không giống tên đăng nhập",
  pwRuleNotCommon: "Không quá phổ biến (vd 12345678, password) — máy chủ kiểm khi gửi",
  /** S48: màn "Đặt mật khẩu mới" bắt buộc lần đầu / sau khi Chủ đặt lại. */
  mustChangeTitle: "Đặt mật khẩu mới",
  mustChangeIntro:
    "Bạn đang dùng mật khẩu tạm do Chủ vựa cấp. Đặt mật khẩu riêng, chỉ mình bạn biết, rồi mới dùng được hệ thống.",
  mustChangeOldHint: "Là mật khẩu tạm Chủ vựa đưa cho bạn.",
  mustChangeDone: "Đã đặt mật khẩu mới. Lần sau đăng nhập bằng mật khẩu này.",
  /** Ô "Nhập lại" của form Chủ đặt mật khẩu tạm (tạo tài khoản, đặt lại). */
  tempPasswordHelp: "Đọc cho nhân viên. Lần đăng nhập đầu, hệ thống bắt họ đổi sang mật khẩu riêng.",
  passwordChanged: "Đã đổi mật khẩu. Máy khác đang đăng nhập tài khoản này sẽ phải đăng nhập lại bằng mật khẩu mới.",
  permsReloaded: "Đã tải lại quyền.",

  // ---- Ghi chú cột phải ----
  noteSaveFailed: "Không lưu được",
} as const;

/**
 * Thông điệp để HIỆN cho người dùng từ một lỗi bất kỳ: ApiError → `message` (= `detail` BE nguyên văn, hoặc câu dự phòng
 * ở trên), lỗi khác (lỗi lạ phía máy, tiếng Anh) → `fallback`. Kiểm theo `name` để không import vòng với http.ts.
 */
export function errorText(err: unknown, fallback: string = MSG.actionFailed): string {
  if (err && typeof err === "object" && (err as Error).name === "ApiError" && (err as Error).message) {
    return (err as Error).message;
  }
  return fallback;
}
