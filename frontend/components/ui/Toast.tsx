"use client";

import Link from "next/link";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Icon from "./Icon";
import { cx } from "./cx";
import s from "./Toast.module.css";

export interface ToastOptions {
  message: string;
  action?: { label: string; href: string };
  tone?: "neutral" | "success";
}

type ToastContextValue = { show: (options: ToastOptions) => void };

const ToastContext = createContext<ToastContextValue | null>(null);

/** Tự ẩn sau 3 giây (UI-RULES, SHOP-1-02 AC4). */
export const TOAST_HIDE_MS = 3000;
const LEAVE_MS = 150;

type Active = ToastOptions & { id: number; leaving: boolean };

/**
 * Phản hồi nhanh, không chặn thao tác, không lấy tiêu điểm. Một toast một lúc: toast mới thay toast cũ.
 * Vùng `role="status"` luôn có trong DOM để trình đọc màn hình đọc chắc chắn.
 * Không dùng cho lỗi cần sửa (dùng Banner hoặc Dialog).
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<Active | null>(null);
  const [paused, setPaused] = useState(false);
  const counter = useRef(0);
  const pendingTimer = useRef<number | null>(null);

  const show = useCallback((options: ToastOptions) => {
    const present = () => {
      counter.current += 1;
      setPaused(false);
      setActive({ ...options, id: counter.current, leaving: false });
    };
    if (pendingTimer.current) window.clearTimeout(pendingTimer.current);
    // Đang có hộp thoại mở thì chờ tới khi nó đóng, tránh đọc chồng (02a mục 7.3).
    const tryPresent = () => {
      if (document.querySelector("dialog[open]")) {
        pendingTimer.current = window.setTimeout(tryPresent, 250);
      } else {
        pendingTimer.current = null;
        present();
      }
    };
    tryPresent();
  }, []);

  // Đếm 3 giây rồi ẩn; rê chuột hoặc tiêu điểm vào toast thì dừng đếm.
  useEffect(() => {
    if (!active || active.leaving || paused) return;
    const timer = window.setTimeout(() => {
      setActive((cur) => (cur && cur.id === active.id ? { ...cur, leaving: true } : cur));
    }, TOAST_HIDE_MS);
    return () => window.clearTimeout(timer);
  }, [active, paused]);

  useEffect(() => {
    if (!active?.leaving) return;
    const timer = window.setTimeout(() => {
      setActive((cur) => (cur && cur.id === active.id ? null : cur));
    }, LEAVE_MS);
    return () => window.clearTimeout(timer);
  }, [active]);

  useEffect(
    () => () => {
      if (pendingTimer.current) window.clearTimeout(pendingTimer.current);
    },
    []
  );

  const value = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className={s.region} role="status" aria-live="polite">
        {active ? (
          <div
            key={active.id}
            className={cx(s.toast, active.leaving && s.leaving)}
            onMouseEnter={() => setPaused(true)}
            onMouseLeave={() => setPaused(false)}
            onFocus={() => setPaused(true)}
            onBlur={() => setPaused(false)}
          >
            <span className={s.tick} aria-hidden="true">
              <Icon name="check" size={14} strokeWidth={2.4} />
            </span>
            <span className={s.message}>{active.message}</span>
            {active.action ? (
              <Link href={active.action.href} className={s.action}>
                {active.action.label}
              </Link>
            ) : null}
          </div>
        ) : null}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast phải được dùng bên trong <ToastProvider>");
  return ctx;
}
