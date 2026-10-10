"use client";

import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { MouseEvent, ReactNode } from "react";
import { getCatalog } from "@/lib/api";
import { pickHotline } from "@/lib/phone";
import { getFooterLinks, getSiteInfo } from "@/features/site/api";
import type { FooterLinkItem, SiteInfoResponse } from "@/features/site/types";
import BottomNav, { type BottomNavTab } from "./BottomNav";
import ShopFooter, { type FooterLinkEntry } from "./ShopFooter";
import ShopHeader, { type NavGroup } from "./ShopHeader";
import { groupHref } from "./shopLinks";
import { useCart } from "./CartContext";
import s from "./ShopFrame.module.css";

export interface ShopFrameProps {
  /** home: H1 · sticky: H2 · sub: H3 · checkout: H4 (điện thoại). */
  header: "home" | "sticky" | "sub" | "checkout";
  /** Tiêu đề H3/H4. */
  title?: string;
  /** full: F1 · compact: F2. */
  footer: "full" | "compact";
  /** Có thanh điều hướng đáy (điện thoại) hay không. */
  bottomNav: boolean;
  /** Đích khi không có lịch sử để quay lại. */
  backHref?: string;
  /** Máy tính: mặc định compact cho checkout, full cho còn lại. Giỏ hàng truyền "compact". */
  desktopHeader?: "full" | "compact";
  /** H3 có nút giỏ hay không (Giỏ hàng: không). */
  showCart?: boolean;
  /** Chặn quay lại / bấm logo (rời trang thanh toán). */
  onBack?: (e: MouseEvent) => void;
  onBrandClick?: (e: MouseEvent<HTMLAnchorElement>) => void;
  /** Nhóm đang xem, để đánh dấu menu nhóm. */
  currentGroupSlug?: string;
  /** Nền khung trang: canvas (mặc định) hoặc muted (xám nhạt, trang chủ). */
  tone?: "canvas" | "muted";
  children: ReactNode;
}

// Dải chữ đầu trang máy tính (06-marketing K2, ĐÃ ĐỐI CHIẾU). Chờ CMS hỗ trợ (SHOP-5-03).
const INTRO_TEXT = "Hải sản cấp đông theo lô · mua từ 1 kg · giao tận nhà";

function zaloUrlOf(raw?: string | null): string | undefined {
  const v = raw?.trim();
  if (!v) return undefined;
  if (/^https:\/\//i.test(v)) return v;
  const digits = v.replace(/\D/g, "");
  return digits ? `https://zalo.me/${digits}` : undefined;
}

/** Khung trang Shop: header, nội dung, footer, thanh đáy. Mỗi màn tự bọc (02b §1.4). */
export default function ShopFrame({
  header,
  title,
  footer,
  bottomNav,
  backHref,
  desktopHeader,
  showCart,
  onBack,
  onBrandClick,
  currentGroupSlug,
  tone = "canvas",
  children,
}: ShopFrameProps) {
  const pathname = usePathname() || "/";
  const { lineCount } = useCart();
  const [info, setInfo] = useState<SiteInfoResponse | null>(null);
  const [footerLinks, setFooterLinks] = useState<FooterLinkItem[]>([]);
  const [groups, setGroups] = useState<NavGroup[] | undefined>(undefined);
  const [groupsLoading, setGroupsLoading] = useState(true);

  // Ba nguồn độc lập, gọi song song. Lỗi nguồn nào thì ẩn khối liên quan, không vỡ bố cục (1-03 AC7, 1-05 AC6).
  useEffect(() => {
    let active = true;
    getSiteInfo()
      .then((v) => active && setInfo(v))
      .catch(() => {});
    getFooterLinks()
      .then((v) => active && setFooterLinks(Array.isArray(v) ? v : []))
      .catch(() => {});
    getCatalog()
      .then((c) => {
        if (!active) return;
        setGroups(c.groups.map((g) => ({ slug: g.slug, label: g.name, href: groupHref(g.slug) })));
      })
      .catch(() => {})
      .finally(() => active && setGroupsLoading(false));
    return () => {
      active = false;
    };
  }, []);

  // Báo cho Toast biết có thanh đáy để nổi phía trên nó.
  useEffect(() => {
    if (!bottomNav) return;
    document.body.dataset.bottomNav = "1";
    return () => {
      delete document.body.dataset.bottomNav;
    };
  }, [bottomNav]);

  const seller = info?.seller;
  // Ưu tiên số của người bán, rồi mới tới số trong cấu hình xác nhận đơn (02b §6.5).
  const hotline = pickHotline(seller?.phone, info?.confirmation_policy?.hotline);

  const policyLinks: FooterLinkEntry[] = useMemo(
    () =>
      footerLinks.map((l) => ({
        // Tên link lấy đúng tiêu đề CMS (lệnh nạp đặt trang `terms` là "Điều kiện giao dịch chung").
        label: l.title,
        href: `/trang/?slug=${encodeURIComponent(l.slug)}`,
      })),
    [footerLinks]
  );

  const normalized = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  const tab: BottomNavTab | null =
    normalized === "/"
      ? "home"
      : normalized === "/shop"
        ? "catalog"
        : normalized === "/shop/cart"
          ? "cart"
          : normalized === "/shop/orders"
            ? "orders"
            : null;

  return (
    <div className={tone === "muted" ? `${s.frame} ${s.muted}` : s.frame}>
      <a href="#main-content" className={s.skip}>
        Bỏ qua tới nội dung chính
      </a>
      <ShopHeader
        variant={header}
        desktopVariant={desktopHeader}
        title={title}
        backHref={backHref}
        onBack={onBack}
        onBrandClick={onBrandClick}
        showCart={showCart}
        cartCount={lineCount}
        hotline={hotline}
        groups={groups}
        groupsLoading={groupsLoading}
        currentGroupSlug={currentGroupSlug}
        currentPath={normalized}
        introText={INTRO_TEXT}
      />
      <main id="main-content" className={s.main} tabIndex={-1}>
        {children}
      </main>
      <ShopFooter
        variant={footer}
        seller={{
          name: seller?.name,
          taxCode: seller?.tax_code,
          address: seller?.address,
          businessLicense: seller?.registration_no,
          licenseIssuedBy: seller?.registration_issued_by,
          licenseIssuedOn: seller?.registration_issued_on,
          email: seller?.email,
        }}
        hotline={hotline}
        zaloUrl={zaloUrlOf(seller?.zalo)}
        policyLinks={policyLinks}
        noticeUrl={seller?.website_notice_url?.trim() || undefined}
        noticeImage={seller?.website_notice_image?.trim() || undefined}
        currentPath={normalized}
        reserveBottomNav={bottomNav}
      />
      {bottomNav ? <BottomNav current={tab} cartCount={lineCount} /> : null}
    </div>
  );
}
