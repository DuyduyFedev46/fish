"use client";

// Nút "…" ở header trang chi tiết (UI-RULES §5.3): thao tác hiếm hoặc đang bị chặn.
// Mục bị chặn hiện MỜ, `aria-disabled`, LÝ DO NGẮN nằm cạnh ("Chốt lô · Lô còn 18,5 kg."), không nằm dưới.
// Mục bị chặn vẫn focus được (để trình đọc màn hình đọc được lý do) nhưng không kích hoạt được. Việc phá huỷ = chữ đỏ.
// Bàn phím: Enter/Space/↓ mở, ↑↓ di chuyển, Esc đóng và trả focus về nút "…", Tab đóng menu.

import { useEffect, useId, useRef, useState } from "react";
import { Icon } from "../Icon";
import s from "./MoreMenu.module.css";

export type MoreMenuItem = {
  key: string;
  label: string;
  onSelect?: () => void;
  /** Có giá trị = mục bị chặn; chuỗi là lý do ngắn hiện cạnh nhãn. */
  blockedReason?: string;
  danger?: boolean;
};

export function MoreMenu({ items, label = "Thao tác khác" }: { items: MoreMenuItem[]; label?: string }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const items = () => Array.from(wrapRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);
    items()[0]?.focus();
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      const list = items();
      const at = list.indexOf(document.activeElement as HTMLElement);
      if (e.key === "Escape") {
        e.stopPropagation();
        setOpen(false);
        btnRef.current?.focus();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        list[(at + 1) % list.length]?.focus();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        list[(at - 1 + list.length) % list.length]?.focus();
      } else if (e.key === "Home") {
        e.preventDefault();
        list[0]?.focus();
      } else if (e.key === "End") {
        e.preventDefault();
        list[list.length - 1]?.focus();
      } else if (e.key === "Tab") {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey, true);
    };
  }, [open]);

  if (items.length === 0) return null;
  return (
    <div className={s.wrap} ref={wrapRef}>
      <button
        ref={btnRef}
        type="button"
        className="iconbtn"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon name="more_horiz" />
      </button>
      {open && (
        <div className={s.menu} role="menu" id={menuId} aria-label={label}>
          {items.map((it) => {
            const blocked = Boolean(it.blockedReason);
            return (
              <button
                key={it.key}
                type="button"
                role="menuitem"
                className={`${s.item} ${blocked ? s.blocked : ""} ${it.danger && !blocked ? s.danger : ""}`}
                aria-disabled={blocked || undefined}
                data-blocked={blocked ? "true" : undefined}
                onClick={() => {
                  if (blocked) return;
                  setOpen(false);
                  btnRef.current?.focus();
                  it.onSelect?.();
                }}
              >
                <span className={s.name}>{it.label}</span>
                {blocked && <span className={s.reason}> · {it.blockedReason}</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
