"use client";

import { useEffect, useState } from "react";
import { getSiteInfo } from "../features/site/api";

export const SELLER_SECTION_ID = "seller-info";

/**
 * Nút "Liên hệ" dùng chung (thẻ mặt hàng, trang chi tiết, thẻ trong bài viết) khi hết hàng.
 * - Có `seller.phone`: mở `tel:` (bỏ khoảng trắng).
 * - Không có số: cuộn tới khối người bán ở footer nếu footer đang hiện;
 *   nếu không (site-info lỗi) thì link thường về trang chủ, không để nút chết.
 * Không bao giờ thêm vào giỏ.
 */
export default function ContactButton({ className }: { className: string }) {
  const [phone, setPhone] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getSiteInfo()
      .then((info) => {
        const clean = info?.seller?.phone?.replace(/[^\d+]/g, "") || null;
        if (active) setPhone(clean);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  return (
    <a
      className={className}
      href={phone ? `tel:${phone}` : "/"}
      data-testid="contact-button"
      onClick={(e) => {
        if (phone) return;
        const section = document.getElementById(SELLER_SECTION_ID);
        if (section) {
          e.preventDefault();
          section.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }}
    >
      Liên hệ
    </a>
  );
}
