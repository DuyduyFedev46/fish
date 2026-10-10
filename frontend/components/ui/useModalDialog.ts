"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent, MouseEvent, RefObject, SyntheticEvent } from "react";
import { useReturnFocus } from "./useReturnFocus";

/** Thời gian hiệu ứng đóng (ms), khớp CSS: 150 ms. */
export const CLOSE_MS = 150;

let scrollLocks = 0;
function lockScroll() {
  if (scrollLocks++ === 0) {
    const root = document.documentElement;
    root.style.overflow = "hidden";
    root.style.scrollbarGutter = "stable";
  }
}
function unlockScroll() {
  if (--scrollLocks <= 0) {
    scrollLocks = 0;
    const root = document.documentElement;
    root.style.overflow = "";
    root.style.scrollbarGutter = "";
  }
}

export interface ModalOptions {
  open: boolean;
  onClose: () => void;
  /** true: đang gửi, không đóng bằng Esc hay lớp phủ. */
  busy?: boolean;
  /** Bấm lớp phủ có đóng không. */
  dismissible?: boolean;
  /** Phần tử nhận tiêu điểm đầu tiên; thiếu thì phần tử `[data-autofocus]`, rồi tiêu đề. */
  initialFocusRef?: RefObject<HTMLElement>;
  /** Có chọn tiêu đề làm nơi nhận tiêu điểm đầu (bỏ qua data-autofocus). */
  focusTitleFirst?: boolean;
  /** Thời gian chờ hiệu ứng đóng (ms) trước khi close() thật; mặc định 150. */
  closeMs?: number;
}

/**
 * Hành vi chung của Dialog, BottomSheet, FullscreenSheet trên thẻ <dialog> gốc:
 * showModal() (nền tự inert, Tab không ra khỏi hộp), Esc đóng, chạm lớp phủ đóng khi cho phép,
 * khoá cuộn trang, hiệu ứng đóng 150 ms rồi mới close(), trả tiêu điểm về nút đã mở.
 */
export function useModalDialog({
  open,
  onClose,
  busy = false,
  dismissible = true,
  initialFocusRef,
  focusTitleFirst = false,
  closeMs = CLOSE_MS,
}: ModalOptions) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [mounted, setMounted] = useState(open);
  const [closing, setClosing] = useState(false);
  const focus = useReturnFocus();
  const baseId = useId();
  const titleId = `${baseId}-title`;
  const descId = `${baseId}-desc`;

  // Mở: nhớ nút đang giữ tiêu điểm, rồi dựng <dialog>.
  useEffect(() => {
    if (open) {
      focus.remember();
      setClosing(false);
      setMounted(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Đã dựng xong: showModal() và đặt tiêu điểm đầu.
  useEffect(() => {
    if (!open || !mounted) return;
    const el = dialogRef.current;
    if (!el) return;
    if (!el.open) el.showModal();
    lockScroll();
    const frame = requestAnimationFrame(() => {
      const target =
        initialFocusRef?.current ??
        (focusTitleFirst ? null : el.querySelector<HTMLElement>("[data-autofocus]")) ??
        titleRef.current;
      target?.focus();
    });
    return () => {
      cancelAnimationFrame(frame);
      unlockScroll();
    };
  }, [open, mounted, initialFocusRef, focusTitleFirst]);

  // Đóng: chạy hiệu ứng rồi close() thật và trả tiêu điểm.
  useEffect(() => {
    if (open || !mounted) return;
    setClosing(true);
    const timer = window.setTimeout(() => {
      dialogRef.current?.close();
      setMounted(false);
      setClosing(false);
      focus.restore();
    }, closeMs);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, mounted]);

  const onCancel = useCallback(
    (e: SyntheticEvent) => {
      // Esc: để React quyết định có đóng không, không để trình duyệt tự đóng.
      e.preventDefault();
      if (!busy) onClose();
    },
    [busy, onClose]
  );

  const onBackdropClick = useCallback(
    (e: MouseEvent<HTMLDialogElement>) => {
      // Phần hộp nội dung phủ kín <dialog>, nên chỉ có chạm vào lớp phủ mới có target là chính <dialog>.
      if (e.target === e.currentTarget && dismissible && !busy) onClose();
    },
    [busy, dismissible, onClose]
  );

  // Giữ Tab/Shift+Tab xoay vòng trong hộp (trình duyệt cho phép Tab thoát ra thanh địa chỉ, G5 thì không).
  const onKeyDown = useCallback((e: KeyboardEvent<HTMLDialogElement>) => {
    if (e.key !== "Tab") return;
    const root = dialogRef.current;
    if (!root) return;
    const items = Array.from(
      root.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((el) => el.getClientRects().length > 0);
    if (items.length === 0) {
      e.preventDefault();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    const active = document.activeElement as HTMLElement | null;
    const inList = !!active && items.includes(active);
    if (e.shiftKey && (active === first || !inList)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && (active === last || !inList)) {
      e.preventDefault();
      first.focus();
    }
  }, []);

  return { onKeyDown, dialogRef, titleRef, mounted, closing, onCancel, onBackdropClick, titleId, descId };
}
