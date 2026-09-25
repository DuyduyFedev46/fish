"use client";

// Trạng thái đăng nhập của console.
// - Mở app: có token → gọi /api/auth/me/; 401 → về đăng nhập.
// - 401 giữa chừng (token bị thu hồi/đã nghỉ): xoá token, GIỮ nháp, chuyển /login/?next=<trang đang mở>.
// - 403: tải lại `me`; quyền thật sự đổi → báo "Quyền của bạn vừa thay đổi" (S47-AC3). 403 do luật (BR-PQ-17)
//   mà quyền không đổi thì không báo.
// - Quay lại tab sau ≥ 5 phút: tải lại `me` (S47-AC2).
// - Đăng nhập người khác trên cùng máy: xoá nháp của người trước (S7-AC6).
// - Tự đổi mật khẩu (S46): BE trả token mới → thay token trên máy, làm tiếp không phải đăng nhập lại; rồi tải lại
//   `me` (S48: cờ must_change_password tắt → cổng console mở).
// - S48: `me.must_change_password` = true → ConsoleGate/nav chỉ mở màn "Đặt mật khẩu mới". Một API bất kỳ trả 403
//   `AUTH_MUST_CHANGE_PASSWORD` (vd Chủ vừa đặt lại mật khẩu khi người này đang mở console) → bật cờ ngay trên máy
//   và tải lại `me`; không báo "Quyền của bạn vừa thay đổi".
// - 403 lặp lại do thiếu quyền ỔN ĐỊNH (code review trước deploy 1): request "METHOD path" đã 403 mà tải lại `me` thấy
//   quyền không đổi → trong STABLE_FORBIDDEN_MS không tải lại `me` cho đúng request đó nữa (tránh mỗi lần mount màn lại
//   gọi /me). Request khác 403 vẫn tải lại bình thường (S47-AC3). Nhớ này xoá khi quyền đổi / đăng nhập / đăng xuất.
// - S48: đặt mật khẩu mới xong (đang bị ép) → `passwordNotice` = "Đã đặt mật khẩu mới…", ConsoleGate hiện ở màn home.

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ApiError, setForbiddenHandler, setUnauthorizedHandler } from "@/shared/lib/http";
import { getToken, setToken } from "@/shared/lib/token";
import { clearAllDrafts, purgeForeignDrafts } from "@/shared/lib/drafts";
import { changePassword as apiChangePassword, getMe, login as apiLogin, logoutRemote } from "../api";
import { getLastUserId, setLastUserId } from "../session";
import { MUST_CHANGE_PASSWORD_CODE, type Me } from "../types";
import { MSG, errorText } from "@/shared/lib/messages";

export type AuthStatus = "loading" | "anon" | "ready" | "error";

type AuthCtx = {
  status: AuthStatus;
  me: Me | null;
  /** Lỗi khi tải `me` không phải 401 (mất mạng, 500) — hiện nút thử lại. */
  error: string | null;
  /** Lý do vừa bị đưa về màn đăng nhập (hết phiên). */
  notice: string | null;
  /** true ngay sau khi người dùng bấm Đăng xuất — cổng console không gắn `next` vào URL đăng nhập. */
  loggedOut: boolean;
  /** S47-AC3: "Quyền của bạn vừa thay đổi" sau khi một thao tác bị 403 và `me` tải lại khác trước. */
  permNotice: string | null;
  dismissPermNotice: () => void;
  /** S48: xác nhận "Đã đặt mật khẩu mới" — hiện ở màn home sau khi rời màn bắt buộc đặt mật khẩu. */
  passwordNotice: string | null;
  dismissPasswordNotice: () => void;
  login: (username: string, password: string) => Promise<Me>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
  /** S46: đổi mật khẩu của chính mình; thành công thì token trên máy được thay bằng token mới. */
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>;
};

export const PERM_CHANGED_NOTICE = MSG.permChanged;

function permSignature(m: Me): string {
  return JSON.stringify([m.groups, m.permissions]);
}

const Ctx = createContext<AuthCtx | null>(null);

