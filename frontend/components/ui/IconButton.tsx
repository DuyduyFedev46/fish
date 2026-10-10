import Link from "next/link";
import type { ButtonHTMLAttributes } from "react";
import Icon, { type IconName } from "./Icon";
import { cx, isInternalHref } from "./cx";
import s from "./IconButton.module.css";

/** Badge số món trong giỏ (không phải tổng kg). Số 0 hoặc không có số thì không render. */
export function CartBadge({ count, tone = "accent" }: { count?: number; tone?: "accent" | "surface" }) {
  if (!count || count <= 0) return null;
  return (
    // key theo số để badge chạy lại hiệu ứng khi đổi số
    <span key={count} className={cx(s.badge, tone === "surface" && s.badgeSurface, "num")} aria-hidden="true">
      {count > 99 ? "99+" : count}
    </span>
  );
}

export interface IconButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type" | "aria-label"> {
  /** Bắt buộc: thành aria-label, ghi rõ đối tượng ("Bỏ Cá thu khỏi giỏ"). */
  label: string;
  icon: IconName;
  variant?: "ghost" | "on-brand" | "close" | "danger-ghost";
  /** Có thì render <a>. */
  href?: string;
  /** undefined: không badge; 0: ẩn badge. */
  badgeCount?: number;
  iconSize?: number;
  /** Màu badge: trên nền accent dùng "surface" (nền trắng), trên nền trắng dùng "accent". */
  badgeTone?: "accent" | "surface";
}

const VARIANT: Record<NonNullable<IconButtonProps["variant"]>, string> = {
  ghost: s.ghost,
  "on-brand": s.onBrand,
  close: s.close,
  "danger-ghost": s.dangerGhost,
};

export default function IconButton({
  label,
  icon,
  variant = "ghost",
  href,
  badgeCount,
  badgeTone,
  iconSize = 21,
  className,
  ...rest
}: IconButtonProps) {
  const classes = cx(s.btn, VARIANT[variant], className);
  const tone = badgeTone ?? (variant === "on-brand" ? "surface" : "accent");
  const inner = (
    <>
      <Icon name={icon} size={iconSize} />
      <CartBadge count={badgeCount} tone={tone} />
    </>
  );
  if (href !== undefined) {
    return isInternalHref(href) ? (
      <Link href={href} className={classes} aria-label={label}>
        {inner}
      </Link>
    ) : (
      <a href={href} className={classes} aria-label={label}>
        {inner}
      </a>
    );
  }
  return (
    <button {...rest} type="button" className={classes} aria-label={label}>
      {inner}
    </button>
  );
}
