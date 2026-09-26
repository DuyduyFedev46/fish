// Dữ liệu mock cho Shop — dùng khi NEXT_PUBLIC_USE_MOCK=1 hoặc khi backend chưa chạy.
// Cho phép /shop render và thao tác được (xem catalog, đặt hàng, tra cứu đơn) mà
// không cần Django API thật.

import {
  ApiError,
  type CatalogItem,
  type CatalogItemDetail,
  type CreateOrderPayload,
  type PaymentCheckoutSession,
  type WireCreateOrderResponse,
  type WireOrderStatus,
} from "./types";

const MOCK_CATALOG: CatalogItemDetail[] = [
  {
    item_code: "CA-BASA-PHILE",
    name: "Cá basa phi lê",
    group: "Cá",
    item_type: "SIMPLE",
    unit: "Kg",
    price: 65000,
    sellable_qty: 120,
  },
  {
    item_code: "CA-THU-KHUC",
    name: "Cá thu cắt khúc",
    group: "Cá",
    item_type: "SIMPLE",
    unit: "Kg",
    price: 150000,
    sellable_qty: 60,
  },
  {
    item_code: "TOM-SU-TUOI",
    name: "Tôm sú tươi",
    group: "Tôm",
    item_type: "SIMPLE",
    unit: "Kg",
    price: 220000,
    sellable_qty: 45,
  },
  {
    item_code: "MUC-ONG",
    name: "Mực ống",
    group: "Mực",
    item_type: "SIMPLE",
    unit: "Kg",
    price: 180000,
    sellable_qty: 30,
  },
  {
    item_code: "GHEO-BIEN",
    name: "Ghẹ biển",
    group: "Cua ghẹ",
    item_type: "SIMPLE",
    unit: "Kg",
    price: 240000,
    sellable_qty: 20,
  },
  {
    item_code: "NGHEU-TRANG",
    name: "Nghêu trắng",
    group: "Ốc/Nghêu/Sò",
    item_type: "SIMPLE",
    unit: "Kg",
    price: 45000,
    sellable_qty: 80,
  },
  {
    item_code: "COMBO-HAISAN-GD",
    name: "Combo hải sản gia đình",
    group: "Combo",
    item_type: "BUNDLE",
    unit: "Kg",
    price: 450000,
    sellable_qty: 15,
    bundle_components: [
      { item_code: "CA-BASA-PHILE", name: "Cá basa phi lê", qty_per_bundle: 1 },
      { item_code: "TOM-SU-TUOI", name: "Tôm sú tươi", qty_per_bundle: 0.5 },
      { item_code: "MUC-ONG", name: "Mực ống", qty_per_bundle: 0.5 },
    ],
  },
  {
    item_code: "COMBO-LAU-HAISAN",
    name: "Combo lẩu hải sản",
    group: "Combo",
    item_type: "BUNDLE",
    unit: "Kg",
    price: 380000,
    sellable_qty: 10,
    bundle_components: [
      { item_code: "TOM-SU-TUOI", name: "Tôm sú tươi", qty_per_bundle: 0.3 },
      { item_code: "MUC-ONG", name: "Mực ống", qty_per_bundle: 0.3 },
      { item_code: "NGHEU-TRANG", name: "Nghêu trắng", qty_per_bundle: 0.5 },
    ],
  },
];

// Kho đơn hàng cho mock — lưu vào localStorage (không phải Map thuần trong bộ nhớ), vì
// luồng thanh toán SePay (P4) đưa khách sang một "trang khác" (giả lập bằng điều hướng
// trình duyệt thật, `window.location.href`) rồi quay về: mỗi lần điều hướng như vậy nạp
// lại toàn bộ JS, một Map trong bộ nhớ sẽ mất trắng. localStorage sống qua việc đó.
type MockOrderLine = { item_code: string; name: string; qty: number; amount: number };