const REFRESH_AFTER_MS = 5 * 60 * 1000;
/** Cùng một request 403 mà quyền không đổi → không tải lại `me` cho request đó trong khoảng này. */
const STABLE_FORBIDDEN_MS = 60 * 1000;

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loggedOut, setLoggedOut] = useState(false);
  const [permNotice, setPermNotice] = useState<string | null>(null);
  const [passwordNotice, setPasswordNotice] = useState<string | null>(null);
  /** "METHOD path" → mốc lần 403 gần nhất mà tải lại `me` thấy quyền KHÔNG đổi. */
  const stableForbidden = useRef<Map<string, number>>(new Map());
  const signature = useRef<string | null>(null);
  /** Đang đăng xuất: request khác đang bay sẽ nhận 401 (token vừa bị thu hồi) — không coi là "hết phiên". */
  const loggingOut = useRef(false);
  const lastLoaded = useRef<number>(0);
  /** S48: vừa nhận 403 AUTH_MUST_CHANGE_PASSWORD — giữ cờ kể cả khi `me` (BE cũ) chưa có field. */
  const forcedChange = useRef(false);
  const pathRef = useRef(pathname);
  pathRef.current = pathname;
  const meRef = useRef<Me | null>(null);
  meRef.current = me;

  /** Trả true/false = quyền đổi/không đổi so với lần trước; undefined = không tải được. */
  const loadMe = useCallback(async (afterForbidden = false): Promise<boolean | undefined> => {
    if (!getToken()) {
      setMe(null);
      setStatus("anon");
      return undefined;
    }
    try {
      let data = await getMe();
      if (forcedChange.current && data.must_change_password === undefined) data = { ...data, must_change_password: true };
      lastLoaded.current = Date.now();
      const sig = permSignature(data);
      const changed = signature.current !== null && signature.current !== sig;
      if (afterForbidden && changed) setPermNotice(PERM_CHANGED_NOTICE);
      if (changed) stableForbidden.current.clear();
      signature.current = sig;
      setMe(data);
      setError(null);
      setStatus("ready");
      return changed;
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return undefined; // handler 401 đã xử lý
      if (err instanceof ApiError && err.status === 403) return undefined; // tránh vòng lặp 403 → tải lại me
      setError(errorText(err, MSG.meLoadFailed));
      setStatus((s) => (s === "ready" ? s : "error"));
      return undefined;
    }
  }, []);

  // 401 / 403 toàn cục từ apiFetch
  useEffect(() => {
    setUnauthorizedHandler(() => {
      if (loggingOut.current) return;
      setToken(null);
      setMe(null);
      setStatus("anon");
      setNotice(MSG.sessionExpired);
      const here = pathRef.current || "/";
      if (!here.startsWith("/login")) {
        router.replace(`/login/?next=${encodeURIComponent(here)}`);
      }
    });
    setForbiddenHandler((code, request) => {
      if (code === MUST_CHANGE_PASSWORD_CODE) {
        forcedChange.current = true;
        setMe((m) => (m ? { ...m, must_change_password: true } : m));
        void loadMe(false);
        return;
      }
      const seen = stableForbidden.current.get(request);
      if (seen !== undefined && Date.now() - seen < STABLE_FORBIDDEN_MS) return; // 403 ổn định: không gọi /me lặp
      void loadMe(true).then((changed) => {
        if (changed === false) stableForbidden.current.set(request, Date.now());
      });
    });
    return () => {
      setUnauthorizedHandler(null);
      setForbiddenHandler(null);
    };
  }, [router, loadMe]);

  // Mở app
  useEffect(() => {
    void loadMe();
  }, [loadMe]);

  // Quay lại tab sau ≥ 5 phút → tải lại quyền
  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState === "visible" && getToken() && Date.now() - lastLoaded.current >= REFRESH_AFTER_MS) {
        void loadMe();
      }
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [loadMe]);

  const login = useCallback(async (username: string, password: string) => {
    const token = await apiLogin(username, password);
    setToken(token);
    let data: Me;
    try {
      data = await getMe();
    } catch (err) {
      setToken(null);
      throw err;
    }
    // Người khác đăng nhập trên cùng máy → xoá nháp của người trước.
    const prev = getLastUserId();
    if (prev !== null && prev !== data.id) clearAllDrafts();
    purgeForeignDrafts(data.id);
    setLastUserId(data.id);
    loggingOut.current = false;
    forcedChange.current = false;
    stableForbidden.current.clear();
    lastLoaded.current = Date.now();
    signature.current = permSignature(data);
    setPermNotice(null);
    setPasswordNotice(null);
    setMe(data);
    setError(null);
    setNotice(null);
    setLoggedOut(false);
    setStatus("ready");
    return data;
  }, []);

  const logout = useCallback(async () => {
    loggingOut.current = true;
    await logoutRemote(); // S46: BE xoá token (mọi máy của người này); lỗi mạng thì bỏ qua
    setToken(null);
    clearAllDrafts(); // S46-AC1: đăng xuất chủ động thì xoá nháp trên máy
    setLastUserId(null);
    setMe(null);
    setNotice(null);
    setPermNotice(null);
    setPasswordNotice(null);
    stableForbidden.current.clear();
    signature.current = null;
    forcedChange.current = false;
    setLoggedOut(true);
    setStatus("anon");
    router.replace("/login/");
    // Request đang bay trả về sau khi đã xoá token thì apiFetch không gọi handler 401 nữa (không gửi token).
    setTimeout(() => {
      loggingOut.current = false;
    }, 2000);
  }, [router]);

  const changePassword = useCallback(async (oldPassword: string, newPassword: string) => {
    const wasForced = forcedChange.current || !!meRef.current?.must_change_password;
    const token = await apiChangePassword(oldPassword, newPassword);
    setToken(token); // token cũ đã bị BE xoá (S46-AC2)
    forcedChange.current = false;
    // S48: đặt TRƯỚC khi tải lại `me` — tải xong cờ tắt, màn đặt mật khẩu chuyển ngay về home và thông báo hiện ở đó.
    if (wasForced) setPasswordNotice(MSG.mustChangeDone);
    await loadMe(false); // S48-AC2: BE tắt must_change_password → cổng console mở, về home
  }, [loadMe]);

  const refreshMe = useCallback(async () => {
    await loadMe(false);
  }, [loadMe]);
  const dismissPermNotice = useCallback(() => setPermNotice(null), []);
  const dismissPasswordNotice = useCallback(() => setPasswordNotice(null), []);

  const value = useMemo<AuthCtx>(
    () => ({
      status,
      me,
      error,
      notice,
      loggedOut,
      permNotice,
      dismissPermNotice,
      passwordNotice,
      dismissPasswordNotice,
      login,
      logout,
      refreshMe,
      changePassword,
    }),
    [
      status,
      me,
      error,
      notice,
      loggedOut,
      permNotice,
      dismissPermNotice,
      passwordNotice,
      dismissPasswordNotice,
      login,
      logout,
      refreshMe,
      changePassword,
    ]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth phải nằm trong <AuthProvider>");
  return v;
}
