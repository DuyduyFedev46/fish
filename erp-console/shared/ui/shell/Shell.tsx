"use client";

// Khung console 2 cột (ERP theo design, Lô 1): Sidebar thu gọn được + (Topbar + nội dung). Không còn cột phải
// (AI nằm TRONG trang: thanh AI ở danh sách, khối Trợ lý AI ở chi tiết).
// <768px: menu trái thành ngăn kéo (nút ☰) + thanh menu đáy tối đa 5 mục (🟡 T4: chưa thiết kế lại điện thoại).
// Shell không biết gì về đăng nhập: features/auth (ConsoleGate) truyền người dùng + hàm đăng xuất vào.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Icon } from "../Icon";
import { useDrawerFocus } from "../useDrawerFocus";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { CommandSearch } from "./CommandSearch";
import { AI_FEATURES_ENABLED } from "@/shared/lib/features";
import { OfflineBanner, useOffline } from "../states/OfflineBanner";
import {
  ACCOUNT_HREF,
  ACCOUNT_LABEL,
  AI_SETTINGS_HREF,
  canView,
  menuItems,
  navMatch,
  visibleNav,
  type NavItem,
  type Viewer,
} from "@/shared/lib/nav";

export type ShellProps = {
  viewer: Viewer;
  userName: string;
  roleText: string;
  onLogout: () => Promise<void>;
  /** Trang "Tài khoản của tôi" (S47), mở từ menu avatar. */
  accountHref?: string;
  children: React.ReactNode;
};

/** Khoá localStorage nhớ thu gọn menu — CHỈ "collapsed" | "open", không chứa gì khác (không dữ liệu cá nhân). */
export const SIDEBAR_KEY = "cave_ui_sidebar";

function readSidebar(): boolean {
  try {
    return window.localStorage.getItem(SIDEBAR_KEY) === "collapsed";
  } catch {
    return false;
  }
}

function writeSidebar(collapsed: boolean) {
  try {
    window.localStorage.setItem(SIDEBAR_KEY, collapsed ? "collapsed" : "open");
  } catch {
    /* chế độ riêng tư / hết chỗ: bỏ qua, chỉ mất việc nhớ */
  }
}

const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

function titleFor(pathname: string, current: NavItem | undefined): string {
  if (pathname === ACCOUNT_HREF || pathname + "/" === ACCOUNT_HREF) return ACCOUNT_LABEL;
  return current ? current.label : "Cá Về";
}

export function Shell({ viewer, userName, roleText, onLogout, accountHref, children }: ShellProps) {
  const pathname = usePathname() || "/";
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const offline = useOffline();
  const drawerRef = useRef<HTMLElement>(null);
  // Ngăn kéo trên điện thoại: focus vào trong khi mở, giữ Tab, trả focus về nút đã mở khi đóng (UI5).
  useDrawerFocus(drawerOpen, drawerRef, "(max-width: 767px)");

  // Đọc trạng thái nhớ sau khi mount (trước khi vẽ lần đầu lên màn, tránh nháy). Giá trị lạ → coi như mở.
  useIsoLayoutEffect(() => {
    setCollapsed(readSidebar());
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((v) => {
      writeSidebar(!v);
      return !v;
    });
  };

  const items = menuItems(viewer);
  // Mục đang chọn tính trên cả mục không có dòng menu (payments, content-categories…) để mục cha sáng.
  const current = navMatch(pathname, visibleNav(viewer));
  const titleItem = navMatch(pathname);
  // Menu đáy chỉ có mục chính.
  const topItems = items.filter((i) => !i.parent);

  // Đổi trang → đóng ngăn kéo
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  // Esc đóng ngăn kéo
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawerOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  // ⌘K / Ctrl+K mở ô tìm màn hình.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Menu đáy: ≤5 mục thì hiện hết; nhiều hơn thì 4 mục đầu + "Thêm" (mở menu đầy đủ).
  const overflow = topItems.length > 5;
  const bottomItems = overflow ? topItems.slice(0, 4) : topItems;
  const showBottom = topItems.length >= 2;

  const aiSettingsHref = AI_FEATURES_ENABLED && canView(viewer, "ai-settings") ? AI_SETTINGS_HREF : undefined;
  const bottomActive = (i: NavItem) => !!current && (current.key === i.key || current.parent === i.key);

  return (
    <div className={`app${collapsed ? " nav-collapsed" : ""}`}>
      <a className="skip-link" href="#main">
        Bỏ qua menu, tới nội dung
      </a>
      <Sidebar
        items={items}
        current={current}
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
        open={drawerOpen}
        onCloseDrawer={() => setDrawerOpen(false)}
        panelRef={drawerRef}
      />

      <div className="center">
        <Topbar
          title={titleFor(pathname, titleItem)}
          drawerOpen={drawerOpen}
          onOpenDrawer={() => setDrawerOpen((v) => !v)}
          onOpenSearch={() => setSearchOpen(true)}
          userName={userName}
          roleText={roleText}
          accountHref={accountHref}
          aiSettingsHref={aiSettingsHref}
          onLogout={onLogout}
        />

        <main className="content" id="main" tabIndex={-1}>
          {/* Mất mạng: một dải báo chung cho mọi màn (UI-RULES §7); màn đăng ký mốc dữ liệu + Thử lại bằng
              useOfflineRegistration (ListPage, usePagedList đã tự làm). Nội dung cũ mờ đi khi mất mạng. */}
          <OfflineBanner />
          <div className={offline ? "is-stale" : undefined}>{children}</div>
        </main>

        {showBottom && (
          <nav className="bottom-nav" aria-label="Menu nhanh">
            {bottomItems.map((i) => (
              <Link
                key={i.key}
                href={i.href}
                className={bottomActive(i) ? "active" : undefined}
                aria-current={current?.key === i.key ? "page" : bottomActive(i) ? "true" : undefined}
              >
                <Icon name={i.icon} />
                <span className="lbl">{i.short}</span>
              </Link>
            ))}
            {overflow && (
              <button type="button" onClick={() => setDrawerOpen(true)} aria-expanded={drawerOpen} aria-controls="rail-left">
                <Icon name="more_horiz" />
                <span className="lbl">Thêm</span>
              </button>
            )}
          </nav>
        )}
      </div>

      <CommandSearch items={items} open={searchOpen} onOpenChange={setSearchOpen} />

      {drawerOpen && <button type="button" className="scrim" tabIndex={-1} aria-label="Đóng" onClick={() => setDrawerOpen(false)} />}
    </div>
  );
}