type MockOrderRecord = {
  order_code: string;
  phone: string;
  total_amount: number;
  lines: MockOrderLine[];
  is_paid: boolean;
  is_expired: boolean;
  booked_expires_at: string | null;
  // Thời điểm (epoch ms) mô phỏng "IPN đến" — chỉ mock dùng, để giả lập độ trễ xác nhận
  // thanh toán mà vẫn sống sót qua một lượt điều hướng thật (xem mockMarkPaymentPending).
  pay_confirmed_at: number | null;
  status_label: string;
  delivery_status: string;
};

const ORDERS_STORAGE_KEY = "cangcaloc_mock_orders_v1";

function nowIso(minutesFromNow: number): string {
  return new Date(Date.now() + minutesFromNow * 60 * 1000).toISOString();
}

function seedDemoOrders(): Map<string, MockOrderRecord> {
  const orders = new Map<string, MockOrderRecord>();
  // Đơn mẫu 1: đã thanh toán — test tra cứu ngay (mã DH-DEMO001, 4 số cuối SĐT 6789).
  orders.set("DH-DEMO001", {
    order_code: "DH-DEMO001",
    phone: "0909006789",
    total_amount: 285000,
    lines: [
      { item_code: "CA-BASA-PHILE", name: "Cá basa phi lê", qty: 2, amount: 130000 },
      { item_code: "TOM-SU-TUOI", name: "Tôm sú tươi", qty: 0.5, amount: 110000 },
    ],
    is_paid: true,
    is_expired: false,
    booked_expires_at: null,
    pay_confirmed_at: null,
    status_label: "Đã thanh toán, đang soạn hàng",
    delivery_status: "Đang soạn hàng",
  });
  // Đơn mẫu 2: đang giữ chỗ, còn hạn — test màn "chưa thanh toán, còn mm:ss" + thanh toán lại
  // (mã DH-DEMO002, 4 số cuối SĐT 1234).
  orders.set("DH-DEMO002", {
    order_code: "DH-DEMO002",
    phone: "0912341234",
    total_amount: 180000,
    lines: [{ item_code: "MUC-ONG", name: "Mực ống", qty: 1, amount: 180000 }],
    is_paid: false,
    is_expired: false,
    booked_expires_at: nowIso(12),
    pay_confirmed_at: null,
    status_label: "Đang giữ chỗ, chờ thanh toán",
    delivery_status: "Chưa xác nhận thanh toán",
  });
  // Đơn mẫu 3: đã hết hạn giữ chỗ — test màn "hết hạn, mời đặt lại" (mã DH-DEMO003, SĐT 4321).
  orders.set("DH-DEMO003", {
    order_code: "DH-DEMO003",
    phone: "0909994321",
    total_amount: 90000,
    lines: [{ item_code: "NGHEU-TRANG", name: "Nghêu trắng", qty: 2, amount: 90000 }],
    is_paid: false,
    is_expired: true,
    booked_expires_at: null,
    pay_confirmed_at: null,
    status_label: "Đơn đã hết hạn giữ hàng",
    delivery_status: "Đã huỷ (hết hạn giữ chỗ)",
  });
  return orders;
}

function loadOrders(): Map<string, MockOrderRecord> {
  if (typeof window === "undefined") return seedDemoOrders();
  try {
    const raw = window.localStorage.getItem(ORDERS_STORAGE_KEY);
    if (!raw) {
      const seeded = seedDemoOrders();
      saveOrders(seeded);
      return seeded;
    }
    const entries: [string, MockOrderRecord][] = JSON.parse(raw);
    return new Map(entries);
  } catch {
    return seedDemoOrders();
  }
}

function saveOrders(orders: Map<string, MockOrderRecord>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      ORDERS_STORAGE_KEY,
      JSON.stringify(Array.from(orders.entries()))
    );
  } catch {
    // localStorage không khả dụng — mock vẫn chạy được trong phiên hiện tại, chỉ không
    // sống sót qua điều hướng thật.
  }
}

