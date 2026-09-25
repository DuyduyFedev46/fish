// Màu + icon cho trạng thái đơn / lô (kế thừa bản HTML cũ). Nhãn chữ luôn lấy từ `status_label` BE trả.

export type Tone = "good" | "warn" | "crit" | "info" | "mute";
export type StatusLook = { tone: Tone; icon: string };

export const ORDER_STATUS: Record<string, StatusLook> = {
  BOOKED: { tone: "warn", icon: "timer" },
  PAID: { tone: "info", icon: "check_circle" },
  PROCESSING: { tone: "info", icon: "local_shipping" },
  COMPLETED: { tone: "good", icon: "flag" },
  CANCELLED: { tone: "mute", icon: "cancel" },
  AUTO_CANCELLED: { tone: "mute", icon: "timer_off" },
};

export const BATCH_STATUS: Record<string, StatusLook> = {
  SELLING: { tone: "good", icon: "check_circle" },
  NEAR_EXPIRY: { tone: "warn", icon: "event_busy" },
  DRAFT: { tone: "mute", icon: "edit" },
  SOLD_OUT: { tone: "mute", icon: "inventory_2" },
  EXPIRED: { tone: "crit", icon: "block" },
  CANCELLED: { tone: "mute", icon: "cancel" },
  CLOSED: { tone: "mute", icon: "lock" },
};

export const UNKNOWN_STATUS: StatusLook = { tone: "mute", icon: "help" };
