// MỘT bảng duy nhất: giá trị enum của BE -> nhãn tiếng Việt + tông màu. Chép từ cột "Nhãn dùng trên artboard" của
// doc/design/erp/enum-map.md (nhãn FE thắng nhãn model; mục đánh dấu ⚑ dùng lời thân thiện).
// Không component nào tự viết nhãn trạng thái: dùng <Chip table={ENUMS.salesOrderStatus} value={...} /> hoặc `enumOf`.
// Tông màu (UI-RULES §9): good xanh lá · warn hổ phách · crit đỏ · info xanh biển · mute xám.
// Mỗi lô chỉ THÊM dòng vào file này (02b mục 5.1).

export type Tone = "good" | "warn" | "crit" | "info" | "mute";
export type EnumEntry = { label: string; tone: Tone };
export type EnumTable = Readonly<Record<string, EnumEntry>>;

/** Giá trị trống (null, undefined, ""): hiện "—", không vẽ chip. */
export const EMPTY_ENUM: EnumEntry = { label: "—", tone: "mute" };

/** Giá trị trống? Chip dùng để quyết định có vẽ chip hay chỉ in "—". */
export const isEmptyEnumValue = (value: unknown): boolean => value === null || value === undefined || value === "";

const e = (label: string, tone: Tone = "mute"): EnumEntry => ({ label, tone });

