/**
 * Luật số lượng của Shop (BR-BH-22): món kg mua tối thiểu `min_qty` (mặc định 1 kg), bước `qty_step`
 * (mặc định 0,5 kg); combo tối thiểu 1, bước 1. Giá trị `min_qty`/`qty_step` lấy từ catalog, không hard-code.
 *
 * File thuần TypeScript, không import gì, để `scripts/test-quantity.mjs` chạy được không cần build.
 * Mọi phép tính qua số nguyên "phần nghìn" để 0,1 + 0,2 không sinh số lẻ kiểu 0.30000000000000004.
 */

const SCALE = 1000;

function toUnits(value: number): number {
  return Math.round(value * SCALE);
}

function fromUnits(units: number): number {
  return units / SCALE;
}

export type QtyRule = { minQty: number; step: number };

/** Đọc `min_qty`, `qty_step` (chuỗi từ API); thiếu hay sai thì dùng 1 và 0,5 cho kg, 1 và 1 cho combo. */
export function parseQtyRule(
  minQty: string | number | null | undefined,
  qtyStep: string | number | null | undefined,
  unit: "kg" | "combo" = "kg"
): QtyRule {
  const fallbackStep = unit === "combo" ? 1 : 0.5;
  const min = Number(minQty);
  const step = Number(qtyStep);
  return {
    minQty: Number.isFinite(min) && min > 0 ? min : 1,
    step: Number.isFinite(step) && step > 0 ? step : fallbackStep,
  };
}

/** Số lượng hợp lệ: không nhỏ hơn mức tối thiểu và nằm đúng bước tính từ 0. */
export function isValidQty(qty: number, rule: QtyRule): boolean {
  if (!Number.isFinite(qty)) return false;
  const q = toUnits(qty);
  return q >= toUnits(rule.minQty) && q % toUnits(rule.step) === 0;
}

/** Tăng một bước. */
export function stepUp(qty: number, rule: QtyRule): number {
  return fromUnits(toUnits(qty) + toUnits(rule.step));
}

/**
 * Giảm một bước. Trả `null` khi giảm sẽ xuống dưới mức tối thiểu: màn hình phải mở hộp thoại
 * xác nhận bỏ món, không bao giờ hiện 0,5 kg hay số lẻ ngoài bước (G4).
 */
export function stepDown(qty: number, rule: QtyRule): number | null {
  const next = toUnits(qty) - toUnits(rule.step);
  return next < toUnits(rule.minQty) ? null : fromUnits(next);
}

/** Làm tròn LÊN tới số lượng hợp lệ gần nhất (dùng khi đọc giỏ cũ có số lẻ). */
export function snapUp(qty: number, rule: QtyRule): number {
  if (!Number.isFinite(qty) || qty <= rule.minQty) return rule.minQty;
  const step = toUnits(rule.step);
  return fromUnits(Math.ceil(toUnits(qty) / step) * step);
}

/** Chuỗi gửi lên máy chủ: "1", "1.5", "2" (bỏ ".0" thừa, dấu chấm). */
export function qtyToApiString(qty: number): string {
  const rounded = Math.round(qty * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

/** Chữ hiển thị: "1", "1,5". Đơn vị do chỗ gọi ghép thêm. */
export function formatQty(qty: number): string {
  return qtyToApiString(qty).replace(".", ",");
}