// Xử lý "tới hạn" một cách lười: mỗi lần đọc một đơn, kiểm xem TTL đã qua chưa, hoặc
// "IPN giả lập" đã tới giờ chưa, rồi cập nhật đúng như job nền thật sẽ làm.
function resolveMockOrder(record: MockOrderRecord): { record: MockOrderRecord; changed: boolean } {
  const now = Date.now();
  let changed = false;

  if (!record.is_paid && record.pay_confirmed_at != null && now >= record.pay_confirmed_at) {
    record.is_paid = true;
    record.is_expired = false;
    record.pay_confirmed_at = null;
    record.booked_expires_at = null;
    record.status_label = "Đã thanh toán, đang soạn hàng";
    record.delivery_status = "Đang soạn hàng";
    changed = true;
  }

  if (
    !record.is_paid &&
    !record.is_expired &&
    record.booked_expires_at &&
    now >= new Date(record.booked_expires_at).getTime()
  ) {
    record.is_expired = true;
    record.booked_expires_at = null;
    record.pay_confirmed_at = null;
    record.status_label = "Đơn đã hết hạn giữ hàng";
    record.delivery_status = "Đã huỷ (hết hạn giữ chỗ)";
    changed = true;
  }

  return { record, changed };
}

// Trả đúng KIỂU TRÊN DÂY (số dạng chuỗi, không có is_paid/is_expired) — giống hệt cấu trúc
// `ShopOrderLookupView` thật trả, để `lib/api.ts` dùng chung một hàm map cho cả mock lẫn
// API thật. Khác BE thật ở 2 chỗ (có ghi chú rõ): mock trả thêm `name` mỗi dòng và
// `booked_expires_at` — BE thật hôm nay chưa có 2 field này ở tra đơn (xem lib/types.ts).
function toWireOrderStatus(record: MockOrderRecord): WireOrderStatus {
  return {
    order_code: record.order_code,
    status: record.is_paid ? "PROCESSING" : record.is_expired ? "AUTO_CANCELLED" : "BOOKED",
    status_label: record.status_label,
    total_amount: String(record.total_amount),
    lines: record.lines.map((l) => ({
      item_code: l.item_code,
      name: l.name,
      qty: String(l.qty),
      amount: String(l.amount),
    })),
    delivery: { status: record.delivery_status },
    ...(record.booked_expires_at ? { booked_expires_at: record.booked_expires_at } : {}),
  };
}

