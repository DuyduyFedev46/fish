"use client";

// Bố cục console (S7): menu trái · nội dung · cột phải.
// <768px: menu trái thành ngăn kéo (nút ☰) + thanh menu đáy tối đa 5 mục; cột phải là ngăn kéo.
// 768–1023px: menu trái cố định, cột phải là ngăn kéo.
// ≥1024px: 3 cột.
// Shell không biết gì về đăng nhập: features/auth (ConsoleGate) truyền người dùng + hàm đăng xuất vào.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";
import { RightRail } from "./RightRail";
import { ThemeToggle } from "./ThemeToggle";
import { useDrawerFocus } from "./useDrawerFocus";
import { ACCOUNT_HREF, ACCOUNT_LABEL, NAV, visibleNav, type NavItem, type Viewer } from "@/shared/lib/nav";

export type ShellProps = {
  viewer: Viewer;
  userName: string;
  roleText: string;
  onLogout: () => Promise<void>;
  /** Trang "Tài khoản của tôi" (S47) — bấm vào tên người dùng ở chân menu để mở. */
  accountHref?: string;
  /** Nội dung tab "Trợ lý" của cột phải (S45). Bỏ trống = "sắp có". */
  assistant?: React.ReactNode;
  /** Nội dung tab "Hoạt động" của cột phải (S8). */
  activity?: React.ReactNode;
  children: React.ReactNode;
};

function isActive(pathname: string, item: NavItem): boolean {
  return pathname === item.href || pathname.startsWith(item.href) || pathname + "/" === item.href;
}

function titleFor(pathname: string): string {
  if (pathname === ACCOUNT_HREF || pathname + "/" === ACCOUNT_HREF) return ACCOUNT_LABEL;
  const item = NAV.find((n) => isActive(pathname, n));
  return item ? item.label : "Cá Về";
}

export function Shell({ viewer, userName, roleText, onLogout, accountHref, assistant, activity, children }: ShellProps) {
  const pathname = usePathname() || "/";
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const leftRef = useRef<HTMLElement>(null);
  const rightRef = useRef<HTMLElement>(null);
  // Ngăn kéo trên điện thoại: focus vào trong khi mở, giữ Tab, trả focus về nút đã mở khi đóng (UI5).
  useDrawerFocus(leftOpen, leftRef, "(max-width: 767px)");
  useDrawerFocus(rightOpen, rightRef, "(max-width: 1023px)");

  const items = visibleNav(viewer);
  const sections = Array.from(new Set(items.map((i) => i.section)));

  // Đổi trang → đóng ngăn kéo
  useEffect(() => {
    setLeftOpen(false);
    setRightOpen(false);
  }, [pathname]);

  // Esc đóng ngăn kéo
  useEffect(() => {
    if (!leftOpen && !rightOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setLeftOpen(false);
        setRightOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [leftOpen, rightOpen]);

  // Menu đáy: ≤5 mục thì hiện hết; nhiều hơn thì 4 mục đầu + "Thêm" (mở menu đầy đủ).
  const overflow = items.length > 5;
  const bottomItems = overflow ? items.slice(0, 4) : items;
  const showBottom = items.length >= 2;

  const doLogout = async () => {
    setLoggingOut(true);
    await onLogout();
  };

  const title = titleFor(pathname);

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Bỏ qua menu, tới nội dung
      </a>
      <aside id="rail-left" ref={leftRef} className={`rail-left${leftOpen ? " open" : ""}`} aria-label="Menu chính">
        <div className="brand">
          <div className="mark">
            <Icon name="set_meal" />
          </div>
          <div className="brand-name">
            <b>Cá Về</b>
            <small>Vận hành</small>
          </div>
          <button type="button" className="iconbtn only-mobile" onClick={() => setLeftOpen(false)} aria-label="Đóng menu">
            <Icon name="close" />
          </button>
        </div>
        <nav className="nav" aria-label="Các mục">
          {sections.map((sec) => (
            <div key={sec}>
              <div className="nav-h">{sec}</div>
              {items
                .filter((i) => i.section === sec)
                .map((i) => (
                  <Link
                    key={i.key}
                    href={i.href}
                    className={isActive(pathname, i) ? "active" : undefined}
                    aria-current={isActive(pathname, i) ? "page" : undefined}
                  >
                    <Icon name={i.icon} />
                    {i.label}
                  </Link>
                ))}
            </div>
          ))}
        </nav>
        <div className="who">
          {(() => {
            const inner = (
              <>
                <div className="avatar" aria-hidden="true">
                  {(userName || "?").charAt(0).toUpperCase()}
                </div>
                <div className="meta">
                  <b>{userName}</b>
                  <span>{roleText}</span>
                </div>
              </>
            );
            if (!accountHref) return <div className="who-link">{inner}</div>;
            const here = pathname === accountHref || pathname + "/" === accountHref;
            return (
              <Link
                href={accountHref}
                className={`who-link${here ? " active" : ""}`}
                aria-current={here ? "page" : undefined}
                title="Tài khoản và quyền của tôi"
              >
                {inner}
              </Link>
            );
          })()}
          <button
            type="button"
            className="iconbtn"
            onClick={doLogout}
            disabled={loggingOut}
            aria-label="Đăng xuất"
            title="Đăng xuất"
          >
            <Icon name={loggingOut ? "progress_activity" : "logout"} className={loggingOut ? "spin" : undefined} />
          </button>
        </div>
      </aside>

      <div className="center">
        <header className="topbar">
          <button
            type="button"
            className="iconbtn only-mobile"
            onClick={() => {
              setRightOpen(false);
              setLeftOpen((v) => !v);
            }}
            aria-label="Mở menu"
            aria-expanded={leftOpen}
            aria-controls="rail-left"
          >
            <Icon name="menu" />
          </button>
          <h1>{title}</h1>
          <ThemeToggle />
          <button
            type="button"
            className="iconbtn only-narrow"
            onClick={() => {
              setLeftOpen(false);
              setRightOpen((v) => !v);
            }}
            aria-label="Mở ghi chú, trợ lý, hoạt động"
            aria-expanded={rightOpen}
            aria-controls="rail-right"
          >
            <Icon name="edit_note" />
          </button>
        </header>

        <main className="content" id="main" tabIndex={-1}>
          {children}
        </main>

        {showBottom && (
          <nav className="bottom-nav" aria-label="Menu nhanh">
            {bottomItems.map((i) => (
              <Link
                key={i.key}
                href={i.href}
                className={isActive(pathname, i) ? "active" : undefined}
                aria-current={isActive(pathname, i) ? "page" : undefined}
              >
                <Icon name={i.icon} />
                <span className="lbl">{i.short}</span>
              </Link>
            ))}
            {overflow && (
              <button
                type="button"
                onClick={() => setLeftOpen(true)}
                aria-expanded={leftOpen}
                aria-controls="rail-left"
              >
                <Icon name="more_horiz" />
                <span className="lbl">Thêm</span>
              </button>
            )}
          </nav>
        )}
      </div>

      <RightRail
        panelRef={rightRef}
        open={rightOpen}
        onClose={() => setRightOpen(false)}
        assistant={assistant}
        activity={activity}
      />

      {(leftOpen || rightOpen) && (
        <button
          type="button"
          className="scrim"
          tabIndex={-1}
          aria-label="Đóng"
          onClick={() => {
            setLeftOpen(false);
            setRightOpen(false);
          }}
        />
      )}
    </div>
  );
}
