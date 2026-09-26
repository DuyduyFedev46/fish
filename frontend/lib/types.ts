// Kiểu dữ liệu khớp Shop API (công khai) — xem doc/BUILD-PLAN.md, mục "Shop API (công khai)".

export type ItemType = "SIMPLE" | "BUNDLE";

export type CatalogItem = {
  item_code: string;
  name: string;
  group: string;
  item_type: ItemType;
  unit: "Kg";
  price: number;
  sellable_qty: number;
};

export type BundleComponent = {
  item_code: string;
  name: string;
  qty_per_bundle: number;
};

export type CatalogItemDetail = CatalogItem & {
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

export type OrderStatus = {
  order_code: string;
  status: string;
  status_label: string;
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
  };
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
  total_amount: string;
  lines: WireOrderLine[];
  delivery: { status: string } | null;
  // BE hôm nay CHƯA trả field này ở tra đơn (chỉ có lúc đặt hàng) — xem OrderStatus ở trên.
  // Mock có trả để luồng đếm ngược chạy đủ.
  booked_expires_at?: string | null;
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}
