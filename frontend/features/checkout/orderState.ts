/**
 * Ánh xạ trạng thái đơn của máy chủ (`state`, bảng E6, 02b §3.4.2) và tham số `result` trên URL sang MÀN hiển thị
 * (02b §6.3, 02a mục 5). Máy chủ luôn thắng `result` (UI-RULES §2c). File thuần TypeScript, chỉ import kiểu,
 * để `scripts/test-order-state.mjs` chạy được không cần build.
 */
import type { OrderState } from "@/lib/types";

/** Kết quả cổng thanh toán đưa khách về qua URL (`?result=`). */
export type PaymentResult = "success" | "cancel" | "error" | null;

export function parsePaymentResult(raw: string | null | undefined): PaymentResult {
  return raw === "success" || raw === "cancel" || raw === "error" ? raw : null;
}

export type OrderScreenKey =
  | "payment" // D1: còn hạn, chưa trả
  | "payment_retry" // D2: về từ cổng với cancel/error
  | "pending" // D3: chờ tiền, dưới ngưỡng
  | "pending_slow" // D3 biến thể: chờ quá ngưỡng, "Cá Về sẽ kiểm tra giao dịch và gọi cho bạn"
  | "expired_dialog" // D4 dạng hộp thoại: đồng hồ về 0, job chưa chạy
  | "expired_page" // D4 dạng trang: đơn đã tự huỷ
  | "cancelled" // E2
  | "cancelled_late" // E2 biến thể: hết giờ giữ hàng, tiền về sau
  | "order" // E1
  | "order_partial_cancel" // E1 + khối E5
  | "delivery_failed" // E4
  | "delivered"; // E3

export type ScreenOrder = {
  state: OrderState;
  late_payment?: boolean;
  cancel_notice?: { scope: string } | null;
  /** Ngưỡng D3 biến thể (phút), từ máy chủ. */
  payment_pending_minutes?: number;
};

export type ScreenClock = {
  /** Giờ hiện tại (epoch ms). */
  now: number;
  /** Lúc trang mở với `result=success` (state cục bộ); null nếu chưa bắt đầu chờ. */
  pendingSince: number | null;
};

export type ScreenDecision = {
  screen: OrderScreenKey;
  /** success: banner "Thanh toán thành công"; already_paid: mở lại link cũ của đơn đã trả. */
  banner: "paid_success" | "already_paid" | null;
  /** Nhịp hỏi lại máy chủ (ms); null = không hỏi. D3 5 giây tới ngưỡng, sau đó 30 giây. D4 hộp thoại 5 giây. */
  pollMs: number | null;
};

const POLL_FAST_MS = 5000;
const POLL_SLOW_MS = 30000;
const DEFAULT_PENDING_MINUTES = 5;

/**
 * Bảng §6.3. `result` chỉ có nghĩa khi đơn còn chờ tiền (`awaiting_payment`) hoặc vừa trả xong
 * (banner). Mọi `state` khác do máy chủ quyết định.
 */
export function screenFor(order: ScreenOrder, result: PaymentResult, clock: ScreenClock): ScreenDecision {
  switch (order.state) {
    case "awaiting_payment": {
      if (result === "cancel" || result === "error") return { screen: "payment_retry", banner: null, pollMs: null };
      if (result === "success") {
        const thresholdMs = (order.payment_pending_minutes ?? DEFAULT_PENDING_MINUTES) * 60 * 1000;
        const waited = clock.pendingSince == null ? 0 : Math.max(0, clock.now - clock.pendingSince);
        return waited >= thresholdMs
          ? { screen: "pending_slow", banner: null, pollMs: POLL_SLOW_MS }
          : { screen: "pending", banner: null, pollMs: POLL_FAST_MS };
      }
      return { screen: "payment", banner: null, pollMs: null };
    }
    case "hold_expired":
      return { screen: "expired_dialog", banner: null, pollMs: POLL_FAST_MS };
    case "expired":
      return { screen: "expired_page", banner: null, pollMs: null };
    case "cancelled":
      return { screen: order.late_payment ? "cancelled_late" : "cancelled", banner: null, pollMs: null };
    case "preparing":
    case "delivering": {
      const banner = result === "success" ? "paid_success" : result === "cancel" || result === "error" ? "already_paid" : null;
      const screen = order.cancel_notice?.scope === "partial" ? "order_partial_cancel" : "order";
      return { screen, banner, pollMs: null };
    }
    case "delivery_failed":
      return { screen: "delivery_failed", banner: null, pollMs: null };
    case "completed":
      return { screen: "delivered", banner: null, pollMs: null };
  }
}

