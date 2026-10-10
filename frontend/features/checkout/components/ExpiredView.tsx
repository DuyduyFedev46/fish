"use client";

import Button from "@/components/ui/Button";
import Icon from "@/components/ui/Icon";
import { contactTarget } from "@/components/shopLinks";
import s from "./ExpiredView.module.css";

export interface ExpiredViewProps {
  orderCode: string;
  holdMinutes: number;
  hotline?: string;
  reordering: boolean;
  onReorder: () => void;
}

/** D4 dạng trang: đơn đã tự huỷ vì quá giờ giữ hàng, chưa có tiền về. */
export default function ExpiredView({ orderCode, holdMinutes, hotline, reordering, onReorder }: ExpiredViewProps) {
  return (
    <section className={s.box} aria-labelledby="expired-title">
      <span className={s.icon} aria-hidden="true">
        <Icon name="hourglass" size={30} />
      </span>
      <h1 id="expired-title" className={s.title}>
        Hết thời gian giữ hàng
      </h1>
      <p className={s.text}>
        Đơn <span className="num">{orderCode}</span> đã tự huỷ sau {holdMinutes} phút chưa thanh toán. Hàng đã trả lại kho, bạn chưa bị trừ tiền.
      </p>
      <div className={s.actions}>
        <Button size="lg" fullWidth loading={reordering} onClick={onReorder}>
          Đặt lại đơn này
        </Button>
        <Button size="lg" fullWidth variant="secondary" href="/">
          Về trang chủ
        </Button>
      </div>
      <p className={s.note}>
        Đã chuyển khoản rồi? Liên hệ{" "}
        {hotline ? <a href={contactTarget(hotline)}>{hotline}</a> : <a href={contactTarget(undefined)}>Cá Về</a>}, Cá Về sẽ kiểm tra và gọi lại cho bạn.
      </p>
    </section>
  );
}
