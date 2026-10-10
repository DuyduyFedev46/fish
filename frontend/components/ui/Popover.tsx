"use client";

import { useEffect, useRef } from "react";
import type { ReactNode, RefObject } from "react";
import { cx } from "./cx";
import s from "./Popover.module.css";

export interface PopoverProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Phần tử neo (nút mở). Phần tử bao ngoài của Popover phải có `position: relative`. */
  anchorRef: RefObject<HTMLElement>;
  placement?: "bottom-start" | "bottom-end";
  /** "anchor": rộng bằng phần tử bao; hoặc số px. */
  width?: number | "anchor";
  /** Rê chuột vào bảng nổi thì giữ mở; ra ngoài thì đóng sau một độ trễ ngắn. */
  openOnHover?: boolean;
  labelledBy?: string;
  children: ReactNode;
}

/**
 * Lớp nổi không modal neo dưới một phần tử (menu nhóm con, giỏ nhanh). Không bẫy tiêu điểm.
 * Đóng: Esc (trả tiêu điểm về nút neo), bấm ra ngoài, Tab ra khỏi bảng.
 * Không dùng role="menu" vì là điều hướng: dùng mẫu disclosure (nút neo có aria-expanded).
 */
export default function Popover({
  open,
  onOpenChange,
  anchorRef,
  placement = "bottom-start",
  width = "anchor",
  openOnHover = false,
  labelledBy,
  children,
}: PopoverProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const hoverTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onOpenChange(false);
        anchorRef.current?.focus();
      }
    };
    const onPointer = (e: PointerEvent) => {
      const target = e.target as Node;
      if (panelRef.current?.contains(target) || anchorRef.current?.contains(target)) return;
      onOpenChange(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open, onOpenChange, anchorRef]);

  useEffect(
    () => () => {
      if (hoverTimer.current) window.clearTimeout(hoverTimer.current);
    },
    []
  );

  if (!open) return null;

  const hoverProps = openOnHover
    ? {
        onMouseEnter: () => {
          if (hoverTimer.current) window.clearTimeout(hoverTimer.current);
        },
        onMouseLeave: () => {
          hoverTimer.current = window.setTimeout(() => onOpenChange(false), 200);
        },
      }
    : {};

  return (
    <div
      ref={panelRef}
      role="region"
      aria-labelledby={labelledBy}
      className={cx(s.panel, placement === "bottom-end" ? s.end : s.start)}
      style={width === "anchor" ? undefined : { width }}
      // Tab ra khỏi bảng thì đóng.
      onBlur={(e) => {
        const next = e.relatedTarget as Node | null;
        if (next && !panelRef.current?.contains(next) && !anchorRef.current?.contains(next)) {
          onOpenChange(false);
        }
      }}
      {...hoverProps}
    >
      {children}
    </div>
  );
}
