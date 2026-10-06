// Mô hình thuần của ba trang chi tiết (đơn · khoản tiền · phiếu hoàn): nút chính, mục "…", thanh trạng thái, đếm lùi giữ
// chỗ. Không React, không gọi API → vitest kiểm được. Luật nghiệp vụ nằm ở BE: nút CHỈ theo `available_actions`; hàm
// này chỉ quyết định nút nào là nút chính và mục nào hiện mờ kèm lý do (bảng 1 và 2 của ERP-D2c).

import { ENUMS, enumOf } from "@/shared/lib/enums";
import type { PathStep } from "@/shared/ui/detail/StatusPath";
import type { TimelineEntry } from "@/shared/ui/detail/Timeline";
import { ORDERS_MSG as M } from "./messages";
import type {
  ConfirmPaymentResult,
  OrderAction,
  OrderDetail,
  OrderTimelineEntry,
  PaymentAction,
  PaymentQueueItem,
  RefundQueueAction,
  RefundQueueItem,
} from "./types";

export type ActionItem = { key: string; label: string; danger?: boolean; blockedReason?: string };
export type ActionPlan = { primary: ActionItem | null; menu: ActionItem[] };

// ---------------------------------------------------------------------------------------------------------------------
// Đơn

export const ORDER_STEPS: PathStep[] = [
  { key: "BOOKED", label: "Giữ chỗ" },
  { key: "CONFIRMING", label: "Chờ gọi xác nhận" },
  { key: "PREPARING", label: "Soạn hàng" },
  { key: "DELIVERING", label: "Đang giao" },
  { key: "COMPLETED", label: "Hoàn tất" },
];

export const BLOCKED_CANCEL_BOOKED = "Đơn chưa thanh toán sẽ tự huỷ khi hết giờ giữ chỗ.";
export const BLOCKED_CANCEL_DELIVERING = "Đơn đang giao: báo giao thất bại trước rồi mới huỷ được.";

type PathInput = { status: string; deliveryStatus?: string | null; hasInvoice?: boolean };

/**
 * Bước hiện tại của thanh trạng thái (đơn huỷ: bước cuối cùng đã qua trước khi huỷ). W37 S7: bước Hoàn tất CHỈ sáng khi
 * đơn `COMPLETED`; phiếu giao xong mà đơn còn PROCESSING (đợi phiếu khác) vẫn đứng ở Đang giao.
 */
export function orderStepKey(o: PathInput): string {
  if (o.status === "BOOKED" || o.status === "AUTO_CANCELLED") return "BOOKED";
  if (o.status === "COMPLETED") return "COMPLETED";
  if (o.status === "PAID") return "CONFIRMING";
  if (o.status === "PROCESSING" || o.status === "CANCELLED") {
    const d = o.deliveryStatus;
    if (d === "DELIVERING" || d === "FAILED" || d === "COMPLETED") return "DELIVERING";
    if (d === "PREPARING" || d === "READY") return "PREPARING";
    if (d === "CONFIRMING") return "CONFIRMING";
    return o.hasInvoice === false ? "BOOKED" : "CONFIRMING";
  }
  return "BOOKED";
}

export function isCancelledStatus(status: string): boolean {
  return status === "CANCELLED" || status === "AUTO_CANCELLED";
}

export function orderPath(o: PathInput): { current: string; badEnd: { label: string; after: string } | null } {
  const key = orderStepKey(o);
  return { current: key, badEnd: isCancelledStatus(o.status) ? { label: "Đã huỷ", after: key } : null };
}

type PlanInput = {
  status: string;
  deliveryStatus?: string | null;
  actions: readonly OrderAction[];
  /** Có quyền huỷ đơn đã thanh toán (để hiện mục "Huỷ đơn" mờ kèm lý do khi đang bị chặn). */
  canCancel: boolean;
  canViewAudit: boolean;
  /** Có việc đang chờ người khác (bước guidance mình chưa làm được) → hiện mục "Nhờ người xử lý" (Lô bổ sung A #19). */
  canEscalate?: boolean;
};

