"use client";

// Thanh trên (UI-RULES §2.2): tên màn bên trái; ô tìm ⌘K + avatar bên phải.
// Điện thoại: nút ☰ mở ngăn kéo menu, ô tìm thu thành nút kính lúp. Không nút Làm mới, không đăng xuất rời,
// không nút đổi sáng/tối (🟡 T3).

import { Icon } from "../Icon";
import { AvatarMenu } from "./AvatarMenu";

type Props = {
  title: string;
  drawerOpen: boolean;
  onOpenDrawer: () => void;
  onOpenSearch: () => void;
  userName: string;
  roleText: string;
  accountHref?: string;
  aiSettingsHref?: string;
  onLogout: () => Promise<void>;
};

export function Topbar({ title, drawerOpen, onOpenDrawer, onOpenSearch, userName, roleText, accountHref, aiSettingsHref, onLogout }: Props) {
  return (
    <header className="topbar">
      <button
        type="button"
        className="iconbtn only-mobile"
        onClick={onOpenDrawer}
        aria-label="Mở menu"
        aria-expanded={drawerOpen}
        aria-controls="rail-left"
      >
        <Icon name="menu" />
      </button>
      <h1>{title}</h1>
      <button type="button" className="search-trigger only-wide" onClick={onOpenSearch} aria-label="Tìm màn hình" aria-keyshortcuts="Control+K Meta+K">
        <Icon name="search" />
        <span className="st-text">Tìm màn hình…</span>
        <kbd>⌘K</kbd>
      </button>
      <button type="button" className="iconbtn only-mobile" onClick={onOpenSearch} aria-label="Tìm màn hình">
        <Icon name="search" />
      </button>
      <AvatarMenu
        userName={userName}
        roleText={roleText}
        accountHref={accountHref}
        aiSettingsHref={aiSettingsHref}
        onLogout={onLogout}
      />
    </header>
  );
}
