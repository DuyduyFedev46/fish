// Giờ đăng nhập của máy này, để màn "Tài khoản của tôi" ghi "Đăng nhập từ dd/mm/yyyy hh:mm" (ED-06 / W4e).
// BE chưa có danh sách phiên nên FE tự nhớ MỐC GIỜ (chuỗi ISO) ở localStorage lúc đăng nhập thành công. Chỉ là mốc giờ,
// KHÔNG chứa tên, SĐT hay mã người dùng (bất biến 9). Đăng xuất thì xoá. Không đọc được/ghi được (chế độ riêng tư) → bỏ qua.

export const SIGNED_IN_KEY = "cave_erp_signed_in_at";

export function rememberSignedIn(now: Date = new Date()): void {
  try {
    window.localStorage.setItem(SIGNED_IN_KEY, now.toISOString());
  } catch {
    /* bỏ qua */
  }
}

export function forgetSignedIn(): void {
  try {
    window.localStorage.removeItem(SIGNED_IN_KEY);
  } catch {
    /* bỏ qua */
  }
}

/** Mốc ISO hợp lệ đã nhớ, hoặc null. Chuỗi lạ (bị sửa tay) cũng coi là không có. */
export function readSignedIn(): string | null {
  try {
    const v = window.localStorage.getItem(SIGNED_IN_KEY);
    return v && !Number.isNaN(new Date(v).getTime()) ? v : null;
  } catch {
    return null;
  }
}
