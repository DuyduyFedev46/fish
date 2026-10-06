// Bộ lọc danh sách: khoảng ngày theo giờ Việt Nam + nhãn lý do huỷ. Hàm thuần để vitest kiểm được.

import { todayInVietnam } from "@/shared/lib/format";
import type { DatePreset } from "./labels";

const DAY_MS = 86_400_000;

/** Khoảng ngày YYYY-MM-DD theo giờ Việt Nam cho một lựa chọn ngày; `custom` lấy đúng hai ô người dùng nhập. */
export function presetRange(p: DatePreset, from: string, to: string, now = Date.now()): { date_from: string; date_to: string } {
  const day = (ms: number) => todayInVietnam(new Date(ms));
  if (p === "today") return { date_from: day(now), date_to: day(now) };
  if (p === "7d") return { date_from: day(now - 6 * DAY_MS), date_to: day(now) };
  if (p === "30d") return { date_from: day(now - 29 * DAY_MS), date_to: day(now) };
  if (p === "custom") return { date_from: from, date_to: to };
  return { date_from: "", date_to: "" };
}

/** Cột "Lý do" của danh sách đơn: BE trả `reason`; đơn Giữ chỗ vừa hết giờ (chip đã đổi sang "Đã huỷ" tại máy) → "Hết giờ giữ chỗ". */
export function reasonText(reason: { label: string } | null | undefined, effectiveStatus: string): string | null {
  if (reason?.label) return reason.label;
  return effectiveStatus === "AUTO_CANCELLED" ? "Hết giờ giữ chỗ" : null;
}

/** Tháng hiện tại YYYY-MM theo giờ Việt Nam. */
export function currentMonth(now = new Date()): string {
  return todayInVietnam(now).slice(0, 7);
}

/** 12 tháng gần nhất (mới → cũ) cho ô chọn tháng của phiếu hoàn tiền. */
export function recentMonths(now = new Date(), count = 12): { value: string; label: string }[] {
  const [y, m] = currentMonth(now).split("-").map(Number);
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(Date.UTC(y, m - 1 - i, 1));
    const yy = d.getUTCFullYear();
    const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
    return { value: `${yy}-${mm}`, label: `Tháng ${mm}/${yy}` };
  });
}

/** Đọc `?order=<id>` của link cũ; null khi không có hoặc không phải số nguyên dương. */
export function legacyOrderRedirect(search: string): string | null {
  const sp = new URLSearchParams(search);
  const raw = sp.get("order");
  if (!raw || !/^\d+$/.test(raw) || Number(raw) <= 0) return null;
  return `/orders/detail/?id=${raw}${sp.get("open") === "refund" ? "&open=refund" : ""}`;
}
