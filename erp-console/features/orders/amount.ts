// Đọc ô số tiền VND dùng chung trong module Đơn & tiền: S11 (xác nhận đã nhận tiền) và S13 (tạo phiếu hoàn tiền từ hàng chờ).
// Tách ra từ ConfirmPaymentForm (B13, QA L7) để hai form chặn trước tại ô cùng một cách. BE vẫn là lớp chặn chính.

import { formatMoneyInput, splitFraction } from "@/shared/lib/moneyInput";
import { ORDERS_MSG } from "./messages";

/** Tối đa 12 chữ số phần nguyên (999.999.999.999 ₫) — cột `amount` của BE là 14 chữ số, 2 lẻ (B13). */
export const AMOUNT_MAX_DIGITS = 12;
/** Mã giao dịch ngân hàng tối đa 100 ký tự (BR-TT-08). */
export const TXN_MAX_LENGTH = 100;

export type AmountProblem = "missing" | "negative" | "zero" | "tooBig" | "notNumber" | "fraction";
export type AmountCheck = { value: string; problem: null } | { value: null; problem: AmountProblem };

/** Chỉ giữ chữ số (tiền VND không số lẻ). "540.000" / "540,000 ₫" → "540000". */
export function digits(v: string): string {
  return v.replace(/\D+/g, "").replace(/^0+(?=\d)/, "");
}

/**
 * Đọc ô số tiền VNĐ: tiền là số nguyên nên giá trị thật CHỈ gồm chữ số; "." / "," / khoảng trắng / "đ" chỉ là trang trí
 * ("540.000", "540,000 ₫" → 540000). Chuỗi có phần lẻ ở cuối (1–2 chữ số sau dấu): toàn số 0 thì bỏ ("150.000,00" → 150000),
 * khác 0 ("150.000,50", "0.5") thì báo `fraction`, không đoán. Ô nhập (`Field type="money"`) luôn nhóm lại từ chuỗi chữ số
 * nên không bao giờ đưa vào đây dạng "150.00" do xoá lùi (QA B4).
 */
export function parseAmount(raw: string): AmountCheck {
  const s = raw.replace(/vnd|₫|đ/gi, "").replace(/\s+/g, "");
  if (/[-−]/.test(s)) return { value: null, problem: "negative" };
  if (/[^\d.,]/.test(s)) return { value: null, problem: "notNumber" };
  if (!/\d/.test(s)) return { value: null, problem: "missing" };
  // Phần lẻ kiểu sao kê: toàn số 0 thì bỏ ("150.000,00" = 150.000); khác 0 thì không đoán, báo lỗi.
  const frac = splitFraction(s);
  if (frac.kind === "nonzero") return { value: null, problem: "fraction" };
  const d = digits(frac.text);
  if (/^0*$/.test(d)) return { value: null, problem: "zero" };
  if (d.length > AMOUNT_MAX_DIGITS) return { value: null, problem: "tooBig" };
  return { value: d, problem: null };
}

/** Giá trị ban đầu cho ô tiền: "1500000" → "1.500.000". Mọi lần sửa sau đó do `Field type="money"` xử lý (`shared/lib/moneyInput.ts`). */
export function formatAmountInput(raw: string): string {
  return formatMoneyInput(raw);
}

/** Câu báo tại ô cho từng lỗi đọc số tiền (nói cách sửa). */
export const AMOUNT_MSG: Record<AmountProblem, string> = {
  missing: ORDERS_MSG.amountMissing,
  negative: ORDERS_MSG.amountNegative,
  zero: ORDERS_MSG.amountZero,
  tooBig: ORDERS_MSG.amountTooBig,
  notNumber: ORDERS_MSG.amountNotNumber,
  fraction: ORDERS_MSG.amountFraction,
};
