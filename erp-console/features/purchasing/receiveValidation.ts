// Kiểm form Nhập lô tại cảng (F1a) trước khi gửi, và dựng body gửi BE. Hàm thuần.
// ED-20-AC3: số kg không hợp lệ báo NGAY DƯỚI ô. QA Lô 10 B5: giá mua lỗi báo dưới ô và không gửi, không tự đổi thành 0.
import { moneyBody, moneyMessage } from "@/features/accounting/money";
import type { ReceiveBatchesLineInput } from "./types";

export const QTY_MESSAGE = "Nhập số kg lớn hơn 0.";
export const QTY_TOO_LARGE_MESSAGE = "Số kg quá lớn, tối đa 999.999.999 kg.";
export const QTY_DECIMALS_MESSAGE = "Số kg chỉ lấy tối đa 3 chữ số lẻ.";

const QTY_FORMAT = /^\d+(?:[.,]\d+)?$/;
// BE: DecimalField(max_digits=12, decimal_places=3) → phần nguyên tối đa 9 chữ số.
const QTY_MAX_INTEGER_DIGITS = 9;

/** "12,5" hay "12.5" → "12.5"; sai dạng (rỗng, chữ, âm) → null. Không đoán. */
export function normalizeQty(value: string): string | null {
  const raw = value.trim();
  return QTY_FORMAT.test(raw) ? raw.replace(",", ".") : null;
}

/** Câu báo cho ô số kg, hoặc null khi hợp lệ. */
export function qtyMessage(value: string): string | null {
  const n = normalizeQty(value);
  if (n === null || Number(n) <= 0) return QTY_MESSAGE;
  const [integer, fraction = ""] = n.split(".");
  if (integer.replace(/^0+(?=\d)/, "").length > QTY_MAX_INTEGER_DIGITS) return QTY_TOO_LARGE_MESSAGE;
  if (fraction.length > 3) return QTY_DECIMALS_MESSAGE;
  return null;
}

/** Giá mua: để trống = chưa có giá (hợp lệ); đã nhập thì phải là số nguyên đồng lớn hơn 0. */
export function rateMessage(value: string): string | null {
  return moneyMessage(value, { noun: "Giá mua", allowEmpty: true, positive: true });
}

export type ReceiveFormErrors = Record<string, string>;

/** Khoá lỗi trùng `name` của ô: `supplier`, `item-<i>`, `qty-<i>`, `rate-<i>`. Rỗng = hợp lệ. */
export function validateReceiveForm(input: { supplierId: number | ""; lines: ReceiveBatchesLineInput[] }): ReceiveFormErrors {
  const errors: ReceiveFormErrors = {};
  if (!input.supplierId) errors.supplier = "Vui lòng chọn nhà cung cấp.";
  input.lines.forEach((l, i) => {
    if (!l.item_code) errors[`item-${i}`] = "Chọn mặt hàng.";
    const qty = qtyMessage(l.qty);
    if (qty) errors[`qty-${i}`] = qty;
    const rate = rateMessage(l.rate);
    if (rate) errors[`rate-${i}`] = rate;
  });
  return errors;
}

/** Tên ô lỗi đầu tiên theo thứ tự trên màn hình (để đưa con trỏ tới). */
export function firstErrorKey(errors: ReceiveFormErrors, lineCount: number): string | null {
  if (errors.supplier) return "supplier";
  for (let i = 0; i < lineCount; i++) {
    for (const key of [`item-${i}`, `qty-${i}`, `rate-${i}`]) if (errors[key]) return key;
  }
  return null;
}

/** Dòng gửi BE. Chỉ gọi khi `validateReceiveForm` rỗng; giá mua trống gửi "0.00" (chưa có giá), giá sai thì NÉM LỖI chứ không thành 0. */
export function buildReceiveLines(lines: ReceiveBatchesLineInput[]): ReceiveBatchesLineInput[] {
  return lines.map((l) => {
    const qty = normalizeQty(l.qty);
    if (qty === null || Number(qty) <= 0) throw new Error("Số kg không hợp lệ, không gửi.");
    return {
      item_code: l.item_code,
      qty: String(Number(qty)),
      rate: l.rate.trim() === "" ? "0.00" : moneyBody(l.rate),
      shelf_life_days: l.shelf_life_days ? Number(l.shelf_life_days) : null,
    };
  });
}
