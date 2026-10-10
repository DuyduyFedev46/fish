import Link from "next/link";
import type { GroupIcon } from "@/lib/types";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import s from "./CategoryTile.module.css";

export interface CategoryTileProps {
  label: string;
  href: string;
  icon: GroupIcon;
  /** Số món (không phải kg). Chỉ hiện ở cỡ md. */
  itemCount?: number;
  /** sm: điện thoại. md: máy tính (có số món). auto (mặc định): sm dưới 768 px, md từ 768 px, bằng CSS. */
  size?: "sm" | "md" | "auto";
}

/** Ô icon nhóm hàng. Cả ô là một link, vùng chạm ≥ 44. */
export default function CategoryTile({ label, href, icon, itemCount, size = "auto" }: CategoryTileProps) {
  const showCount = size !== "sm" && itemCount !== undefined;
  return (
    <Link
      href={href}
      className={cx(s.tile, s[size])}
      aria-label={showCount ? `${label}, ${itemCount} món` : undefined}
    >
      <span className={s.iconBox}>
        <Icon name={icon} size={26} strokeWidth={1.5} />
      </span>
      <span className={s.label}>{label}</span>
      {showCount ? <span className={cx(s.count, "num")}>{itemCount} món</span> : null}
    </Link>
  );
}
