// Contract GET /api/dashboard/summary/ — khớp đúng JSON của backend
// (backend/apps/reports/dashboard_api.py, DashboardSummaryView). Dùng chung cho 3 module S8
// (overview, orders, inventory) và tab "Hoạt động" của cột phải, nên để ở shared/.
//
// Quyền BE: reports.view_dashboard (S6, CanViewDashboard) — menu Đơn/Kho & lô đòi thêm quyền này (nav.ts). Giá vốn: `batches[].unit_cost` CHỈ có khi user có
// `inventory.view_costprice` (user.can_cost = true). Số tiền/kg BE trả kiểu float (hàm _money).
// Mỗi module tự typed phần nó đọc bằng Pick<> trong features/<x>/types.ts.

export const DASHBOARD_SUMMARY_PATH = "/api/dashboard/summary/";

/** Khoá cache dùng chung (useResource): 3 màn + cột phải chỉ gọi 1 request. Theo từng người dùng. */
export function dashboardSummaryKey(userId: number): string {
  return `GET ${DASHBOARD_SUMMARY_PATH}#${userId}`;
}

export type OrderStatus = "BOOKED" | "PAID" | "PROCESSING" | "COMPLETED" | "CANCELLED" | "AUTO_CANCELLED";
export type BatchStatus = "DRAFT" | "SELLING" | "NEAR_EXPIRY" | "SOLD_OUT" | "EXPIRED" | "CANCELLED" | "CLOSED";
export type MovementType = "RECEIPT" | "SALE" | "RETURN_RESTOCK" | "RECONCILE" | "WRITE_OFF" | "CANCEL_RESTORE";

export type DashboardKpis = {
  revenue_today: number;
  /** Đơn BOOKED + PAID + PROCESSING (toàn bộ, không chỉ 8 đơn gần nhất). */
  pending_orders: number;
  /** Đơn BOOKED hết giữ chỗ trong ≤ 10 phút. */
  booked_soon: number;
  /** Lô bán được (SELLING/NEAR_EXPIRY, hạn ≥ hôm nay) có hạn ≤ hôm nay + near_expiry_days (BE R6). */
  near_expiry: number;
  /** Tổng tồn × giá vốn lô. CHỈ có key khi người xem có `inventory.view_costprice` (BE L6 vá rò, bất biến #1). */
  inventory_value?: number;
};

/** 8 đơn mới nhất (created_at giảm dần). */
export type RecentOrder = {
  code: string;
  customer: string;
  phone_last4: string;
  amount: number;
  status: OrderStatus;
  status_label: string;
  /** Mốc hết giữ chỗ (ISO) — chỉ có ý nghĩa khi BOOKED. */
  expires_at: string | null;
};

/** Tối đa 20 lô đang hoạt động (DRAFT/SELLING/NEAR_EXPIRY). Màn hiện theo thứ tự xuất FEFO (`fefoOrder`). */
export type DashboardBatch = {
  batch_id: string;
  item: string;
  warehouse: string;
  supplier: string;
  qty_available: number;
  qty_reserved: number;
  received_date: string;
  expiry_date: string;
  status: BatchStatus;
  status_label: string;
  near_expiry: boolean;
  /** Giá vốn/kg — KHÔNG có key này khi user thiếu view_costprice. */
  unit_cost?: number;
};

/** Tối đa 6 lô cận hạn, hạn gần nhất trước. */
export type ExpiryAlert = {
  batch_id: string;
  item: string;
  expiry_date: string;
  days_left: number;
  qty: number;
};

/** 8 dòng sổ kho mới nhất. */
export type LedgerActivity = {
  type: MovementType;
  type_label: string;
  batch_id: string;
  qty_change: number;
  reference: string;
  at: string;
};

export type DashboardSummary = {
  as_of: string;
  /**
   * Số ngày "cận hạn" BE đang dùng (settings BATCH_NEAR_EXPIRY_DAYS) — key MỚI ở CẤP GỐC (BE sửa theo code review trước
   * deploy 1; `kpis` giữ nguyên 4 key). Optional: BE cũ chưa có → FE ẩn số ngày (nearExpiryDays() trả null).
   */
  near_expiry_days?: number;
  user: { username: string; can_cost: boolean };
  kpis: DashboardKpis;
  recent_orders: RecentOrder[];
  batches: DashboardBatch[];
  alerts: ExpiryAlert[];
  activity: LedgerActivity[];
};

/** Số ngày cận hạn từ BE (`near_expiry_days` cấp gốc); thiếu/không hợp lệ → null (UI ẩn số ngày). */
export function nearExpiryDays(data: Pick<DashboardSummary, "near_expiry_days">): number | null {
  const v = data.near_expiry_days;
  return typeof v === "number" && Number.isFinite(v) && v > 0 ? v : null;
}

/**
 * Thứ tự xuất kho FEFO (BR-BH-05 sửa, hồ sơ 2026-09-26-fefo F2-AC1): hạn dùng sớm nhất trước, cùng hạn thì ngày nhập sớm
 * hơn trước, cùng cả hai thì giữ thứ tự BE trả. Lô không có hạn xếp cuối. Chỉ để HIỂN THỊ — chọn lô thật do BE (F1).
 */
export function fefoOrder<T extends { expiry_date?: string | null; received_date?: string | null }>(rows: T[]): T[] {
  const key = (v: string | null | undefined) => v || "9999-12-31";
  return rows
    .map((r, i) => ({ r, i }))
    .sort(
      (a, b) =>
        key(a.r.expiry_date).localeCompare(key(b.r.expiry_date)) ||
        key(a.r.received_date).localeCompare(key(b.r.received_date)) ||
        a.i - b.i,
    )
    .map((x) => x.r);
}
