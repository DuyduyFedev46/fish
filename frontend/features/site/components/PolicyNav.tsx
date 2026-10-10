import Link from "next/link";
import { useId } from "react";
import Icon from "@/components/ui/Icon";
import Skeleton from "@/components/ui/Skeleton";
import s from "./PolicyNav.module.css";

/**
 * PolicyNav (COMPONENTS #36, SHOP-5-04 AC1). Ba biến thể:
 * - `toc`: mục lục trong trang (link neo tới các H2 có id).
 * - `list`: "Các chính sách" cuối trang (điện thoại).
 * - `aside`: cột trái "Chính sách", dính khi cuộn (máy tính).
 * Danh sách chính sách lấy từ CMS (footer-links), không viết cứng. Mục là `<a>`, không là `<button>`.
 */
export interface PolicyNavProps {
  policies: { slug: string; label: string; href: string }[];
  /** Slug trang đang xem; mục khớp có `aria-current="page"`. */
  currentSlug: string;
  toc?: { id: string; label: string }[];
  /** "Cách mua hàng" (máy tính, dưới đường kẻ). */
  extraLinks?: { label: string; href: string; slug?: string }[];
  variant: "toc" | "list" | "aside";
  /** Đang tải danh sách: khung xương 5 vạch. */
  loading?: boolean;
}

export default function PolicyNav({ policies, currentSlug, toc, extraLinks, variant, loading }: PolicyNavProps) {
  const headingId = useId();

  if (variant === "toc") {
    if (!toc || toc.length < 2) return null;
    return (
      <nav className={s.toc} aria-labelledby={headingId}>
        <h2 id={headingId} className={s.tocTitle}>
          Mục lục
        </h2>
        <ol className={s.tocList}>
          {toc.map((t) => (
            <li key={t.id}>
              <a href={`#${t.id}`} className={s.tocLink}>
                {t.label}
              </a>
            </li>
          ))}
        </ol>
      </nav>
    );
  }

  if (loading) {
    return (
      <div className={variant === "aside" ? s.aside : s.list} aria-busy="true">
        <span className="visually-hidden" role="status">
          Đang tải danh sách chính sách
        </span>
        {Array.from({ length: 5 }, (_, i) => (
          <Skeleton key={i} width={`${70 + ((i * 7) % 25)}%`} height={14} />
        ))}
      </div>
    );
  }

  if (policies.length === 0 && (!extraLinks || extraLinks.length === 0)) return null;

  if (variant === "aside") {
    return (
      <nav className={s.aside} aria-labelledby={headingId}>
        <h2 id={headingId} className={s.asideTitle}>
          Chính sách
        </h2>
        <ul className={s.asideList}>
          {policies.map((p) => {
            const current = p.slug === currentSlug;
            return (
              <li key={p.slug}>
                <Link href={p.href} className={s.asideItem} aria-current={current ? "page" : undefined}>
                  {p.label}
                </Link>
              </li>
            );
          })}
        </ul>
        {extraLinks && extraLinks.length > 0 ? (
          <ul className={s.asideExtra}>
            {extraLinks.map((x) => (
              <li key={x.href}>
                <Link
                  href={x.href}
                  className={s.asideItem}
                  aria-current={x.slug && x.slug === currentSlug ? "page" : undefined}
                >
                  {x.label}
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </nav>
    );
  }

  return (
    <nav className={s.list} aria-labelledby={headingId}>
      <h2 id={headingId} className={s.listTitle}>
        Các chính sách
      </h2>
      <ul className={s.listItems}>
        {policies.map((p) => {
          const current = p.slug === currentSlug;
          return (
            <li key={p.slug} className={s.listRow}>
              <Link href={p.href} className={current ? `${s.listLink} ${s.listCurrent}` : s.listLink} aria-current={current ? "page" : undefined}>
                <span>{p.label}</span>
                {current ? (
                  <span className={s.viewing}>Đang xem</span>
                ) : (
                  <span className={s.arrow}>
                    <Icon name="chevron-right" size={16} />
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
