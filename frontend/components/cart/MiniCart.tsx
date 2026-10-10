"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { formatPriceVnd } from "@/lib/format";
import type { GroupIcon, ItemImage, Money } from "@/lib/types";
import ImageFrame from "../catalog/ImageFrame";
import PriceTag from "../catalog/PriceTag";
import Button from "../ui/Button";
import IconButton from "../ui/IconButton";
import { CART_HREF } from "../shopLinks";
import s from "./MiniCart.module.css";

export interface MiniCartProps {
  open: boolean;
  onClose: () => void;
  lines: { itemCode: string; name: string; qtyText: string; amount: Money; group: GroupIcon; image?: ItemImage | null }[];
  itemCount: number;
  subtotal: Money;
  cartHref?: string;
}

/** Tự đóng sau 3 giây nếu chuột/tiêu điểm không ở trong (như Toast). */
const AUTO_CLOSE_MS = 3000;

/**
 * Giỏ nhanh nổi góc phải sau khi thêm món (chỉ máy tính). Chỉ để xem: không sửa số lượng, không xoá món.
 * Không lấy tiêu điểm và không bẫy tiêu điểm (khách đang ở lưới hàng).
 */
export default function MiniCart({ open, onClose, lines, itemCount, subtotal, cartHref = CART_HREF }: MiniCartProps) {
  const rootRef = useRef<HTMLElement>(null);
  const [hovering, setHovering] = useState(false);
  // Thêm món khác khi đang mở: đếm lại từ đầu.
  const signature = `${itemCount}|${subtotal}`;

  useEffect(() => {
    if (!open || hovering) return;
    const timer = window.setTimeout(onClose, AUTO_CLOSE_MS);
    return () => window.clearTimeout(timer);
  }, [open, hovering, signature, onClose]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && rootRef.current?.contains(document.activeElement)) onClose();
    };
    const onPointer = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) onClose();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <section
      ref={rootRef}
      className={s.mini}
      aria-labelledby="mini-cart-title"
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      onFocus={() => setHovering(true)}
      onBlur={() => setHovering(false)}
    >
      <div className={s.head}>
        <h2 id="mini-cart-title" className={s.title}>
          Giỏ hàng <span className={s.count}>({itemCount} món)</span>
        </h2>
        <IconButton label="Đóng giỏ hàng nhanh" icon="close" variant="close" iconSize={18} onClick={onClose} />
      </div>
      <ul className={s.list}>
        {lines.map((l) => (
          <li key={l.itemCode} className={s.line}>
            <ImageFrame image={l.image} alt="" group={l.group} ratio="1/1" squareSize={44} />
            <span className={s.text}>
              <Link href={`/shop/item/?code=${encodeURIComponent(l.itemCode)}`} className={s.name}>
                {l.name}
              </Link>
              <span className={s.qty}>{l.qtyText}</span>
            </span>
            <span className={`${s.amount} num`}>{formatPriceVnd(l.amount)}</span>
          </li>
        ))}
      </ul>
      <div className={s.subtotal}>
        <span>Tạm tính</span>
        <PriceTag amount={subtotal} size="total" />
      </div>
      <Button href={cartHref} size="lg" fullWidth>
        Xem giỏ
      </Button>
    </section>
  );
}
