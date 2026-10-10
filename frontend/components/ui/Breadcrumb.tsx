import Link from "next/link";
import { Fragment } from "react";
import s from "./Breadcrumb.module.css";

export interface BreadcrumbProps {
  /** Phần tử cuối là trang hiện tại (không có href). */
  items: { label: string; href?: string }[];
}

/** Đường dẫn vị trí trang (máy tính). Mục cuối là chữ, không phải link. */
export default function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav aria-label="Đường dẫn" className={s.nav}>
      <ol className={s.list}>
        {items.map((it, i) => {
          const last = i === items.length - 1;
          return (
            <Fragment key={`${i}-${it.label}`}>
              <li className={s.item}>
                {last || !it.href ? (
                  <span className={s.current} aria-current={last ? "page" : undefined}>
                    {it.label}
                  </span>
                ) : (
                  <Link href={it.href} className={s.link}>
                    {it.label}
                  </Link>
                )}
              </li>
              {!last ? (
                <li className={s.sep} aria-hidden="true">
                  /
                </li>
              ) : null}
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
