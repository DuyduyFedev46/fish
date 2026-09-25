// Dữ liệu mock cho Shop — dùng khi NEXT_PUBLIC_USE_MOCK=1 hoặc khi backend chưa chạy.
// Cho phép /shop render và thao tác được (xem catalog, đặt hàng, tra cứu đơn) mà
// không cần Django API thật.

import type {
  CatalogItem,
  CatalogItemDetail,
  CreateOrderPayload,
  CreateOrderResponse,
  OrderStatus,
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

// Kho đơn hàng trong bộ nhớ (chỉ tồn tại trong tiến trình dev hiện tại) — đủ để demo
// luồng đặt hàng -> tra cứu khi chưa có backend thật.
const MOCK_ORDERS = new Map<string, OrderStatus & { phone: string; total_amount: number }>();

// Một đơn mẫu có sẵn để test tra cứu ngay mà không cần đặt hàng trước:
// mã đơn DH-DEMO001, 4 số cuối SĐT 6789
MOCK_ORDERS.set("DH-DEMO001", {
  order_code: "DH-DEMO001",
  status: "CONFIRMED",
  status_label: "Đã xác nhận thanh toán",
  phone: "0909006789",
  total_amount: 285000,
  lines: [
    { item_code: "CA-BASA-PHILE", name: "Cá basa phi lê", qty: 2, price: 65000, line_total: 130000 },
    { item_code: "TOM-SU-TUOI", name: "Tôm sú tươi", qty: 0.5, price: 220000, line_total: 110000 },
  ],
  delivery: { status: "Đang soạn hàng" },
});

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

export async function mockCreateOrder(payload: CreateOrderPayload): Promise<CreateOrderResponse> {
  let total = 0;
  const lines: OrderStatus["lines"] = [];
  for (const line of payload.items) {
    const item = MOCK_CATALOG.find((i) => i.item_code === line.item_code);
    if (!item) {
      throw new Error(`Mặt hàng không tồn tại: ${line.item_code}`);
    }
    if (line.qty > item.sellable_qty) {
      throw new Error(`Mặt hàng "${item.name}" không đủ tồn kho khả dụng`);
    }
    const lineTotal = item.price * line.qty;
    total += lineTotal;
    lines.push({
      item_code: item.item_code,
      name: item.name,
      qty: line.qty,
      price: item.price,
      line_total: lineTotal,
    });
  }

  const order_code = genOrderCode();
  const booked_expires_at = new Date(Date.now() + 30 * 60 * 1000).toISOString();

  MOCK_ORDERS.set(order_code, {
    order_code,
    status: "BOOKED",
    status_label: "Đang giữ chỗ, chờ thanh toán",
    phone: payload.phone,
    total_amount: total,
    lines,
    delivery: { status: "Chưa xác nhận thanh toán" },
  });

  return delay({
    order_code,
    total_amount: total,
    vietqr: {
      payload: `00020101021238570010A00000072701270006970436011${order_code}0208QRIBFTTA5303704540${total}5802VN6304ABCD`,
      amount: total,
      content: order_code,
    },
    booked_expires_at,
  });
}

export async function mockGetOrderStatus(
  orderCode: string,
  phoneLast4: string
): Promise<OrderStatus | null> {
  const order = MOCK_ORDERS.get(orderCode);
  if (!order) return delay(null);
  if (!order.phone.endsWith(phoneLast4)) return delay(null);
  const { phone: _phone, total_amount: _total, ...status } = order;
  return delay(status);
}
