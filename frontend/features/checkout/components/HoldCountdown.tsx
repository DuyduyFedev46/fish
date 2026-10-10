"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Skeleton from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import { clockOffsetMs, formatRemaining, remainingLabel, remainingMs } from "../orderState";
import s from "./HoldCountdown.module.css";

export interface HoldCountdownProps {
  orderCode: string;
  /** ISO UTC từ máy chủ: hạn giữ hàng. Không tự cộng 30 phút ở FE. */
  expiresAt: string;
  /** Tổng thời gian giữ (phút) từ máy chủ; thiếu thì ẩn thanh. */
  holdMinutes?: number;
  /** Giờ máy chủ lúc trả lời, để bù lệch giờ máy khách. */
  serverNow?: string;
  /** created: vừa tạo đơn (D1). retry: về từ cổng với huỷ/lỗi (D2). */
  variant?: "created" | "retry";
  /** Gọi một lần khi về 0. */
  onExpire?: () => void;
}

const WARN_SECONDS = 300;

/**
 * Đồng hồ đếm ngược giữ hàng (COMPONENTS #24). Tính từ `expiresAt` của máy chủ trừ giờ hiện tại đã bù lệch;
 * dưới 5 phút chuyển hổ phách, về 0 thì đỏ. Số lớn là `role="timer"` không đọc mỗi giây; vùng `aria-live` riêng báo ở mốc 5 phút và 1 phút.
 */
export default function HoldCountdown({
  orderCode,
  expiresAt,
  holdMinutes,
  serverNow,
  variant = "created",
  onExpire,
}: HoldCountdownProps) {
  const offset = useMemo(() => clockOffsetMs(serverNow, Date.now()), [serverNow, expiresAt]);
  const [now, setNow] = useState(() => Date.now());
  const [announce, setAnnounce] = useState("");
  const expiredRef = useRef(false);
  const warnedRef = useRef<{ five: boolean; one: boolean }>({ five: false, one: false });
  const onExpireRef = useRef(onExpire);
  onExpireRef.current = onExpire;

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const remaining = remainingMs(expiresAt, now, offset);
  const seconds = remaining === null ? null : Math.ceil(remaining / 1000);

  useEffect(() => {
    if (seconds === null) return;
    if (seconds <= 0 && !expiredRef.current) {
      expiredRef.current = true;
      onExpireRef.current?.();
    }
    if (seconds > 0 && seconds <= 60 && !warnedRef.current.one) {
      warnedRef.current.one = true;
      warnedRef.current.five = true;
      setAnnounce("Còn 1 phút để thanh toán.");
    } else if (seconds > 60 && seconds <= WARN_SECONDS && !warnedRef.current.five) {
      warnedRef.current.five = true;
      setAnnounce("Còn 5 phút để thanh toán.");
    }
  }, [seconds]);

  const tone = seconds === null ? "ok" : seconds <= 0 ? "crit" : seconds <= WARN_SECONDS ? "warn" : "ok";
  const ratio =
    remaining !== null && holdMinutes && holdMinutes > 0 ? Math.min(1, remaining / (holdMinutes * 60 * 1000)) : null;
  // Nhãn đọc cho trình đọc màn hình chỉ đổi theo phút, không theo giây.
  const minuteLabel = remaining === null ? "" : remainingLabel(Math.ceil(remaining / 60000) * 60000);

  const isRetry = variant === "retry";
  return (
    <section className={cx(s.box, s[tone])} aria-labelledby="hold-title">
      <p id="hold-title" className={s.code}>
        Đơn <span className={cx(s.codeValue, "num")}>{orderCode}</span> {isRetry ? "chưa thanh toán" : "đã được tạo"}
      </p>
      <p className={s.lead}>
        {seconds !== null && seconds <= 0
          ? "Thời gian giữ hàng còn lại"
          : isRetry
            ? "Cá Về còn giữ hàng cho bạn trong"
            : "Cá Về đang giữ hàng cho bạn trong"}
      </p>
      {remaining === null ? (
        <Skeleton width={140} height={44} radius="md" />
      ) : (
        <span role="timer" aria-live="off" aria-label={minuteLabel} className={cx(s.time, "num")}>
          {formatRemaining(remaining)}
        </span>
      )}
      {ratio !== null ? (
        <div className={s.track} aria-hidden="true">
          <div className={s.bar} style={{ transform: `scaleX(${ratio})` }} />
        </div>
      ) : null}
      <span className="visually-hidden" role="status" aria-live="polite">
        {announce}
      </span>
    </section>
  );
}
