import { ENUMS } from "@/shared/lib/enums";

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
  /** Tên người giao (R4). Không có người giao → null. Là tên NHÂN VIÊN, không phải dữ liệu khách. */
  assigned_to_name?: string | null;
  failed_attempts: number;
  /** Mã lý do giao thất bại lần gần nhất (B5): NOT_MET | REFUSED | WRONG_ADDRESS | DAMAGED | OTHER; "" = chưa có. */
  failure_reason?: string;
  failure_reason_label?: string;
  /** `null` = đã ẩn theo thời hạn (SR-PII-02); "" = không có ghi chú. */
  note: string | null;
  created_at: string;
  completed_at: string | null;
  /** Lô bổ sung A #18: lúc nhận hàng đi giao (giao lại thì ghi đè). `null`/thiếu = chưa đi giao. */
  delivery_started_at?: string | null;
  /** Lô bổ sung A #18: lúc báo giao thất bại gần nhất. `null`/thiếu = chưa thất bại. */
  failed_at?: string | null;
  lines_summary: string;
  total_kg: string;
  label: LabelInfo;
  /** `null` = đã ẩn theo thời hạn (NV giao, phiếu kết thúc quá 7 ngày — SR-PII-02); "" = chưa có. */
  customer_name: string | null;
  address: string | null;
  available_actions: string[];
  /**
   * Lô bổ sung A #17: SĐT đủ của người nhận, CHỈ có khi gọi danh sách với `assigned_to=me` (Việc giao của tôi).
   * Phiếu Đang giao/Giao thất bại còn trong cửa sổ 7 ngày mới có số; ngoài ra là `null`; truy vấn khác không có khoá này.
   * Chỉ để hiện và `tel:`; không ghi vào log, URL, localStorage.
   */
  phone?: string | null;
};

export type DeliveryLine = {
  item_name: string;
  qty_kg: string;
  batch_id: string;
  expiry_date: string;
  /** Kho xuất (ED-17-AC7). BE `get_lines` CHƯA trả field này: chưa có thì cột Kho hiện "—" (xem dev-notes, chỗ lệch). */
  warehouse_name?: string | null;
};

export type DeliveryNoteDetail = DeliveryNoteItem & {
  lines: DeliveryLine[];
  /** Rỗng thật cũng là `null` — KHÔNG dùng để biết "đã ẩn"; xem `customer_name === null`. */
  recipient_name: string | null;
  /** SĐT đủ của người nhận (R4: chỉ ở chi tiết, theo cửa sổ SR-PII-02; `null` = đã ẩn). Chỉ để hiện và `tel:`; không ghi vào log, URL, localStorage. */
  phone?: string | null;
  /** Ghi chú giao thất bại (chữ tự do, có thể chứa dữ liệu cá nhân). `null` = đã ẩn theo thời hạn. */
  failure_note?: string | null;
};

/** Lý do giao thất bại gửi lên B5 (khớp `ENUMS.deliveryFailureReason`). */
export type DeliveryFailureReason = "NOT_MET" | "REFUSED" | "WRONG_ADDRESS" | "DAMAGED" | "OTHER";

/** Lý do in tem gửi kèm `label/print/`. */
export type LabelPrintReason = "FIRST" | "REPRINT" | "ADDRESS_CHANGED";

/** B6 `GET /api/delivery/deliverers/` — người giao kèm số phiếu đang gánh. */
export type Deliverer = {
  id: number;
  display_name: string;
  delivering_count: number;
  ready_count: number;
};

export type AssignDeliveryResponse = DeliveryNoteItem & { already?: boolean };

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
  { key: "CONFIRMING", label: ENUMS.deliveryStatus.CONFIRMING.label },
  { key: "PREPARING", label: ENUMS.deliveryStatus.PREPARING.label },
  { key: "READY", label: ENUMS.deliveryStatus.READY.label },
  { key: "DELIVERING", label: ENUMS.deliveryStatus.DELIVERING.label },
  { key: "FAILED", label: ENUMS.deliveryStatus.FAILED.label },
  { key: "COMPLETED", label: `${ENUMS.deliveryStatus.COMPLETED.label} (hôm nay)` },
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


/**
 * CS-17 `GET /api/delivery/notes/lookup/?code=`: kết quả tra mã tem. KHÔNG có tên, SĐT, địa chỉ, mã đơn hay giá.
 * `warning`: "BR-GH-16" = tem cũ hoặc đã huỷ tem (`valid_print_no` = lần tem còn hiệu lực), "BR-GH-07" = phiếu đã huỷ.
 */
export type TagLookup = {
  note_id: number;
  status: DeliveryStatus;
  print_no: number;
  valid_print_no: number | null;
  warning: "BR-GH-16" | "BR-GH-07" | null;
};

/** CS-16: dòng của phiếu soạn nội bộ. Chỉ 4 trường này được giữ lại từ chi tiết phiếu giao (không tên, SĐT, địa chỉ, giá). */
export type PickSheetLine = {
  item_name: string;
  batch_id: string;
  expiry_date: string;
  qty_kg: string;
};

export type PickSheetData = {
  note_code: string;
  status: DeliveryStatus;
  total_kg: string;
  lines: PickSheetLine[];
};
