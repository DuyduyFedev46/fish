// Script nhỏ chạy trong <head> trước khi vẽ, để không nháy sai màu sáng/tối.
// Tách khỏi ThemeToggle.tsx ("use client") vì app/layout.tsx là server component.
// Key giống bản HTML cũ (legacy/index.html) để giữ lựa chọn người dùng đã có.
// Màu thanh trình duyệt (<meta name="theme-color">) đọc từ token CSS --canvas (tokens.css), không viết cứng mã màu:
// đồng bộ khi tải trang, khi máy đổi sáng/tối và khi bấm nút đổi giao diện (window.__caveSyncThemeColor).

export const THEME_KEY = "cave_theme";

export const THEME_INIT_SCRIPT = `try{var t=localStorage.getItem("${THEME_KEY}");if(t)document.documentElement.setAttribute("data-theme",t)}catch(e){}
(function(){function s(){try{var c=getComputedStyle(document.documentElement).getPropertyValue("--canvas").trim();if(!c)return;var m=document.querySelector('meta[name="theme-color"]');if(!m){m=document.createElement("meta");m.setAttribute("name","theme-color");document.head.appendChild(m)}m.setAttribute("content",c)}catch(e){}}
window.__caveSyncThemeColor=s;document.addEventListener("DOMContentLoaded",s);try{matchMedia("(prefers-color-scheme: dark)").addEventListener("change",s)}catch(e){}})();`;

/** Gọi sau khi đổi data-theme để thanh trình duyệt đổi màu theo. */
export function syncThemeColor(): void {
  const w = window as unknown as { __caveSyncThemeColor?: () => void };
  w.__caveSyncThemeColor?.();
}
