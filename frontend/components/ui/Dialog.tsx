"use client";

import type { ReactNode, RefObject } from "react";
import Icon, { type IconName } from "./Icon";
import IconButton from "./IconButton";
import { cx } from "./cx";
import { useModalDialog } from "./useModalDialog";
import s from "./Dialog.module.css";

export type ModalIconTone = "neutral" | "info" | "warn" | "crit";

/** Ô icon tròn đầu hộp thoại (dùng chung với BottomSheet). */
export function ModalIcon({ name, tone }: { name: IconName; tone: ModalIconTone }) {
  return (
    <span className={cx(s.icon, s[`tone_${tone}`])} aria-hidden="true">
      <Icon name={name} size={26} />
    </span>
  );
}

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: ReactNode;
  /** confirm: chữ trái, hai nút chia đôi. alert: icon trên, chữ giữa, nút xếp dọc. */
  kind?: "confirm" | "alert";
  icon?: { name: IconName; tone: ModalIconTone };
  /** Các Button. Nút nhận tiêu điểm đầu đánh dấu `data-autofocus`. */
  actions: ReactNode;
  footnote?: ReactNode;
  /** sm 440, md 480 (từ máy tính). */
  size?: "sm" | "md";
  /** Bấm lớp phủ có đóng không (D4 không). */
  dismissible?: boolean;
  /** aria-label nút X (chỉ hiện từ máy tính). */
  closeLabel?: string;
  initialFocusRef?: RefObject<HTMLElement>;
  /** true: đang gửi, chặn đóng. */
  busy?: boolean;
  children?: ReactNode;
}

/**
 * Hộp thoại giữa màn trên <dialog> gốc: role="dialog" aria-modal="true", giữ tiêu điểm bên trong,
 * Esc đóng, trả tiêu điểm về nút đã mở (G5). Không dùng cho phản hồi nhanh (dùng Toast).
 */
export default function Dialog({
  open,
  onClose,
  title,
  description,
  kind = "confirm",
  icon,
  actions,
  footnote,
  size = "sm",
  dismissible = true,
  closeLabel = "Đóng",
  initialFocusRef,
  busy = false,
  children,
}: DialogProps) {
  const m = useModalDialog({ open, onClose, busy, dismissible, initialFocusRef });
  if (!m.mounted) return null;

  return (
    <dialog
      ref={m.dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={m.titleId}
      aria-describedby={description ? m.descId : undefined}
      className={cx(s.dialog, size === "md" && s.md)}
      data-closing={m.closing || undefined}
      onCancel={m.onCancel}
      onKeyDown={m.onKeyDown}
      onClick={m.onBackdropClick}
    >
      <div className={cx(s.box, kind === "alert" ? s.alert : s.confirm)}>
        <span className={s.closeBtn}>
          <IconButton label={closeLabel} icon="close" variant="close" iconSize={18} onClick={onClose} disabled={busy} />
        </span>
        {icon ? <ModalIcon name={icon.name} tone={icon.tone} /> : null}
        <div className={s.text}>
          <h2 id={m.titleId} ref={m.titleRef} tabIndex={-1} className={s.title}>
            {title}
          </h2>
          {description ? (
            <p id={m.descId} className={s.description}>
              {description}
            </p>
          ) : null}
          {children}
        </div>
        <div className={s.actions}>{actions}</div>
        {footnote ? <p className={s.footnote}>{footnote}</p> : null}
      </div>
    </dialog>
  );
}