/** Màn nào là bước thanh toán (header H4, có hộp thoại D6 khi rời trang). */
export function isPaymentScreen(screen: OrderScreenKey): boolean {
  return screen === "payment" || screen === "payment_retry" || screen === "expired_dialog";
}

/** Chênh lệch giữ giờ máy khách và máy chủ lúc nhận kết quả: `offset = server_now − giờ máy`. */
export function clockOffsetMs(serverNow: string | null | undefined, receivedAtMs: number): number {
  const server = serverNow ? Date.parse(serverNow) : NaN;
  return Number.isFinite(server) ? server - receivedAtMs : 0;
}

/** Còn lại bao lâu tới hạn giữ hàng (ms, không âm), theo giờ máy chủ đã bù lệch. Hạn không hợp lệ -> null. */
export function remainingMs(expiresAt: string | null | undefined, nowMs: number, offsetMs: number): number | null {
  const end = expiresAt ? Date.parse(expiresAt) : NaN;
  if (!Number.isFinite(end)) return null;
  return Math.max(0, end - (nowMs + offsetMs));
}

/**
 * `awaiting_payment` mà đồng hồ đã về 0 (job chưa chạy) thì coi như `hold_expired`, để mở hộp thoại D4 ngay
 * rồi hỏi lại máy chủ cho tới khi `expired`.
 */
export function effectiveState(state: OrderState, remaining: number | null): OrderState {
  return state === "awaiting_payment" && remaining !== null && remaining <= 0 ? "hold_expired" : state;
}

/** mm:ss từ số ms còn lại (làm tròn lên giây). */
export function formatRemaining(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(total / 60)
    .toString()
    .padStart(2, "0");
  const s = (total % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

/** Số phút/giây đọc cho trình đọc màn hình: "Còn 18 phút 24 giây". */
export function remainingLabel(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  if (m === 0) return `Còn ${s} giây`;
  return s === 0 ? `Còn ${m} phút` : `Còn ${m} phút ${s} giây`;
}

/** "Đã chờ 0:04". */
export function formatWaited(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(total / 60)}:${(total % 60).toString().padStart(2, "0")}`;
}

export type TimelineStep = {
  key: "placed" | "paid" | "preparing" | "shipping" | "delivered";
  label: string;
  state: "done" | "current" | "upcoming" | "failed";
  /** Dòng phụ cố định ("Chuyển khoản ngân hàng", "Cá Về soạn hàng", "chưa giao được"). */
  detail?: string;
  /** Mốc giờ ISO UTC; chỉ 3 mốc có giờ (BR-BH-26): đặt, trả, giao. Bước giữa không có giờ. */
  time?: string | null;
};

/**
 * Dòng thời gian 5 bước của trang đơn (02b §6.4). Đơn chưa trả, đã huỷ hay hết giờ không có dòng thời gian (trả mảng rỗng).
 */
export function buildOrderTimeline(order: {
  state: OrderState;
  placed_at: string;
  paid_at: string | null;
  delivered_at: string | null;
}): TimelineStep[] {
  const rank: Partial<Record<OrderState, number>> = {
    preparing: 2,
    delivering: 3,
    delivery_failed: 3,
    completed: 5,
  };
  const at = rank[order.state];
  if (at === undefined) return [];
  const stateOf = (index: number): TimelineStep["state"] => {
    if (index < at) return "done";
    if (index === at) return order.state === "delivery_failed" ? "failed" : "current";
    return "upcoming";
  };
  return [
    { key: "placed", label: "Đã đặt", state: stateOf(0), time: order.placed_at },
    { key: "paid", label: "Đã thanh toán", state: stateOf(1), detail: "Chuyển khoản ngân hàng", time: order.paid_at },
    { key: "preparing", label: "Đang chuẩn bị hàng", state: stateOf(2), detail: "Cá Về soạn hàng" },
    {
      key: "shipping",
      label: "Đang giao",
      state: stateOf(3),
      detail: order.state === "delivery_failed" ? "chưa giao được" : undefined,
    },
    { key: "delivered", label: "Đã giao", state: stateOf(4), time: order.delivered_at },
  ];
}
