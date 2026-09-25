// Gợi ý quy tắc mật khẩu hiển thị TRƯỚC khi gửi (S48-AC4). Chỉ để người gõ biết trước — BE mới là nơi kiểm thật
// (Django AUTH_PASSWORD_VALIDATORS: ≥ 8 ký tự, không quá phổ biến, không toàn số, không quá giống tên đăng nhập).
// FE KHÔNG chặn gửi theo các điều này; lỗi BE trả về vẫn hiện nguyên văn `detail`.
// BE đổi độ dài tối thiểu (MinimumLengthValidator) thì sửa PASSWORD_MIN_LENGTH ở đây.

import { MSG } from "./messages";

export const PASSWORD_MIN_LENGTH = 8;

/** ok: true = đạt · false = chưa đạt · null = máy không tự kiểm được (máy chủ kiểm khi gửi). */
export type PasswordCheck = { key: string; label: string; ok: boolean | null };

export function passwordChecks(password: string, username?: string): PasswordCheck[] {
  const typed = password.length > 0;
  const name = (username || "").trim().toLowerCase();
  return [
    { key: "length", label: MSG.pwRuleLength(PASSWORD_MIN_LENGTH), ok: typed ? password.length >= PASSWORD_MIN_LENGTH : false },
    { key: "numeric", label: MSG.pwRuleNotNumeric, ok: typed ? !/^\d+$/.test(password) : false },
    {
      key: "similar",
      label: MSG.pwRuleNotSimilar,
      ok: typed && name.length >= 3 ? !password.toLowerCase().includes(name) : typed ? null : false,
    },
    { key: "common", label: MSG.pwRuleNotCommon, ok: null },
  ];
}
