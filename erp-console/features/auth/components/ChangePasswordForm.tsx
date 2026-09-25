"use client";

// Tự đổi mật khẩu (hỏi mật khẩu hiện tại) — dùng ở 2 chỗ:
// - S46: hộp thoại "Đổi mật khẩu" trong Tài khoản của tôi.
// - S48: màn "Đặt mật khẩu mới" bắt buộc khi còn mật khẩu tạm (`mustChange`).
// Thành công → máy này nhận token mới, `me` tải lại (S48: cờ tắt → vào home); máy khác của cùng tài khoản bị đăng
// xuất. "Nhập lại" khác "Mật khẩu mới" → báo "Hai mật khẩu không khớp", KHÔNG gọi API (S48-AC3). Lỗi BE
// (AUTH_OLD_PASSWORD, AUTH_WEAK_PASSWORD, BR-PQ-17) hiện NGUYÊN VĂN. Không giữ nháp: mật khẩu không vào localStorage.

import { useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { Icon } from "@/shared/ui/Icon";
import { PasswordInput } from "@/shared/ui/PasswordInput";
import { useAuth } from "./AuthProvider";
import { MSG, errorText } from "@/shared/lib/messages";

type Props = {
  onDone: (message: string) => void;
  /** S48: form của màn bắt buộc đặt mật khẩu mới (nhãn nút, gợi ý ô mật khẩu hiện tại). */
  mustChange?: boolean;
};

export function ChangePasswordForm({ onDone, mustChange = false }: Props) {
  const { me, changePassword } = useAuth();
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [again, setAgain] = useState("");
  const [shownNew, setShownNew] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mismatch, setMismatch] = useState(false);
  // UI5: nút gửi không bị tắt khi thiếu ô — bấm thì báo tại ô trống đầu tiên và đưa focus vào đó.
  const [missing, setMissing] = useState<"old" | "new" | "again" | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setError(null);
    const empty = !oldPw ? "old" : !newPw ? "new" : !again ? "again" : null;
    setMissing(empty);
    if (empty) {
      document.getElementById(`cp-${empty}`)?.focus();
      return;
    }
    if (newPw !== again) {
      setMismatch(true); // S48-AC3: báo tại máy, không gọi API
      return;
    }
    setMismatch(false);
    setBusy(true);
    try {
      await changePassword(oldPw, newPw);
      setOldPw("");
      setNewPw("");
      setAgain("");
      onDone(mustChange ? MSG.mustChangeDone : MSG.passwordChanged);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 401)) {
        setError(errorText(err));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="sheet-form" onSubmit={onSubmit} aria-label={mustChange ? MSG.mustChangeTitle : "Đổi mật khẩu"} noValidate>
      {error && (
        <div className="alert-box err" role="alert">
          <Icon name="error" />
          <span>{error}</span>
        </div>
      )}
      <PasswordInput
        id="cp-old"
        label="Mật khẩu hiện tại"
        autoComplete="current-password"
        autoFocus
        value={oldPw}
        onChange={(v) => {
          setOldPw(v);
          if (missing === "old") setMissing(null);
        }}
        disabled={busy}
        required
        help={mustChange ? MSG.mustChangeOldHint : undefined}
        error={missing === "old" ? MSG.needOldPassword : null}
      />
      <PasswordInput
        id="cp-new"
        label="Mật khẩu mới"
        autoComplete="new-password"
        value={newPw}
        onChange={(v) => {
          setNewPw(v);
          setMismatch(false);
          if (missing === "new") setMissing(null);
        }}
        disabled={busy}
        required
        error={missing === "new" ? MSG.needNewPassword : null}
        rules
        username={me?.username}
        shown={shownNew}
        onShownChange={setShownNew}
      />
      <PasswordInput
        id="cp-again"
        label="Nhập lại mật khẩu mới"
        autoComplete="new-password"
        value={again}
        onChange={(v) => {
          setAgain(v);
          setMismatch(false);
          if (missing === "again") setMissing(null);
        }}
        disabled={busy}
        required
        shown={shownNew}
        onShownChange={setShownNew}
        error={missing === "again" ? MSG.needAgainPassword : mismatch ? MSG.passwordMismatch : null}
      />
      <div className="form-actions">
        <button type="submit" className="btn primary" disabled={busy} aria-busy={busy || undefined}>
          {busy && <Icon name="progress_activity" className="spin" />}
          {busy ? "Đang lưu…" : mustChange ? "Lưu mật khẩu mới" : "Đổi mật khẩu"}
        </button>
      </div>
    </form>
  );
}
