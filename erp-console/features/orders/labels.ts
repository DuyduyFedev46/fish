// Lựa chọn lọc của các danh sách Đơn & tiền. Nhãn trạng thái KHÔNG viết ở đây: dùng ENUMS (shared/lib/enums.ts).

export const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Mọi trạng thái" },
  { value: "BOOKED,PAID,PROCESSING", label: "Chưa xong" },
  { value: "BOOKED", label: "Giữ chỗ" },
  { value: "PAID", label: "Đã thanh toán" },
  { value: "PROCESSING", label: "Đang xử lý" },
  { value: "COMPLETED", label: "Hoàn tất" },
  { value: "CANCELLED,AUTO_CANCELLED", label: "Đã huỷ" },
];

export type DatePreset = "all" | "today" | "7d" | "30d" | "custom";
export const DATE_FILTERS: { value: DatePreset; label: string }[] = [
  { value: "all", label: "Mọi ngày" },
  { value: "today", label: "Hôm nay" },
  { value: "7d", label: "7 ngày qua" },
  { value: "30d", label: "30 ngày qua" },
  { value: "custom", label: "Chọn khoảng ngày" },
];

/** Lọc loại khoản tiền ở hàng chờ — giá trị gửi thẳng lên `?match_status=`. */
export const QUEUE_TYPE_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Mọi loại khoản tiền" },
  { value: "UNDERPAID", label: "Thiếu tiền" },
  { value: "UNMATCHED", label: "Không khớp đơn" },
  { value: "ORPHAN", label: "Về sau khi đơn tự huỷ" },
  { value: "OVERPAID", label: "Chuyển thừa" },
];

/** Lý do huỷ đơn (F2b). OTHER bắt buộc ghi chú (S14-AC6). */
export const CANCEL_REASONS: { value: string; label: string }[] = [
  { value: "CUSTOMER_CHANGED_MIND", label: "Khách đổi ý" },
  { value: "DAMAGED_WHEN_PACKING", label: "Hư khi đóng hàng" },
  { value: "GIVE_UP_AFTER_FAILED", label: "Bỏ sau khi giao thất bại" },
  { value: "OTHER", label: "Khác" },
];
