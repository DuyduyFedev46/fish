"use client";

// Tìm id đơn của một phiếu hàng hoàn để làm liên kết "Đơn" → /orders/detail/?id=<id> (QA Lô 9 B3).
// Phiếu hàng hoàn chỉ có mã đơn (`order_code`), không có id đơn (lệch contract, ghi ở 03-dev-notes). Phiếu giao thì có `order: {id, code}`,
// nên đọc phiếu giao qua hàm công khai của module Giao hàng. Chỉ gọi khi người xem được màn Đơn (`enabled`); lỗi hay thiếu thì trả null
// và màn giữ mã đơn dạng chữ thường (không chặn trang, không báo lỗi). Không log, không ghi storage.
import { useEffect, useState } from "react";
import { fetchDeliveryNoteDetail } from "@/features/deliveries/api";

export function useReturnOrderId(deliveryNoteId: number, orderCode: string | null, enabled: boolean): number | null {
  const [orderId, setOrderId] = useState<number | null>(null);

  useEffect(() => {
    setOrderId(null);
    if (!enabled || !orderCode) return;
    const ctrl = new AbortController();
    fetchDeliveryNoteDetail(deliveryNoteId, ctrl.signal)
      .then((note) => {
        // Chỉ nhận khi đúng đơn của phiếu (cùng mã) để không trỏ nhầm.
        if (!ctrl.signal.aborted && note.order && note.order.code === orderCode) setOrderId(note.order.id);
      })
      .catch(() => {
        /* không có liên kết thì giữ chữ thường */
      });
    return () => ctrl.abort();
  }, [deliveryNoteId, orderCode, enabled]);

  return orderId;
}
