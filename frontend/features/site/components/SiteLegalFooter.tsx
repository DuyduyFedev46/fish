"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { getFooterLinks, getSiteInfo } from "../api";
import type { FooterLinkItem, SellerInfo } from "../types";
import styles from "./SiteLegalFooter.module.css";

const EMAIL_REGEX = /^[^\s@<>"]+@[^\s@<>"]+$/;

export default function SiteLegalFooter() {
  const [seller, setSeller] = useState<SellerInfo | null>(null);
  const [links, setLinks] = useState<FooterLinkItem[] | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;

    Promise.allSettled([getSiteInfo(), getFooterLinks()]).then(([siteRes, linksRes]) => {
      if (!active) return;

      if (siteRes.status === "fulfilled" && siteRes.value?.seller) {
        setSeller(siteRes.value.seller);
      } else {
        setSeller(null);
      }

      if (linksRes.status === "fulfilled" && Array.isArray(linksRes.value)) {
        setLinks(linksRes.value);
      } else {
        setLinks(null);
      }

      setLoaded(true);
    });

    return () => {
      active = false;
    };
  }, []);

  if (!loaded) {
    return null;
  }

  const hasSeller = seller !== null;
  const hasLinks = links !== null && links.length > 0;

  if (!hasSeller && !hasLinks) {
    return null;
  }

  const cleanPhone = seller?.phone ? seller.phone.replace(/[^\d+]/g, "") : "";
  const isValidEmail = seller?.email ? EMAIL_REGEX.test(seller.email) : false;

  return (
    <footer className={styles.legalFooter} aria-label="Thông tin pháp lý và người bán">
      <div className={styles.inner}>
        {hasSeller && (
          <section id="seller-info" className={styles.sellerSection} aria-label="Thông tin người bán">
            <h2 className={styles.sellerTitle}>Thông tin đơn vị bán hàng</h2>
            <p className={styles.sellerItem}>
              <strong>Tên đơn vị:</strong> {seller.name || "Đang cập nhật"}
            </p>
            <p className={styles.sellerItem}>
              <strong>Loại hình:</strong> {seller.business_type || "Đang cập nhật"}
            </p>
            <p className={styles.sellerItem}>
              <strong>Số ĐKKD:</strong> {seller.registration_no || "Đang cập nhật"}
            </p>
            <p className={styles.sellerItem}>
              <strong>Mã số thuế:</strong> {seller.tax_code || "Đang cập nhật"}
            </p>
            <p className={styles.sellerItem}>
              <strong>Địa chỉ:</strong> {seller.address || "Đang cập nhật"}
            </p>
            <p className={styles.sellerItem}>
              <strong>Điện thoại:</strong>{" "}
              {seller.phone ? (
                <a href={`tel:${cleanPhone}`} className={styles.link}>
                  {seller.phone}
                </a>
              ) : (
                "Đang cập nhật"
              )}
            </p>
            <p className={styles.sellerItem}>
              <strong>Email:</strong>{" "}
              {seller.email ? (
                isValidEmail ? (
                  <a href={`mailto:${seller.email}`} className={styles.link}>
                    {seller.email}
                  </a>
                ) : (
                  <span>{seller.email}</span>
                )
              ) : (
                "Đang cập nhật"
              )}
            </p>
          </section>
        )}

        {hasLinks && (
          <section className={styles.linksSection} aria-label="Chính sách và điều khoản">
            <ul className={styles.linksList}>
              {links.map((link) => (
                <li key={link.slug}>
                  <Link
                    href={{ pathname: "/trang/", query: { slug: link.slug } }}
                    className={styles.footerLink}
                  >
                    {link.title}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </footer>
  );
}
