// Kiểu dữ liệu module Nhà cung cấp (ED-22, Lô 11). Chép đúng contract BE Lô 11 (B3), 03-dev-notes.md "Lô 11 — BE".
// Tiền là chuỗi thập phân của BE ("14326000.00"): FE chỉ đưa qua `vnd()`, không tự cộng trừ.
// `purchase_total` CHỈ có key khi người xem có inventory.view_costprice (Chủ); người khác không có key (không phải null).
// Lệch story: khoá thật là `last_received_at` và `purchase_total` (story ghi last_receipt_at / total_purchase_amount).

export type SupplierType = "INDIVIDUAL" | "COMPANY";

/** Một dòng của GET /api/purchasing/suppliers/ và thân của GET /{id}/ (chi tiết KHÔNG kèm danh sách phiếu hay lô). */
export type Supplier = {
  id: number;
  name: string;
  supplier_type: SupplierType;
  supplier_type_label: string;
  /** Số điện thoại đối tác (không phải của khách): hiện đủ. */
  phone: string;
  note: string;
  is_active: boolean;
  /** Chỉ tính phiếu Đã ghi nhận. */
  receipt_count: number;
  /** ISO; null = chưa có phiếu nào. */
  last_received_at: string | null;
  purchase_total?: string;
};

/** Lọc của danh sách. Chuỗi rỗng = không lọc. */
export type SupplierListParams = {
  q: string;
  /** "" | "INDIVIDUAL" | "COMPANY". */
  type: string;
  /** "" | "1" | "0". */
  active: string;
};

/** Body POST (tạo mới). */
export type SupplierInput = {
  name: string;
  supplier_type: SupplierType;
  phone: string;
  note: string;
  is_active: boolean;
};

/** Body PATCH: chỉ các trường đổi. Không bao giờ có DELETE/PUT (BE trả 405). */
export type SupplierPatch = Partial<SupplierInput>;

/** Một dòng của GET /api/purchasing/receipts/?supplier=<id> (R10). `purchase_amount` chỉ có key với Chủ. */
export type SupplierReceiptRow = {
  id: number;
  code: string;
  supplier: number;
  /** Ngày nhập (chỉ ngày). Cột "Nhập lúc" dùng `created_at` (giờ ghi nhận), cùng mốc với `last_received_at` của nhà cung cấp. */
  received_date: string;
  created_at: string;
  status: string;
  status_label: string;
  items_summary: string;
  line_count: number;
  total_qty: string;
  purchase_amount?: string;
};

/** Một dòng của GET /api/inventory/batches/?supplier=<id>&has_stock=1 (R5), chỉ các cột bảng "Lô đang bán" dùng. */
export type SupplierBatchRow = {
  id: number;
  batch_id: string;
  item_name: string;
  qty_available: string;
  expiry_date: string;
  status: string;
};
