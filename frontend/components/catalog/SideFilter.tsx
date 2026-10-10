import Link from "next/link";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import s from "./SideFilter.module.css";

export interface SideFilterProps {
  groups: { slug: string; label: string; count: number; href: string }[];
  /** "all" khi đang xem tất cả. */
  currentSlug: string;
  /** Câu luật mua dựng từ `min_qty` và `qty_step`. */
  rulesText?: string;
}

/** Cột lọc nhóm hàng có đếm món (máy tính). Mục là link để nút Back và link chia sẻ đúng. */
export default function SideFilter({ groups, currentSlug, rulesText }: SideFilterProps) {
  return (
    <aside className={s.aside} aria-labelledby="side-filter-title">
      <nav className={s.box} aria-labelledby="side-filter-title">
        <h2 id="side-filter-title" className={s.title}>
          Danh mục
        </h2>
        <ul className={s.list}>
          {groups.map((g) => {
            const current = g.slug === currentSlug;
            return (
              <li key={g.slug}>
                <Link
                  href={g.href}
                  className={cx(s.link, current && s.current)}
                  aria-current={current ? "page" : undefined}
                >
                  <span>{g.label}</span>
                  <span className={cx(s.count, "num")}>
                    {g.count}
                    <span className="visually-hidden"> món</span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      {rulesText ? (
        <p className={s.rules}>
          <Icon name="info" size={18} />
          <span>{rulesText}</span>
        </p>
      ) : null}
    </aside>
  );
}
