"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { GroupIcon, ItemImage } from "@/lib/types";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import s from "./CategoryTile.module.css";

export interface CategoryTileProps {
  label: string;
  href: string;
  icon: GroupIcon;
  /** Ảnh đại diện của mục danh mục (lấy từ món đầu tiên có ảnh trong nhóm). */
  image?: ItemImage | null;
  /** Số món (không phải kg). Chỉ hiện ở cỡ md. */
  itemCount?: number;
  /** sm: điện thoại. md: máy tính (có số món). auto (mặc định): sm dưới 768 px, md từ 768 px, bằng CSS. */
  size?: "sm" | "md" | "auto";
}

/** Ô icon/ảnh nhóm hàng. Cả ô là một link, vùng chạm ≥ 44. */
export default function CategoryTile({ label, href, icon, image, itemCount, size = "auto" }: CategoryTileProps) {
  const showCount = size !== "sm" && itemCount !== undefined;
  const src = image?.urls?.thumb || image?.urls?.card || image?.urls?.detail || "";
  const [broken, setBroken] = useState(false);

  useEffect(() => {
    setBroken(false);
  }, [src]);

  const showImage = Boolean(src) && !broken;

  return (
    <Link
      href={href}
      className={cx(s.tile, s[size])}
      aria-label={showCount ? `${label}, ${itemCount} món` : label}
    >
      <span className={cx(s.iconBox, showImage && s.iconBoxHasImg)}>
        {showImage ? (
          <img
            src={src}
            alt={image?.alt || label}
            loading="lazy"
            className={s.thumbImg}
            onError={() => setBroken(true)}
          />
        ) : (
          <Icon name={icon} size={26} strokeWidth={1.5} />
        )}
      </span>
      <span className={s.label}>{label}</span>
      {showCount ? <span className={cx(s.count, "num")}>{itemCount} món</span> : null}
    </Link>
  );
}
