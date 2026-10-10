"use client";

import type { ReactNode } from "react";
import IconButton from "./IconButton";
import { ModalIcon, type ModalIconTone } from "./Dialog";
import type { IconName } from "./Icon";
import { cx } from "./cx";
import { useModalDialog } from "./useModalDialog";
import s from "./Sheet.module.css";

export interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: ReactNode;
  icon?: { name: IconName; tone: Exclude<ModalIconTone, "crit"> };
  children?: ReactNode;
  actions?: ReactNode;
  /** title: tiêu đề nhận tiêu điểm đầu (mặc định). first-action: nút `[data-autofocus]` hoặc nút đầu. */
  initialFocus?: "title" | "first-action";
  /** aria-label nút X khi thành hộp thoại trên máy tính. */
  closeLabel?: string;
}

/**
 * Điện thoại: tấm trượt từ đáy có thanh kéo. Máy tính (từ 768 px): hộp thoại giữa màn rộng 480 có nút X.
 * Dùng cho danh sách lựa chọn và thông báo có danh sách (C3, sắp xếp). Xác nhận phá huỷ dùng Dialog.
 */
export function BottomSheet({
  open,
  onClose,
  title,
  description,
  icon,
  children,
  actions,
  initialFocus = "title",
  closeLabel = "Đóng",
}: BottomSheetProps) {
  const m = useModalDialog({ open, onClose, focusTitleFirst: initialFocus === "title", closeMs: 240 });
  if (!m.mounted) return null;

  return (
    <dialog
      ref={m.dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={m.titleId}
      aria-describedby={description ? m.descId : undefined}
      className={s.sheet}
      data-closing={m.closing || undefined}
      onCancel={m.onCancel}
      onKeyDown={m.onKeyDown}
      onClick={m.onBackdropClick}
    >
      <div className={s.box}>
        <span className={s.handle} aria-hidden="true" />
        <span className={s.closeBtn}>
          <IconButton label={closeLabel} icon="close" variant="close" iconSize={18} onClick={onClose} />
        </span>
        <div className={cx(s.head, icon && s.headIcon)}>
          {icon ? <ModalIcon name={icon.name} tone={icon.tone} /> : null}
          <h2 id={m.titleId} ref={m.titleRef} tabIndex={-1} className={s.title}>
            {title}
          </h2>
          {description ? (
            <p id={m.descId} className={s.description}>
              {description}
            </p>
          ) : null}
        </div>
        {children ? <div className={s.body}>{children}</div> : null}
        {actions ? <div className={s.actions}>{actions}</div> : null}
      </div>
    </dialog>
  );
}

export default BottomSheet;
