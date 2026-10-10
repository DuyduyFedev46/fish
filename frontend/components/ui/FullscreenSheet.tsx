"use client";

import type { ReactNode, RefObject } from "react";
import IconButton from "./IconButton";
import { useModalDialog } from "./useModalDialog";
import s from "./FullscreenSheet.module.css";

export interface FullscreenSheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  /** aria-label nút X, ví dụ "Đóng, quay lại nhập tay". */
  closeLabel: string;
  footer?: ReactNode;
  initialFocusRef?: RefObject<HTMLElement>;
  children: ReactNode;
}

/**
 * Tấm gần toàn màn cho tác vụ dài có thanh đầu và chân riêng (chọn vị trí bản đồ).
 * Điện thoại: chừa 24 px phía trên, X bên trái. Máy tính: hộp thoại lớn, X bên phải.
 * Chạm lớp phủ KHÔNG đóng (tránh mất thao tác); Esc và X đóng.
 */
export default function FullscreenSheet({
  open,
  onClose,
  title,
  closeLabel,
  footer,
  initialFocusRef,
  children,
}: FullscreenSheetProps) {
  const m = useModalDialog({ open, onClose, dismissible: false, initialFocusRef, closeMs: 240 });
  if (!m.mounted) return null;

  return (
    <dialog
      ref={m.dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={m.titleId}
      className={s.sheet}
      data-closing={m.closing || undefined}
      onCancel={m.onCancel}
      onKeyDown={m.onKeyDown}
      onClick={m.onBackdropClick}
    >
      <div className={s.box}>
        <header className={s.head}>
          <span className={s.close}>
            <IconButton label={closeLabel} icon="close" variant="close" iconSize={20} onClick={onClose} />
          </span>
          <h2 id={m.titleId} ref={m.titleRef} tabIndex={-1} className={s.title}>
            {title}
          </h2>
        </header>
        <div className={s.body}>{children}</div>
        {footer ? <footer className={s.footer}>{footer}</footer> : null}
      </div>
    </dialog>
  );
}
