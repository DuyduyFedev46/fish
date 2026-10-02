export type Supplier = {
  id: number;
  name: string;
  phone?: string;
  note?: string;
  is_active: boolean;
};

export type ReceiveBatchesLineInput = {
  item_code: string;
  qty: string;
  rate: string;
  shelf_life_days?: number | null;
};

export type ReceiveBatchesPayload = {
  supplier: number;
  received_date?: string;
  warehouse?: number;
  idempotency_key?: string;
  lines: ReceiveBatchesLineInput[];
};

export type PurchaseReceiptSummary = {
  id: number;
  supplier: number;
  warehouse: number;
  received_date: string;
  status: string;
  created_by: number;
  note?: string;
  lines: Array<{
    id: number;
    item: number;
    item_code: string;
    qty: string;
    rate?: string;
    shelf_life_days?: number | null;
    batch?: number | null;
  }>;
};

export type ReceivedBatchItem = {
  batch_id: string;
  status: string;
  expiry_date: string;
  qty_available: string;
  purchase_rate?: string;
  landed_unit_cost?: string;
};

export type ReceiveBatchesResponse = {
  receipt: PurchaseReceiptSummary;
  batches: ReceivedBatchItem[];
};

export type CancelPurchaseReceiptResponse = {
  id: number;
  status: string;
};


// ---- Đọc phiếu nhập (R10, ED-20) ----

/** Hoá đơn gắn với phiếu ở danh sách: chỉ cho biết có hay chưa (id), không có số tiền. */
export type ReceiptInvoiceRef = { id: number };

/** Một dòng của danh sách Mua hàng (GET /api/purchasing/receipts/). `purchase_amount` chỉ có khi người xem có view_costprice. */
export type ReceiptRow = {
  id: number;
  /** "PR-<id>". */
  code: string;
  supplier: number;
  supplier_name: string;
  warehouse: number;
  warehouse_name: string;
  received_date: string;
  status: string;
  status_label: string;
  created_by: number | null;
  created_by_name: string;
  created_at: string;
  note: string;
  items_summary: string;
  line_count: number;
  /** Tổng kg, chuỗi 3 chữ số lẻ. */
  total_qty: string;
  batch_codes: string[];
  invoice: ReceiptInvoiceRef | null;
  /** Tiền mua (giá vốn): chỉ Chủ. Người khác không có khoá này. */
  purchase_amount?: string;
};

export type ReceiptListParams = {
  /** Trạng thái, một hay nhiều (cách dấu phẩy). Rỗng = mọi trạng thái. */
  status: string;
  supplier: string;
  date_from: string;
  date_to: string;
  /** "1" = chỉ phiếu có hoá đơn, "0" = chưa có hoá đơn, rỗng = mọi phiếu. */
  has_invoice: string;
};

/** Dòng nhập kèm lô sinh ra. `rate`, `purchase_amount`, `landed_unit_cost` chỉ Chủ. */
export type ReceiptLine = {
  id: number;
  item: number;
  item_code: string;
  item_name: string;
  qty: string;
  shelf_life_days: number | null;
  batch: number | null;
  batch_code: string | null;
  batch_status: string | null;
  expiry_date: string | null;
  rate?: string;
  purchase_amount?: string;
  landed_unit_cost?: string | null;
};

/** Hoá đơn của phiếu: `amount` theo quyền xem hoá đơn mua (Quản lý có, nhân viên kho không có cả mảng `invoices`). */
export type ReceiptInvoice = {
  id: number;
  code: string;
  invoice_date: string;
  is_paid: boolean;
  amount?: string;
};

/** Chi phí phụ rơi vào lô của phiếu (chỉ Chủ). */
export type ReceiptCost = {
  id: number;
  cost_type: string;
  cost_type_label: string;
  allocation_method: string;
  allocation_method_label: string;
  incurred_date: string;
  amount: string;
  allocated_amount: string;
  batch_count: number;
};

export type ReceiptDetail = ReceiptRow & {
  lines: ReceiptLine[];
  /** Có khoá này khi người xem có view_purchaseinvoice. */
  invoices?: ReceiptInvoice[];
  costs?: ReceiptCost[];
  allocated_amount?: string;
};

export type SubmitReceiptResponse = {
  receipt: PurchaseReceiptSummary;
  batches_created: string[];
};
