"use client";

import { useEffect, useState } from "react";
import { holdInfo } from "./orderDetailModel";

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

/**
 * true khi đơn Giữ chỗ (BOOKED) đã qua mốc hết giờ. Chỉ MỘT lần đặt giờ tới mốc hết hạn (không tick mỗi giây), nên trang chỉ vẽ lại
 * đúng lúc chip đổi sang "Đã huỷ" (ED-09-AC5, L5). Ô đếm ngược mm:ss tự giữ đồng hồ riêng (`HoldLeft`).
 */
export function useHoldExpired(status: string, reservedUntil: string | null | undefined): boolean {
  const end = status === "BOOKED" && reservedUntil ? new Date(reservedUntil).getTime() : NaN;
  const [expired, setExpired] = useState(() => !Number.isNaN(end) && Date.now() >= end);
  useEffect(() => {
    if (Number.isNaN(end)) {
      setExpired(false);
      return;
    }
    const wait = end - Date.now();
    if (wait <= 0) {
      setExpired(true);
      return;
    }
    setExpired(false);
    const t = setTimeout(() => setExpired(true), Math.min(wait, 2_000_000_000));
    return () => clearTimeout(t);
  }, [end]);
  return expired;
}

/** Ô "Còn giữ chỗ": đồng hồ mm:ss riêng, chỉ ô này vẽ lại mỗi giây. Dừng khi hết giờ. */
export function holdLeftText(status: string, reservedUntil: string | null | undefined, now: number): string | null {
  const h = holdInfo(status, reservedUntil, now);
  return h ? (h.over ? "00:00" : h.left) : null;
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
