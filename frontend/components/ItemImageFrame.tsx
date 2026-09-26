"use client";

// Ảnh mặt hàng ở lưới danh mục và trang chi tiết (A4, doc/features/2026-09-26-anh-mat-hang/02-stories.md).
// Chưa có ảnh HOẶC ảnh lỗi (URL hỏng) -> khung mặc định vẽ bằng SVG NỘI TUYẾN trong code (không phải
// tệp ảnh riêng, không phát thêm request mạng nào — A4-AC5). Khung luôn vuông 1:1, width/height cố định
// để không nhảy bố cục (CLS) trong lúc ảnh thật đang tải.
import { useState } from "react";
import type { ItemImage } from "../lib/types";

type Size = "card" | "detail";

// px chỉ để trình duyệt biết tỉ lệ khung trước khi CSS tải xong — kích thước thật do CSS (width:100%,
// aspect-ratio) quyết định.
const INTRINSIC_PX: Record<Size, number> = { card: 320, detail: 640 };

function srcSetFor(urls: ItemImage["urls"], size: Size): string {
  // A4-AC3: lưới KHÔNG tải bản detail — chỉ đưa detail vào srcSet của trang chi tiết.
  if (size === "card") return `${urls.thumb} 160w, ${urls.card} 480w`;
  return `${urls.card} 480w, ${urls.detail} 1200w`;
}

function sizesFor(size: Size): string {
  return size === "card" ? "(max-width: 480px) 45vw, 220px" : "(max-width: 640px) 90vw, 480px";
}

export default function ItemImageFrame({
  image,
  alt,
  groupLabel,
  size,
}: {
  image: ItemImage | null | undefined;
  /** Tên mặt hàng — dùng làm alt/aria-label khi ảnh không có mô tả riêng hoặc khi hiện khung mặc định. */
  alt: string;
  groupLabel?: string;
  size: Size;
}) {
  const [broken, setBroken] = useState(false);
  const showImage = !!image && !broken;
  const px = INTRINSIC_PX[size];

  return (
    <div className={`item-image item-image-${size}`}>
      {showImage ? (
        <img
          src={image!.urls[size === "card" ? "card" : "detail"]}
          srcSet={srcSetFor(image!.urls, size)}
          sizes={sizesFor(size)}
          alt={image!.alt || alt}
          width={px}
          height={px}
          loading={size === "card" ? "lazy" : "eager"}
          onError={() => setBroken(true)}
        />
      ) : (
        <div className="item-image-fallback" role="img" aria-label={alt}>
          <svg viewBox="0 0 64 64" width="42%" height="42%" aria-hidden="true" focusable="false">
            <path
              d="M4 32c9-13 23-19 35-13 6 3 10 7 12 12.5-2 5.5-6 9.5-12 12.5-12 6-26 0-35-13z"
              fill="currentColor"
              opacity="0.55"
            />
            <circle cx="16" cy="27.5" r="2.2" fill="#fff" />
            <path d="M51 31.5l9-9v18z" fill="currentColor" opacity="0.55" />
          </svg>
          {groupLabel && <span className="item-image-fallback-label">{groupLabel}</span>}
        </div>
      )}
      {showImage && image!.is_illustration && (
        <span className="item-image-badge">Ảnh minh hoạ</span>
      )}
    </div>
  );
}
