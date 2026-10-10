"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { MouseEvent } from "react";
import LogoSlot from "./LogoSlot";
import { useSearchSuggest } from "@/features/catalog/useSearchSuggest";
import SearchBox from "./search/SearchBox";
import Icon from "./ui/Icon";
import IconButton, { CartBadge } from "./ui/IconButton";
import Skeleton from "./ui/Skeleton";
import { cx } from "./ui/cx";
import {
  ABOUT_HREF,
  CART_HREF,
  HOW_TO_BUY_HREF,
  KITCHEN_HREF,
  ORDERS_HREF,
  telHref,
} from "./shopLinks";
import s from "./ShopHeader.module.css";

export interface NavGroup {
  slug: string;
  label: string;
  href: string;
  /** Nhóm con (chưa có dữ liệu, L-20): có thì mới vẽ nút mũi tên. Hiện chưa dùng. */
  children?: { label: string; href: string }[];
}

export interface ShopHeaderProps {
  /** home: H1 (cuộn thì thu về H2). sticky: H2. sub: H3 trang con. checkout: H4 bước đặt hàng. */
  variant: "home" | "sticky" | "sub" | "checkout";
  /** Máy tính: full (2 tầng + menu) hoặc compact (Giỏ, Đặt hàng, Thanh toán). */
  desktopVariant?: "full" | "compact";
  /** Tiêu đề ở H3/H4. */
  title?: string;
  /** Đích khi không có lịch sử để quay lại. H3: /shop/. H4: /shop/cart/. */
  backHref?: string;
  /** Chặn quay lại (rời trang thanh toán). */
  onBack?: (e: MouseEvent) => void;
  onBrandClick?: (e: MouseEvent<HTMLAnchorElement>) => void;
  /** H3 có nút giỏ hay không (giỏ hàng không có). */
  showCart?: boolean;
  /** Số món trong giỏ (không phải kg). */
  cartCount: number;
  hotline?: string;
  /** Menu nhóm máy tính, một cấp. undefined: chưa có (lỗi hoặc đang tải). */
  groups?: NavGroup[];
  groupsLoading?: boolean;
  currentGroupSlug?: string;
  /** Để đặt aria-current cho "Tra cứu đơn", "Góc bếp". */
  currentPath?: string;
  /** Dải chữ trên cùng của máy tính. */
  introText?: string;
  logoSrc?: string;
}

const PLACEHOLDER_MOBILE = "Tìm cá, tôm, mực, combo…";
const PLACEHOLDER_DESKTOP = "Tìm cá thu, mực ống, tôm sú, combo lẩu…";

function useGoBack(backHref: string) {
  const router = useRouter();
  return (e?: MouseEvent) => {
    e?.preventDefault();
    // Vào thẳng từ link chia sẻ thì không có lịch sử của Shop: về trang dự phòng.
    let sameOrigin = false;
    try {
      sameOrigin = !!document.referrer && new URL(document.referrer).origin === window.location.origin;
    } catch {
      sameOrigin = false;
    }
    if (window.history.length > 1 && sameOrigin) router.back();
    else router.push(backHref);
  };
}

/** Ô tìm của header kèm gợi ý khi gõ (SHOP-2-04). Header được phép đọc catalog (cache sẵn). */
function HeaderSearch({ placeholder }: { placeholder: string }) {
  const search = useSearchSuggest();
  return <SearchBox variant="brand" placeholder={placeholder} {...search} />;
}

function cartLabel(count: number) {
  return count > 0 ? `Giỏ hàng, ${count} món` : "Giỏ hàng";
}

/* ------------------------------------------------------------------ điện thoại */

