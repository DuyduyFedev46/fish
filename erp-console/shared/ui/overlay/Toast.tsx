"use client";

// Thông báo nổi góc DƯỚI PHẢI (UI-RULES §7): thành công · cảnh báo · lỗi; "Hoàn tác" tuỳ chọn (chỉ khi thao tác thật sự
// hoàn tác được); có nút đóng; `aria-live="polite"` (lỗi dùng role="alert"). Tự ẩn sau vài giây, dừng đếm khi rê chuột /
// focus vào hoặc khi tab bị ẩn. Là nơi báo KẾT QUẢ đã thấy được trên màn, không phải nơi duy nhất chứa thông tin quan trọng.
// Dùng: bọc <ToastProvider> ở gốc rồi `const toast = useToast(); toast.success("Đã lưu")`.
// (shared/ui/Toast.tsx cũ còn dùng ở các màn chưa chuyển; các lô sau chuyển dần rồi xoá ở Lô 17.)

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "../Icon";

export type ToastKind = "success" | "warn" | "error";
export type ToastItem = { id: number; kind: ToastKind; message: string; undo?: () => void; duration?: number };
type Options = { undo?: () => void; duration?: number };

const ICON: Record<ToastKind, string> = { success: "check_circle", warn: "warning", error: "error" };
const DURATION: Record<ToastKind, number> = { success: 6000, warn: 8000, error: 10000 };

/** Thời gian tự ẩn (ms): theo `duration` nếu người gọi truyền (số dương), không thì theo loại. */
export function toastDuration(kind: ToastKind, duration?: number): number {
  return typeof duration === "number" && duration > 0 ? duration : DURATION[kind];
}

/** Tạo một mục thông báo, giữ `undo` và `duration` của người gọi. */
export function makeToastItem(id: number, kind: ToastKind, message: string, opts?: Options): ToastItem {
  return { id, kind, message, undo: opts?.undo, duration: opts?.duration };
}

type Api = {
  success: (message: string, opts?: Options) => void;
  warn: (message: string, opts?: Options) => void;
  error: (message: string, opts?: Options) => void;
};

const ToastContext = createContext<Api | null>(null);

export function useToast(): Api {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast phải nằm trong <ToastProvider>");
  return ctx;
}

type ViewProps = {
  kind: ToastKind;
  message: string;
  onClose: () => void;
  onUndo?: () => void;
  duration?: number;
};

/** Một thông báo (dùng riêng được khi không cần Provider). */
export function ToastView({ kind, message, onClose, onUndo, duration }: ViewProps) {
  const [hover, setHover] = useState(false);
  const [focus, setFocus] = useState(false);
  const [hidden, setHidden] = useState(false);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const onVis = () => setHidden(document.visibilityState === "hidden");
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  const paused = hover || focus || hidden;
  const ms = toastDuration(kind, duration);
  useEffect(() => {
    if (paused) return;
    const t = setTimeout(() => closeRef.current(), ms);
    return () => clearTimeout(t);
  }, [paused, ms, message]);

  return (
    <div
      className={`toast-item ${kind}`}
      role={kind === "error" ? "alert" : "status"}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setFocus(true)}
      onBlur={() => setFocus(false)}
    >
      <Icon name={ICON[kind]} />
      <span className="toast-msg">{message}</span>
      {onUndo && (
        <button type="button" className="toast-undo" onClick={onUndo}>
          Hoàn tác
        </button>
      )}
      <button type="button" className="iconbtn toast-close" aria-label="Đóng thông báo" onClick={onClose}>
        <Icon name="close" />
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const seq = useRef(0);

  const remove = useCallback((id: number) => setItems((xs) => xs.filter((x) => x.id !== id)), []);
  const push = useCallback((kind: ToastKind, message: string, opts?: Options) => {
    const id = ++seq.current;
    setItems((xs) => [...xs.slice(-3), makeToastItem(id, kind, message, opts)]);
  }, []);

  const api = useMemo<Api>(
    () => ({
      success: (m, o) => push("success", m, o),
      warn: (m, o) => push("warn", m, o),
      error: (m, o) => push("error", m, o),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {items.map((t) => (
          <ToastView
            key={t.id}
            kind={t.kind}
            message={t.message}
            duration={t.duration}
            onClose={() => remove(t.id)}
            onUndo={
              t.undo
                ? () => {
                    t.undo?.();
                    remove(t.id);
                  }
                : undefined
            }
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
