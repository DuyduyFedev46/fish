// Kiểu dữ liệu module orders — khớp contract S10 (GET /api/sales/orders/, GET /api/sales/orders/{id}/) và
// S11 (POST /api/sales/orders/{id}/confirm-payment) trong 02-stories.md. Tiền/kg là CHUỖI thập phân (bất biến #7).
// Field đánh dấu optional = contract không ghi rõ ở chi tiết; FE chịu được khi BE không trả (xem 03-dev-notes.md, L7 FE).

export type OrderStatus = "BOOKED" | "PAID" | "PROCESSING" | "COMPLETED" | "CANCELLED" | "AUTO_CANCELLED";

/** Một dòng của GET /api/sales/orders/ (phân trang DRF, 20 dòng/trang). */
export type OrderListItem = {
  id: number;
  code: string;
  status: OrderStatus | string;
  status_label: string;
  customer_name: string;
  customer_phone: string;
  total_amount: string;
  created_at: string;
  /** Mốc hết giữ chỗ (BR-BH-03) — BE trả; FE chỉ đếm lùi, không tự tính. */
  reserved_until: string | null;
  /** Mã trạng thái phiếu giao (PREPARING…), null khi chưa có phiếu. */
  delivery_status: string | null;
  needs_attention: boolean;
};

/** Bộ lọc danh sách — gửi lên BE đúng tên tham số của contract. */
export type OrderListParams = {
  /** Nhiều trạng thái nối bằng dấu phẩy, vd "BOOKED,PAID". Rỗng = mọi trạng thái. */
  status: string;
  /** YYYY-MM-DD (ngày theo giờ Việt Nam). Rỗng = không giới hạn. */
  date_from: string;
  date_to: string;
  /** Mã đơn hoặc SĐT, khớp một phần. */
  q: string;
};

export type OrderLine = {
  no: number;
  item_code: string;
  item_name: string;
  qty_kg: string;
  unit_price: string;
  discount: string;
  line_total: string;
};

/** Phân bổ lô (BR-BH-06). `unit_cost` CHỈ có key khi người xem có view_costprice (BR-PQ-15). */
export type OrderAllocation = {
  line_no: number;
  batch_id: string;
  qty_kg: string;
  unit_cost?: string;
};

export type OrderPayment = {
  id: number;
  bank_txn_id: string;
  amount: string;
  /** MATCHED | UNDERPAID | ORPHAN | UNMATCHED */
  match_status: string;
  /** Nhãn BE (L7 bổ sung) — ưu tiên; thiếu thì FE dịch bằng labels.ts. */
  match_status_label?: string;
  received_at: string | null;
  /** WEBHOOK | MANUAL */
  source?: string;
  source_label?: string;
};

export type OrderDelivery = {
  id: number;
  code: string;
  /** PREPARING | READY | DELIVERING | COMPLETED | FAILED */
  status: string;
  status_label?: string;
  assigned_to: { id: number; display_name: string; phone: string } | null;
  failed_attempts: number;
};

export type OrderRefund = {
  id: number;
  amount: string;
  /** PENDING | REFUNDED | FAILED */
  status: string;
  status_label?: string;
  bank_txn_ref: string;
};

/**
 * Loại mốc trên dòng thời gian (tập đóng, BE L7 bổ sung). FE chỉ dùng để chọn icon; mã lạ vẫn hiện được (icon mặc định).
 */
export type TimelineKind =
  | "order_placed"
  | "payment_received"
  | "invoice_issued"
  | "delivery_created"
  | "delivery_status"
  | "delivered"
  | "delivery_failed"
  | "return_to_warehouse"
  | "return_approved"
  | "auto_cancelled"
  | "cancelled"
  | "refund_created"
  | "refund_confirmed";

/** Một mốc trên dòng thời gian (BE L7 bổ sung: ghép chứng từ + AuditLog, `at` tăng dần). `actor_display` "Hệ thống" khi actor=None. */
export type OrderTimelineEntry = {
  at: string;
  kind: TimelineKind | string;
  label: string;
  actor_display?: string | null;
};

/**
 * Thao tác người đang đăng nhập làm được ở trạng thái hiện tại — BE tính cả luật lẫn quyền, FE chỉ đọc để hiện nút.
 * L7 chỉ nối `confirm_payment` (S11); `cancel` (S14), `create_refund` (S15) nối ở lô sau.
 */
export type OrderAction = "confirm_payment" | "cancel" | "create_refund" | string;

/** GET /api/sales/orders/{id}/ */
export type OrderDetail = {
  id: number;
  code: string;
  status: OrderStatus | string;
  status_label?: string;
  total_amount?: string;
  created_at?: string;
  reserved_until?: string | null;
  customer: { name: string; phone: string; address: string };
  lines: OrderLine[];
  allocations: OrderAllocation[];
  invoice: { id: number; code: string; issued_at: string | null } | null;
  payments: OrderPayment[];
  delivery: OrderDelivery | null;
  refunds: OrderRefund[];
  /** Có ở BE L7 bổ sung. Thiếu (BE cũ) → FE ghép tạm từ các mốc giờ sẵn có. */
  timeline?: OrderTimelineEntry[];
  available_actions: OrderAction[];
};

/** Body POST /api/sales/orders/{id}/confirm-payment — `amount` bỏ trống thì BE lấy tổng đơn. */
export type ConfirmPaymentInput = { bank_txn_id: string; amount?: string };

/** 200 của confirm-payment (BR-TT-03/04/05/08). `duplicate: true` = trùng mã GD, trả lại kết quả lần đầu. */
export type ConfirmPaymentResult = {
  result: "PAID" | "UNDERPAID" | "ORPHAN" | string;
  duplicate: boolean;
  order_status: string;
  invoice_id?: number;
  delivery_note_code?: string;
  paid_total?: string;
  missing?: string;
};
