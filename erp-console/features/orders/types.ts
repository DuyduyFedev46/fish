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
  /** L8 bổ sung tiền: chuyển thừa ngay lần đầu → phần thừa thành dòng `<mã GD>-THUA` OVERPAID trong hàng chờ. */
  overpaid_amount?: string;
};

// ---------------------------------------------------------------------------------------------------------------------
// S12 — Hàng chờ thanh toán lệch (GET /api/sales/payments/?resolution_status=OPEN, POST …/{id}/resolve)
// S13 — Hoàn tiền cho khoản không có hoá đơn (POST /api/sales/refunds/create {payment_transaction, amount, reason, request_id})
// Khớp contract THỰC TẾ ở 03-dev-notes.md "Lô L8 — S12, S13 (BE)". Key optional = BE không luôn trả / FE đề xuất thêm.

/** Loại lệch. UNDERPAID/ORPHAN/UNMATCHED (BR-TT-04/05); OVERPAID = tiền về cho đơn đã thanh toán (BR-TT-10, P5). */
export type QueueMatchStatus = "UNDERPAID" | "ORPHAN" | "UNMATCHED" | "OVERPAID" | "MATCHED";

export type ResolutionStatus = "OPEN" | "RESOLVED";
/** Cách đã đóng khoản lệch (BR-TT-09): gắn vào đơn · xác nhận đơn khi khách đã bù · hoàn tiền (S13, qua phiếu hoàn đã xác nhận). */
export type Resolution = "ATTACHED" | "CONFIRMED" | "REFUNDED";

/** Thao tác trên một khoản lệch — BE tính cả luật lẫn quyền; FE chỉ đọc để hiện nút. */
export type PaymentAction = "attach_to_order" | "confirm_order" | "refund" | string;

/** Đơn liên quan của một khoản lệch (null khi tiền không khớp đơn nào — UNMATCHED). */
export type QueueOrderRef = {
  id: number;
  code: string;
  status: OrderStatus | string;
  status_label?: string;
  total_amount: string;
  /** Tổng tiền đã nhận của đơn (MATCHED + UNDERPAID, trừ giao dịch đang có phiếu hoàn chưa Thất bại) — BE tính. */
  paid_total: string;
  /** FE đề xuất (BE L8 chưa trả) — có thì hiện tên khách cạnh mã đơn. */
  customer_name?: string;
};

/** Phiếu hoàn đã lập cho khoản lệch (S13) — FE ĐỀ XUẤT, BE L8 chưa trả trong dòng hàng chờ; có thì hiện. */
export type QueueRefund = {
  id: number;
  amount: string;
  /** PENDING | REFUNDED | FAILED */
  status: string;
  status_label?: string;
  bank_txn_ref?: string;
};

/** Một dòng của GET /api/sales/payments/ (phân trang DRF, 20 dòng/trang). */
export type PaymentQueueItem = {
  id: number;
  bank_txn_id: string;
  amount: string;
  received_at: string | null;
  match_status: QueueMatchStatus | string;
  match_status_label?: string;
  /** WEBHOOK | MANUAL */
  source?: string;
  source_label?: string;
  /** Nội dung chuyển khoản trên sao kê (SePay `content`) — FE ĐỀ XUẤT, BE L8 chưa trả; có thì hiện. */
  content?: string;
  order: QueueOrderRef | null;
  resolution_status: ResolutionStatus | string;
  resolution?: Resolution | string | null;
  resolution_label?: string;
  /** Tên người xử lý (BE có thể trả id số — FE chỉ hiện khi là chuỗi). */
  resolved_by?: string | number | null;
  resolved_at?: string | null;
  resolution_note?: string;
  refunds?: QueueRefund[];
  /** Số tiền còn được hoàn (BR-HT-04) — BE tính; thiếu thì FE mặc định = `amount`, BE vẫn chặn. */
  refundable_amount?: string;
  available_actions: PaymentAction[];
};

export type PaymentQueueParams = {
  /** OPEN | RESOLVED. */
  resolution_status: ResolutionStatus;
  /** Lọc theo loại lệch (BE L8 nhận nhiều giá trị cách dấu phẩy). Rỗng = mọi loại. */
  match_status: string;
};

export type ResolveInput =
  | { action: "ATTACH_TO_ORDER"; order_id: number; note: string }
  | { action: "CONFIRM_ORDER"; note: string };

/** 200 của POST /api/sales/payments/{id}/resolve. */
export type ResolveResult = {
  payment_id: number;
  resolution_status: ResolutionStatus | string;
  /** "" khi khoản vẫn OPEN (gắn đơn mà chưa đủ tiền). */
  resolution: Resolution | string | null;
  order_status: OrderStatus | string;
  /** Có khi đơn vừa đủ tiền (xuất hoá đơn + phiếu giao). */
  invoice_id?: number;
  delivery_note_code?: string;
  /** Mọi giao dịch được đóng trong lần này (S12-AC3: cả hai khoản thiếu). */
  resolved_payment_ids?: number[];
  /** Khoản gắn vào lớn hơn tổng đơn → phần thừa tách thành dòng `-THUA` OVERPAID (L8 bổ sung tiền). */
  overpaid_amount?: string;
};

/** Body POST /api/sales/refunds/create — S13 gửi `payment_transaction` (không kèm `sales_invoice`, BR-HT-01). */
export type CreateRefundInput = {
  payment_transaction: number;
  amount: string;
  reason: string;
  /** Chống tạo trùng khi bấm đúp / gửi lại: cùng một lần mở form = cùng một mã. */
  request_id: string;
};

/** 201 phiếu mới · 200 + `duplicate: true` khi cùng `request_id` (phiếu đã tạo trước đó). */
export type CreateRefundResult = {
  id: number;
  status: string;
  status_label?: string;
  amount: string;
  payment_transaction: number | null;
  sales_invoice: number | null;
  reason?: string;
  bank_txn_ref?: string;
  request_id?: string | null;
  duplicate?: boolean;
};
