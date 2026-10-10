import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import Spinner from "./Spinner";
import { cx, isInternalHref } from "./cx";
import s from "./Button.module.css";

export type ButtonVariant =
  | "primary"
  | "outline"
  | "secondary"
  | "ghost"
  | "danger"
  | "danger-text"
  | "on-brand"
  | "on-brand-outline";

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type"> {
  variant?: ButtonVariant;
  size?: "lg" | "md" | "sm";
  shape?: "rounded" | "pill";
  type?: "button" | "submit";
  loading?: boolean;
  loadingText?: string;
  iconStart?: ReactNode;
  iconEnd?: ReactNode;
  fullWidth?: boolean;
  /** Có thì render <a> (next/link nếu là route nội bộ). */
  href?: string;
  /** true: target="_blank" rel="noopener". */
  external?: boolean;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: s.primary,
  outline: s.outline,
  secondary: s.secondary,
  ghost: s.ghost,
  danger: s.danger,
  "danger-text": s.dangerText,
  "on-brand": s.onBrand,
  "on-brand-outline": s.onBrandOutline,
};

export default function Button({
  variant = "primary",
  size = "md",
  shape,
  type = "button",
  loading = false,
  loadingText,
  iconStart,
  iconEnd,
  fullWidth = false,
  href,
  external = false,
  className,
  children,
  disabled,
  onClick,
  ...rest
}: ButtonProps) {
  const effectiveShape = shape ?? (size === "lg" ? "pill" : "rounded");
  const classes = cx(
    s.btn,
    VARIANT_CLASS[variant],
    s[size],
    effectiveShape === "pill" ? s.pill : s.rounded,
    fullWidth && s.full,
    className
  );
  const label = loading && loadingText ? loadingText : children;
  const content = (
    <>
      {loading ? <Spinner size={18} /> : iconStart}
      <span className={s.label}>{label}</span>
      {!loading && iconEnd}
    </>
  );

  if (href !== undefined && !disabled && !loading) {
    // Giữ lại nhãn truy cập khi nút render thành link.
    const a11y = {
      "aria-label": rest["aria-label"],
      "aria-describedby": rest["aria-describedby"],
    };
    if (!external && isInternalHref(href)) {
      return (
        <Link href={href} className={classes} {...a11y}>
          {content}
        </Link>
      );
    }
    return (
      <a
        href={href}
        className={classes}
        {...a11y}
        {...(external ? { target: "_blank", rel: "noopener" } : {})}
      >
        {content}
        {external ? <span className="visually-hidden"> (mở tab mới)</span> : null}
      </a>
    );
  }

  return (
    <button
      {...rest}
      type={type}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      onClick={loading ? undefined : onClick}
    >
      {content}
    </button>
  );
}
