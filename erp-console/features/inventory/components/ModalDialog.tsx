"use client";

// Hộp thoại nhỏ giữa màn, mở TRÊN tấm chi tiết lô (SideSheet). Tách riêng vì tấm chi tiết đã có bẫy Tab / Esc ở cấp cửa sổ:
// hộp này bắt phím ở pha capture và chặn lan lên, nên Esc chỉ đóng hộp thoại (không đóng luôn tấm bên dưới)
// và Tab xoay vòng trong hộp. `busy` = đang gửi → không cho đóng (tránh bỏ dở thao tác).

import { useEffect, useId, useRef } from "react";
import s from "../inventory.module.css";

type Props = {
  title: string;
  onClose: () => void;
  busy?: boolean;
  tone?: "default" | "danger";
  children: React.ReactNode;
};

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function ModalDialog({ title, onClose, busy = false, tone = "default", children }: Props) {
  const id = useId();
  const box = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const busyRef = useRef(busy);
  busyRef.current = busy;

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    const auto = box.current?.querySelector<HTMLElement>("[data-autofocus]");
    (auto || box.current)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        if (!busyRef.current) closeRef.current();
        return;
      }
      if (e.key !== "Tab" || !box.current) return;
      e.stopPropagation();
      const items = Array.from(box.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (!items.length) {
        e.preventDefault();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === first || active === box.current)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => {
      window.removeEventListener("keydown", onKey, true);
      prev?.focus?.();
    };
  }, []);

  return (
    <div className={s.modalOverlay}>
      <button
        type="button"
        className={s.modalScrim}
        aria-label="Đóng"
        tabIndex={-1}
        onClick={() => !busy && onClose()}
      />
      <div className={s.modalCard} role="dialog" aria-modal="true" aria-labelledby={id} ref={box} tabIndex={-1}>
        <h3 id={id} className={tone === "danger" ? `${s.modalTitle} ${s.modalTitleDanger}` : s.modalTitle}>
          {title}
        </h3>
        {children}
      </div>
    </div>
  );
}
