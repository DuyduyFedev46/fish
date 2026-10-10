// Kiểu dữ liệu khớp Shop API (công khai) — xem doc/BUILD-PLAN.md, mục "Shop API (công khai)".

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

export type CreateOrderItemInput = {
  item_code: string;
  qty: number;
};

export type CreateOrderPayload = {
  customer: {
    phone: string;
    name: string;
  };
  delivery_address: string;
  phone: string;
  items: CreateOrderItemInput[];
  privacy_consent?: {
    accepted: boolean;
    policy_version_id: number;
  };
};

// Cổng thanh toán SePay (VietQR) — xem doc/features/2026-09-26-sepay-cong-thanh-toan.
// Không còn trường `vietqr` giả (BR-TT-01): Shop không tự vẽ QR, cổng SePay lo việc đó.
export type CreateOrderResponse = {
  order_code: string;
  total_amount: number;
  booked_expires_at: string; // ISO datetime — hạn giữ chỗ (BR-BH-03)
};

export type OrderLineStatus = {
  item_code: string;
  // Tra đơn thật (`ShopOrderLookupView`) CHƯA trả tên mặt hàng, chỉ `item_code` — xem
  // "còn nợ" trong 03-dev-notes.md. FE hiện tạm mã hàng khi thiếu (lib/api.ts).
  name: string;
  qty: number;
  line_total?: number;
};

export type OrderCancelNotice = {
  reason_code: string | null;
  message: string;
  refund: {
    amount: string;
    status_label: string;
    deadline: string;
    refunded_at: string | null;
  };
  contact: string;
};

export type OrderStatus = {
  order_code: string;
  status: string;
  status_label: string;
  fulfilment?: string;
  lines: OrderLineStatus[];
  total_amount: number;
  // Suy ra từ `status` ở lib/api.ts (BE trả status thô: BOOKED/PAID/PROCESSING/COMPLETED/
  // CANCELLED/AUTO_CANCELLED — xem apps/sales/models/orders.py). BE chưa có field boolean
  // riêng, FE tự map để không phải rải chuỗi trạng thái khắp UI.
  is_paid: boolean;
  is_expired: boolean;
  // CHƯA có trong response tra đơn thật hôm nay (chỉ có ở response đặt hàng) — xem "còn nợ"
  // 03-dev-notes.md. Thiếu thì FE ẩn đồng hồ đếm ngược, không suy đoán.
  booked_expires_at?: string;
  delivery?: {
    status: string;
    status_label?: string;
  };
  cancel_notice?: OrderCancelNotice | null;
};

// Một field gửi cổng thanh toán, ĐÚNG THỨ TỰ máy chủ trả (chữ ký HMAC phụ thuộc thứ tự —
// BR-TT-13). FE không được thêm/bớt/sắp lại/đổi tên field trong mảng này.
export type PaymentGatewayField = { name: string; value: string };

// Bộ tham số lập cổng thanh toán SePay (P1, BE, endpoint `POST
// /api/shop/orders/<order_code>/checkout/`). FE chỉ dựng `<form method="POST"
// action={checkout_url}>` với `fields` làm input ẩn, giữ nguyên thứ tự, rồi submit.
export type PaymentCheckoutSession = {
  checkout_url: string;
  fields: PaymentGatewayField[];
  environment?: "SANDBOX" | "PRODUCTION";
};

// ---- Kiểu "trên dây" (JSON thô Django trả — số dạng chuỗi, không có is_paid/is_expired) ----
// Khớp `ShopOrderCreateView`/`ShopOrderLookupView` (backend/apps/sales/orders/shop_api.py),
// đối chiếu theo 03-dev-notes.md mục "P5, P1, P3 (BE)". `lib/api.ts` map sang kiểu FE dùng ở
// trên; `lib/mock.ts` trả thẳng đúng kiểu này để chỉ có MỘT đường map, dùng chung cho cả
// mock lẫn API thật (đỡ lệch hai luồng).
export type WireCreateOrderResponse = {
  order_code: string;
  total_amount: string;
  booked_expires_at: string;
};

export type WireOrderLine = {
  item_code: string;
  qty: string;
  amount: string;
  // BE hôm nay CHƯA trả field này ở tra đơn — xem OrderLineStatus ở trên. Mock có trả.
  name?: string;
};

export type WireOrderStatus = {
  order_code: string;
  status: string; // BOOKED | PAID | PROCESSING | COMPLETED | CANCELLED | AUTO_CANCELLED
  status_label: string;
  fulfilment?: string;
  total_amount: string;
  lines: WireOrderLine[];
  delivery: { status: string; status_label?: string } | null;
  // BE hôm nay CHƯA trả field này ở tra đơn (chỉ có lúc đặt hàng) — xem OrderStatus ở trên.
  // Mock có trả để luồng đếm ngược chạy đủ.
  booked_expires_at?: string | null;
  cancel_notice?: OrderCancelNotice | null;
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
