"use client";

// Menu tài khoản ở góc phải topbar (UI-RULES §2.2): Tài khoản của tôi · AI của tôi · Đăng xuất.
// Bàn phím: Enter/Space/mũi tên xuống mở, Esc đóng (trả focus về nút), mũi tên lên/xuống/Home/End di chuyển.
// Không nút đăng xuất ở chỗ nào khác của khung.

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { Icon } from "../Icon";

type Props = {
  userName: string;
  roleText: string;
  accountHref?: string;
  /** Bỏ trống = người này không có màn "AI của tôi" → menu chỉ còn 2 dòng. */
  aiSettingsHref?: string;
  onLogout: () => Promise<void>;
};

export function AvatarMenu({ userName, roleText, accountHref, aiSettingsHref, onLogout }: Props) {
  const [open, setOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const initial = (userName || "?").trim().charAt(0).toUpperCase();

  const items = () => Array.from(menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not([aria-disabled="true"])') ?? []);

  // Mở bằng bàn phím → focus mục đầu; đóng khi bấm ra ngoài hoặc Esc.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const close = (refocus: boolean) => {
    setOpen(false);
    if (refocus) btnRef.current?.focus();
  };

  const onMenuKey = (e: React.KeyboardEvent) => {
    const list = items();
    const idx = list.indexOf(document.activeElement as HTMLElement);
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      close(true);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      list[(idx + 1) % list.length]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      list[(idx - 1 + list.length) % list.length]?.focus();
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

  const focusFirstSoon = () => requestAnimationFrame(() => items()[0]?.focus());

  const doLogout = async () => {
    setLoggingOut(true);
    await onLogout();
  };

  return (
    <div className="avatar-wrap" ref={wrapRef}>
      <button
        ref={btnRef}
        type="button"
        className="avatar-btn"
        aria-label={`Tài khoản ${userName}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => {
          setOpen((v) => !v);
          if (!open) focusFirstSoon();
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" && !open) {
            e.preventDefault();
            setOpen(true);
            focusFirstSoon();
          }
        }}
      >
        <span className="avatar" aria-hidden="true">
          {initial}
        </span>
      </button>
      {open && (
        <div id={menuId} ref={menuRef} className="avatar-menu" role="menu" aria-label="Tài khoản" onKeyDown={onMenuKey}>
          <div className="am-head">
            <span className="avatar" aria-hidden="true">
              {initial}
            </span>
            <span className="am-who">
              <b>{userName}</b>
              <span>{roleText}</span>
            </span>
          </div>
          {accountHref && (
            <Link href={accountHref} role="menuitem" className="am-item" tabIndex={-1} onClick={() => setOpen(false)}>
              <Icon name="person" />
              Tài khoản của tôi
            </Link>
          )}
          {aiSettingsHref && (
            <Link href={aiSettingsHref} role="menuitem" className="am-item" tabIndex={-1} onClick={() => setOpen(false)}>
              <Icon name="auto_awesome" />
              AI của tôi
            </Link>
          )}
          <button
            type="button"
            role="menuitem"
            className="am-item crit"
            tabIndex={-1}
            onClick={doLogout}
            disabled={loggingOut}
          >
            <Icon name={loggingOut ? "progress_activity" : "logout"} className={loggingOut ? "spin" : undefined} />
            Đăng xuất
          </button>
        </div>
      )}
    </div>
  );
}
