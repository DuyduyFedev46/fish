// Kiểu dữ liệu module ledger (Lô 7, ED-29): Sổ nhập xuất, GET /api/inventory/ledger/ (R6). Kg là CHUỖI thập phân.

export type MovementType =
  | "RECEIPT"
  | "SALE"
  | "RETURN_RESTOCK"
  | "RECONCILE"
  | "WRITE_OFF"
  | "CANCEL_RESTORE"
  | "SUPPLIER_RETURN";

export type ReferenceKind = "stocktake" | "return" | "supplier_return" | "receipt" | "invoice" | "order" | "batch";

/** Dòng của GET /api/inventory/ledger/ (mới nhất trước). `balance_after` = tồn của lô sau dòng này. */
export type LedgerEntry = {
  id: number;
  batch: number;
  batch_code: string;
  item: number;
  item_name: string;
  warehouse: number;
  warehouse_name: string;
  movement_type: MovementType | string;
  type_label: string;
  qty_change: string;
  balance_after: string;
  /** Chuỗi gốc kỹ thuật (giữ để BE cũ không vỡ); màn KHÔNG hiển thị, chỉ dùng `reference_display`. */
  reference: string;
  reference_display: string;
  reference_link: { kind: ReferenceKind | string; id: number } | null;
  created_at: string;
  created_by: number | null;
  created_by_name: string;
};

export type LedgerParams = {
  batch: string;
  /** Nhiều loại nối bằng dấu phẩy. */
  movement_type: string;
  warehouse: string;
  /** YYYY-MM-DD theo giờ Việt Nam. */
  date_from: string;
  date_to: string;
};
