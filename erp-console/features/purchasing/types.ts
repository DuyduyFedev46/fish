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

