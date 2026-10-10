import Link from "next/link";
import { formatPriceVnd } from "@/lib/format";
import type { Money } from "@/lib/types";
import Icon from "../ui/Icon";
import { CART_HREF } from "../shopLinks";
import s from "./CartBar.module.css";

export interface CartBarProps {
  /** Số món (số dòng), không phải số kg. */
  itemCount: number;
  /** Tạm tính ở client, chỉ để xem. */
  subtotal: Money;
  href?: string;
}

/** Thanh dính đáy ở danh mục điện thoại: số món, tạm tính, "Xem giỏ". Ẩn khi giỏ trống và từ 768 px. */
export default function CartBar({ itemCount, subtotal, href = CART_HREF }: CartBarProps) {
  if (itemCount <= 0) return null;
  return (
    <div className={s.bar}>
      <Link href={href} className={s.link}>
        <span className="num">
          {itemCount} món · {formatPriceVnd(subtotal)}
        </span>
        <span className={s.go}>
          Xem giỏ
          <Icon name="chevron-right" size={16} strokeWidth={2} />
        </span>
      </Link>
    </div>
  );
}
