// Nhãn + tông màu cho các mã trạng thái lồng trong chi tiết đơn. BE L7 bổ sung đã trả `*_label` (match_status_label,
// source_label, delivery.status_label, refunds[].status_label) → FE LUÔN ưu tiên nhãn BE; bảng dưới (chép nguyên TextChoices
// của BE) chỉ là DỰ PHÒNG khi thiếu key, và cho danh sách (delivery_status chỉ có mã). Chỉ để HIỂN THỊ, không suy luật.

import type { StatusLook } from "@/shared/lib/status";

export const DELIVERY_LABEL: Record<string, string> = {
  PREPARING: "Soạn hàng",
  READY: "Chờ lấy hàng",
  DELIVERING: "Đang giao",
  COMPLETED: "Hoàn tất",
  FAILED: "Giao thất bại",
};
export const DELIVERY_STATUS: Record<string, StatusLook> = {
  PREPARING: { tone: "info", icon: "inventory" },
  READY: { tone: "info", icon: "package_2" },
  DELIVERING: { tone: "info", icon: "local_shipping" },
  COMPLETED: { tone: "good", icon: "flag" },
  FAILED: { tone: "crit", icon: "report" },
};

export const PAYMENT_LABEL: Record<string, string> = {
  MATCHED: "Khớp — đã xác nhận",
  UNDERPAID: "Thiếu tiền — chờ Chủ",
  ORPHAN: "Đến sau khi đơn đã huỷ — chờ Chủ",
  UNMATCHED: "Không khớp đơn — chờ Chủ",
};
export const PAYMENT_STATUS: Record<string, StatusLook> = {
  MATCHED: { tone: "good", icon: "check_circle" },
  UNDERPAID: { tone: "warn", icon: "error" },
  ORPHAN: { tone: "warn", icon: "error" },
  UNMATCHED: { tone: "warn", icon: "error" },
};
export const PAYMENT_SOURCE_LABEL: Record<string, string> = {
  WEBHOOK: "Webhook SePay",
  MANUAL: "Xác nhận tay",
};

export const REFUND_LABEL: Record<string, string> = {
  PENDING: "Chờ hoàn",
  REFUNDED: "Đã hoàn",
  FAILED: "Thất bại",
};
export const REFUND_STATUS: Record<string, StatusLook> = {
  PENDING: { tone: "warn", icon: "schedule" },
  REFUNDED: { tone: "good", icon: "check_circle" },
  FAILED: { tone: "crit", icon: "error" },
};

/** Nhãn trạng thái đơn khi chi tiết không có `status_label` (chép TextChoices SalesOrder.Status). */
export const ORDER_LABEL: Record<string, string> = {
  BOOKED: "Giữ chỗ",
  PAID: "Đã thanh toán",
  PROCESSING: "Đang xử lý",
  COMPLETED: "Hoàn tất",
  CANCELLED: "Đã huỷ",
  AUTO_CANCELLED: "Tự huỷ (quá TTL)",
};

/** Lựa chọn lọc trạng thái — giá trị gửi thẳng lên `?status=` (nhiều mã nối dấu phẩy). */
export const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Mọi trạng thái" },
  { value: "BOOKED,PAID,PROCESSING", label: "Chưa xong" },
  { value: "BOOKED", label: "Giữ chỗ" },
  { value: "PAID", label: "Đã thanh toán" },
  { value: "PROCESSING", label: "Đang xử lý" },
  { value: "COMPLETED", label: "Hoàn tất" },
  { value: "CANCELLED,AUTO_CANCELLED", label: "Đã huỷ / tự huỷ" },
];

export type DatePreset = "all" | "today" | "7d" | "30d" | "custom";
export const DATE_FILTERS: { value: DatePreset; label: string }[] = [
  { value: "all", label: "Mọi ngày" },
  { value: "today", label: "Hôm nay" },
  { value: "7d", label: "7 ngày qua" },
  { value: "30d", label: "30 ngày qua" },
  { value: "custom", label: "Chọn khoảng ngày" },
];

export function labelOf(map: Record<string, string>, code: string, fromBe?: string): string {
  return fromBe || map[code] || code;
}
