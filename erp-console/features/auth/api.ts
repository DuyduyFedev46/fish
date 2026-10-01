// API của module auth. Mỗi hàm truyền kèm bản mock (chạy khi NEXT_PUBLIC_USE_MOCK=1).

import { ApiError, apiFetch } from "@/shared/lib/http";
import type { ChangePasswordResponse, Me, TokenResponse } from "./types";
import { mockChangePassword, mockLogin, mockLogout, mockMe } from "./mock";
import { MSG } from "@/shared/lib/messages";
import { normalizeHome, normalizeRole, normalizeRoles } from "@/shared/lib/roles";

// Viết đúng nguyên biểu thức `process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockX : undefined` tại chỗ
// (không qua biến/hằng import): webpack gập được biểu thức này lúc build, nên bản build thật
// loại bỏ hẳn mock.ts khỏi bundle. Module mới làm y như vậy.

export const LOGIN_FAILED_MESSAGE = MSG.loginFailed;

/** POST /api/auth/token/ — DRF trả 400 cho cả sai mật khẩu lẫn tài khoản is_active=False (S7-AC4). */
export async function login(username: string, password: string): Promise<string> {
  try {
    const res = await apiFetch<TokenResponse>("/api/auth/token/", {
      method: "POST",
      body: { username, password },
      auth: false,
      mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockLogin : undefined,
    });
    return res.token;
  } catch (err) {
    if (err instanceof ApiError && (err.status === 400 || err.status === 401)) {
      throw new ApiError(LOGIN_FAILED_MESSAGE, err.status);
    }
    throw err;
  }
}

/**
 * Chuẩn hoá `me` ngay khi nhận (P8b Lô 3): tên Group và `home` do BE trả có thể là tên cũ hoặc tên tiếng Anh (Lô 4);
 * mọi nơi còn lại chỉ thấy giá trị nội bộ của `ROLE` / `HOME_CONFIRMATION_QUEUE`.
 */
export function normalizeMe(me: Me): Me {
  return {
    ...me,
    groups: normalizeRoles(me.groups),
    home: normalizeHome(me.home) as Me["home"],
    ...(me.group_labels ? { group_labels: me.group_labels.map((g) => ({ ...g, code: normalizeRole(g.code) })) } : {}),
  };
}

/** GET /api/auth/me/ — contract S6. */
export async function getMe(signal?: AbortSignal): Promise<Me> {
  const me = await apiFetch<Me>("/api/auth/me/", { signal, mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockMe : undefined });
  return normalizeMe(me);
}

/**
 * POST /api/auth/logout/ — S46: 204, BE xoá token đang dùng. DRF cấp MỘT token cho mỗi người nên đăng xuất ở
 * một máy là đăng xuất mọi máy của người đó (C8). Lỗi gì (mất mạng, token đã hết) cũng bỏ qua: console vẫn
 * xoá token trên máy.
 */
export async function logoutRemote(): Promise<void> {
  try {
    await apiFetch<void>("/api/auth/logout/", { method: "POST", body: {}, mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockLogout : undefined });
  } catch {
    /* bỏ qua */
  }
}

/**
 * POST /api/auth/change-password/ — S46. 200 → token mới (token cũ bị xoá, máy khác của người này nhận 401).
 * Lỗi 400 giữ nguyên `code` (AUTH_OLD_PASSWORD, AUTH_WEAK_PASSWORD) và `detail` của BE để hiện nguyên văn.
 */
export async function changePassword(oldPassword: string, newPassword: string): Promise<string> {
  const res = await apiFetch<ChangePasswordResponse>("/api/auth/change-password/", {
    method: "POST",
    body: { old_password: oldPassword, new_password: newPassword },
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockChangePassword : undefined,
  });
  return res.token;
}