/** Nút chính + mục "…" của một đơn (ED-09-AC3, AC4). Quyền đã nằm sẵn trong `actions` (BE tính cả luật lẫn quyền). */
export function orderActionPlan(i: PlanInput): ActionPlan {
  const has = (a: string) => i.actions.includes(a);
  let primary: ActionItem | null = null;
  const menu: ActionItem[] = [];

  // #15: đơn Tự huỷ là đơn đã chết — mọi thao tác ghi bị ẩn, dù `actions` (bản cũ của BE / đơn vừa hết giờ giữ chỗ) còn mục nào.
  if (i.status === "AUTO_CANCELLED") {
    menu.push({ key: "copy_code", label: "Sao chép mã đơn" });
    if (i.canViewAudit) menu.push({ key: "audit", label: "Xem nhật ký của đơn" });
    return { primary, menu };
  }

  if (has("confirm_payment")) primary = { key: "confirm_payment", label: "Xác nhận đã nhận tiền" };
  else if (has("cancel")) primary = { key: "cancel", label: "Huỷ đơn", danger: true };
  else if (has("create_refund") && isCancelledStatus(i.status)) primary = { key: "create_refund", label: "Lập phiếu hoàn" };
  else if (has("create_refund") && i.status === "COMPLETED") primary = { key: "create_refund", label: "Lập phiếu hoàn" };

  if (has("create_refund") && primary?.key !== "create_refund") menu.push({ key: "create_refund", label: "Lập phiếu hoàn" });

  if (!has("cancel") && i.canCancel) {
    if (i.status === "BOOKED") menu.push({ key: "cancel", label: "Huỷ đơn", danger: true, blockedReason: BLOCKED_CANCEL_BOOKED });
    else if (i.status === "PROCESSING" && i.deliveryStatus === "DELIVERING")
      menu.push({ key: "cancel", label: "Huỷ đơn", danger: true, blockedReason: BLOCKED_CANCEL_DELIVERING });
  }

  if (i.canEscalate) menu.push({ key: "escalate", label: "Nhờ người xử lý" });
  menu.push({ key: "copy_code", label: "Sao chép mã đơn" });
  if (i.canViewAudit) menu.push({ key: "audit", label: "Xem nhật ký của đơn" });
  return { primary, menu };
}

// ---------------------------------------------------------------------------------------------------------------------
// Giữ chỗ

export type HoldInfo = { over: boolean; left: string | null; until: string | null };

/** "Còn giữ chỗ" mm:ss và "Tự huỷ lúc" — hai trường riêng (ED-09-AC5). Chỉ đơn Giữ chỗ; mốc luôn do BE trả. */
export function holdInfo(status: string, reservedUntil: string | null | undefined, now: number): HoldInfo | null {
  if (status !== "BOOKED" || !reservedUntil) return null;
  const end = new Date(reservedUntil).getTime();
  if (Number.isNaN(end)) return null;
  const ms = Math.max(0, end - now);
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return { over: ms <= 0, left: `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`, until: reservedUntil };
}

/** Đơn Giữ chỗ đã hết giờ thì chip đổi sang "Đã huỷ" ngay, không cần tải lại (ED-09-AC5). BE vẫn là nơi chốt trạng thái. */
export function effectiveOrderStatus(status: string, reservedUntil: string | null | undefined, now: number): string {
  const h = holdInfo(status, reservedUntil, now);
  return h?.over ? "AUTO_CANCELLED" : status;
}

// ---------------------------------------------------------------------------------------------------------------------
// Liên kết "Mở trang khách" (ED-09-AC8): chỉ khi có id khách VÀ người xem có quyền xem khách.

