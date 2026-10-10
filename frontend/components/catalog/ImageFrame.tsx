"use client";

// Khung ảnh mặt hàng có tỉ lệ cố định (chống nhảy bố cục), ảnh dự phòng theo nhóm, nhãn "Ảnh minh hoạ".
// Chưa có ảnh HOẶC ảnh lỗi (URL hỏng) -> khung mặc định vẽ bằng SVG nội tuyến trong code, không phát thêm
// request mạng nào (A4-AC5). Giữ nguyên logic srcSet/sizes/onError của ItemImageFrame cũ.
import { useState } from "react";
import type { ReactNode } from "react";
import type { GroupIcon, ItemImage } from "@/lib/types";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import s from "./ImageFrame.module.css";

export interface ImageFrameProps {
  image?: ItemImage | null;
  /** "" khi tên món đã hiện cạnh ảnh (tránh đọc hai lần). */
  alt: string;
  /** Icon dự phòng theo nhóm. */
  group: GroupIcon;
  ratio?: "3/2" | "1/1" | "4/3";
  /** Dùng thay ratio cho dòng/thumb vuông cố định. */
  squareSize?: 44 | 48 | 56 | 64 | 68 | 72;
  /** lazy: ảnh trong lưới (không tải bản detail). eager: trang chi tiết. */
  loadingPriority?: "lazy" | "eager";
  /** Hết hàng: chỉ lớp ảnh mờ, nhãn góc giữ nguyên độ đậm. */
  dimmed?: boolean;
  topLeft?: ReactNode;
  topRight?: ReactNode;
  counter?: { current: number; total: number };
  className?: string;
}

const RATIO_CLASS = { "3/2": s.r32, "1/1": s.r11, "4/3": s.r43 } as const;

// px chỉ để trình duyệt biết tỉ lệ khung trước khi CSS tải xong; kích thước thật do CSS quyết định.
const INTRINSIC_PX = { lazy: 320, eager: 640 } as const;

function srcSetFor(urls: ItemImage["urls"], priority: "lazy" | "eager", square: boolean): string {
  if (square) return `${urls.thumb} 160w, ${urls.card} 480w`;
  // Lưới KHÔNG tải bản detail: chỉ trang chi tiết (eager) mới có detail trong srcSet.
  if (priority === "lazy") return `${urls.thumb} 160w, ${urls.card} 480w`;
  return `${urls.card} 480w, ${urls.detail} 1200w`;
}

function sizesFor(priority: "lazy" | "eager", square: boolean): string {
  if (square) return "72px";
  return priority === "lazy" ? "(max-width: 480px) 45vw, 220px" : "(max-width: 640px) 90vw, 480px";
}

export default function ImageFrame({
  image,
  alt,
  group,
  ratio = "3/2",
  squareSize,
  loadingPriority = "lazy",
  dimmed = false,
  topLeft,
  topRight,
  counter,
  className,
}: ImageFrameProps) {
  const [broken, setBroken] = useState(false);
  const showImage = !!image && !broken;
  const px = INTRINSIC_PX[loadingPriority];
  const square = squareSize !== undefined;
  const decorative = alt === "";

  return (
    <div
      className={cx(s.frame, square ? s.square : RATIO_CLASS[ratio], className)}
      style={square ? { width: squareSize, height: squareSize } : undefined}
    >
      <div className={cx(s.layer, dimmed && s.dimmed)}>
        {showImage ? (
          <img
            src={image!.urls[loadingPriority === "eager" && !square ? "detail" : "card"]}
            srcSet={srcSetFor(image!.urls, loadingPriority, square)}
            sizes={sizesFor(loadingPriority, square)}
            alt={decorative ? "" : image!.alt || alt}
            width={px}
            height={px}
            loading={loadingPriority}
            onError={() => setBroken(true)}
          />
        ) : (
          <div
            className={s.fallback}
            {...(decorative ? { "aria-hidden": true } : { role: "img", "aria-label": alt })}
          >
            <Icon name={group} size={32} strokeWidth={1.4} />
          </div>
        )}
      </div>
      {topLeft ? <span className={s.topLeft}>{topLeft}</span> : null}
      {topRight ? <span className={s.topRight}>{topRight}</span> : null}
      {showImage && image!.is_illustration ? <span className={s.illustration}>Ảnh minh hoạ</span> : null}
      {counter && counter.total > 1 ? (
        <span className={cx(s.counter, "num")}>
          <span className="visually-hidden">Ảnh </span>
          {counter.current}/{counter.total}
        </span>
      ) : null}
    </div>
  );
}
