import Link from "next/link";
import Icon, { type IconName } from "./ui/Icon";
import { CartBadge } from "./ui/IconButton";
import { cx } from "./ui/cx";
import { CART_HREF, CATALOG_HREF, ORDERS_HREF } from "./shopLinks";
import s from "./BottomNav.module.css";

export type BottomNavTab = "home" | "catalog" | "cart" | "orders";

export interface BottomNavProps {
  /** Mục đang ở; null khi trang không thuộc 4 mục (vd. Góc bếp). */
  current: BottomNavTab | null;
  /** Số món trong giỏ. */
  cartCount: number;
}

const TABS: { key: BottomNavTab; label: string; href: string; icon: IconName }[] = [
  { key: "home", label: "Trang chủ", href: "/", icon: "home" },
  { key: "catalog", label: "Danh mục", href: CATALOG_HREF, icon: "grid" },
  { key: "cart", label: "Giỏ hàng", href: CART_HREF, icon: "cart" },
  { key: "orders", label: "Đơn hàng", href: ORDERS_HREF, icon: "receipt" },
];

/** Thanh điều hướng đáy của điện thoại: đúng 4 mục, ẩn từ 768 px. */
export default function BottomNav({ current, cartCount }: BottomNavProps) {
  return (
    <nav className={s.nav} aria-label="Điều hướng chính">
      {TABS.map((tab) => {
        const isCurrent = tab.key === current;
        const label =
          tab.key === "cart" && cartCount > 0 ? `${tab.label}, ${cartCount} món` : undefined;
        return (
          <Link
            key={tab.key}
            href={tab.href}
            className={cx(s.item, isCurrent && s.current)}
            aria-current={isCurrent ? "page" : undefined}
            aria-label={label}
          >
            <span className={s.iconWrap}>
              <Icon name={tab.icon} size={22} strokeWidth={1.8} />
              {tab.key === "cart" ? (
                <span className={s.badgeSlot}>
                  <CartBadge count={cartCount} />
                </span>
              ) : null}
            </span>
            <span className={s.label}>{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
