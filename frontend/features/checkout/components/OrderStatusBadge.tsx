import { cx } from "@/components/ui/cx";
import type { OrderState } from "@/lib/types";
import s from "./OrderStatusBadge.module.css";

const TONE: Record<OrderState, "warn" | "accent" | "good" | "neutral"> = {
  awaiting_payment: "warn",
  hold_expired: "warn",
  preparing: "accent",
  delivering: "accent",
  completed: "good",
  delivery_failed: "warn",
  expired: "neutral",
  cancelled: "neutral",
};

/**
 * Nhãn trạng thái đơn (COMPONENTS #27, 02b §6.4). Chữ lấy từ `status_label` của máy chủ (khách không bao giờ thấy mã thô);
 * màu theo `state`: chờ/giao lỗi hổ phách, chuẩn bị/giao xanh nhấn, đã giao xanh lá, huỷ/hết giờ xám (không đỏ).
 */
export default function OrderStatusBadge({ state, label }: { state: OrderState; label: string }) {
  return <span className={cx(s.badge, s[TONE[state]])}>{label}</span>;
}
