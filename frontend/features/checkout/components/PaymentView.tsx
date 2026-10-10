"use client";

import Banner from "@/components/ui/Banner";
import Button from "@/components/ui/Button";
import CartSummary from "@/components/cart/CartSummary";
import { formatQty } from "@/lib/quantity";
import type { OrderLookupResult } from "@/lib/types";
import HoldCountdown from "./HoldCountdown";
import PaymentMethod from "./PaymentMethod";
import OrderLines from "./OrderLines";
import s from "./PaymentView.module.css";

export interface PaymentViewProps {
  order: OrderLookupResult;
  /** retry: về từ cổng với huỷ hoặc lỗi (D2). expired: đồng hồ về 0, chờ máy chủ xác nhận (D4 hộp thoại). */
  mode: "payment" | "retry" | "expired";
  paying: boolean;
  payError: string | null;
  onPay: () => void;
  onExpire: () => void;
  onReorder: () => void;
  reordering: boolean;
}

/** Thanh toán (D1), thanh toán chưa thành công (D2), nền của hộp thoại hết giờ (D4). Không có nút "Huỷ đơn" (BR-BH-28). */
export default function PaymentView({ order, mode, paying, payError, onPay, onExpire, onReorder, reordering }: PaymentViewProps) {
  const expired = mode === "expired";
  const discount = order.discount.source && order.discount.code ? { code: order.discount.code, amount: order.discount.amount } : undefined;
  const summaryLines = order.lines.map((l) => ({
    name: l.name,
    qtyText: `${formatQty(Number(l.qty))} ${l.unit}`,
    amount: l.amount,
  }));
  return (
    <div className={s.layout}>
      <div className={s.main}>
        {mode === "retry" ? (
          <Banner tone="crit" title="Thanh toán chưa thành công" live="polite">
            Bạn đã huỷ hoặc ngân hàng báo lỗi. Đơn vẫn đang được giữ.
          </Banner>
        ) : null}
        {expired ? (
          <Banner
            tone="warn"
            title="Hết thời gian giữ hàng"
            live="polite"
            action={
              <Button size="sm" variant="outline" loading={reordering} onClick={onReorder}>
                Đặt lại đơn này
              </Button>
            }
          >
            Cá Về đang xác nhận với hệ thống.
          </Banner>
        ) : null}
        {payError ? (
          <Banner tone="crit" live="assertive">
            {payError}
          </Banner>
        ) : null}
        {order.booked_expires_at ? (
          <HoldCountdown
            orderCode={order.order_code}
            expiresAt={order.booked_expires_at}
            holdMinutes={order.hold_minutes}
            serverNow={order.server_now}
            variant={mode === "retry" ? "retry" : "created"}
            onExpire={onExpire}
          />
        ) : null}
        <PaymentMethod />
        <div className={s.onlyMobile}>
          <OrderLines
            title="Tóm tắt"
            variant="summary"
            lines={order.lines}
            discount={discount}
          />
        </div>
      </div>
      <div className={s.side}>
        <CartSummary
          context={mode === "retry" ? "payment-retry" : "payment"}
          itemCount={order.lines.length}
          total={order.total_amount}
          title="Tóm tắt đơn"
          totalLabel="Cần thanh toán"
          lines={summaryLines}
          discount={discount}
          cta={{
            label: mode === "retry" ? "Thanh toán lại" : "Thanh toán",
            icon: "lock",
            loading: paying,
            loadingText: "Đang chuyển…",
            disabled: expired,
            onClick: onPay,
          }}
        />
      </div>
    </div>
  );
}
