import Link from "next/link";
import Icon, { type IconName } from "./Icon";
import { cx, isInternalHref } from "./cx";
import s from "./Chip.module.css";

export interface ChipProps {
  label: string;
  /** filter: lọc nhóm hàng / chuyên mục. link: gợi ý nhóm, tìm gần đây. */
  variant?: "filter" | "link";
  /** Có thì render <a> (đổi URL, nút Back hoạt động); thiếu thì <button>. */
  href?: string;
  selected?: boolean;
  onClick?: () => void;
  icon?: IconName;
}

export default function Chip({ label, variant = "filter", href, selected = false, onClick, icon }: ChipProps) {
  const classes = cx(s.chip, variant === "link" ? s.link : s.filter, selected && s.selected);
  const content = (
    <>
      {icon ? <Icon name={icon} size={16} /> : null}
      {label}
    </>
  );
  if (href !== undefined) {
    const current = selected ? { "aria-current": "page" as const } : {};
    return isInternalHref(href) ? (
      <Link href={href} className={classes} {...current}>
        {content}
      </Link>
    ) : (
      <a href={href} className={classes} {...current}>
        {content}
      </a>
    );
  }
  return (
    <button type="button" className={classes} aria-pressed={selected} onClick={onClick}>
      {content}
    </button>
  );
}
