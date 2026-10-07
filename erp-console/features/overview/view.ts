// Phần THUẦN của màn Tổng quan (ED-08 / D1): nhãn thẻ, các dòng "Cần chú ý", đề xuất AI theo khu, cột Lý do.
// Không đụng React, mạng hay giờ máy: mọi hàm nhận dữ liệu vào, trả chuỗi/mảng ra để kiểm bằng vitest.

import { effectiveOrderStatus } from "@/features/orders/orderDetailModel";
import { dateKeyInVietnam, dateOnly } from "@/shared/lib/format";
import type { DashboardAttentionData } from "./types";

// ---------------------------------------------------------------------------------------------------------------------
// Thẻ số liệu

/** "Doanh thu 01/10/2026" — ngày theo giờ Việt Nam của mốc dữ liệu (`as_of` của BE); thiếu mốc → "Doanh thu hôm nay". */
export function revenueLabel(asOf: string | null | undefined): string {
  const key = dateKeyInVietnam(asOf);
  return key ? `Doanh thu ${dateOnly(key)}` : "Doanh thu hôm nay";
}

/** "Lô cận hạn (14 ngày tới)"; BE cũ chưa trả số ngày thì bỏ phần trong ngoặc. */
export function nearExpiryLabel(days: number | null): string {
  return days === null ? "Lô cận hạn" : `Lô cận hạn (${days} ngày tới)`;
}

// ---------------------------------------------------------------------------------------------------------------------
// Cần chú ý

export type AttentionRow = {
  key: string;
  count: number;
  /** Phần chữ sau con số, vd "lô quá hạn còn tồn". */
  label: string;
  /** Cả câu, vd "2 lô quá hạn còn tồn". */
  text: string;
  href: string;
  crit: boolean;
};

/** Các dòng cảnh báo từ `/api/dashboard/attention/`; chỉ dòng có số > 0. Thứ tự: quá hạn, gọi xác nhận, hoàn/huỷ, tem. */
export function attentionRows(data: DashboardAttentionData): AttentionRow[] {
  const rows: AttentionRow[] = [];
  const add = (key: string, count: number | undefined, label: string, href: string, crit: boolean) => {
    if (typeof count === "number" && count > 0) rows.push({ key, count, label, text: `${count} ${label}`, href, crit });
  };
  add("expired_batches_open", data.expired_batches_open, "lô quá hạn còn tồn", "/inventory/?status=EXPIRED", true);
  add("confirmation_queue_waiting", data.confirmation_queue_waiting, "đơn chờ gọi xác nhận quá hạn", "/confirmation/", true);
  add("confirmation_escalated", data.confirmation_escalated, "đơn cần Quản lý quyết định", "/confirmation/", true);
  add("confirmation_auto_cancel_blocked", data.confirmation_auto_cancel_blocked, "đơn quá hạn bị hoãn tự huỷ", "/confirmation/", true);
  add("refund_calls_open", data.refund_calls_open, "cuộc gọi cần nhắc báo hoàn/huỷ", "/confirmation/", false);
  add("labels_not_printed", data.labels_not_printed, "phiếu soạn chưa in tem quá hạn", "/deliveries/", false);
  add("labels_to_void", data.labels_to_void, "tem giấy cần huỷ (xé)", "/deliveries/", true);
  return rows;
}

/** "Còn 1 ngày tới hạn" / "Hết hạn hôm nay". */
export function expiryLine(daysLeft: number): string {
  if (daysLeft <= 0) return "Hết hạn hôm nay";
  return `Còn ${daysLeft} ngày tới hạn`;
}

// ---------------------------------------------------------------------------------------------------------------------
// Đề xuất AI theo khu

export type AiZone = "purchasing" | "orders" | "inventory";

export const AI_ZONE_LABEL: Record<AiZone, string> = {
  purchasing: "Mua hàng",
  orders: "Đơn & tiền",
  inventory: "Kho & lô",
};

const ZONE_ORDER: AiZone[] = ["purchasing", "orders", "inventory"];

/** Loại chứng từ đích (vd "purchasing.purchasereceipt") → khu. Loại không thuộc khu nào (danh mục, tài khoản) → null. */
export function aiZoneOf(targetModel: string): AiZone | null {
  const app = targetModel.toLowerCase().split(".")[0];
  if (app === "purchasing") return "purchasing";
  if (app === "sales" || app === "delivery") return "orders";
  if (app === "inventory") return "inventory";
  return null;
}

export type ProposalSummary = {
  total: number;
  zones: { zone: AiZone; label: string; count: number }[];
};

/** Gom số đề xuất theo khu để vẽ dòng "N đề xuất AI chờ duyệt — Mua hàng 1 · Đơn & tiền 1 · Kho & lô 1". Tổng gồm cả loại ngoài 3 khu. */
export function summarizeProposals(byTargetModel: Record<string, number>): ProposalSummary {
  const per: Record<AiZone, number> = { purchasing: 0, orders: 0, inventory: 0 };
  let total = 0;
  for (const [model, n] of Object.entries(byTargetModel)) {
    if (!Number.isFinite(n) || n <= 0) continue;
    total += n;
    const zone = aiZoneOf(model);
    if (zone) per[zone] += n;
  }
  return {
    total,
    zones: ZONE_ORDER.filter((z) => per[z] > 0).map((z) => ({ zone: z, label: AI_ZONE_LABEL[z], count: per[z] })),
  };
}

export function zonesText(summary: ProposalSummary): string {
  return summary.zones.map((z) => `${z.label} ${z.count}`).join(" · ");
}

// ---------------------------------------------------------------------------------------------------------------------
// Đơn gần đây

export type OrderLine = { status: string; reason: string | null; holdUntil: string | null };

/**
 * Trạng thái hiệu lực của đơn ở máy (đơn Giữ chỗ quá mốc → Đã huỷ ngay, ED-09-AC5), cột Lý do và mốc đếm ngược.
 * Đếm ngược nằm ở CỘT RIÊNG (ED-08-AC2).
 */
export function orderLine(status: string, expiresAt: string | null, now: number, serverReason?: { label: string } | null): OrderLine {
  const effective = effectiveOrderStatus(status, expiresAt, now);
  return {
    status: effective,
    // Lô 17b (G1): lý do lấy từ BE (`reason.label`, Lô 17a); riêng đơn Giữ chỗ vừa quá mốc ở máy thì BE chưa kịp huỷ nên FE tự ghi.
    reason: effective === "AUTO_CANCELLED" ? (serverReason?.label ?? "Hết giờ giữ chỗ") : (serverReason?.label ?? null),
    holdUntil: effective === "BOOKED" ? expiresAt : null,
  };
}
