"use client";

// Hộp thoại nổi trên đúng màn mở ra nó (UI-RULES §6.1): nền màn cha mờ (--scrim), giữ focus trong hộp,
// Esc / bấm nền / nút X để đóng, trả focus về nút đã mở. Đang gửi (`busy`) thì KHÔNG đóng được (tránh bỏ dở thao tác).
// Điện thoại = tấm trượt từ đáy; từ 640px = hộp giữa màn. Dành cho form ngắn (≤ 6 trường) và bước xác nhận;
// form dài là trang riêng (shared/ui/form/FormPage).
// Nhiều hộp chồng nhau: Esc chỉ đóng hộp trên cùng.

import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Icon } from "../Icon";
import { focusablesIn, trapTarget } from "./focus";
import s from "./Modal.module.css";

type Props = {
  title: string;
  onClose: () => void;
  /** Đang gửi → không đóng được bằng Esc / nền / nút X. */
  busy?: boolean;
  /** Thanh nút cuối hộp: [phụ … chính]. */
  footer?: React.ReactNode;
  /** `sm` cho xác nhận ngắn, mặc định `md`. */
  size?: "sm" | "md";
  children: React.ReactNode;
};

// Chồng hộp đang mở (phần tử cuối = trên cùng).
const stack: symbol[] = [];

export function Modal({ title, onClose, busy = false, footer, size = "md", children }: Props) {
  const titleId = useId();
  const boxRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const busyRef = useRef(busy);
  busyRef.current = busy;
  // Phần tử đang focus LÚC HỘP ĐƯỢC DỰNG (= nút đã mở nó). Phải lấy trong lúc render: tới useEffect thì ô `autoFocus` bên trong đã cướp focus.
  const [opener] = useState<HTMLElement | null>(() => (typeof document === "undefined" ? null : (document.activeElement as HTMLElement | null)));

  useEffect(() => {
    const me = Symbol("modal");
    stack.push(me);
    const returnTo = opener;
    const box = boxRef.current;
    const auto = box?.querySelector<HTMLElement>("[data-autofocus]");
    (auto || box)?.focus({ preventScroll: true });
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKey = (e: KeyboardEvent) => {
      if (stack[stack.length - 1] !== me) return;
      if (e.key === "Escape") {
        e.stopPropagation();
        if (!busyRef.current) closeRef.current();
        return;
      }
      if (e.key === "Tab" && box) {
        const items = focusablesIn(box);
        const next = trapTarget<HTMLElement>(items, document.activeElement as HTMLElement | null, box, e.shiftKey, (el) => !!el && box.contains(el));
        if (next) {
          e.preventDefault();
          next.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      const at = stack.indexOf(me);
      if (at >= 0) stack.splice(at, 1);
      document.body.style.overflow = prevOverflow;
      if (returnTo && returnTo.isConnected) returnTo.focus({ preventScroll: true });
    };
  }, [opener]);

  if (typeof document === "undefined") return null;
  return createPortal(
    <div className={s.wrap}>
      <button type="button" className={s.scrim} aria-label="Đóng" tabIndex={-1} onClick={() => !busy && onClose()} />
      <div
        ref={boxRef}
        className={`${s.box} ${size === "sm" ? s.sm : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-busy={busy || undefined}
        tabIndex={-1}
      >
        <div className={s.head}>
          <h2 id={titleId} className={s.title}>
            {title}
          </h2>
          <button type="button" className="iconbtn" onClick={onClose} disabled={busy} aria-label="Đóng">
            <Icon name="close" />
          </button>
        </div>
        <div className={s.body}>{children}</div>
        {footer && <div className={s.foot}>{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}
