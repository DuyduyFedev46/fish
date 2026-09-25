"use client";

import { useEffect, useState } from "react";

function formatRemaining(ms: number): string {
  if (ms <= 0) return "00:00";
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (totalSeconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function CountdownTimer({
  expiresAt,
  onExpire,
}: {
  expiresAt: string;
  onExpire?: () => void;
}) {
  const [remainingMs, setRemainingMs] = useState<number>(() =>
    new Date(expiresAt).getTime() - Date.now()
  );
  const [expiredNotified, setExpiredNotified] = useState(false);

  useEffect(() => {
    const target = new Date(expiresAt).getTime();
    const tick = () => setRemainingMs(target - Date.now());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [expiresAt]);

  useEffect(() => {
    if (remainingMs <= 0 && !expiredNotified) {
      setExpiredNotified(true);
      onExpire?.();
    }
  }, [remainingMs, expiredNotified, onExpire]);

  const expired = remainingMs <= 0;

  return (
    <div className={"countdown" + (expired ? " countdown-expired" : "")}>
      <span className="countdown-label">
        {expired ? "Đơn đã hết hạn giữ chỗ" : "Thời gian giữ chỗ còn lại"}
      </span>
      <span className="countdown-value">{formatRemaining(remainingMs)}</span>
    </div>
  );
}