function MobileHome({ cartCount, hotline, onBrandClick, logoSrc }: ShopHeaderProps) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [stuck, setStuck] = useState(false);

  // H1 thu về H2 dính khi cuộn qua ô tìm.
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(([entry]) => {
      setStuck(!entry.isIntersecting && entry.boundingClientRect.top < 0);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <header className={cx(s.mobile, s.h1)}>
        <div className={s.h1Row}>
          <LogoSlot size={30} tone="brand" showTagline src={logoSrc} onClick={onBrandClick} />
          <nav className={s.actions} aria-label="Tài khoản và giỏ">
            {hotline ? (
              <IconButton label="Gọi hotline Cá Về" icon="phone" variant="on-brand" href={telHref(hotline)} />
            ) : null}
            <IconButton label="Tra cứu đơn hàng" icon="receipt" variant="on-brand" href={ORDERS_HREF} />
            <IconButton
              label={cartLabel(cartCount)}
              icon="cart"
              variant="on-brand"
              href={CART_HREF}
              badgeCount={cartCount}
            />
          </nav>
        </div>
        <HeaderSearch placeholder={PLACEHOLDER_MOBILE} />
        <div ref={sentinelRef} className={s.sentinel} aria-hidden="true" />
      </header>
      <header className={cx(s.mobile, s.bar, s.fixedBar, stuck && s.fixedBarShown)}>
        <div className={s.barLogo}>
          <LogoSlot size={28} src={logoSrc} onClick={onBrandClick} />
        </div>
        <IconButton label="Tìm sản phẩm" icon="search" href="/shop/?focus=search" />
        <IconButton label={cartLabel(cartCount)} icon="cart" href={CART_HREF} badgeCount={cartCount} />
      </header>
    </>
  );
}

function MobileSticky({ cartCount, onBrandClick, logoSrc }: ShopHeaderProps) {
  return (
    <header className={cx(s.mobile, s.bar, s.stickyBar)}>
      <div className={s.barLogo}>
        <LogoSlot size={28} src={logoSrc} onClick={onBrandClick} />
      </div>
      <IconButton label="Tìm sản phẩm" icon="search" href="/shop/?focus=search" />
      <IconButton label={cartLabel(cartCount)} icon="cart" href={CART_HREF} badgeCount={cartCount} />
    </header>
  );
}

function MobileSub({ title, backHref = "/shop/", onBack, showCart = true, cartCount }: ShopHeaderProps) {
  const goBack = useGoBack(backHref);
  return (
    <header className={cx(s.mobile, s.bar, s.sub)}>
      <IconButton label="Quay lại" icon="chevron-left" iconSize={22} onClick={(e) => (onBack ? onBack(e) : goBack(e))} />
      <span className={s.subTitle}>{title}</span>
      {showCart ? (
        <IconButton label={cartLabel(cartCount)} icon="cart" href={CART_HREF} badgeCount={cartCount} />
      ) : (
        <span className={s.spacer} aria-hidden="true" />
      )}
    </header>
  );
}

function MobileCheckout({ title, backHref = "/shop/cart/", onBack }: ShopHeaderProps) {
  const router = useRouter();
  return (
    <header className={cx(s.mobile, s.bar, s.checkout)}>
      <IconButton
        label="Quay lại giỏ hàng"
        icon="chevron-left"
        iconSize={22}
        onClick={(e) => (onBack ? onBack(e) : router.push(backHref))}
      />
      <h1 className={s.checkoutTitle}>{title}</h1>
      <span className={s.secure}>
        <Icon name="lock" size={14} strokeWidth={2} />
        Bảo mật
      </span>
    </header>
  );
}

/* ------------------------------------------------------------------ máy tính */

