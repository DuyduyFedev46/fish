"use client";

import { useEffect, useId, useState } from "react";
import type { MouseEvent } from "react";
import { currentYearInVietnam, formatDateOnly } from "@/lib/format";
import { isSafeHref } from "@/features/content/safeHref";
import LogoSlot from "./LogoSlot";
import Button from "./ui/Button";
import Icon from "./ui/Icon";
import TextLink from "./ui/TextLink";
import { cx } from "./ui/cx";
import {
  ABOUT_HREF,
  CATALOG_HREF,
  CONTACT_HREF,
  HOW_TO_BUY_HREF,
  KITCHEN_HREF,
  ORDERS_HREF,
  telHref,
} from "./shopLinks";
import s from "./ShopFooter.module.css";

export interface FooterSeller {
  name?: string | null;
  taxCode?: string | null;
  address?: string | null;
  /** Số giấy chứng nhận đăng ký kinh doanh. */
  businessLicense?: string | null;
  licenseIssuedBy?: string | null;
  /** Ngày cấp dạng YYYY-MM-DD. */
  licenseIssuedOn?: string | null;
  email?: string | null;
}

export interface FooterLinkEntry {
  label: string;
  href: string;
}

export interface ShopFooterProps {
  /** full: F1 (trang chủ, danh mục, Góc bếp…). compact: F2 (Giỏ, Đặt hàng, Thanh toán). */
  variant?: "full" | "compact";
  seller: FooterSeller;
  hotline?: string;
  /** Link Zalo đầy đủ (https://zalo.me/…). Không có thì ẩn nút/dòng Zalo. */
  zaloUrl?: string;
  /** Nhóm "Chính sách": đúng danh sách của CMS (footer-links). */
  policyLinks: FooterLinkEntry[];
  /** Có link xác nhận thông báo website thì mới gắn biểu tượng; chưa có thì ẩn hẳn khối. */
  noticeUrl?: string;
  noticeImage?: string;
  currentPath?: string;
  /** Chừa chỗ cho thanh điều hướng đáy (điện thoại) để không che nội dung cuối trang. */
  reserveBottomNav?: boolean;
  logoSrc?: string;
}

/** Ba link chính sách của F2: đổi trả, quyền riêng tư, thanh toán (lọc theo slug trong href). */
export function pickCompactPolicyLinks(links: FooterLinkEntry[]): FooterLinkEntry[] {
  const patterns = [/doi-tra/, /quyen-rieng-tu|bao-mat/, /thanh-toan/];
  const picked: FooterLinkEntry[] = [];
  for (const pattern of patterns) {
    const found = links.find((l) => pattern.test(l.href) && !picked.includes(l));
    if (found) picked.push(found);
  }
  return picked;
}

function sellerLine(seller: FooterSeller): string {
  const parts = [seller.name?.trim(), seller.taxCode?.trim() ? `MST ${seller.taxCode.trim()}` : ""];
  return parts.filter(Boolean).join(" · ");
}

function licenseLine(seller: FooterSeller): string {
  if (!seller.businessLicense?.trim()) return "";
  let text = `GCN ĐKKD số ${seller.businessLicense.trim()}`;
  if (seller.licenseIssuedBy?.trim()) text += ` do ${seller.licenseIssuedBy.trim()} cấp`;
  const date = seller.licenseIssuedOn ? formatDateOnly(seller.licenseIssuedOn) : "—";
  if (date !== "—") text += `${seller.licenseIssuedBy?.trim() ? "" : " cấp"} ngày ${date}`;
  return text;
}

