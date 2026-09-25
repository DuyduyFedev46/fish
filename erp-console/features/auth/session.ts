// Id người đăng nhập gần nhất trên máy (còn giữ sau khi token hết hạn) — để biết lần đăng nhập
// kế tiếp là "cùng người" (giữ nháp, quay lại trang đang dở) hay "người khác" (xoá nháp). S7-AC6.

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
