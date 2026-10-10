import { formatPriceVnd } from "@/lib/format";
import type { Money, SaleUnit } from "@/lib/types";
import { cx } from "../ui/cx";
import s from "./PriceTag.module.css";

export interface PriceTagProps {
  amount: Money;
  /** null: không hiện đơn vị. */
  unit?: SaleUnit | null;
  size?: "card" | "rail" | "detail" | "meta" | "total" | "line";
  /** accent: màu nhấn (tổng tiền, giá chi tiết). muted: hết hàng, đơn đã huỷ. */
  tone?: "default" | "accent" | "muted";
  /** Có thì hiện giá cũ gạch ngang trước giá mới. */
  previousAmount?: Money;
}

const DEFAULT_TONE: Record<NonNullable<PriceTagProps["size"]>, "default" | "accent"> = {
  card: "default",
  rail: "default",
  detail: "accent",
  meta: "default",
  total: "accent",
  line: "default",
};

/** Giá theo đơn vị: "278.000đ / kg" hoặc "450.000đ / combo". Giá thẻ màu ink; giá chi tiết và tổng tiền màu nhấn. */
export default function PriceTag({ amount, unit = null, size = "card", tone, previousAmount }: PriceTagProps) {
  const effective = tone ?? DEFAULT_TONE[size];
  return (
    <span className={cx(s.price, s[size], s[effective], "num")}>
      {previousAmount ? (
        <>
          <del className={s.old}>
            <span className="visually-hidden">Giá cũ </span>
            {formatPriceVnd(previousAmount)}
          </del>
          <span className={s.arrow} aria-hidden="true">
            →
          </span>
          <span className="visually-hidden">Giá mới </span>
        </>
      ) : null}
      <span className={s.amount}>{formatPriceVnd(amount)}</span>
      {unit ? <span className={s.unit}>/ {unit}</span> : null}
    </span>
  );
}
