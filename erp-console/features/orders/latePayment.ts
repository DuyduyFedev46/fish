// Hàm thuần cho "Ghi tiền về muộn" (#15, BR-TT-18): chuẩn hoá mã giao dịch, kiểm giờ nhận, dựng thân gửi, đọc thân 409.
// BE là lớp chặn chính (cùng luật); FE chỉ báo sớm tại ô. Không có ô ghi chú (thu tối thiểu, bất biến 9): thân gửi chỉ gồm 5 khoá.

import { timeHM, todayInVietnam, vnInputToIso } from "@/shared/lib/format";
import { ApiError } from "@/shared/lib/http";
import { TXN_MAX_LENGTH } from "./amount";
import type { RecordLatePaymentInput, SimilarPayment } from "./types";

/** Mã lỗi 409: có khoản giống đã ghi — phải tick xác nhận rồi gửi lại. */
export const POSSIBLE_DUPLICATE_CODE = "LATE_PAYMENT_POSSIBLE_DUPLICATE";
/** Mã lỗi 400: đơn còn Giữ chỗ — dẫn sang đơn để dùng "Xác nhận đã nhận tiền". */
export const ORDER_BOOKED_CODE = "LATE_PAYMENT_ORDER_BOOKED";
/** Mã lỗi 409 của POST /refunds/create/: khoản có nhãn nghi trùng mà chưa tick. */
export const DUPLICATE_WARNING_CODE = "PAYMENT_DUPLICATE_WARNING";
/** Giờ nhận được phép lệch tối đa so với giờ máy (khớp BE: không muộn hơn hiện tại quá 5 phút). */
const FUTURE_SLACK_MS = 5 * 60_000;

/** Mã giao dịch như BE chuẩn hoá: bỏ mọi khoảng trắng, viết hoa. " ft 2610 0300001 " → "FT26100300001". */
export function normalizeTxnId(raw: string): string {
  return raw.replace(/\s+/g, "").toUpperCase();
}

export type TxnProblem = "missing" | "tooLong" | "badChars";

/** Mã GD hợp lệ: không rỗng, ≤ 100 ký tự, chỉ `A-Z 0-9 . _ - /` (mã GD hiện trên dòng thời gian nên không cho gõ tên hay SĐT). */
export function checkTxnId(raw: string): TxnProblem | null {
  const t = normalizeTxnId(raw);
  if (!t) return "missing";
  if (t.length > TXN_MAX_LENGTH) return "tooLong";
  if (!/^[A-Z0-9._/-]+$/.test(t)) return "badChars";
  return null;
}

export type ReceivedAtProblem = "missing" | "future";

/** Giờ nhận (ô datetime-local, giờ Việt Nam) phải có và không ở tương lai. */
export function checkReceivedAt(local: string, now: Date = new Date()): ReceivedAtProblem | null {
  const iso = vnInputToIso(local);
  if (!iso) return "missing";
  return new Date(iso).getTime() > now.getTime() + FUTURE_SLACK_MS ? "future" : null;
}

/** Giá trị ban đầu của ô giờ nhận: giờ Việt Nam hiện tại, dạng "2026-10-07T09:30". */
export function nowForInput(now: Date = new Date()): string {
  return `${todayInVietnam(now)}T${timeHM(now)}`;
}

/** Dựng thân gửi. Mã đơn rỗng thì bỏ khoá (BE hiểu là khoản không gắn đơn). `ack` chỉ gửi sau khi người dùng tick. */
export function buildLateBody(v: { txn: string; amount: string; receivedAt: string; orderCode: string; ack: boolean }): RecordLatePaymentInput {
  const body: RecordLatePaymentInput = {
    bank_txn_id: normalizeTxnId(v.txn),
    amount: v.amount,
    received_at: vnInputToIso(v.receivedAt),
  };
  const code = v.orderCode.trim();
  if (code) body.order_code = code;
  if (v.ack) body.acknowledge_possible_duplicate = true;
  return body;
}

/** Đọc khoản giống từ thân 409 (`similar_payment_id`, `similar_bank_txn_id`, `similar_received_at`). Thiếu/sai kiểu → null. */
export function similarOf(err: unknown): SimilarPayment | null {
  if (!(err instanceof ApiError) || err.status !== 409 || err.code !== POSSIBLE_DUPLICATE_CODE) return null;
  const d = err.details && typeof err.details === "object" ? (err.details as Record<string, unknown>) : {};
  const id = Number(d.similar_payment_id);
  const txn = d.similar_bank_txn_id;
  const at = d.similar_received_at;
  return Number.isInteger(id) && id > 0 && typeof txn === "string" ? { id, bank_txn_id: txn, received_at: typeof at === "string" ? at : "" } : null;
}

/** `order_id` trong thân 400 LATE_PAYMENT_ORDER_BOOKED (để dẫn sang đơn). */
export function bookedOrderIdOf(err: unknown): number | null {
  if (!(err instanceof ApiError) || err.code !== ORDER_BOOKED_CODE) return null;
  const d = err.details && typeof err.details === "object" ? (err.details as Record<string, unknown>) : {};
  const id = Number(d.order_id);
  return Number.isInteger(id) && id > 0 ? id : null;
}

/** `existing_payment_id` trong thân 400 BR-TT-03 (trùng mã GD) — để mở giao dịch đã có. */
export function existingPaymentIdOf(err: unknown): number | null {
  if (!(err instanceof ApiError) || err.status !== 400) return null;
  const d = err.details && typeof err.details === "object" ? (err.details as Record<string, unknown>) : {};
  const id = Number(d.existing_payment_id);
  return Number.isInteger(id) && id > 0 ? id : null;
}

/** Khoản có nhãn nghi trùng (BR-TT-15 / BR-TT-18) → lập phiếu hoàn tiền phải tick xác nhận. */
export function hasDuplicateWarning(p: { duplicate_warning?: string | null }): boolean {
  return typeof p.duplicate_warning === "string" && p.duplicate_warning.trim() !== "";
}