export const ENUMS = {
  // ---- sales ----
  salesOrderStatus: {
    BOOKED: e("Giữ chỗ", "warn"),
    PAID: e("Đã thanh toán", "info"),
    PROCESSING: e("Đang xử lý", "info"),
    COMPLETED: e("Hoàn tất", "good"),
    CANCELLED: e("Đã huỷ"),
    AUTO_CANCELLED: e("Đã huỷ"), // ⚑ lý do (hết giờ giữ chỗ) ở cột riêng
  },
  salesInvoiceStatus: {
    ISSUED: e("Đã xuất", "good"),
    CANCELLED: e("Đã huỷ"),
  },
  paymentMatchStatus: {
    MATCHED: e("Khớp", "good"),
    UNDERPAID: e("Thiếu tiền", "warn"),
    ORPHAN: e("Về sau khi đơn tự huỷ", "warn"),
    UNMATCHED: e("Không khớp đơn", "crit"),
    OVERPAID: e("Chuyển thừa", "warn"),
  },
  paymentResolutionStatus: {
    OPEN: e("Chờ xử lý", "warn"),
    RESOLVED: e("Đã xử lý", "good"),
  },
  paymentResolution: {
    ATTACHED: e("Đã gắn vào đơn", "good"),
    CONFIRMED: e("Đã xác nhận đơn", "good"),
    REFUNDED: e("Đã hoàn tiền", "info"),
  },
  paymentSource: {
    WEBHOOK: e("Webhook SePay"),
    MANUAL: e("Xác nhận tay"),
    GATEWAY: e("Cổng SePay"),
  },
  cancelReason: {
    CUSTOMER_CHANGED_MIND: e("Khách đổi ý"),
    DAMAGED_WHEN_PACKING: e("Hư khi đóng hàng"),
    GIVE_UP_AFTER_FAILED: e("Bỏ sau khi giao thất bại"),
    OTHER: e("Khác"),
  },
  refundMethod: {
    MANUAL_TRANSFER: e("Chuyển khoản tay"),
    GATEWAY: e("Qua cổng"),
  },
  refundStatus: {
    PENDING: e("Chờ hoàn", "warn"),
    REFUNDED: e("Đã hoàn", "good"),
    FAILED: e("Thất bại", "crit"),
  },

  // ---- delivery ----
  deliveryStatus: {
    CONFIRMING: e("Chờ xác nhận", "warn"),
    PREPARING: e("Soạn hàng", "info"),
    READY: e("Chờ lấy hàng", "info"),
    DELIVERING: e("Đang giao", "info"),
    COMPLETED: e("Hoàn tất", "good"),
    FAILED: e("Giao thất bại", "crit"),
    CANCELLED: e("Đã huỷ theo đơn"),
  },
  /** Tem in (suy ra từ `label.printed` / `valid_print_no`); số lần in lấy qua `deliveryLabelText`. */
  deliveryLabel: {
    UNPRINTED: e("Chưa in tem", "warn"),
    PRINTED: e("Đã in", "good"),
  },
  deliveryLabelReason: {
    FIRST: e("In lần đầu"),
    REPRINT: e("In lại"),
    ADDRESS_CHANGED: e("Đổi thông tin nhận"),
  },
  /** B5 (02b): lý do giao thất bại. */
  deliveryFailureReason: {
    NOT_MET: e("Không gặp khách"),
    REFUSED: e("Khách từ chối nhận"),
    WRONG_ADDRESS: e("Sai địa chỉ"),
    DAMAGED: e("Hàng hư khi giao"),
    OTHER: e("Khác"),
  },
  confirmTaskState: {
    PENDING: e("Chờ gọi", "warn"),
    CALLBACK: e("Hẹn gọi lại", "info"),
    ESCALATED: e("Cần quyết định", "crit"),
    REFUND_CALL: e("Gọi báo hoàn tiền", "warn"),
    DONE: e("Hoàn tất", "good"),
  },
  confirmEscalationReason: {
    UNREACHABLE: e("Không nghe máy"),
    WRONG_NUMBER: e("Sai số"),
    WANT_CANCEL: e("Khách muốn huỷ"),
    WANT_CHANGE: e("Khách muốn đổi"),
  },
  confirmCallResult: {
    CONFIRMED: e("Đã xác nhận", "good"),
    CONFIRMED_CHANGED: e("Đã xác nhận, có đổi", "good"),
    UNREACHABLE: e("Không nghe máy", "warn"),
    WRONG_NUMBER: e("Sai số điện thoại", "crit"),
    CALLBACK: e("Hẹn gọi lại", "info"),
    WANT_CHANGE: e("Khách muốn đổi món", "info"),
    WANT_CANCEL: e("Khách muốn huỷ đơn", "warn"),
    NOTIFIED: e("Đã báo hoàn tiền", "good"),
  },
  /** Quyết định đơn chưa xác nhận được. */
  unconfirmedDecision: {
    DELIVER_WITHOUT_CONFIRM: e("Giao không xác nhận"),
    EXTEND: e("Gia hạn thêm"),
    CANCEL: e("Huỷ đơn"),
  },

  // ---- inventory ----
  batchStatus: {
    DRAFT: e("Nháp"),
    SELLING: e("Đang bán", "good"),
    NEAR_EXPIRY: e("Cận hạn", "warn"),
    SOLD_OUT: e("Hết hàng"),
    EXPIRED: e("Quá hạn", "crit"),
    CANCELLED: e("Đã huỷ"),
    CLOSED: e("Đã chốt"),
  },
  stockMovementType: {
    RECEIPT: e("Nhập lô", "good"),
    SALE: e("Bán ra", "info"),
    RETURN_RESTOCK: e("Hàng hoàn tái nhập", "good"),
    RECONCILE: e("Điều chỉnh kiểm kê", "info"),
    WRITE_OFF: e("Ghi lỗ, huỷ hàng", "warn"), // ⚑
    CANCEL_RESTORE: e("Hoàn kho do huỷ đơn"),
    SUPPLIER_RETURN: e("Trả nhà cung cấp"),
  },
  stockEntryPurpose: {
    MATERIAL_RECEIPT: e("Nhập vật tư", "info"),
    ADJUSTMENT: e("Điều chỉnh"),
  },
  stockReconciliationStatus: {
    DRAFT: e("Nháp"),
    SUBMITTED: e("Chờ duyệt", "warn"),
    APPROVED: e("Đã duyệt", "good"),
  },
  returnToStockStatus: {
    DRAFT: e("Chờ duyệt", "warn"),
    APPROVED: e("Đã duyệt", "good"),
    CANCELLED: e("Đã huỷ"),
  },
  returnToStockDecision: {
    PENDING: e("Chờ quyết định", "warn"),
    RESTOCK: e("Tái nhập", "good"),
    WRITE_OFF: e("Huỷ bỏ, ghi lỗ", "warn"), // ⚑
  },
  warehouseKind: {
    true: e("Nhóm kho"),
    false: e("Kho"),
  },

  // ---- purchasing ----
  purchaseReceiptStatus: {
    DRAFT: e("Nháp"),
    SUBMITTED: e("Đã ghi nhận", "good"),
    CANCELLED: e("Đã huỷ"),
  },
  purchaseCostType: {
    ICE: e("Đá"),
    TRANSPORT: e("Vận chuyển"),
    LOADING: e("Bốc vác"),
    OTHER: e("Khác"),
  },
  purchaseCostAllocation: {
    BY_QTY: e("Theo số kg"),
    BY_VALUE: e("Theo giá trị"),
  },
  /** `PurchaseInvoice.is_paid` (Boolean): khoá là "true"/"false", dùng `booleanEntry`. */
  purchaseInvoicePaid: {
    true: e("Đã trả tiền", "good"),
    false: e("Chưa trả tiền", "warn"),
  },
  supplierType: {
    INDIVIDUAL: e("Cá nhân"),
    COMPANY: e("Doanh nghiệp"),
  },
  supplierActive: {
    true: e("Đang hợp tác", "good"),
    false: e("Ngừng hợp tác"),
  },

  // ---- catalog ----
  itemType: {
    SIMPLE: e("Mặt hàng thường"),
    BUNDLE: e("Combo", "info"),
  },
  itemActive: {
    true: e("Đang kinh doanh", "good"),
    false: e("Đang ẩn"),
  },
  pricingRuleActive: {
    true: e("Đang bật", "good"),
    false: e("Đã tắt"),
  },
  pricingRuleApplyOn: {
    ITEM: e("Theo mặt hàng"),
    ORDER: e("Theo đơn"),
  },
  pricingRuleDiscountType: {
    AMOUNT: e("Giảm số tiền"),
    PERCENT: e("Giảm phần trăm"),
  },

  // ---- content ----
  entryStatus: {
    draft: e("Nháp"),
    pending_review: e("Chờ duyệt", "warn"),
    published: e("Đã đăng", "good"),
    unpublished: e("Đã gỡ"),
  },
  entryKind: {
    post: e("Bài viết"),
    page: e("Trang"),
  },
  entrySource: {
    human: e("Người dùng"),
    ai: e("AI", "info"),
  },
  entryPageRole: {
    privacy: e("Bảo mật"),
    terms: e("Điều kiện giao dịch"),
    refund: e("Đổi trả hoàn tiền"),
    seller_info: e("Thông tin người bán"),
  },
  entryReturnReason: {
    missing_info: e("Thiếu thông tin, hình ảnh"),
    wrong_content: e("Nội dung chưa chuẩn, cần sửa"),
    legal_risk: e("Rủi ro pháp lý, bản quyền"),
    other: e("Khác"),
  },
  entryUnpublishReason: {
    wrong_price: e("Giá chưa đúng"),
    complaint: e("Khiếu nại, rủi ro pháp lý"),
    out_of_season: e("Hết mùa vụ"),
    wrong_content: e("Nội dung chưa chuẩn"),
    other: e("Khác"),
  },
  categoryActive: {
    true: e("Đang hoạt động", "good"),
    false: e("Ngừng dùng"),
  },

  // ---- accounts ----
  staffStatus: {
    ACTIVE: e("Đang làm", "good"),
    INACTIVE: e("Đã nghỉ"),
  },
  auditActorKind: {
    user: e("Người"),
    system: e("Hệ thống"),
    ai: e("AI", "info"),
  },

  // ---- ai ----
  aiActionKind: {
    read: e("Đọc"),
    write: e("Ghi"),
  },
  aiLevel: {
    OFF: e("Tắt"),
    A: e("Tự đọc", "info"), // ⚑
    C: e("Hỏi trước khi làm", "warn"), // ⚑
    B: e("Tự ghi", "good"), // ⚑
  },
  aiActionStatus: {
    PENDING: e("Chờ duyệt", "warn"),
    CONFIRMED: e("Đã duyệt", "good"),
    REJECTED: e("Đã từ chối"),
    EXPIRED: e("Hết hạn"),
    SCHEDULED: e("Đã lên lịch", "info"),
    DONE: e("Đã thực hiện", "good"),
    UNDONE: e("Đã hoàn tác"),
    CANCELLED: e("Đã huỷ"),
    ESCALATED: e("Đã chuyển việc", "info"),
    FAILED: e("Thất bại", "crit"),
  },
  aiGlobalMode: {
    on: e("Bật", "good"), // ⚑
    c_only: e("Luôn hỏi trước", "warn"), // ⚑
    off: e("Tắt", "crit"), // ⚑
  },
} as const satisfies Record<string, EnumTable>;

export type EnumName = keyof typeof ENUMS;

/**
 * Tra một giá trị. Giá trị lạ (BE thêm enum mà FE chưa biết) hiện đúng MÃ GỐC trong chip trung tính, để người
 * vận hành biết BE vừa trả gì (ED-02-AC4). Không tự đặt nhãn. Giá trị trống -> "—".
 */
export function enumOf(table: EnumTable, value: string | number | boolean | null | undefined): EnumEntry {
  if (isEmptyEnumValue(value)) return EMPTY_ENUM;
  const key = String(value);
  return table[key] ?? { label: key, tone: "mute" };
}

export const enumLabel = (table: EnumTable, value: string | number | boolean | null | undefined) => enumOf(table, value).label;

/** Tem in: "Chưa in tem" · "Đã in (lần N)". */
export function deliveryLabelText(printNo: number | null | undefined): EnumEntry {
  if (!printNo || printNo < 1) return ENUMS.deliveryLabel.UNPRINTED;
  return { label: `${ENUMS.deliveryLabel.PRINTED.label} (lần ${printNo})`, tone: "good" };
}
