"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { getCatalogItem } from "@/lib/api";
import { formatVnd } from "@/lib/format";
import type { CatalogItemDetail } from "@/lib/types";
import s from "./ItemCard.module.css";

interface ItemCardProps {
  itemCode: string;
  postSlug?: string;
}

export default function ItemCard({ itemCode, postSlug }: ItemCardProps) {
  const [item, setItem] = useState<CatalogItemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [isUnavailable, setIsUnavailable] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setIsUnavailable(false);

    getCatalogItem(itemCode)
      .then((data) => {
        if (!active) return;
        if (!data || data.sellable_qty <= 0) {
          setIsUnavailable(true);
          setItem(null);
        } else {
          setItem(data);
          setIsUnavailable(false);
        }
      })
      .catch(() => {
        if (!active) return;
        setIsUnavailable(true);
        setItem(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [itemCode]);

  const campaign = postSlug ? encodeURIComponent(postSlug) : "";
  const shopItemUrl = `/shop/item/?code=${encodeURIComponent(itemCode)}&utm_source=caveve_web&utm_medium=bai_viet&utm_campaign=${campaign}`;
  const shopCatalogUrl = `/shop/?utm_source=caveve_web&utm_medium=bai_viet&utm_campaign=${campaign}`;

  if (loading) {
    return (
      <div className={s.cardWrapper}>
        <div className={s.loadingText}>Đang tải thông tin mặt hàng #{itemCode}...</div>
      </div>
    );
  }

  // Trường hợp mặt hàng ẩn, hết hàng hoặc API lỗi (CMS-06-AC5)
  if (isUnavailable || !item) {
    return (
      <div className={`${s.cardWrapper} ${s.unavailable}`}>
        <div className={s.itemInfo}>
          <span className={s.tag}>Hải sản Cá Về</span>
          <h4 className={s.name}>Mặt hàng #{itemCode}</h4>
          <span className={s.statusBadge}>Tạm hết hàng</span>
        </div>
        <Link href={shopCatalogUrl} className={s.btnSecondary}>
          Xem cửa hàng
        </Link>
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
