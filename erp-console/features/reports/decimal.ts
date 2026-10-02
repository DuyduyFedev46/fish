// Số thập phân dạng chuỗi của BE ("1650000.50", "-250000"): cộng, trừ, làm tròn bằng BigInt, KHÔNG dùng số thực
// (shared/lib/format.ts chỉ đổi sang số để HIỂN THỊ). Hàm thuần, có test.

const SCALE = 6;
const FACTOR = BigInt(10) ** BigInt(SCALE);
const ZERO = BigInt(0);
const TWO = BigInt(2);

/** "-1234.5" → số nguyên lớn nhân 10^6. Chuỗi rỗng hay sai dạng → null. Phần lẻ quá 6 chữ số bị cắt (BE không trả nhiều hơn). */
export function parseDecimal(text: string | null | undefined): bigint | null {
  const m = /^\s*([+-])?(\d+)(?:\.(\d*))?\s*$/.exec(text ?? "");
  if (!m) return null;
  const fraction = (m[3] ?? "").slice(0, SCALE).padEnd(SCALE, "0");
  const value = BigInt(m[2]) * FACTOR + BigInt(fraction || "0");
  return m[1] === "-" ? -value : value;
}

/** Ngược lại của parseDecimal; bỏ số 0 thừa ở phần lẻ ("12.500000" → "12.5", "7.000000" → "7"). */
export function formatDecimal(value: bigint): string {
  const negative = value < ZERO;
  const abs = negative ? -value : value;
  const whole = abs / FACTOR;
  const fraction = String(abs % FACTOR).padStart(SCALE, "0").replace(/0+$/, "");
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
}

function combine(a: string, b: string, subtract: boolean): string | null {
  const x = parseDecimal(a);
  const y = parseDecimal(b);
  if (x === null || y === null) return null;
  return formatDecimal(subtract ? x - y : x + y);
}

/** a + b; một trong hai sai dạng → null (không đoán thành 0). */
export const addDecimal = (a: string, b: string): string | null => combine(a, b, false);
/** a − b. */
export const subDecimal = (a: string, b: string): string | null => combine(a, b, true);

/** -1 âm · 0 bằng không · 1 dương; sai dạng → null. */
export function signOf(text: string | null | undefined): -1 | 0 | 1 | null {
  const v = parseDecimal(text);
  if (v === null) return null;
  return v < ZERO ? -1 : v > ZERO ? 1 : 0;
}

/** Số đồng nguyên gần nhất, .5 làm tròn lên (xa số 0): "1650000.50" → "1650001". Sai dạng → "". */
export function roundToDong(text: string | null | undefined): string {
  const v = parseDecimal(text);
  if (v === null) return "";
  const negative = v < ZERO;
  const abs = negative ? -v : v;
  const rounded = (abs + FACTOR / TWO) / FACTOR;
  return `${negative && rounded > ZERO ? "-" : ""}${rounded}`;
}

/** Giá trị tuyệt đối dạng chuỗi ("-250000.5" → "250000.5"). Sai dạng → "". */
export function absDecimal(text: string): string {
  const v = parseDecimal(text);
  return v === null ? "" : formatDecimal(v < ZERO ? -v : v);
}

/**
 * Chuẩn hoá một giá trị tiền/kg BE trả về thành chuỗi thập phân. Hai endpoint báo cáo trả JSON number (DRF đổi Decimal
 * thành float), còn các endpoint khác trả chuỗi; hàm nhận cả hai. Chuỗi giữ nguyên. Số dùng dạng ngắn nhất của JS;
 * dạng mũ ("1e-7", "1e+21") đổi sang dạng thường để parseDecimal đọc được. null/undefined giữ nguyên (không đoán thành 0).
 */
export function toDecimalString(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return value as unknown as string;
  if (typeof value === "string") return value;
  if (!Number.isFinite(value)) return "";
  const text = String(value);
  if (!/e/i.test(text)) return text;
  if (Math.abs(value) >= 1) return BigInt(value).toString();
  return value.toFixed(SCALE);
}

/** |a| / |b| dưới dạng số thực 0..1 CHỈ để vẽ độ dài thanh (không phải số tiền). */
export function ratioOf(a: string, b: string): number {
  const x = parseDecimal(a);
  const y = parseDecimal(b);
  if (x === null || y === null || y === ZERO) return 0;
  const abs = (n: bigint) => (n < ZERO ? -n : n);
  return Math.min(1, Number((abs(x) * BigInt(10_000)) / abs(y)) / 10_000);
}
