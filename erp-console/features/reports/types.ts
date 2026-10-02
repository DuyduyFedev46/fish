// Kiểu dữ liệu Báo cáo lãi lỗ (ED-32). Mọi số tiền/kg là chuỗi thập phân của BE ("1650000.00"); cộng trừ qua ./decimal.ts.
// Chỉ Chủ (reports.view_profitreport) gọi được; vai khác nhận 403.

/** GET /api/reports/period/?year=&month= */
export type PeriodReport = {
  year: number;
  month: number;
  /** Doanh thu ghi nhận của kỳ, ĐÃ trừ chứng từ đảo (`credit_notes`). */
  revenue: string;
  /** Giá vốn ghi nhận của kỳ, ĐÃ trừ phần đảo (`cogs_reversed`). */
  cogs: string;
  credit_notes: string;
  cogs_reversed: string;
  refunds: string;
  /** Lãi/lỗ kỳ = revenue − cogs − refunds; có thể âm. */
  profit: string;
  invoice_count: number;
  refund_count: number;
};

/** GET /api/reports/batches/ — một dòng là `batch_pnl` của lô kèm tên mặt hàng và trạng thái. */
export type BatchPnl = {
  /** Mã lô (chuỗi), không phải khoá số. */
  batch_id: string;
  provisional: boolean;
  qty_received: string;
  qty_sold: string;
  landed_unit_cost: string;
  revenue: string;
  reversed_qty: string;
  reversed_revenue: string;
  purchase_cost: string;
  allocated_cost: string;
  shrinkage_qty: string;
  shrinkage_cost: string;
  damage_qty: string;
  damage_cost: string;
  expired_qty: string;
  expired_cost: string;
  supplier_return_qty: string;
  supplier_refund_amount: string;
  total_cost: string;
  profit: string;
};

export type BatchReportRow = BatchPnl & {
  /** Số thứ tự do FE gán chỉ để thoả usePagedList (BE không trả khoá số); khoá dòng thật là `batch_id`. */
  id: number;
  item_name: string;
  /** Mã trạng thái lô (inventory.Batch.Status). */
  status: string;
  status_label: string;
};

export type BatchReportParams = {
  /** YYYY-MM. */
  month: string;
  /** "closed" | "provisional" | "" (tất cả). */
  state: string;
};
