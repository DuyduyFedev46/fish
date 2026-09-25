"use client";

// Hook "giữ nháp" cho form (S7-AC6). Chủ nháp là id người đăng nhập:
//   const { me } = useAuth();
//   const [form, setForm, clear, restored] = useDraft(me?.id ?? null, "purchase-receipt:new", { supplier: "" });
//   gửi thành công → clear();
// Hết phiên (401) vẫn giữ nháp; người khác đăng nhập trên cùng máy thì nháp bị xoá (features/auth).
//
// THỜI ĐIỂM ÁP NHÁP (sửa flake QA Q2, lô L6b): nháp được đọc ĐỒNG BỘ ngay lần render đầu khi đã biết chủ nháp
// (`owner` có sẵn lúc mount — trường hợp thường gặp), nên form hiện ra đã là nội dung nháp; không còn một lần
// `setValue(nháp)` chạy SAU khi người dùng/kịch bản đã bắt đầu gõ. Nếu `owner` chỉ có sau khi mount thì nháp
// được áp đúng một lần, và BỎ QUA nếu người dùng đã sửa form trước đó (không đè lên chữ vừa gõ).
//
// KHÔNG đưa mật khẩu vào `value` (S48-AC5): nháp nằm trong localStorage.

import { useCallback, useEffect, useRef, useState } from "react";
import { clearDraft, loadDraft, saveDraft } from "./drafts";

type State<T> = { value: T; restored: boolean; owner: number | null };

function initialState<T>(owner: number | null, formKey: string, initial: T): State<T> {
  if (owner != null) {
    const saved = loadDraft<T>(formKey, owner);
    if (saved !== null) return { value: saved, restored: true, owner };
  }
  return { value: initial, restored: false, owner };
}

export function useDraft<T>(owner: number | null, formKey: string, initial: T) {
  const [state, setState] = useState<State<T>>(() => initialState(owner, formKey, initial));
  const initialRef = useRef(initial);
  /** Người dùng đã sửa form (qua setValue) — nháp đến muộn không được đè. */
  const dirty = useRef(false);

  // Chủ nháp đổi sau khi mount (null → id, hoặc đổi người): áp nháp của chủ mới đúng một lần.
  if (owner !== state.owner) {
    const next = dirty.current && state.owner == null ? { ...state, owner } : initialState(owner, formKey, initialRef.current);
    dirty.current = false;
    setState(next); // cập nhật trong lúc render (mẫu "derived state" của React) → không có khung hình nào lệch
  }

  useEffect(() => {
    if (owner == null || state.owner !== owner) return;
    const t = setTimeout(() => saveDraft(formKey, owner, state.value), 400);
    return () => clearTimeout(t);
  }, [state.value, state.owner, owner, formKey]);

  const setValue = useCallback((v: T | ((prev: T) => T)) => {
    dirty.current = true;
    setState((s) => ({ ...s, value: typeof v === "function" ? (v as (prev: T) => T)(s.value) : v }));
  }, []);

  const clear = useCallback(() => {
    clearDraft(formKey);
    dirty.current = false;
    setState((s) => ({ ...s, value: initialRef.current, restored: false }));
  }, [formKey]);

  return [state.value, setValue, clear, state.restored] as const;
}
