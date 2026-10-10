import Link from "next/link";
import type { AnchorHTMLAttributes } from "react";
import Icon, { type IconName } from "./Icon";
import { cx, isInternalHref } from "./cx";
import s from "./TextLink.module.css";

export interface TextLinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> {
  href: string;
  variant?: "inline" | "standalone" | "nav" | "on-brand" | "danger-inline";
  /** true: mở tab mới (target="_blank" rel="noopener") kèm chữ ẩn "(mở tab mới)". */
  external?: boolean;
  /** true: aria-current="page". */
  current?: boolean;
  iconEnd?: IconName;
}

const VARIANT: Record<NonNullable<TextLinkProps["variant"]>, string> = {
  inline: s.inline,
  standalone: s.standalone,
  nav: s.nav,
  "on-brand": s.onBrand,
  "danger-inline": s.dangerInline,
};

export default function TextLink({
  href,
  variant = "inline",
  external = false,
  current = false,
  iconEnd,
  className,
  children,
  ...rest
}: TextLinkProps) {
  const classes = cx(s.link, VARIANT[variant], className);
  const content = (
    <>
      {children}
      {external ? <span className="visually-hidden"> (mở tab mới)</span> : null}
      {iconEnd ? <Icon name={iconEnd} size={16} /> : null}
    </>
  );
  const common = { ...rest, className: classes, "aria-current": current ? ("page" as const) : undefined };
  if (!external && isInternalHref(href)) {
    return (
      <Link href={href} {...common}>
        {content}
      </Link>
    );
  }
  return (
    <a href={href} {...common} {...(external ? { target: "_blank", rel: "noopener" } : {})}>
      {content}
    </a>
  );
}
