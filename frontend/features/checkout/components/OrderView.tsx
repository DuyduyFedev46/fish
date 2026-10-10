"use client";

import Banner from "@/components/ui/Banner";
import Button from "@/components/ui/Button";
import Icon from "@/components/ui/Icon";
import { useToast } from "@/components/ui/Toast";
import { contactTarget } from "@/components/shopLinks";
import { formatTimeDayVn } from "@/lib/format";
import type { OrderLookupResult } from "@/lib/types";
import { buildOrderTimeline, type OrderScreenKey, type ScreenDecision } from "../orderState";
import CancelNotice from "./CancelNotice";
import ConfirmCallBlock from "./ConfirmCallBlock";
import LookupForm, { type LookupFormProps } from "./LookupForm";
import OrderLines from "./OrderLines";
import OrderStatusBadge from "./OrderStatusBadge";
import OrderTimeline from "./OrderTimeline";
import SuccessBanner from "./SuccessBanner";
import s from "./OrderView.module.css";

export interface OrderViewProps {
  order: OrderLookupResult;
  decision: ScreenDecision;
  hotline?: string;
  /** Khung giờ gọi xác nhận từ site-info; null thì ẩn khối. */
  confirmHours: string | null;
  /** Số giờ báo vấn đề sau khi nhận hàng (E3); null thì ẩn câu. */
  returnReportHours: number | null;
  bannerDismissed: boolean;
  onDismissBanner: () => void;
  reordering: boolean;
  onReorder: () => void;
  lookup: Omit<LookupFormProps, "idPrefix">;
}

const CANCEL_SCREENS: OrderScreenKey[] = ["cancelled", "cancelled_late"];

/** Trang đơn hàng (E1 đang xử lý, E2 đã huỷ, E3 đã giao, E4 giao lỗi, E5 huỷ một phần). Không hiện người nhận. */
export default function OrderView({
  order,
  decision,
  hotline,
  confirmHours,
  returnReportHours,
  bannerDismissed,
  onDismissBanner,
  reordering,
  onReorder,
  lookup,
}: OrderViewProps) {
  const toast = useToast();
  const screen = decision.screen;
  const cancelled = CANCEL_SCREENS.includes(screen);
  const steps = buildOrderTimeline(order);
  const discount = order.discount.source && order.discount.code ? { code: order.discount.code, amount: order.discount.amount } : undefined;
  const confirming = order.state === "preparing" && /xác nhận/i.test(order.delivery?.step_label ?? "");
  const call = contactTarget(hotline);

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(order.order_code);
      toast.show({ message: "Đã sao chép" });
    } catch {
      toast.show({ message: "Chưa sao chép được, bạn chép mã đơn bằng tay nhé" });
    }
  }

  return (
    <div className={s.page}>
      {decision.banner === "paid_success" && !bannerDismissed ? <SuccessBanner onDismiss={onDismissBanner} /> : null}
      {decision.banner === "already_paid" ? (
        <Banner tone="info" live="polite">
          Đơn đã thanh toán.
        </Banner>
      ) : null}
      {screen === "delivery_failed" ? (
        <Banner tone="warn" live="polite">
          Giao không thành công. Cá Về sẽ gọi để hẹn lại.
        </Banner>
      ) : null}
      {screen === "order_partial_cancel" && order.cancel_notice ? (
        <CancelNotice notice={order.cancel_notice} fallbackHotline={hotline} variant="partial" />
      ) : null}

      <div className={s.head}>
        <h1 className={s.title}>
          Đơn hàng <span className="num">{order.order_code}</span>
        </h1>
        <Button variant="ghost" size="sm" iconStart={<Icon name="copy" size={16} />} onClick={copyCode}>
          Sao chép mã đơn
        </Button>
      </div>
      {order.placed_at ? <p className={s.placed}>Đặt lúc {formatTimeDayVn(order.placed_at)}</p> : null}

      {cancelled && order.cancel_notice ? (
        <>
          <section className={s.block} aria-labelledby="order-status-title">
            <div className={s.statusRow}>
              <h2 id="order-status-title" className={s.blockTitle}>
                Trạng thái
              </h2>
              <OrderStatusBadge state={order.state} label={order.status_label} />
            </div>
          </section>
          <CancelNotice notice={order.cancel_notice} fallbackHotline={hotline} variant="full" />
        </>
      ) : (
        <section className={s.block} aria-labelledby="order-status-title">
          <div className={s.statusRow}>
            <h2 id="order-status-title" className={s.blockTitle}>
              Trạng thái
            </h2>
            <OrderStatusBadge state={order.state} label={order.status_label} />
          </div>
          {cancelled ? null : <OrderTimeline steps={steps} />}
        </section>
      )}

      {confirming && confirmHours ? <ConfirmCallBlock hours={confirmHours} /> : null}

      <OrderLines
        title="Món trong đơn"
        variant={cancelled ? "cancelled" : "order"}
        lines={order.lines}
        total={order.total_amount}
        discount={discount}
        headingId="order-lines-title"
      />

      {screen === "delivered" && returnReportHours !== null && hotline ? (
        <section className={s.block} aria-labelledby="order-issue-title">
          <h2 id="order-issue-title" className={s.blockTitle}>
            Có vấn đề với hàng nhận được?
          </h2>
          <p className={s.text}>
            Gọi {hotline} trong {returnReportHours} giờ sau khi nhận hàng.
          </p>
          <Button variant="outline" href={call}>
            Gọi {hotline}
          </Button>
        </section>
      ) : null}

      <section className={s.block} aria-labelledby="order-other-title">
        <h2 id="order-other-title" className={s.blockTitle}>
          Tra đơn khác
        </h2>
        <LookupForm idPrefix="other" {...lookup} />
      </section>

      <div className={s.actions}>
        {cancelled || screen === "delivered" ? (
          <Button size="lg" fullWidth loading={reordering} onClick={onReorder}>
            {cancelled ? "Đặt lại món tương tự" : "Mua lại đơn này"}
          </Button>
        ) : null}
        {hotline ? (
          <Button size="lg" fullWidth variant="secondary" href={call}>
            {cancelled ? `Liên hệ ${hotline}` : "Gọi Cá Về"}
          </Button>
        ) : null}
        <Button size="lg" fullWidth variant={cancelled || screen === "delivered" ? "ghost" : "secondary"} href="/shop/">
          Tiếp tục mua
        </Button>
      </div>
    </div>
  );
}
