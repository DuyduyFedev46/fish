// Định dạng hiển thị dùng chung. Tiền/kg từ API là chuỗi thập phân ("540000", "2.500") — không
// cộng trừ bằng float ở FE; chỉ đổi sang số để HIỂN THỊ.

/** "540000" → "540.000" (không đơn vị, không số lẻ) — cho ô bảng đã có đơn vị ở tiêu đề cột. */
export function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "—";
  return Math.round(n).toLocaleString("vi-VN");
}

/** "540000" → "540.000 đ" (UI-RULES §1.6: tiền có "đ", không số lẻ). */
export function vnd(value: string | number | null | undefined): string {
  const m = money(value);
  return m === "—" ? m : `${m} đ`;
}

/** "2.500" → "2,5 kg". */
export function kg(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${n.toLocaleString("vi-VN", { maximumFractionDigits: 3 })} kg`;
}

/** Múi giờ hiển thị duy nhất của Cá Về (GMT+7, không đổi giờ mùa hè). DB lưu UTC; hiển thị luôn qua đây (SR-25). */
export const VN_TIME_ZONE = "Asia/Ho_Chi_Minh";

// Một formatter/lần gọi rẻ hơn tạo mới mỗi dòng bảng; dựng lười để không chạy Intl khi import ở test node.
let partsFmt: Intl.DateTimeFormat | null = null;

/** Tách ngày giờ theo giờ VN → { year, month, day, hour, minute, second } (chuỗi 2 chữ số). null nếu không hợp lệ. */
function vnParts(input: string | number | Date | null | undefined) {
  if (input === null || input === undefined || input === "") return null;
  const d = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(d.getTime())) return null;
  partsFmt ??= new Intl.DateTimeFormat("en-GB", {
    timeZone: VN_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23", // tránh "24:05" lúc nửa đêm
  });
  const o: Record<string, string> = {};
  for (const p of partsFmt.formatToParts(d)) o[p.type] = p.value;
  return { year: o.year, month: o.month, day: o.day, hour: o.hour, minute: o.minute, second: o.second };
}

/** ISO → "24/09/2026 14:05" (giờ VN, bất kể múi giờ máy; UI-RULES §1.5: luôn đủ ngày giờ, có năm). */
export function dateTime(iso: string | Date | null | undefined): string {
  const p = vnParts(iso);
  return p ? `${p.day}/${p.month}/${p.year} ${p.hour}:${p.minute}` : "—";
}

/** Giữ tên cũ cho chỗ đang gọi: giống `dateTime`. */
export function dateTimeFull(iso: string | Date | null | undefined): string {
  const p = vnParts(iso);
  return p ? `${p.day}/${p.month}/${p.year} ${p.hour}:${p.minute}` : "—";
}

/** ISO → "24/09/2026" (ngày theo giờ VN). */
export function date(iso: string | Date | null | undefined): string {
  const p = vnParts(iso);
  return p ? `${p.day}/${p.month}/${p.year}` : "—";
}

/** ISO → "14:05" (giờ VN). */
export function timeHM(iso: string | Date | null | undefined): string {
  const p = vnParts(iso);
  return p ? `${p.hour}:${p.minute}` : "—";
}

/** ISO → "14:05:09" (giờ VN) — chỉ cho mốc hẹn giờ cần độ chính xác tới giây. */
export function timeHMS(iso: string | Date | null | undefined): string {
  const p = vnParts(iso);
  return p ? `${p.hour}:${p.minute}:${p.second}` : "—";
}

/** Ngày "hôm nay" theo giờ VN dạng "2026-09-30" (dùng cho lọc/so sánh ngày; KHÔNG dùng `toISOString().slice(0,10)` vì đó là UTC). */
export function todayInVietnam(now: Date = new Date()): string {
  const p = vnParts(now);
  return p ? `${p.year}-${p.month}-${p.day}` : "";
}

/**
 * Giá trị ô `datetime-local` ("2026-09-30T15:00") do người dùng nhập là GIỜ VIỆT NAM, không phải giờ máy →
 * ISO UTC để gửi BE ("2026-09-30T08:00:00.000Z"). "" hoặc sai định dạng → "".
 */
export function vnInputToIso(local: string | null | undefined): string {
  const m = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::(\d{2}))?$/.exec(local ?? "");
  if (!m) return "";
  const d = new Date(`${m[1]}T${m[2]}:${m[3] ?? "00"}+07:00`);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString();
}

/** ISO → "2026-09-30" theo giờ VN (khoá gom nhóm theo ngày). "" nếu không hợp lệ. */
export function dateKeyInVietnam(iso: string | Date | null | undefined): string {
  const p = vnParts(iso);
  return p ? `${p.year}-${p.month}-${p.day}` : "";
}

/** "2026-10-28" → "28/10/2026" (ngày thuần từ BE như hạn hoàn tiền; không đổi múi giờ). */
export function dateOnly(isoDate: string | null | undefined): string {
  if (!isoDate) return "—";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(isoDate);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : "—";
}

/** "2026-09-30" → "30/09" (ngày thuần, không đổi múi giờ). */
export function dayMonth(isoDate: string | null | undefined): string {
  if (!isoDate) return "—";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(isoDate);
  return m ? `${m[3]}/${m[2]}` : "—";
}

/** Đếm ngược tới mốc `iso` (mốc do backend trả) dạng "mm:ss" (phút có thể quá 59: "65:12"); "hết giờ" khi đã qua. null nếu không có mốc. */
export function remaining(iso: string | null | undefined, now: number): string | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - now;
  if (Number.isNaN(ms)) return null;
  if (ms <= 0) return "hết giờ";
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const sec = total % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}