export function customerLinkHref(customerId: number | null | undefined, canViewCustomer: boolean): string | null {
  if (!canViewCustomer || !customerId) return null;
  return `/customers/detail/?id=${customerId}`;
}

// ---------------------------------------------------------------------------------------------------------------------
// Khoản tiền (hàng chờ thanh toán)

export const PAYMENT_STEPS: PathStep[] = [
  { key: "OPEN", label: "Chờ xử lý" },
  { key: "RESOLVED", label: "Đã xử lý" },
];

const PAYMENT_LABEL: Record<string, string> = {
  attach_to_order: "Gắn vào đơn",
  confirm_order: "Xác nhận đơn đủ tiền",
  refund: "Lập phiếu hoàn",
};

/** Khoản tiền: thao tác đầu tiên BE cho phép là nút chính, còn lại vào "…". */
export function paymentActionPlan(actions: readonly PaymentAction[]): ActionPlan {
  const order = ["attach_to_order", "confirm_order", "refund"];
  const items = order.filter((a) => actions.includes(a)).map((a) => ({ key: a, label: PAYMENT_LABEL[a] }));
  return { primary: items[0] ?? null, menu: items.slice(1) };
}

// ---------------------------------------------------------------------------------------------------------------------
// Phiếu hoàn

export const REFUND_STEPS: PathStep[] = [
  { key: "PENDING", label: "Chờ hoàn" },
  { key: "REFUNDED", label: "Đã hoàn" },
];

export function refundPath(status: string): { current: string; badEnd: { label: string; after: string } | null } {
  if (status === "FAILED") return { current: "PENDING", badEnd: { label: "Thất bại", after: "PENDING" } };
  return { current: status === "REFUNDED" ? "REFUNDED" : "PENDING", badEnd: null };
}

/** Phiếu hoàn: Xác nhận / Chuyển lại là nút chính; "Báo chuyển thất bại" vào "…" (việc hiếm, đỏ). Quản lý: `actions` rỗng. */
export function refundActionPlan(actions: readonly RefundQueueAction[]): ActionPlan {
  let primary: ActionItem | null = null;
  const menu: ActionItem[] = [];
  if (actions.includes("confirm")) primary = { key: "confirm", label: "Xác nhận đã hoàn tiền" };
  else if (actions.includes("retry")) primary = { key: "retry", label: "Chuyển lại" };
  if (actions.includes("mark_failed")) menu.push({ key: "mark_failed", label: "Báo chuyển thất bại", danger: true });
  return { primary, menu };
}

// ---------------------------------------------------------------------------------------------------------------------
// Dòng thời gian (mới nhất trước) và câu báo kết quả

const byNewest = (a: TimelineEntry, b: TimelineEntry) => Date.parse(b.at) - Date.parse(a.at);

/** Liên kết của mốc có chứng từ: phiếu hoàn → màn chi tiết phiếu hoàn, chỉ khi người xem mở được màn đó (không thì chỉ là chữ). */
export function timelineDocHref(doc: OrderTimelineEntry["doc"], opts: { canOpenRefund?: boolean } = {}): string | undefined {
  if (!doc || !Number.isInteger(doc.id) || doc.id <= 0) return undefined;
  if (doc.type === "refund" && opts.canOpenRefund) return `/orders/refunds/detail/?id=${doc.id}`;
  return undefined;
}

/** Dòng thời gian của đơn: ưu tiên `timeline` của BE; thiếu thì ghép tạm từ các mốc giờ đang có. */
export function orderTimeline(
  o: Pick<OrderDetail, "timeline" | "created_at" | "invoice" | "payments">,
  opts: { canOpenRefund?: boolean } = {},
): TimelineEntry[] {
  if (o.timeline && o.timeline.length > 0) {
    return o.timeline
      .map((e) => ({ at: e.at, label: e.label, actor: e.actor_display || undefined, href: timelineDocHref(e.doc, opts) }))
      .sort(byNewest);
  }
  const out: TimelineEntry[] = [];
  if (o.created_at) out.push({ at: o.created_at, label: "Khách đặt đơn" });
  for (const p of o.payments) if (p.received_at) out.push({ at: p.received_at, label: M.tlPaymentReceived });
  if (o.invoice?.issued_at) out.push({ at: o.invoice.issued_at, label: "Xuất hoá đơn" });
  return out.sort(byNewest);
}

