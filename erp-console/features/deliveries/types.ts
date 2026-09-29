export type DeliveryStatus =
  | "CONFIRMING"
  | "PREPARING"
  | "READY"
  | "DELIVERING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type LabelInfo = {
  printed: boolean;
  valid_print_no: number | null;
  needs_void: number;
  to_void: number[];
};

export type DeliveryNoteItem = {
  id: number;
  code: string;
  status: DeliveryStatus;
  status_label: string;
  sales_invoice: number;
  invoice_code: string;
  order: {
    id: number;
    code: string;
  } | null;
  paid_at: string | null;
  confirmed_at: string | null;
  confirm_skipped: boolean;
  assigned_to: number | null;
  failed_attempts: number;
  note: string;
  created_at: string;
  completed_at: string | null;
  lines_summary: string;
  total_kg: string;
  label: LabelInfo;
  customer_name: string;
  address: string;
  available_actions: string[];
};

export type DeliveryLine = {
  item_name: string;
  qty_kg: string;
  batch_id: string;
  expiry_date: string;
};

export type DeliveryNoteDetail = DeliveryNoteItem & {
  lines: DeliveryLine[];
  recipient_name: string | null;
  recipient_phone: string | null;
};

export type DeliveryListResponse = {
  count: number;
  next: string | null;
  previous: string | null;
  results: DeliveryNoteItem[];
};

export type DeliveryStatusGroup =
  | "CONFIRMING"
  | "PREPARING"
  | "READY"
  | "DELIVERING"
  | "FAILED"
  | "COMPLETED";

export const STATUS_GROUP_TABS: Array<{ key: DeliveryStatusGroup; label: string }> = [
  { key: "CONFIRMING", label: "Chờ xác nhận" },
  { key: "PREPARING", label: "Soạn hàng" },
  { key: "READY", label: "Chờ lấy" },
  { key: "DELIVERING", label: "Đang giao" },
  { key: "FAILED", label: "Giao thất bại" },
  { key: "COMPLETED", label: "Hoàn tất (hôm nay)" },
];

export type LabelData = {
  note_code: string;
  order_code: string;
  print_no: number;
  next_print_no: number;
  is_reprint: boolean;
  reprint_reason: string | null;
  barcode_value: string;
  recipient_name: string;
  recipient_phone_masked: string;
  address: string;
  packages: string;
  total_kg: string;
  earliest_expiry: string;
  paid_text: string;
};

export type PrintDeliveryLabelResponse = {
  print_no: number;
  printed_at: string;
  is_reprint: boolean;
  duplicate: boolean;
};

export type VoidLabelResponse = {
  print_no: number;
  voided_at: string;
  already: boolean;
};

