"use client";

import { formatPriceVnd } from "@/lib/format";
import type { Money } from "@/lib/types";
import PriceTag from "../catalog/PriceTag";
import Button from "../ui/Button";
import Icon, { type IconName } from "../ui/Icon";
import { cx } from "../ui/cx";
import s from "./CartSummary.module.css";

export interface CartSummaryProps {
  /** Lô 2 chỉ dùng "cart"; các ngữ cảnh còn lại dành cho đặt hàng và thanh toán (lô 3+4). */
  context: "cart" | "checkout" | "payment" | "payment-retry";
  /** Số món trong giỏ. */
  itemCount: number;
  /** Số món còn hàng; nhỏ hơn `itemCount` khi có món hết. */
  availableCount?: number;
  subtotal?: Money;
  /** Tổng tiền hàng. Ở thanh toán lấy từ máy chủ, không cộng lại ở FE. */
  total: Money;
  /** Dòng giảm giá, số lấy từ máy chủ (mã giảm giá, lô 3b). */
  discount?: { code: string; amount: Money };
  /** Tiêu đề hộp máy tính. Mặc định "Tóm tắt đơn"; đặt hàng ghi "Đơn hàng (3 món)". */
  title?: string;
  /** Nhãn dòng tổng. Mặc định "Tổng tiền hàng"; thanh toán ghi "Cần thanh toán". */
  totalLabel?: string;
  /** Danh sách món rút gọn, chỉ hiện từ máy tính (bước đặt hàng và thanh toán). */
  lines?: { name: string; qtyText: string; amount: Money }[];
  /** Dòng cảnh báo `role="alert"` ngay trên nút (vd. "Bỏ món đã hết để đặt hàng."). */
  notice?: { id: string; text: string };
  cta: {
    label: string;
    /** Nhãn riêng cho máy tính (điện thoại dùng `label`). */
    labelDesktop?: string;
    href?: string;
    onClick?: () => void;
    loading?: boolean;
    loadingText?: string;
    disabled?: boolean;
    form?: string;
    /** Icon đầu nút (vd. ổ khoá ở nút "Thanh toán"). */
    icon?: IconName;
  };
}

/**
 * Khối tóm tắt tiền và nút đi tiếp. Điện thoại: thanh dính đáy. Máy tính: hộp dính ở cột phải.
 * Không có dòng "Phí giao" (BR-BH-30). Nút chính không tắt khi chỉ thiếu điều kiện (Q-UX-4): báo lỗi khi bấm.
 */
export default function CartSummary({
  context,
  itemCount,
  availableCount,
  subtotal,
  total,
  discount,
  notice,
  cta,
  title = "Tóm tắt đơn",
  totalLabel = "Tổng tiền hàng",
  lines,
}: CartSummaryProps) {
  const someOut = availableCount !== undefined && availableCount < itemCount;
  const subtotalLabel = someOut ? `Tạm tính (${availableCount} món còn hàng)` : "Tạm tính";
  const buttonProps = {
    variant: "primary" as const,
    size: "lg" as const,
    fullWidth: true,
    loading: cta.loading,
    loadingText: cta.loadingText,
    disabled: cta.disabled,
    iconStart: cta.icon ? <Icon name={cta.icon} size={18} /> : undefined,
    "aria-describedby": notice?.id,
  };

  return (
    <section className={cx(s.summary, s[context])} aria-labelledby="cart-summary-title">
      <h2 id="cart-summary-title" className={s.title}>
        {title}
      </h2>
      {lines && lines.length > 0 ? (
        <ul className={s.lines} aria-label="Món trong đơn">
          {lines.map((l) => (
            <li key={`${l.name}-${l.qtyText}`} className={s.line}>
              <span className={s.lineName}>
                {l.name}
                <span className={s.lineQty}> · {l.qtyText}</span>
              </span>
              <span className="num">{formatPriceVnd(l.amount)}</span>
            </li>
          ))}
        </ul>
      ) : null}
      <dl className={s.rows}>
        {subtotal !== undefined ? (
          <div className={s.row}>
            <dt>{subtotalLabel}</dt>
            <dd className="num">{formatPriceVnd(subtotal)}</dd>
          </div>
        ) : null}
        {discount ? (
          <div className={cx(s.row, s.discount)}>
            <dt>Giảm giá ({discount.code})</dt>
            <dd className="num">−{formatPriceVnd(discount.amount)}</dd>
          </div>
        ) : null}
        <div className={cx(s.row, s.totalRow)}>
          <dt>{totalLabel}</dt>
          <dd>
            <PriceTag amount={total} size="total" />
          </dd>
        </div>
      </dl>
      <p className={s.note}>Đã gồm giao hàng. Bạn trả một lần, không trả thêm khi nhận hàng.</p>
      {notice ? (
        <p id={notice.id} role="alert" className={s.notice}>
          {notice.text}
        </p>
      ) : null}
      {cta.href ? (
        <Button {...buttonProps} href={cta.href}>
          <span className={s.onlyMobile}>{cta.label}</span>
          <span className={s.onlyDesktop}>{cta.labelDesktop ?? cta.label}</span>
        </Button>
      ) : (
        <Button {...buttonProps} form={cta.form} type={cta.form ? "submit" : "button"} onClick={cta.onClick}>
          <span className={s.onlyMobile}>{cta.label}</span>
          <span className={s.onlyDesktop}>{cta.labelDesktop ?? cta.label}</span>
        </Button>
      )}
    </section>
  );
}
