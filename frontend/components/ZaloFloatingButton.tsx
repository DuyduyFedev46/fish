"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { isSafeHref } from "@/features/content/safeHref";
import { useHotline } from "./useHotline";
import s from "./ZaloFloatingButton.module.css";

export interface ZaloFloatingButtonProps {
  /** Link Zalo từ site-info (`seller.zalo`); không truyền thì tự đọc qua `useHotline()`. */
  zaloUrl?: string;
  /** Ẩn ở luồng đặt hàng / thanh toán để không che nút hành động chính (GUI-06). */
  hidden?: boolean;
}

function validZaloHref(url?: string): string | undefined {
  if (!url) return undefined;
  const trimmed = url.trim();
  if (!/^https:\/\/([a-z0-9-]+\.)?zalo\.me\/.+/i.test(trimmed)) return undefined;
  return isSafeHref(trimmed) ? trimmed : undefined;
}

/**
 * Nút tròn "Nhắn Zalo" nổi góc dưới phải trên các trang Shop (GUI-06).
 * Đọc `zaloUrl` từ site-info `seller.zalo` (`ShopFrame` / `useHotline()`); chưa cấu hình thì ẩn hẳn.
 * Trên điện thoại tự nhường chỗ cho BottomNav, thanh mua chi tiết món, CartBar và thanh tóm tắt giỏ.
 */
export default function ZaloFloatingButton({ zaloUrl: propZaloUrl, hidden = false }: ZaloFloatingButtonProps) {
  const fallback = useHotline({ skip: propZaloUrl !== undefined });
  const safeHref = validZaloHref(propZaloUrl ?? fallback.zaloUrl);
  const [cartOffset, setCartOffset] = useState(0);

  useEffect(() => {
    if (hidden || !safeHref) {
      setCartOffset(0);
      return;
    }

    let frame = 0;
    const measure = () => {
      frame = 0;
      if (window.innerWidth >= 768) {
        setCartOffset((prev) => (prev === 0 ? prev : 0));
        return;
      }
      const summary = document.querySelector<HTMLElement>("[data-cart-summary]");
      if (!summary) {
        setCartOffset((prev) => (prev === 0 ? prev : 0));
        return;
      }
      const rect = summary.getBoundingClientRect();
      if (rect.height <= 0 || rect.top >= window.innerHeight) {
        setCartOffset((prev) => (prev === 0 ? prev : 0));
        return;
      }
      const overlap = Math.max(0, window.innerHeight - rect.top);
      const maxOffset = Math.max(80, window.innerHeight - 136);
      const next = overlap > 0 ? Math.min(Math.round(overlap + 12), maxOffset) : 0;
      setCartOffset((prev) => (prev === next ? prev : next));
    };

    const schedule = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(measure);
    };

    measure();
    window.addEventListener("resize", schedule, { passive: true });
    window.addEventListener("scroll", schedule, { passive: true });

    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(schedule) : null;
    const mo =
      typeof MutationObserver !== "undefined"
        ? new MutationObserver(() => {
            const el = document.querySelector<HTMLElement>("[data-cart-summary]");
            if (el && ro) ro.observe(el);
            schedule();
          })
        : null;

    const initialSummary = document.querySelector<HTMLElement>("[data-cart-summary]");
    if (initialSummary && ro) ro.observe(initialSummary);
    if (mo) mo.observe(document.body, { childList: true, subtree: true });

    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", schedule);
      window.removeEventListener("scroll", schedule);
      ro?.disconnect();
      mo?.disconnect();
    };
  }, [hidden, safeHref]);

  if (hidden || !safeHref) return null;

  const customStyle =
    cartOffset > 0 ? ({ "--zalo-cart-offset": `${cartOffset}px` } as CSSProperties) : undefined;

  return (
    <a
      href={safeHref}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Nhắn Zalo với Cá Về"
      data-testid="floating-zalo"
      className={s.fab}
      style={customStyle}
    >
      <svg className={s.icon} viewBox="0 0 36 36" width="28" height="28" aria-hidden="true" focusable="false">
        <path
          d="M18 5C10.268 5 4 10.373 4 17c0 3.74 2.002 7.08 5.14 9.277-.21 1.676-.846 3.314-1.82 4.602-.22.29-.01.708.352.695 2.47-.09 4.862-.892 6.663-2.012A16.17 16.17 0 0 0 18 29c7.732 0 14-5.373 14-12S25.732 5 18 5Z"
          fill="currentColor"
        />
        <text
          x="18"
          y="19.6"
          textAnchor="middle"
          fill="var(--zalo-bg)"
          fontSize="8.8"
          fontWeight="800"
          fontFamily="system-ui, -apple-system, sans-serif"
          letterSpacing="-0.2"
        >
          Zalo
        </text>
      </svg>
      <span className={s.tooltip} aria-hidden="true">
        Nhắn Zalo
      </span>
    </a>
  );
}
