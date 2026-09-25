"use client";

// Hộp thoại dùng chung: điện thoại = tấm trượt từ đáy (full ngang), ≥640px = hộp giữa màn.
// Esc / bấm nền / nút X để đóng (trừ khi `busy`). Focus vào ô đầu tiên có autoFocus hoặc vào hộp.

import { useEffect, useId, useRef } from "react";
import { Icon } from "./Icon";

type Props = {
  title: string;
  onClose: () => void;
  /** Đang gửi → không cho đóng (tránh bỏ dở thao tác). */
  busy?: boolean;
  children: React.ReactNode;
};

export function Sheet({ title, onClose, busy = false, children }: Props) {
  const id = useId();
  const box = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const busyRef = useRef(busy);
  busyRef.current = busy;

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    const auto = box.current?.querySelector<HTMLElement>("[autofocus], [data-autofocus]");
    (auto || box.current)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busyRef.current) closeRef.current();
      // Giữ Tab trong hộp thoại (aria-modal): từ phần tử cuối quay về đầu và ngược lại.
      if (e.key === "Tab" && box.current) {
        const items = Array.from(
          box.current.querySelectorAll<HTMLElement>(
            'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
          ),
        ).filter((el) => el.offsetParent !== null);
        if (!items.length) return;
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
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      prev?.focus?.();
    };
  }, []);

  return (
    <div className="sheet-wrap">
      <button
        type="button"
        className="sheet-scrim"
        aria-label="Đóng"
        tabIndex={-1}
        onClick={() => !busy && onClose()}
      />
      <div className="sheet" role="dialog" aria-modal="true" aria-labelledby={id} ref={box} tabIndex={-1}>
        <div className="sheet-h">
          <h2 id={id}>{title}</h2>
          <button type="button" className="iconbtn" onClick={onClose} disabled={busy} aria-label="Đóng">
            <Icon name="close" />
          </button>
        </div>
        <div className="sheet-b">{children}</div>
      </div>
    </div>
  );
}
