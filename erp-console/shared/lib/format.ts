// Định dạng hiển thị dùng chung. Tiền/kg từ API là chuỗi thập phân ("540000", "2.500") — không
// cộng trừ bằng float ở FE; chỉ đổi sang số để HIỂN THỊ.

/** "540000" → "540.000 ₫" (không số lẻ). */
export function vnd(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${Math.round(n).toLocaleString("vi-VN")} ₫`;
}

/** "2.500" → "2,5 kg". */
export function kg(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${n.toLocaleString("vi-VN", { maximumFractionDigits: 3 })} kg`;
}

/** ISO → "24/09 14:05". */
export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

/** ISO → "14:05" (giờ máy người dùng). */
export function timeHM(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

/** "2026-09-30" → "30/09" (ngày thuần, không đổi múi giờ). */
export function dayMonth(isoDate: string | null | undefined): string {
  if (!isoDate) return "—";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(isoDate);
  return m ? `${m[3]}/${m[2]}` : "—";
}

/** Thời gian còn lại tới mốc `iso` (mốc do backend trả): "1h05′", "12′", "hết giờ". null nếu không có mốc. */
export function remaining(iso: string | null | undefined, now: number): string | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - now;
  if (Number.isNaN(ms)) return null;
  if (ms <= 0) return "hết giờ";
  const m = Math.floor(ms / 60000);
  return (m >= 60 ? `${Math.floor(m / 60)}h${String(m % 60).padStart(2, "0")}′` : `${m}′`);
}