function useIsDesktop(): boolean {
  const [desktop, setDesktop] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    const update = () => setDesktop(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return desktop;
}

/** Một nhóm link: điện thoại là <details> thu gọn được, máy tính là cột luôn mở. */
function Group({
  title,
  links,
  isDesktop,
  openDefault = false,
  currentPath,
}: {
  title: string;
  links: FooterLinkEntry[];
  isDesktop: boolean;
  openDefault?: boolean;
  currentPath?: string;
}) {
  const [open, setOpen] = useState(openDefault);
  const titleId = useId();
  const expanded = isDesktop || open;
  if (links.length === 0) return null;
  return (
    <nav aria-labelledby={titleId} className={s.group}>
      <details open={expanded} className={s.details}>
        <summary
          className={s.summary}
          aria-expanded={expanded}
          onClick={(e: MouseEvent) => {
            e.preventDefault();
            if (!isDesktop) setOpen((v) => !v);
          }}
        >
          <h2 id={titleId} className={s.groupTitle}>
            {title}
          </h2>
          <span className={cx(s.chevron, expanded && s.chevronOpen)}>
            <Icon name="chevron-down" size={16} strokeWidth={2} />
          </span>
        </summary>
        <ul className={s.list}>
          {links.map((l) => (
            <li key={l.href + l.label}>
              <TextLink
                href={l.href}
                variant="on-brand"
                current={!!currentPath && l.href.split("?")[0] === currentPath}
              >
                {l.label}
              </TextLink>
            </li>
          ))}
        </ul>
      </details>
    </nav>
  );
}

function CompactFooter({ seller, policyLinks }: ShopFooterProps) {
  const links = pickCompactPolicyLinks(policyLinks);
  const line = sellerLine(seller);
  return (
    <footer className={s.compact}>
      <div className={cx("container", s.compactInner)}>
        <span>
          {line ? `${line} · ` : ""}© {currentYearInVietnam()} Cá Về
        </span>
        {links.length > 0 ? (
          <span className={s.compactLinks}>
            {links.map((l) => (
              <TextLink key={l.href} href={l.href} external className={s.compactLink}>
                {l.label}
              </TextLink>
            ))}
          </span>
        ) : null}
      </div>
    </footer>
  );
}

/**
 * Chân trang: F1 đầy đủ (gộp dải pháp lý người bán) và F2 rút gọn. Trường người bán trống thì ẩn dòng đó,
 * không hiện chữ chờ (BR-ND-18). Biểu tượng đã thông báo website chỉ gắn khi có link xác nhận (D12).
 */
export default function ShopFooter(props: ShopFooterProps) {
  const isDesktop = useIsDesktop();
  if (props.variant === "compact") return <CompactFooter {...props} />;

  const { seller, hotline, zaloUrl, policyLinks, noticeUrl, noticeImage, currentPath, reserveBottomNav, logoSrc } = props;
  const year = currentYearInVietnam();
  // Link thông báo website chỉ nhận https và phải qua isSafeHref.
  const safeNoticeUrl = noticeUrl && /^https:\/\//i.test(noticeUrl.trim()) && isSafeHref(noticeUrl) ? noticeUrl.trim() : undefined;
  const safeNoticeImage = noticeImage && /^https:\/\//i.test(noticeImage.trim()) && isSafeHref(noticeImage) ? noticeImage.trim() : undefined;
  const sellerText = sellerLine(seller);
  const licenseText = licenseLine(seller);
  const address = seller.address?.trim();
  const email = seller.email?.trim();

  const buy: FooterLinkEntry[] = [
    { label: "Hàng đang có", href: CATALOG_HREF },
    { label: "Combo nấu nhanh", href: "/shop/?type=combo" },
    { label: "Cách mua hàng", href: HOW_TO_BUY_HREF },
    { label: "Tra cứu đơn", href: ORDERS_HREF },
  ];
  const about: FooterLinkEntry[] = [
    { label: "Giới thiệu", href: ABOUT_HREF },
    { label: "Góc bếp", href: KITCHEN_HREF },
    { label: "Liên hệ", href: CONTACT_HREF },
  ];

  return (
    <footer className={cx(s.footer, reserveBottomNav && s.reserveNav)}>
      <div className={cx("container", s.top)}>
        <div className={s.intro}>
          <LogoSlot size={36} tone="brand" src={logoSrc} />
          <p className={s.sentence}>Hải sản cấp đông theo lô, giá tính theo kg, giao tận nhà.</p>
          {/* Điện thoại: hai nút to. */}
          {hotline || zaloUrl ? (
            <div className={s.contactButtons}>
              {hotline ? (
                <Button href={telHref(hotline)} variant="on-brand" shape="pill">
                  Gọi {hotline}
                </Button>
              ) : null}
              {zaloUrl ? (
                <Button href={zaloUrl} variant="on-brand-outline" shape="pill" external>
                  Nhắn Zalo
                </Button>
              ) : null}
            </div>
          ) : null}
          {/* Máy tính: danh sách Hotline · Zalo · Email. */}
          <ul className={s.contactList}>
            {hotline ? (
              <li>
                <TextLink href={telHref(hotline)} variant="on-brand">
                  Hotline: {hotline}
                </TextLink>
              </li>
            ) : null}
            {zaloUrl ? (
              <li>
                <TextLink href={zaloUrl} variant="on-brand" external>
                  Zalo
                </TextLink>
              </li>
            ) : null}
            {email ? (
              <li>
                <TextLink href={`mailto:${email}`} variant="on-brand">
                  Email: {email}
                </TextLink>
              </li>
            ) : null}
          </ul>
        </div>
        <Group title="Mua hàng" links={buy} isDesktop={isDesktop} openDefault currentPath={currentPath} />
        <Group title="Chính sách" links={policyLinks} isDesktop={isDesktop} currentPath={currentPath} />
        <Group title="Về Cá Về" links={about} isDesktop={isDesktop} currentPath={currentPath} />
      </div>
      <div className={s.legalWrap}>
        <div className={cx("container", s.legal)}>
          <div className={s.legalLines}>
            {sellerText ? <span>{sellerText}</span> : null}
            {address ? <span>Địa chỉ: {address}</span> : null}
            {licenseText ? <span>{licenseText}</span> : null}
            {email ? (
              <span className={s.emailLine}>
                Email: <a href={`mailto:${email}`}>{email}</a>
              </span>
            ) : null}
            <span className={s.copy}>© {year} Cá Về</span>
          </div>
          {safeNoticeUrl ? (
            <a href={safeNoticeUrl} target="_blank" rel="noopener" className={s.notice}>
              {safeNoticeImage ? (
                <img src={safeNoticeImage} alt="Đã thông báo website thương mại điện tử" height={44} />
              ) : (
                "Đã thông báo website thương mại điện tử"
              )}
              <span className="visually-hidden"> (mở tab mới)</span>
            </a>
          ) : null}
        </div>
      </div>
    </footer>
  );
}
