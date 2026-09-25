"use client";

// Ngăn kéo (menu trái < 768px, cột phải < 1024px) — UI5, fixing-accessibility "focus and dialogs":
// - mở: nhớ phần tử đang focus (nút ☰ / nút cột phải / "Thêm"), chuyển focus vào trong ngăn kéo
//   (mục đang chọn nếu có, không thì phần tử bấm được đầu tiên);
// - đang mở: giữ Tab trong ngăn kéo (Shift+Tab từ đầu về cuối và ngược lại);
// - đóng: trả focus về đúng nút đã mở, nếu focus còn đang ở trong ngăn kéo hoặc rơi về <body>.
// Chỉ chạy khi ngăn kéo thật sự đang phủ lên nội dung (`overlayQuery` khớp); ở màn rộng cột là cố định, không bẫy Tab.
// Esc và bấm nền để đóng do Shell lo.

import { useEffect, useRef } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function focusables(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.offsetParent !== null && !el.closest("[hidden]"),
  );
}

export function useDrawerFocus(open: boolean, ref: React.RefObject<HTMLElement>, overlayQuery: string) {
  const returnTo = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const root = ref.current;
    if (!open || !root || !window.matchMedia(overlayQuery).matches) return;
    returnTo.current = document.activeElement as HTMLElement | null;
    // Ngăn kéo vừa đổi từ visibility:hidden → visible (có transition) nên focus ngay lúc này có thể trượt:
    // thử ở khung hình kế tiếp, chưa vào được thì thử lại một lần.
    const focusStart = () => {
      if (root.contains(document.activeElement)) return;
      const start =
        root.querySelector<HTMLElement>('[aria-current="page"], [role="tab"][aria-selected="true"]') || focusables(root)[0];
      start?.focus({ preventScroll: true });
    };
    const raf = requestAnimationFrame(focusStart);
    const retry = setTimeout(focusStart, 80);

    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const items = focusables(root);
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      if (!root.contains(active)) {
        e.preventDefault();
        first.focus();
      } else if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(retry);
      document.removeEventListener("keydown", onKey);
      const back = returnTo.current;
      returnTo.current = null;
      const active = document.activeElement;
      if (back && back.isConnected && (active === document.body || active === null || root.contains(active))) {
        back.focus({ preventScroll: true });
      }
    };
  }, [open, ref, overlayQuery]);
}
