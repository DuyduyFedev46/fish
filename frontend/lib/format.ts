// Định dạng hiển thị dùng chung cho Shop (P8 Lô 8, SR-25). Thống nhất với ERP
// (`erp-console/shared/lib/format.ts`):
//   - Tiền là VNĐ, dạng "260.000 ₫" (dấu chấm ngăn nghìn, không số lẻ). API trả Decimal dạng chuỗi
//     ("260000.00") nên hàm nhận cả chuỗi lẫn số; giá trị rác -> "—".
//   - Ngày giờ luôn theo giờ Việt Nam (GMT+7, "Asia/Ho_Chi_Minh"), bất kể múi giờ máy người xem.
//     DB/API lưu UTC, chỉ đổi ở lúc hiển thị.
// Cấm gọi `toLocaleString`/`toLocaleDateString`/`toLocaleTimeString`/`Intl.DateTimeFormat` rải rác
// trong component — dùng các hàm ở đây.

export const VN_TIME_ZONE = "Asia/Ho_Chi_Minh";

type Nullable = string | number | null | undefined;

/** Ép về số hữu hạn; chuỗi rỗng, null, chữ rác -> null. */
function toNumber(value: Nullable): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

/** "260000.00" | 260000 -> "260.000 ₫". */
export function formatVnd(value: Nullable): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return `${Math.round(n).toLocaleString("vi-VN")} ₫`;
}

/** "2.500" | 2.5 -> "2,5 kg" (tối đa 3 số lẻ). */
export function formatKg(value: Nullable): string {
  const n = toNumber(value);
  if (n === null) return "—";
  const rounded = Math.round(n * 1000) / 1000;
  return `${rounded.toLocaleString("vi-VN")} kg`;
}

const vnParts = new Intl.DateTimeFormat("en-GB", {
  timeZone: VN_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

type VnParts = { year: string; month: string; day: string; hour: string; minute: string };

/** Tách một mốc thời gian (ISO/Date/epoch ms) thành các phần theo giờ VN; không hợp lệ -> null. */
function vnPartsOf(value: string | number | Date | null | undefined): VnParts | null {
  if (value === null || value === undefined || value === "") return null;
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  const out: Record<string, string> = {};
  for (const p of vnParts.formatToParts(d)) out[p.type] = p.value;
  return out as unknown as VnParts;
}

/** ISO -> "01/10 00:30" (giờ VN). */
export function formatDateTime(value: string | number | Date | null | undefined): string {
  const p = vnPartsOf(value);
  return p ? `${p.day}/${p.month} ${p.hour}:${p.minute}` : "—";
}

/** ISO -> "01/10/2026" (ngày theo giờ VN). */
export function formatDate(value: string | number | Date | null | undefined): string {
  const p = vnPartsOf(value);
  return p ? `${p.day}/${p.month}/${p.year}` : "—";
}

/** ISO -> "00:30" (giờ VN). */
export function formatTime(value: string | number | Date | null | undefined): string {
  const p = vnPartsOf(value);
  return p ? `${p.hour}:${p.minute}` : "—";
}

/** "2026-10-28" (ngày thuần do backend đã tính theo giờ VN) -> "28/10/2026"; không đổi múi giờ. */
export function formatDateOnly(value: string | null | undefined): string {
  if (!value) return "—";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : "—";
}

/** Ngày "hôm nay" theo giờ VN, dạng "YYYY-MM-DD" (dùng cho lọc/đặt mã theo ngày). */
export function todayVn(now: Date = new Date()): string {
  const p = vnPartsOf(now)!;
  return `${p.year}-${p.month}-${p.day}`;
}

/** Năm hiện tại theo giờ VN (dùng cho dòng bản quyền). */
export function currentYearVn(now: Date = new Date()): number {
  return Number(vnPartsOf(now)!.year);
}
