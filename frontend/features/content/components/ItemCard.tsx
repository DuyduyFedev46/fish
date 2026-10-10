"use client";

import React from "react";
import Link from "next/link";
import { formatVnd } from "@/lib/format";
import type { CatalogItem } from "@/lib/types";
import ContactButton from "@/components/ContactButton";
import s from "./ItemCard.module.css";

interface ItemCardProps {
  itemCode: string;
  postSlug?: string;
  /** Mặt hàng lấy từ catalog mà `ArticleBody` nạp 1 lần (SR-23 F7). `null` = không có trong catalog. */
  item: CatalogItem | null;
  /** `true` khi catalog còn đang tải. */
  loading: boolean;
}

// Thẻ chỉ hiển thị, không tự gọi API: `ArticleBody` nạp catalog một lần cho cả bài rồi truyền
// mặt hàng xuống (trước đây mỗi thẻ gọi `getCatalogItem` riêng -> bài 3 thẻ = 3 request).
export default function ItemCard({ itemCode, postSlug, item, loading }: ItemCardProps) {
  const campaign = postSlug ? encodeURIComponent(postSlug) : "";
  const shopItemUrl = `/shop/item/?code=${encodeURIComponent(itemCode)}&utm_source=caveve_web&utm_medium=bai_viet&utm_campaign=${campaign}`;

  if (loading) {
    return (
      <div className={s.cardWrapper}>
        <div className={s.loadingText}>Đang tải thông tin mặt hàng #{itemCode}...</div>
      </div>
    );
  }

  // Trường hợp mặt hàng ẩn, hết hàng hoặc API lỗi (CMS-06-AC5)
  // (API lỗi cũng rơi vào đây: không có `item` -> "Tạm hết · liên hệ để đặt").
  if (!item || item.stock_level === "out") {
    return (
      <div className={`${s.cardWrapper} ${s.unavailable}`}>
        <div className={s.itemInfo}>
          <span className={s.tag}>Hải sản Cá Về</span>
          <h4 className={s.name}>Mặt hàng #{itemCode}</h4>
          <span className={s.statusBadge}>Tạm hết · liên hệ để đặt</span>
        </div>
        <ContactButton className={s.btnSecondary} />
      </div>
    );
  }

  // Trường hợp mặt hàng đang bán bình thường (CMS-06-AC3, AC4)
  const imgSrc = item.image?.urls?.card || item.image?.urls?.thumb || null;

  return (
    <div className={s.cardWrapper}>
      {imgSrc && (
        <div className={s.imageBox}>
          <img src={imgSrc} alt={item.name} className={s.image} loading="lazy" />
        </div>
      )}
      <div className={s.itemInfo}>
        <span className={s.tag}>Mặt hàng đang bán</span>
        <h4 className={s.name}>{item.name}</h4>
        <div className={s.priceBox}>
          <span className={s.price}>{formatVnd(item.price)}</span>
          <span className={s.unit}> / kg</span>
        </div>
      </div>
      <Link href={shopItemUrl} className={s.btnPrimary}>
        Xem giá &amp; đặt
      </Link>
    </div>
  );
}
