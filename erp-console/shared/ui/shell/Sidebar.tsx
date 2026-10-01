"use client";

// Menu trái (UI-RULES §2.1): 240 px ↔ 60 px chỉ icon (có tooltip), nhóm theo nghiệp vụ, mục hiện theo quyền.
// Dưới 768 px là ngăn kéo (Shell lo mở/đóng); trạng thái thu gọn chỉ có nghĩa ở màn rộng.
// Mục đang chọn = mục khớp đường dẫn DÀI NHẤT (Shell tính bằng navMatch), mục cha sáng khi đang ở mục con.

import Link from "next/link";
import { Icon } from "../Icon";
import { NAV_SECTIONS, type NavItem } from "@/shared/lib/nav";

type Props = {
  items: NavItem[];
  current: NavItem | undefined;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  /** Ngăn kéo điện thoại đang mở. */
  open: boolean;
  onCloseDrawer: () => void;
  panelRef: React.RefObject<HTMLElement>;
};

function isActive(current: NavItem | undefined, item: NavItem): boolean {
  if (!current) return false;
  return current.key === item.key || current.parent === item.key;
}

export function Sidebar({ items, current, collapsed, onToggleCollapsed, open, onCloseDrawer, panelRef }: Props) {
  const sections = NAV_SECTIONS.filter((sec) => items.some((i) => i.section === sec));
  const toggleLabel = collapsed ? "Mở rộng menu" : "Thu gọn menu";
  return (
    <aside
      id="rail-left"
      ref={panelRef}
      className={`rail-left${open ? " open" : ""}${collapsed ? " collapsed" : ""}`}
      aria-label="Menu chính"
    >
      <div className="brand">
        <div className="mark">
          <Icon name="set_meal" />
        </div>
        <div className="brand-name">
          <b>Cá Về</b>
          <small>Vận hành</small>
        </div>
        <button type="button" className="iconbtn only-mobile" onClick={onCloseDrawer} aria-label="Đóng menu">
          <Icon name="close" />
        </button>
        <button
          type="button"
          className="iconbtn collapse-btn only-wide"
          onClick={onToggleCollapsed}
          aria-label={toggleLabel}
          aria-expanded={!collapsed}
          aria-controls="rail-left-nav"
          title={toggleLabel}
          data-testid="sidebar-toggle"
        >
          <Icon name={collapsed ? "left_panel_open" : "left_panel_close"} />
        </button>
      </div>
      <nav className="nav" id="rail-left-nav" aria-label="Các mục">
        {sections.map((sec) => (
          <div className="nav-group" key={sec || "root"}>
            {sec && <div className="nav-h">{sec}</div>}
            {items
              .filter((i) => i.section === sec)
              .map((i) => {
                const active = isActive(current, i);
                return (
                  <Link
                    key={i.key}
                    href={i.href}
                    className={active ? "active" : undefined}
                    aria-current={active ? "page" : undefined}
                    title={collapsed ? i.label : undefined}
                    aria-label={collapsed ? i.label : undefined}
                  >
                    <Icon name={i.icon} />
                    <span className="nav-label">{i.label}</span>
                  </Link>
                );
              })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
