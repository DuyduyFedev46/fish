// Kiểu dữ liệu module inventory (Lô 7, ED-23/24/25). Khớp contract 02b: R5 danh sách lô, R6 sổ nhập xuất, R7 kho,
// R7b phiếu điều chỉnh tồn (chỉ đọc), R3 đơn theo lô, báo cáo lãi lỗ lô. Tiền và kg từ API là CHUỖI thập phân (bất biến 7).

/** Một dòng của GET /api/inventory/batches/ (R5). `purchase_rate`, `landed_unit_cost` chỉ có key khi người xem có inventory.view_costprice. */
export type BatchApiRow = {
  id: number;
  batch_id: string;
  item: number;
  item_code: string;
  item_name: string;
  supplier: number;
  supplier_name: string;
  warehouse: number;
  warehouse_name: string;
  received_date: string;
  expiry_date: string;
  qty_received: string;
  qty_available: string;
  qty_reserved: string;
  qty_sellable: string;
  status: string;
  status_label: string;
  closed_at: string | null;
  /** Phiếu nhập sinh ra lô; null = lô tạo tay. */
  receipt: { id: number; code: string } | null;
  purchase_rate?: string;
  landed_unit_cost?: string;
};

/** Lọc của R5. Chuỗi rỗng = không lọc. `search` KHÔNG có ở BE: màn tìm trên các dòng đã tải. */
export type BatchListParams = {
  status: string;
  warehouse: string;
  has_stock: boolean;
};

export type BatchActionResult = Pick<BatchApiRow, "id" | "batch_id" | "status"> & { qty_available?: string };

/** Body POST /api/inventory/batches/<id>/return-to-supplier/. `qty` và `supplier_refund_amount` là chuỗi thập phân. */
export type ReturnToSupplierInput = {
  qty: string;
  supplier_refund_amount: string;
  note: string;
  /** UUID sinh một lần khi mở form: gửi lại cùng mã (bấm đúp, mạng chập chờn) thì BE trả bản ghi cũ, không trừ tồn lần hai. */
  request_id: string;
};

/** 200 của return-to-supplier. KHÔNG có số tiền nhà cung cấp hoàn (nhạy cảm), FE cũng không hiện lại sau khi lưu. */
export type ReturnToSupplierResult = {
  batch_id: string;
  status: string;
  qty_available: string;
  returned_qty: string;
  return_id: number;
};

// ---- Kho (R7) và phiếu điều chỉnh tồn (R7b) ----

export type Warehouse = {
  id: number;
  name: string;
  is_group: boolean;
  is_group_label: string;
  active_batch_count: number;
  total_qty: string;
};

export type WarehouseInput = { name: string; is_group: boolean };

export type StockEntry = {
  id: number;
  /** SE-<số> */
  code: string;
  purpose: string;
  purpose_label: string;
  batch: number;
  batch_code: string;
  item_name: string;
  qty_change: string;
  reason: string;
  created_by: number | null;
  created_by_name: string;
  created_at: string;
};

export type StockEntryParams = { purpose: string; date_from: string; date_to: string };

// ---- Đơn dùng lô (R3: GET /api/sales/orders/?batch=) ----

/** Chỉ các trường màn này dùng. Tên, SĐT khách có trong response nhưng KHÔNG đọc và KHÔNG hiện ở đây. */
export type OrderUsingBatch = {
  id: number;
  code: string;
  status: string;
  total_amount: string;
  created_at: string;
};

// ---- Lãi lỗ lô (GET /api/reports/batch/<mã lô>/, chỉ Chủ: reports.view_profitreport) ----

export type BatchProfitReport = {
  batch_id: string;
  provisional: boolean;
  qty_received: string;
  qty_sold: string;
  /** Hao hụt (kg): nhập − bán − còn lại (không tính phần đã trả nhà cung cấp). */
  shrinkage_qty: string;
  landed_unit_cost: string;
  revenue: string;
  total_cost: string;
  profit: string;
};
