// Đọc ô số tiền VND dùng chung trong module Đơn & tiền: S11 (xác nhận đã nhận tiền) và S13 (tạo phiếu hoàn từ hàng chờ).
// Tách ra từ ConfirmPaymentForm (B13, QA L7) để hai form chặn trước tại ô cùng một cách. BE vẫn là lớp chặn chính.

import { ORDERS_MSG } from "./messages";

/** Tối đa 12 chữ số phần nguyên (999.999.999.999 ₫) — cột `amount` của BE là 14 chữ số, 2 lẻ (B13). */
export const AMOUNT_MAX_DIGITS = 12;
/** Mã giao dịch ngân hàng tối đa 100 ký tự (BR-TT-08). */
export const TXN_MAX_LENGTH = 100;

export type AmountProblem = "missing" | "negative" | "zero" | "tooBig" | "notNumber";
export type AmountCheck = { value: string; problem: null } | { value: null; problem: AmountProblem };

/** Chỉ giữ chữ số (tiền VND không số lẻ). "540.000" / "540,000 ₫" → "540000". */
export function digits(v: string): string {
  return v.replace(/\D+/g, "").replace(/^0+(?=\d)/, "");
}

/**
 * Đọc ô số tiền theo cách người Việt gõ: "." / "," / khoảng trắng là dấu nghìn ("540.000", "540,000 ₫").
 * Dấu cuối theo sau 1–2 chữ số ("540000,5") hoặc "0," / "0." ở đầu ("0,004") là phần lẻ → bỏ, chỉ giữ đồng.
 */
export function parseAmount(raw: string): AmountCheck {
  const s = raw.replace(/vnd|₫|đ/gi, "").replace(/\s+/g, "");
  if (/[-−]/.test(s)) return { value: null, problem: "negative" };
  if (/[^\d.,]/.test(s)) return { value: null, problem: "notNumber" };
  if (!/\d/.test(s)) return { value: null, problem: "missing" };
  let int = s;
  const frac = s.match(/^(.*?)[.,](\d{1,2})$/);
  if (frac) int = frac[1];
  else if (/^0*[.,]\d/.test(s) || /^0+[.,]/.test(s)) int = "0";
  const d = int.replace(/\D+/g, "").replace(/^0+/, "");
  if (!d) return { value: null, problem: "zero" };
  if (d.length > AMOUNT_MAX_DIGITS) return { value: null, problem: "tooBig" };
  return { value: d, problem: null };
}

/** Câu báo tại ô cho từng lỗi đọc số tiền (nói cách sửa). */
export const AMOUNT_MSG: Record<AmountProblem, string> = {
  missing: ORDERS_MSG.amountMissing,
  negative: ORDERS_MSG.amountNegative,
  zero: ORDERS_MSG.amountZero,
  tooBig: ORDERS_MSG.amountTooBig,
  notNumber: ORDERS_MSG.amountNotNumber,
};
