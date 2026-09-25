"use client";

// Đổi sáng/tối, nhớ trên máy (key giống bản HTML cũ: cave_theme). Script chống nháy ở app/layout.tsx.
import { useEffect, useState } from "react";
import { Icon } from "./Icon";

import { THEME_KEY as KEY, syncThemeColor } from "./themeScript";

function isDark(): boolean {
  const t = document.documentElement.getAttribute("data-theme");
  if (t) return t === "dark";
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

export function ThemeToggle() {
  const [dark, setDark] = useState<boolean | null>(null);
  useEffect(() => setDark(isDark()), []);

  const toggle = () => {
    const next = !isDark();
    document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
    try {
      localStorage.setItem(KEY, next ? "dark" : "light");
    } catch {
      /* bỏ qua */
    }
    setDark(next);
    syncThemeColor();
  };

  return (
    <button
      type="button"
      className="iconbtn"
      onClick={toggle}
      aria-label={dark ? "Chuyển giao diện sáng" : "Chuyển giao diện tối"}
      title="Đổi giao diện"
    >
      <Icon name={dark ? "light_mode" : "dark_mode"} />
    </button>
  );
}