function delay<T>(value: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export async function mockGetCatalog(): Promise<CatalogItem[]> {
  return delay(
    MOCK_CATALOG.map(({ bundle_components: _bc, ...rest }) => rest)
  );
}

export async function mockGetCatalogItem(itemCode: string): Promise<CatalogItemDetail | null> {
  const found = MOCK_CATALOG.find((i) => i.item_code === itemCode);
  return delay(found ?? null);
}

function genOrderCode(): string {
  const now = new Date();
  const y = now.getFullYear().toString().slice(2);
  const m = (now.getMonth() + 1).toString().padStart(2, "0");
  const d = now.getDate().toString().padStart(2, "0");
  const rand = Math.floor(1000 + Math.random() * 9000);
  return `DH-${y}${m}${d}-${rand}`;
}

export async function mockCreateOrder(
  payload: CreateOrderPayload
): Promise<WireCreateOrderResponse> {
  let total = 0;
  const lines: MockOrderLine[] = [];
  for (const line of payload.items) {
    const item = MOCK_CATALOG.find((i) => i.item_code === line.item_code);
    if (!item) {
      throw new Error(`Mặt hàng không tồn tại: ${line.item_code}`);
    }
    if (line.qty > item.sellable_qty) {
      throw new Error(`Mặt hàng "${item.name}" không đủ tồn kho khả dụng`);
    }
    // Làm tròn nguyên đồng (BR-BH-15, story P5) để số gửi cổng khớp số trên hoá đơn.
    const lineAmount = Math.round(item.price * line.qty);
    total += lineAmount;
    lines.push({
      item_code: item.item_code,
      name: item.name,
      qty: line.qty,
      amount: lineAmount,
    });
  }

  const order_code = genOrderCode();
  const booked_expires_at = nowIso(30);

  const orders = loadOrders();
  orders.set(order_code, {
    order_code,
    phone: payload.phone,
    total_amount: total,
    lines,
    is_paid: false,
    is_expired: false,
    booked_expires_at,
    pay_confirmed_at: null,
    status_label: "Đang giữ chỗ, chờ thanh toán",
    delivery_status: "Chưa xác nhận thanh toán",
  });
  saveOrders(orders);

  return delay({
    order_code,
    total_amount: String(total),
    booked_expires_at,
  });
}

export async function mockGetOrderStatus(
  orderCode: string,
  phoneLast4: string
): Promise<WireOrderStatus | null> {
  const orders = loadOrders();
  const record = orders.get(orderCode);
  if (!record) return delay(null);
  if (!record.phone.endsWith(phoneLast4)) return delay(null);

  const { record: resolved, changed } = resolveMockOrder(record);
  if (changed) {
    orders.set(orderCode, resolved);
    saveOrders(orders);
  }
  return delay(toWireOrderStatus(resolved));
}

// Lập bộ tham số thanh toán cổng — giả lập BR-TT-01/13/14/17 (story P1). Hình dạng
// `fields` (mảng có thứ tự) khớp SDK SePay thật theo ghi chú điều phối 2026-09-26: merchant,
// operation, payment_method, order_amount, currency, order_invoice_number, order_description,
// success_url, error_url, cancel_url, signature. Mock KHÔNG dùng URL trong `fields` để điều
// hướng thật (static export không có route nhận POST) — xem `goToMockGateway` ở
// features/checkout/gateway.ts, dùng riêng cho nhánh mock.
export async function mockStartCheckoutSession(
  orderCode: string
): Promise<PaymentCheckoutSession> {
  const orders = loadOrders();
  const record = orders.get(orderCode);
  if (!record) {
    throw new ApiError("Không tìm thấy đơn.", 404);
  }

  const { record: resolved, changed } = resolveMockOrder(record);
  if (changed) {
    orders.set(orderCode, resolved);
    saveOrders(orders);
  }

  if (resolved.is_paid) {
    throw new ApiError("Đơn đã thanh toán.", 400);
  }
  if (resolved.is_expired || !resolved.booked_expires_at) {
    throw new ApiError("Đơn đã hết hạn giữ hàng, vui lòng đặt lại.", 400);
  }

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const returnBase = `${origin}/shop/orders?code=${encodeURIComponent(orderCode)}`;

  return delay({
    checkout_url: "https://pay-sandbox.sepay.vn/v1/checkout/init",
    environment: "SANDBOX",
    fields: [
      { name: "merchant", value: "MOCK_MERCHANT" },
      { name: "operation", value: "pay" },
      { name: "payment_method", value: "BANK_TRANSFER" },
      { name: "order_amount", value: String(resolved.total_amount) },
      { name: "currency", value: "VND" },
      { name: "order_invoice_number", value: orderCode },
      { name: "order_description", value: `Thanh toan don hang ${orderCode}` },
      { name: "success_url", value: `${returnBase}&result=success` },
      { name: "error_url", value: `${returnBase}&result=error` },
      { name: "cancel_url", value: `${returnBase}&result=cancel` },
      { name: "signature", value: "mock-signature-khong-dung-that" },
    ],
  });
}

// Chỉ mock dùng: giả lập "IPN sẽ đến sau `delayMs`". Ghi thẳng vào localStorage (không
// dùng setTimeout) để sống sót qua việc điều hướng thật sang trang "cổng" rồi quay về.
export function mockMarkPaymentPending(orderCode: string, delayMs: number): void {
  const orders = loadOrders();
  const record = orders.get(orderCode);
  if (!record) return;
  record.pay_confirmed_at = Date.now() + delayMs;
  orders.set(orderCode, record);
  saveOrders(orders);
}
