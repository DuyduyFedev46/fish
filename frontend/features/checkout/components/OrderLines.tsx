import { formatPriceVnd } from "@/lib/format";
import { formatQty } from "@/lib/quantity";
import type { Money, OrderLineData } from "@/lib/types";
import { cx } from "@/components/ui/cx";
import PriceTag from "@/components/catalog/PriceTag";
import s from "./OrderLines.module.css";

export interface OrderLinesProps {
  /** "Tóm tắt" hoặc "Món trong đơn". */
  title: string;
  lines: OrderLineData[];
  /** summary: thanh toán (không dòng tổng). order: có tổng. cancelled: chữ nhạt, không tổng. */
  variant?: "summary" | "order" | "cancelled";
  /** Tổng lấy từ máy chủ, không cộng lại ở FE. */
  total?: Money;
  totalLabel?: string;
  /** Dòng giảm giá, số từ máy chủ. */
  discount?: { code: string; amount: Money };
  headingId?: string;
}

/**
 * Danh sách món trong đơn kèm tiền (COMPONENTS #28). Dòng lấy từ máy chủ (tên, đơn vị, số lượng, thành tiền gộp), không từ giỏ.
 * Không có dòng "Phí giao" và không có người nhận (tên, SĐT, địa chỉ).
 */
export default function OrderLines({
  title,
  lines,
  variant = "order",
  total,
  totalLabel = "Đã thanh toán",
  discount,
  headingId = "order-lines-title",
}: OrderLinesProps) {
  return (
    <section className={cx(s.box, s[variant])} aria-labelledby={headingId}>
      <h2 id={headingId} className={s.title}>
        {title}
      </h2>
      <ul className={s.list}>
        {lines.map((l) => (
          <li key={l.item_code} className={s.line}>
            <span className={s.name}>
              {l.name}
              <span className={s.qty}>
                {" "}
                · {formatQty(Number(l.qty))} {l.unit}
              </span>
            </span>
            <span className={cx(s.amount, "num")}>{formatPriceVnd(l.amount)}</span>
          </li>
        ))}
        {discount ? (
          <li className={cx(s.line, s.discount)}>
            <span>Mã giảm giá ({discount.code})</span>
            <span className="num">−{formatPriceVnd(discount.amount)}</span>
          </li>
        ) : null}
      </ul>
      {total !== undefined && variant === "order" ? (
        <dl className={s.total}>
          <dt>{totalLabel}</dt>
          <dd>
            <PriceTag amount={total} size="total" />
          </dd>
        </dl>
      ) : null}
      {variant === "order" || variant === "summary" ? (
        <p className={s.note}>Đã gồm giao hàng. Bạn trả một lần, không trả thêm khi nhận hàng.</p>
      ) : null}
    </section>
  );
}
