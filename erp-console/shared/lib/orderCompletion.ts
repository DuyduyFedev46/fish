// BR-BH-18 (W37 S1): đơn xong khi mọi phiếu giao còn hiệu lực đã COMPLETED. Hàm thuần, cùng luật với BE
// (`apps/sales/orders/completion.py:is_delivery_finished`). Phiếu CANCELLED không tính; không còn phiếu nào thì chưa xong.

export function isDeliveryFinished(noteStatuses: readonly string[]): boolean {
  const live = noteStatuses.filter((s) => s !== "CANCELLED");
  return live.length > 0 && live.every((s) => s === "COMPLETED");
}
