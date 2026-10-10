// Id người đăng nhập gần nhất trên máy (còn giữ sau khi token hết hạn) — để biết lần đăng nhập
// kế tiếp là "cùng người" (giữ nháp, quay lại trang đang dở) hay "người khác" (xoá nháp). S7-AC6.

import { setToken } from "@/shared/lib/token";
import { forgetSignedIn } from "./signedInAt";

const LAST_USER_KEY = "cave_erp_last_user";

export function getLastUserId(): number | null {
  try {
    const v = window.localStorage.getItem(LAST_USER_KEY);
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}

export function setLastUserId(id: number | null): void {
  try {
    if (id == null) window.localStorage.removeItem(LAST_USER_KEY);
    else window.localStorage.setItem(LAST_USER_KEY, String(id));
  } catch {
    /* bỏ qua */
  }
}

/**
 * Kết thúc phiên trên máy này: xoá token VÀ mốc giờ đăng nhập (signedInAt). Mọi đường ra khỏi phiên (nút Đăng xuất, 401 hết hạn,
 * đăng nhập lỗi giữa chừng) phải đi qua đây để không sót mốc (Lô 17b TL15-L4).
 */
export function endSession(): void {
  setToken(null);
  forgetSignedIn();
}