function DesktopFull(props: ShopHeaderProps) {
  const {
    cartCount,
    hotline,
    groups,
    groupsLoading,
    currentGroupSlug,
    currentPath = "",
    introText,
    onBrandClick,
    logoSrc,
  } = props;
  const onOrders = currentPath.startsWith("/shop/orders");
  const onKitchen = currentPath.startsWith("/blog");

  return (
    // display: contents: các tầng là con trực tiếp của khung trang, nên chỉ tầng chính dính được (position: sticky).
    <header className={cx(s.desktop, s.full)}>
      <div className={s.strip}>
        <div className={cx("container", s.stripInner)}>
          <span>{introText}</span>
          <span className={s.stripLinks}>
            <Link href={HOW_TO_BUY_HREF} className={s.stripLink}>
              Cách mua hàng
            </Link>
            <Link href={ABOUT_HREF} className={s.stripLink}>
              Về Cá Về
            </Link>
          </span>
        </div>
      </div>
      <div className={s.main}>
        <div className={cx("container", s.mainInner)}>
          <LogoSlot size={40} tone="brand" showTagline src={logoSrc} onClick={onBrandClick} />
          <div className={s.search}>
            <HeaderSearch placeholder={PLACEHOLDER_DESKTOP} />
          </div>
          <nav className={s.mainNav} aria-label="Tài khoản và giỏ">
            {hotline ? (
              <a href={telHref(hotline)} className={s.mainLink}>
                <Icon name="phone" size={20} />
                <span className={s.hotline}>
                  <span className={s.hotlineLabel}>Hotline</span>
                  <span className={s.hotlineNumber}>{hotline}</span>
                </span>
              </a>
            ) : null}
            <Link
              href={ORDERS_HREF}
              className={cx(s.mainLink, onOrders && s.mainLinkCurrent)}
              aria-current={onOrders ? "page" : undefined}
            >
              <Icon name="receipt" size={20} />
              Tra cứu đơn
            </Link>
            <Link href={CART_HREF} className={cx(s.mainLink, s.cartLink)} aria-label={cartLabel(cartCount)}>
              <Icon name="cart" size={20} />
              Giỏ hàng
              <CartBadgeInline count={cartCount} />
            </Link>
          </nav>
        </div>
      </div>
      <nav className={s.menu} aria-label="Danh mục sản phẩm">
        <div className={cx("container", s.menuInner)}>
          {groupsLoading ? (
            <span className={s.menuSkeleton} aria-hidden="true">
              {[56, 48, 52, 72, 64].map((w, i) => (
                <Skeleton key={i} width={w} height={14} />
              ))}
            </span>
          ) : (
            (groups ?? []).map((g) => (
              <Link
                key={g.slug}
                href={g.href}
                className={s.menuLink}
                aria-current={g.slug === currentGroupSlug ? "page" : undefined}
              >
                {g.label}
              </Link>
            ))
          )}
          <Link href={KITCHEN_HREF} className={s.menuLink} aria-current={onKitchen ? "page" : undefined}>
            Góc bếp
          </Link>
          <Link href={ABOUT_HREF} className={cx(s.menuLink, s.menuEnd)}>
            Về Cá Về
          </Link>
        </div>
      </nav>
    </header>
  );
}

function CartBadgeInline({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span key={count} className={cx(s.inlineBadge, "num")} aria-hidden="true">
      {count > 99 ? "99+" : count}
    </span>
  );
}

function DesktopCompact({ hotline, onBrandClick, logoSrc }: ShopHeaderProps) {
  return (
    <header className={cx(s.desktop, s.compact)}>
      <div className={cx("container", s.compactInner)}>
        <LogoSlot size={36} src={logoSrc} onClick={onBrandClick} />
        <span className={s.compactDivider} aria-hidden="true" />
        <span className={s.safe}>
          <Icon name="lock" size={16} strokeWidth={2} />
          Đặt hàng an toàn
        </span>
        {hotline ? (
          <a href={telHref(hotline)} className={s.help}>
            Cần hỗ trợ? <span className={s.helpNumber}>{hotline}</span>
          </a>
        ) : null}
      </div>
    </header>
  );
}

/**
 * Header Shop: điện thoại H1–H4 (trang chủ, khi cuộn/danh mục, trang con, bước đặt hàng), máy tính 2 tầng hoặc rút gọn.
 * Thành phần trình bày: mọi dữ liệu (hotline, nhóm, số món) do ShopFrame truyền vào.
 * Badge giỏ là số món, ẩn khi 0. Không có dải chip "Tìm nhiều" (Duy chốt 10/10).
 */
export default function ShopHeader(props: ShopHeaderProps) {
  const desktopVariant = props.desktopVariant ?? (props.variant === "checkout" ? "compact" : "full");
  return (
    <>
      {props.variant === "home" ? <MobileHome {...props} /> : null}
      {props.variant === "sticky" ? <MobileSticky {...props} /> : null}
      {props.variant === "sub" ? <MobileSub {...props} /> : null}
      {props.variant === "checkout" ? <MobileCheckout {...props} /> : null}
      {desktopVariant === "full" ? <DesktopFull {...props} /> : <DesktopCompact {...props} />}
    </>
  );
}
