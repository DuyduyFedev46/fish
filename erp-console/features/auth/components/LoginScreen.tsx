"use client";

// Màn đăng nhập (S7-AC4, S7-AC6).

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Icon } from "@/shared/ui/Icon";
import { PasswordInput } from "@/shared/ui/PasswordInput";
import { NAV, canView, homePath, safeNext } from "@/shared/lib/nav";
import { getLastUserId } from "../session";
import type { Me } from "../types";
import { useAuth } from "./AuthProvider";
import { MSG, errorText } from "@/shared/lib/messages";

/** Sau đăng nhập: cùng người như lần trước → quay lại trang đang dở (S7-AC6); khác người → trang mặc định. */
const MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "1";

function destination(me: Me, next: string | null, prevUser: number | null): string {
  if (me.must_change_password) return homePath(me); // S48-AC1: chỉ mở màn "Đặt mật khẩu mới"
  const safe = safeNext(next);
  if (!safe || safe === "/" || prevUser !== me.id) return homePath(me);
  const item = NAV.find((n) => safe === n.href || safe + "/" === n.href || safe.startsWith(n.href));
  if (item && !canView(me, item.key)) return homePath(me);
  return safe;
}

function LoginForm() {
  const { status, me, notice, login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // UI5: nút Đăng nhập không bị tắt khi thiếu ô; bấm thì báo lỗi ngay tại ô trống và đưa focus vào đó.
  const [missing, setMissing] = useState<"u" | "p" | null>(null);

  // Đã đăng nhập sẵn → đi thẳng
  useEffect(() => {
    if (status === "ready" && me && !busy) router.replace(destination(me, next, me.id));
  }, [status, me, next, router, busy]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setError(null);
    const empty = !username.trim() ? "u" : !password ? "p" : null;
    setMissing(empty);
    if (empty) {
      document.getElementById(empty)?.focus();
      return;
    }
    setBusy(true);
    const prevUser = getLastUserId(); // đọc TRƯỚC khi login() ghi đè
    try {
      const data = await login(username.trim(), password);
      router.replace(destination(data, next, prevUser));
    } catch (err) {
      setError(errorText(err, MSG.loginFailed));
      setBusy(false);
    }
  };

  return (
    <main className="login">
      <form className="card" onSubmit={onSubmit} noValidate>
        <div className="lg">
          <div className="mark">
            <Icon name="set_meal" />
          </div>
          <div>
            <b>Cá Về</b>
            <small>Vận hành</small>
          </div>
        </div>
        <h1>Đăng nhập vận hành</h1>
        <p>Mỗi người dùng tài khoản riêng của mình.</p>

        {notice && !error && (
          <div className="alert-box info" role="status">
            <Icon name="schedule" />
            <span>{notice}</span>
          </div>
        )}
        {error && (
          <div className="alert-box err" role="alert">
            <Icon name="error" />
            <span>{error}</span>
          </div>
        )}

        <div className="field">
          <label htmlFor="u">Tài khoản</label>
          <input
            id="u"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            required
            aria-invalid={missing === "u" || undefined}
            aria-describedby={missing === "u" ? "u-err" : undefined}
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
              if (missing === "u") setMissing(null);
            }}
          />
          {missing === "u" && (
            <span className="field-err" id="u-err" role="alert">
              <Icon name="error" />
              <span>{MSG.needUsername}</span>
            </span>
          )}
        </div>
        <PasswordInput
          id="p"
          name="password"
          label="Mật khẩu"
          autoComplete="current-password"
          required
          value={password}
          onChange={(v) => {
            setPassword(v);
            if (missing === "p") setMissing(null);
          }}
          error={missing === "p" ? MSG.needPassword : null}
        />
        <button className="btn primary block" type="submit" disabled={busy} aria-busy={busy || undefined}>
          {busy && <Icon name="progress_activity" className="spin" />}
          {busy ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>
        <div className="hint">Quên mật khẩu? Nhờ Chủ vựa đặt lại.</div>
        {MOCK && (
          <div className="mock-hint">
            <b>Chế độ mock.</b> Tài khoản: <code>loc</code> (Chủ), <code>ql1</code>, <code>kho1</code>,{" "}
            <code>giao1</code>, <code>admin</code> (chưa phân quyền), <code>nghi1</code> (đã nghỉ), <code>kho5</code> (phải đặt
            mật khẩu mới). Mật khẩu{" "}
            <code>demo1234</code>.
          </div>
        )}
      </form>
    </main>
  );
}

export function LoginScreen() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
