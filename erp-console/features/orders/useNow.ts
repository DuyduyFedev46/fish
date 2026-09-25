"use client";

import { useEffect, useState } from "react";

/** Đồng hồ cho đếm lùi giữ chỗ — chỉ chạy khi `active` (có đơn đang giữ chỗ). Mốc hết hạn luôn do BE trả. */
export function useNow(active: boolean, everyMs: number): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    setNow(Date.now());
    const t = setInterval(() => setNow(Date.now()), everyMs);
    return () => clearInterval(t);
  }, [active, everyMs]);
  return now;
}

/** "mm:ss" còn lại tới mốc `iso` (S10-AC5); null nếu không có mốc; "00:00" khi đã qua. */
export function mmss(iso: string | null | undefined, now: number): { text: string; over: boolean; ms: number } | null {
  if (!iso) return null;
  const end = new Date(iso).getTime();
  if (Number.isNaN(end)) return null;
  const ms = Math.max(0, end - now);
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return { text: `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`, over: ms <= 0, ms };
}
