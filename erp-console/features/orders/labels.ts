// Lựa chọn lọc của các danh sách Đơn & tiền. Nhãn trạng thái KHÔNG viết ở đây: dùng ENUMS (shared/lib/enums.ts).

import { ENUMS } from "@/shared/lib/enums";

export const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Mọi trạng thái" },
  { value: "BOOKED,PAID,PROCESSING", label: "Chưa xong" },
  { value: "BOOKED", label: ENUMS.salesOrderStatus.BOOKED.label },
  { value: "PROCESSING", label: ENUMS.salesOrderStatus.PROCESSING.label },
  { value: "COMPLETED", label: ENUMS.salesOrderStatus.COMPLETED.label },
  // Nhóm gộp CANCELLED và AUTO_CANCELLED (Q-2): nhãn nhóm là "Đã huỷ", chip từng đơn vẫn tách theo ENUMS.
  { value: "CANCELLED,AUTO_CANCELLED", label: ENUMS.salesOrderStatus.CANCELLED.label },
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
  ...(["UNDERPAID", "UNMATCHED", "ORPHAN", "OVERPAID"] as const).map((value) => ({ value: value as string, label: ENUMS.paymentMatchStatus[value].label })),
];

/** Lý do huỷ đơn (F2b). OTHER bắt buộc ghi chú (S14-AC6). */
/** BR-GH-19: ghi chú huỷ tối đa 200 ký tự (BE chặn thêm chuỗi số dài như SĐT/số tài khoản). */
export const CANCEL_NOTE_MAX = 200;

/** Ô chọn lý do huỷ tay: 4 mã người dùng được chọn, nhãn lấy từ ENUMS (UNREACHABLE và UNREACHABLE_AUTO do luồng gọi xác nhận / hệ thống). */
export const CANCEL_REASONS: { value: string; label: string }[] = (["CUSTOMER_CHANGED_MIND", "DAMAGED_WHEN_PACKING", "GIVE_UP_AFTER_FAILED", "OTHER"] as const).map((value) => ({
  value: value as string,
  label: ENUMS.cancelReason[value].label,
}));