/** Khoản do "Ghi tiền về muộn" tạo ra: nguồn MANUAL mà loại là ORPHAN / UNMATCHED (xác nhận tay trên đơn thì luôn MATCHED / UNDERPAID, BE chặn đơn Tự huỷ). */
export function isLateEntry(p: Partial<Pick<PaymentQueueItem, "source" | "match_status">>): boolean {
  return p.source === "MANUAL" && (p.match_status === "ORPHAN" || p.match_status === "UNMATCHED");
}

/** Dòng thời gian của khoản tiền, ghép từ mốc nhận và mốc xử lý (BE chưa có timeline riêng cho khoản tiền). */
export function paymentTimeline(
  p: Pick<PaymentQueueItem, "received_at" | "resolved_at" | "resolved_by"> & Partial<Pick<PaymentQueueItem, "source" | "match_status" | "amount" | "bank_txn_id">>,
): TimelineEntry[] {
  const out: TimelineEntry[] = [];
  // #15: khoản ghi tay ở hàng chờ (MANUAL + Về sau khi đơn huỷ / Không khớp đơn) là "Ghi tay tiền về muộn" (kind payment_recorded_late
  // ở BE). Nhãn chuẩn, chỉ có tiền và mã GD — không chữ tự do. Mốc hiện là giờ nhận theo sao kê (serializer chưa trả giờ ghi).
  if (p.received_at) out.push({ at: p.received_at, label: isLateEntry(p) ? M.tlRecordedLate(p.amount ?? "0", p.bank_txn_id ?? "") : M.tlPaymentReceived });
  if (p.resolved_at) out.push({ at: p.resolved_at, label: M.tlPaymentResolved, actor: typeof p.resolved_by === "string" ? p.resolved_by : undefined });
  return out.sort(byNewest);
}

/** Dòng thời gian của phiếu hoàn: lập · xác nhận (BE chưa trả mốc báo thất bại → chỉ ghi nhận qua chip và lý do). */
export function refundTimeline(r: Pick<RefundQueueItem, "created_at" | "confirmed_at" | "created_by" | "confirmed_by">): TimelineEntry[] {
  const out: TimelineEntry[] = [];
  if (r.created_at) out.push({ at: r.created_at, label: M.tlRefundCreated, actor: typeof r.created_by === "string" ? r.created_by : undefined });
  if (r.confirmed_at) out.push({ at: r.confirmed_at, label: M.tlRefundConfirmed, actor: typeof r.confirmed_by === "string" ? r.confirmed_by : undefined });
  return out.sort(byNewest);
}

/** Câu toast sau "Xác nhận đã nhận tiền": PAID thành công, còn lại là cảnh báo (kết quả do BE quyết). */
export function confirmPaymentToast(r: ConfirmPaymentResult, code: string): { kind: "success" | "warn"; message: string } {
  if (r.duplicate) return { kind: "warn", message: M.duplicate };
  const extra = r.overpaid_amount && Number(r.overpaid_amount) > 0 ? M.resultOverpaid(r.overpaid_amount) : "";
  if (r.result === "PAID") return { kind: "success", message: M.resultPaid(code) + extra };
  if (r.result === "UNDERPAID") return { kind: "warn", message: M.resultUnder(r.paid_total ?? "0", r.missing ?? "0") + extra };
  if (r.result === "ORPHAN") return { kind: "warn", message: M.resultOrphan };
  return { kind: "warn", message: M.resultOther(enumOf(ENUMS.salesOrderStatus, r.order_status).label) };
}
