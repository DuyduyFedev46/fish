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
