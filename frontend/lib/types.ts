// Kiểu dữ liệu khớp Shop API công khai — contract chuẩn ở doc/features/2026-10-06-shop-giao-dien-moi/02b-tech-design.md §3.

export type ItemType = "SIMPLE" | "BUNDLE";

/** Mức tồn công khai (BR-BH-23). Chỉ ba mức, không bao giờ là số kg. */
export type StockLevel = "in" | "low" | "out";
/** Đơn vị bán: kg cho món lẻ, combo cho BUNDLE. */
export type SaleUnit = "kg" | "combo";
/** Tiền là chuỗi số nguyên đồng ("278000"), chỉ đổi sang số ở chỗ cần tính. */
export type Money = string;
/** Icon nhóm dùng làm ảnh dự phòng, FE suy từ slug nhóm (features/catalog/groupIcon.ts). */
export type GroupIcon = "fish" | "shrimp" | "squid" | "crab" | "combo";

// Ảnh mặt hàng (A4, doc/features/2026-09-26-anh-mat-hang/02-stories.md). Chưa có ảnh -> `image: null`,
// Shop vẽ khung mặc định bằng code (components/catalog/ImageFrame.tsx) — KHÔNG có field id/người tải/tệp
// gốc (bất biến 1: Shop không lộ dữ liệu nội bộ, chỉ nhận URL công khai).
export type ItemImageUrls = { thumb: string; card: string; detail: string };

export type ItemImage = {
  alt: string;
  is_illustration: boolean;
  urls: ItemImageUrls;
};

export type CatalogGroup = {
  slug: string;
  name: string;
  /** Số món đang bán trong nhóm (đếm trong `items`), không phải số kg. */
  item_count: number;
};

// Khớp 02b-tech-design §3.1 (GET /api/shop/catalog/). Không có khoá nào chứa số kg tồn, giá vốn hay mã lô.
export type CatalogItem = {
  item_code: string;
  name: string;
  item_type: ItemType;
  unit: SaleUnit;
  price: Money;
  stock_level: StockLevel;
  min_qty: string;
  qty_step: string;
  group: { slug: string; name: string };
  short_note: string;
  image: ItemImage | null;
};

export type CatalogResponse = {
  groups: CatalogGroup[];
  items: CatalogItem[];
};

export type BundleComponent = {
  item_code: string;
  name: string;
  qty_per_bundle: string;
  unit: SaleUnit;
};

// §3.2 GET /api/shop/catalog/<item_code>/
export type CatalogItemDetail = CatalogItem & {
  description: string;
  spec: string;
  storage: string;
  origin: string;
  bundle_components?: BundleComponent[];
};

// ---- Đặt hàng, tra đơn, thanh toán (02b §3.3–3.5). Kiểu dây = kiểu dùng: tiền là chuỗi `Money`, giờ là ISO UTC có `Z`. ----

export type CreateOrderItemInput = {
  item_code: string;
  /** Chuỗi tối giản: "1", "1.5"; combo luôn nguyên (BR-BH-22). */
  qty: string;
};

export type CreateOrderPayload = {
  /** UUID sinh một lần khi mở form, giữ qua các lần "Thử lại" để không tạo đơn trùng (BR-BH-27). */
  client_request_id: string;
  customer: { name: string; phone: string };
  delivery_address: string;
  items: CreateOrderItemInput[];
  privacy_consent?: { accepted: boolean; policy_version_id: number };
  /** Lô 3b. */
  voucher_code?: string;
};

/** Giảm giá của đơn: nguồn là ưu đãi tự động, mã giảm giá, hoặc không có (`code: null`, `amount: "0"`). */
export type OrderDiscount = {
  source: "promo" | "voucher" | null;
  code: string | null;
  amount: Money;
};

/** Một dòng đơn. `amount` là thành tiền gộp (số lượng nhân đơn giá), không có tên người nhận. */
export type OrderLineData = {
  item_code: string;
  name: string;
  unit: SaleUnit;
  qty: string;
  amount: Money;
};

export type CreateOrderResponse = {
  order_code: string;
  status: string;
  subtotal: Money;
  discount: OrderDiscount;
  total_amount: Money;
  booked_expires_at: string;
  server_now: string;
  hold_minutes: number;
  lines: OrderLineData[];
  lookup_token: string;
};

/** Một dòng lỗi tồn kho: `out` hết hẳn, `short` còn nhưng không đủ số khách đặt. Không có số kg (BR-BH-24). */
export type OutOfStockLine = { item_code: string; stock_level: "out" | "short" };
export type InvalidQtyLine = { item_code: string; min_qty: string; qty_step: string };

/** `state` do máy chủ tính (bảng E6, 02b §3.4.2). FE chỉ ánh xạ sang màn (features/checkout/orderState.ts). */
export type OrderState =
  | "awaiting_payment"
  | "hold_expired"
  | "expired"
  | "cancelled"
  | "preparing"
  | "delivering"
  | "delivery_failed"
  | "completed";

/** Thông báo đơn huỷ sau khi đã trả tiền (BR-HT-12). Không có tiến độ phiếu hoàn. */
export type CancelNotice = {
  scope: "full" | "partial";
  reason_code: string;
  reason_label: string;
  cancelled_amount: Money;
  message: string;
  hotline: string;
  policy_url: string;
};

export type OrderDelivery = { step: "preparing" | "delivering" | "delivered" | "failed"; step_label: string };

/** Kết quả tra đơn (`POST /api/shop/orders/lookup/`). Không có tên, SĐT hay địa chỉ người nhận. */
export type OrderLookupResult = {
  order_code: string;
  status: string;
  state: OrderState;
  status_label: string;
  placed_at: string;
  paid_at: string | null;
  delivered_at: string | null;
  booked_expires_at: string | null;
  server_now: string;
  hold_minutes: number;
  payment_pending_minutes: number;
  delivery: OrderDelivery | null;
  lines: OrderLineData[];
  subtotal: Money;
  discount: OrderDiscount;
  total_amount: Money;
  cancel_notice: CancelNotice | null;
  late_payment: boolean;
  lookup_token: string;
};

/** Tra bằng mã đơn + SĐT đầy đủ, hoặc mã đơn + mã tra đơn (có cả hai thì máy chủ dùng `token`). */
export type OrderLookupInput = { order_code: string; phone?: string; token?: string };

// Cổng thanh toán (BR-TT-01/13). Shop không tự vẽ QR, cổng lo việc đó. Không hiện tên cổng cho khách.
// Một field gửi cổng thanh toán, ĐÚNG THỨ TỰ máy chủ trả (chữ ký HMAC phụ thuộc thứ tự —
// BR-TT-13). FE không được thêm/bớt/sắp lại/đổi tên field trong mảng này.
export type PaymentGatewayField = { name: string; value: string };

// Bộ tham số lập cổng thanh toán (`POST /api/shop/orders/<order_code>/checkout/`). FE chỉ dựng
// `<form method="POST" action={checkout_url}>` với `fields` làm input ẩn, giữ nguyên thứ tự, rồi submit.
export type PaymentCheckoutSession = {
  checkout_url: string;
  fields: PaymentGatewayField[];
  environment?: "SANDBOX" | "PRODUCTION";
};

export class ApiError extends Error {
  status: number;
  code?: string;
  data?: any;
  constructor(message: string, status: number, code?: string, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.data = data;
  }
}
