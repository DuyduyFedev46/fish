// Token DRF lưu trên máy. http.ts đọc để gắn header; features/auth ghi khi đăng nhập/đăng xuất.
// Mọi truy cập localStorage bọc try/catch (Safari private mode, hết chỗ).

const TOKEN_KEY = "cave_erp_token";

function store(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return store()?.getItem(TOKEN_KEY) ?? null;
}

export function setToken(token: string | null): void {
  const s = store();
  if (!s) return;
  try {
    if (token) s.setItem(TOKEN_KEY, token);
    else s.removeItem(TOKEN_KEY);
  } catch {
    /* bỏ qua */
  }
}
