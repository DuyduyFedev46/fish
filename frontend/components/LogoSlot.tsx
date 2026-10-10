"use client";

import Link from "next/link";
import { useState } from "react";
import type { MouseEvent } from "react";
import { cx } from "./ui/cx";
import s from "./LogoSlot.module.css";

export interface LogoSlotProps {
  /** Cỡ logo: 28 (H2) · 30 (H1 điện thoại) · 36 (rút gọn, footer máy tính) · 40 (H1 máy tính). */
  size?: 28 | 30 | 36 | 40;
  /** light: nền trắng. brand: nền accent hoặc brand-deep. */
  tone?: "light" | "brand";
  showTagline?: boolean;
  /** Đường dẫn file logo trong frontend/public. Chưa có file thì chỉ hiện chữ "Cá Về". */
  src?: string;
  href?: string;
  onClick?: (e: MouseEvent<HTMLAnchorElement>) => void;
}

/** Chỗ logo + chữ "Cá Về". Chưa có file logo thì chỉ có chữ; ảnh hỏng cũng về chữ. */
export default function LogoSlot({
  size = 28,
  tone = "light",
  showTagline = false,
  src,
  href = "/",
  onClick,
}: LogoSlotProps) {
  const [broken, setBroken] = useState(false);
  return (
    <Link
      href={href}
      className={cx(s.logo, tone === "brand" ? s.brand : s.light, s[`size${size}`])}
      aria-label="Cá Về — trang chủ"
      onClick={onClick}
    >
      {src && !broken ? (
        <img src={src} width={size} height={size} alt="" className={s.mark} onError={() => setBroken(true)} />
      ) : null}
      <span className={s.words}>
        <span className={s.name}>Cá Về</span>
        {showTagline ? <span className={s.tagline}>Từ cảng về bếp nhà bạn</span> : null}
      </span>
    </Link>
  );
}
