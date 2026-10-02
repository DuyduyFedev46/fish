// Trợ giúp cho phiếu hoàn gắn hoá đơn (S15). BE là lớp chặn thật cho BR-HT-04 (câu lỗi nguyên văn khi vượt số còn được
// hoàn); số dưới đây chỉ để ĐIỀN SẴN ô số tiền và nhắc tại chỗ — chi tiết đơn (contract S10) chưa có field
// `refundable_amount` riêng nên FE tính từ `total_amount` và `refunds[]` đã có sẵn.

import type { OrderDetail } from "./types";

/** Số tiền còn được hoàn của một đơn: tổng đơn trừ các phiếu hoàn CHƯA Thất bại (PENDING/REFUNDED tính đủ). */
export function refundableOfOrder(order: OrderDetail): string {
  const total = Number(order.total_amount ?? 0);
  const used = order.refunds.filter((r) => r.status !== "FAILED").reduce((sum, r) => sum + Number(r.amount), 0);
  return String(Math.max(0, total - used));
}

/**
 * Mã chống tạo trùng — BE đòi UUID ("request_id phải là UUID."). crypto.randomUUID chỉ có ở ngữ cảnh an toàn (https,
 * localhost); không có thì dựng UUID v4 từ crypto.getRandomValues (hoặc Math.random ở máy rất cũ).
 */
export function newRequestId(): string {
  const c = typeof crypto !== "undefined" ? (crypto as Crypto & { randomUUID?: () => string }) : undefined;
  if (c?.randomUUID) return c.randomUUID();
  const b = new Uint8Array(16);
  if (c?.getRandomValues) c.getRandomValues(b);
  else for (let i = 0; i < 16; i++) b[i] = Math.floor(Math.random() * 256);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

/** Số tiền vượt mức còn hoàn được? (F2c: báo lỗi tại ô + khoá nút chính). Hai số đều là chuỗi chữ số. */
export function overRefundMax(amount: string, max: string): boolean {
  return !!amount && !!max && Number(amount) > Number(max);
}
