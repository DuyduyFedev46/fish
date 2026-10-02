// Kiểu dữ liệu hoá đơn mua (R11) và chi phí phụ (R12). Lô 10 dùng ở Mua hàng; Lô 12 dùng lại ở "Hoá đơn mua & chi phí".

/** GET /api/purchasing/invoices/. `amount` hiện cho người có view_purchaseinvoice (Chủ, Quản lý; quyết định D-3). */
export type PurchaseInvoiceRow = {
  id: number;
  /** "#<id>". */
  code: string;
  supplier: number;
  supplier_name: string;
  receipt: number | null;
  /** "PR-<id>" hoặc null khi hoá đơn chưa gắn phiếu. */
  receipt_code: string | null;
  amount: string;
  is_paid: boolean;
  is_paid_label: string;
  invoice_date: string;
  paid_at: string | null;
  created_by: number | null;
};

export type PurchaseInvoiceListParams = {
  /** "1" đã trả, "0" chưa trả, rỗng = tất cả. */
  is_paid: string;
  supplier: string;
  /** YYYY-MM. */
  month: string;
};

/** POST /api/purchasing/invoices/. Tiền gửi dạng chuỗi chữ số ("1650000"), không số lẻ. */
export type PurchaseInvoiceInput = {
  supplier: number;
  receipt: number | null;
  amount: string;
  invoice_date: string;
  is_paid: boolean;
  /** ISO UTC; chỉ gửi khi đã trả tiền. */
  paid_at: string | null;
};

/** Một phần chi phí chia vào một lô. */
export type PurchaseCostAllocation = {
  id: number;
  purchase_cost: number;
  batch: number;
  allocated_amount: string;
};

/** GET /api/purchasing/costs/ (chỉ Chủ: cả chứng từ là giá vốn). */
export type PurchaseCostRow = {
  id: number;
  cost_type: string;
  cost_type_label: string;
  amount: string;
  allocation_method: string;
  allocation_method_label: string;
  incurred_date: string;
  note: string;
  created_by: number | null;
  created_at: string;
  allocations: PurchaseCostAllocation[];
  batch_count: number;
};

export type PurchaseCostListParams = {
  /** Một hay nhiều loại, cách dấu phẩy. */
  cost_type: string;
  month: string;
};

/** POST /api/purchasing/costs/: truyền sẵn số tiền từng lô (tổng phải bằng `amount`, BE kiểm lại). */
export type PurchaseCostInput = {
  cost_type: string;
  amount: string;
  allocation_method: string;
  incurred_date: string;
  note: string;
  allocations: { batch: number; amount: string }[];
};

/** Lô nhận chi phí (lấy từ dòng nhập của phiếu). */
export type CostTargetBatch = {
  batch: number;
  batch_code: string;
  item_name: string;
  qty: string;
  /** Giá mua/kg: chỉ để chia theo giá trị, người có quyền ghi chi phí (Chủ) mới có. */
  rate: string;
};

// ---- Hoá đơn bán (R13, ED-33) ----

/**
 * Một dòng GET /api/sales/invoices/. Hoá đơn chỉ do hệ thống phát hành khi đơn đủ tiền (BR-PQ-11), màn này chỉ đọc.
 * `cogs` và `gross_profit` chỉ có khi người xem có view_costprice; `customer_name` là null khi người xem
 * không có sales.view_customer_list (không phải chuỗi rỗng).
 */
export type SalesInvoiceRow = {
  id: number;
  /** Mã hoá đơn, dạng INV…. */
  code: string;
  sales_order: number;
  order_code: string;
  customer_name: string | null;
  issued_at: string;
  amount: string;
  /** ISSUED | CANCELLED. */
  status: string;
  status_label: string;
  cogs?: string;
  gross_profit?: string;
};

/** Tổng trên TOÀN BỘ kết quả đã lọc (mọi trang), đã bỏ hoá đơn có trạng thái Đã huỷ. `gross_profit` chỉ khi có view_costprice. */
export type SalesInvoiceTotals = { amount: string; gross_profit?: string };

export type SalesInvoicePage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: SalesInvoiceRow[];
  totals: SalesInvoiceTotals;
};

export type SalesInvoiceListParams = {
  /** Mã hoá đơn hoặc mã đơn (BE không tìm theo tên hay SĐT khách). */
  q: string;
  /** "" = cả hai; ISSUED hoặc CANCELLED. */
  status: string;
  /** YYYY-MM-DD, ngày Việt Nam của `issued_at`. */
  date_from: string;
  date_to: string;
};

export type SupplierOption = { id: number; name: string };
export type ReceiptOption = { id: number; code: string; supplier: number; label: string };
