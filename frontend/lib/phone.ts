/**
 * Số hotline hợp lệ để hiện và gắn `tel:`. File thuần TypeScript, không import gì (test bằng `scripts/test-phone.mjs`).
 * Chỉ nhận chuỗi gồm chữ số, khoảng trắng và dấu + (cho phép + ở đầu), có 8 đến 15 chữ số.
 * Số giữ chỗ kiểu "1900 xxxx" hay "[hotline]" bị loại: không có số thật thì ẩn nút gọi, không đưa `tel:` sai.
 */
export function validHotline(raw: string | null | undefined): string | undefined {
  const value = (raw ?? "").trim();
  if (!value) return undefined;
  if (!/^\+?[\d ]+$/.test(value)) return undefined;
  const digits = value.replace(/\D/g, "");
  if (digits.length < 8 || digits.length > 15) return undefined;
  return value;
}

/** Số hotline hợp lệ đầu tiên trong các nguồn, theo thứ tự ưu tiên. */
export function pickHotline(...candidates: Array<string | null | undefined>): string | undefined {
  for (const c of candidates) {
    const ok = validHotline(c);
    if (ok) return ok;
  }
  return undefined;
}
