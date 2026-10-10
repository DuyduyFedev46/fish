"use client";

import { useCallback, useRef } from "react";

/**
 * Nhớ phần tử đang có tiêu điểm lúc mở popup và trả tiêu điểm về đó khi popup đã đóng hẳn (G5).
 * `restore` phải gọi SAU khi <dialog> đã `close()`, vì lúc còn modal phần còn lại của trang bị `inert`.
 */
export function useReturnFocus() {
  const saved = useRef<HTMLElement | null>(null);

  const remember = useCallback(() => {
    const el = document.activeElement;
    saved.current = el instanceof HTMLElement && el !== document.body ? el : null;
  }, []);

  const restore = useCallback(() => {
    const el = saved.current;
    saved.current = null;
    if (el && el.isConnected) el.focus();
  }, []);

  return { remember, restore };
}
