// Dữ liệu mock cho Shop — dùng khi NEXT_PUBLIC_USE_MOCK=1 hoặc khi backend chưa chạy.
// Cho phép /shop render và thao tác được (xem catalog, đặt hàng, tra cứu đơn) mà
// không cần Django API thật.

import {
  ApiError,
  type BundleComponent,
  type CatalogItem,
  type CatalogItemDetail,
  type CatalogResponse,
  type CancelNotice,
  type CreateOrderPayload,
  type CreateOrderResponse,
  type InvalidQtyLine,
  type ItemImage,
  type OrderDelivery,
  type OrderDiscount,
  type OrderLookupInput,
  type OrderLookupResult,
  type OrderState,
  type OutOfStockLine,
  type PaymentCheckoutSession,
  type SaleUnit,
  type StockLevel,
} from "./types";
import { todayInVietnam } from "./format";

// Ảnh mẫu cho mock (A4) — sinh BẰNG CODE lúc chạy (SVG data URI), KHÔNG commit tệp ảnh nào vào repo
// (quy ước 2026-09-25, BR-DM-16). Đủ 3 trạng thái theo 02-stories.md: có ảnh, `image: null`, ảnh lỗi
// (data URI không giải mã được — thử khung mặc định A4-AC6 mà không phụ thuộc mạng thật).
function toBase64Utf8(text: string): string {
  if (typeof TextEncoder !== "undefined" && typeof window !== "undefined") {
    const bytes = new TextEncoder().encode(text);
    let binary = "";
    bytes.forEach((b) => (binary += String.fromCharCode(b)));
    return window.btoa(binary);
  }
  return Buffer.from(text, "utf-8").toString("base64");
}

function mockImage(bg: string, label: string, isIllustration = false): ItemImage {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480"><rect width="480" height="480" fill="${bg}"/><text x="240" y="252" font-size="44" text-anchor="middle" fill="white" font-family="sans-serif" font-weight="600">${label}</text></svg>`;
  const src = `data:image/svg+xml;base64,${toBase64Utf8(svg)}`;
  return { alt: label, is_illustration: isIllustration, urls: { thumb: src, card: src, detail: src } };
}

/** Data URI hỏng — không giải mã được, để thử khung mặc định khi ảnh lỗi (A4-AC6), không cần mạng. */
const BROKEN_IMAGE: ItemImage = {
  alt: "Tôm sú tươi",
  is_illustration: false,
  urls: {
    thumb: "data:image/webp;base64,AAAA",
    card: "data:image/webp;base64,AAAA",
    detail: "data:image/webp;base64,AAAA",
  },
};

// Seed giữ lượng bán được (`mock_stock`: kg với món lẻ, số combo với BUNDLE) CHỈ để mock tự tính
// `stock_level` và kiểm đủ hàng lúc đặt. Ra ngoài mock chỉ còn `stock_level` ("in" | "low" | "out"),
// đúng contract 02b §3.1: không có số kg tồn.
type MockSeedItem = {
  item_code: string;
  name: string;
  item_type: "SIMPLE" | "BUNDLE";
  group: { slug: string; name: string };
  price: number;
  mock_stock: number;
  image: ItemImage | null;
  bundle_components?: BundleComponent[];
};

const MOCK_LOW_STOCK = 3; // khớp mặc định SHOP_LOW_STOCK_KG / SHOP_LOW_STOCK_COMBO ở backend
const MOCK_MIN_STOCK = 1;

function stockLevelOf(stock: number): StockLevel {
  if (stock < MOCK_MIN_STOCK) return "out";
  if (stock < MOCK_LOW_STOCK) return "low";
  return "in";
}

// Ghi chú ngắn và thông tin chi tiết giả để chụp màn (02b §3.1–3.2); món không có trong bảng thì để trống.
const MOCK_TEXT: Record<string, { short_note: string; spec: string; storage: string; origin: string; description: string }> = {
  "MUC-ONG": {
    short_note: "Đã bỏ nội tạng",
    spec: "Đã làm sạch, bỏ nội tạng",
    storage: "Cấp đông, giữ ngăn đá",
    origin: "",
    description: "Mực ống thân dày, đã làm sạch sẵn, rã đông là nấu được.",
  },
  "CA-THU-KHUC": { short_note: "Cắt khúc dày 2–3 cm", spec: "", storage: "Cấp đông, giữ ngăn đá", origin: "", description: "" },
  "TOM-SU-TUOI": { short_note: "Size 30–35 con/kg", spec: "", storage: "", origin: "", description: "" },
};

function toWireItem(seed: MockSeedItem): CatalogItem {
  const isBundle = seed.item_type === "BUNDLE";
  return {
    item_code: seed.item_code,
    name: seed.name,
    item_type: seed.item_type,
    unit: isBundle ? "combo" : "kg",
    price: String(seed.price),
    stock_level: stockLevelOf(seed.mock_stock),
    min_qty: "1",
    qty_step: isBundle ? "1" : "0.5",
    group: seed.group,
    short_note: MOCK_TEXT[seed.item_code]?.short_note ?? "",
    image: seed.image,
  };
}

function toWireDetail(seed: MockSeedItem): CatalogItemDetail {
  return {
    ...toWireItem(seed),
    description: MOCK_TEXT[seed.item_code]?.description ?? "",
    spec: MOCK_TEXT[seed.item_code]?.spec ?? "",
    storage: MOCK_TEXT[seed.item_code]?.storage ?? "",
    origin: MOCK_TEXT[seed.item_code]?.origin ?? "",
    ...(seed.bundle_components ? { bundle_components: seed.bundle_components } : {}),
  };
}

const GROUP_FISH = { slug: "ca", name: "Cá" };
const GROUP_SHRIMP = { slug: "tom", name: "Tôm" };
const GROUP_SQUID = { slug: "muc", name: "Mực" };
const GROUP_CRAB = { slug: "cua-ghe", name: "Cua ghẹ" };
const GROUP_SHELLFISH = { slug: "oc-ngheu-so", name: "Ốc/Nghêu/Sò" };
const GROUP_COMBO = { slug: "combo", name: "Combo" };

const MOCK_CATALOG: MockSeedItem[] = [
  {
    item_code: "CA-BASA-PHILE",
    name: "Cá basa phi lê",
    item_type: "SIMPLE",
    group: GROUP_FISH,
    price: 65000,
    mock_stock: 120,
    image: null,
  },
  {
    item_code: "CA-THU-KHUC",
    name: "Cá thu cắt khúc",
    item_type: "SIMPLE",
    group: GROUP_FISH,
    price: 150000,
    mock_stock: 60,
    image: mockImage("rgb(10 110 140)", "Ca thu"),
  },
  {
    item_code: "TOM-SU-TUOI",
    name: "Tôm sú tươi",
    item_type: "SIMPLE",
    group: GROUP_SHRIMP,
    price: 220000,
    // Sắp hết (dưới ngưỡng 3 kg) và ảnh hỏng: thử cả nhãn "Sắp hết" lẫn khung dự phòng.
    mock_stock: 2.7,
    image: BROKEN_IMAGE,
  },
  {
    item_code: "MUC-ONG",
    name: "Mực ống",
    item_type: "SIMPLE",
    group: GROUP_SQUID,
    price: 180000,
    mock_stock: 30,
    image: null,
  },
  {
    item_code: "GHEO-BIEN",
    name: "Ghẹ biển",
    item_type: "SIMPLE",
    group: GROUP_CRAB,
    price: 240000,
    mock_stock: 20,
    // Q8 (02-stories.md): ảnh minh hoạ khi chưa có ảnh Lộc tự chụp — Shop phải ghi rõ nhãn.
    image: mockImage("rgb(168 90 7)", "Ghe bien", true),
  },
  {
    item_code: "NGHEU-TRANG",
    name: "Nghêu trắng",
    item_type: "SIMPLE",
    group: GROUP_SHELLFISH,
    price: 45000,
    mock_stock: 80,
    image: null,
  },
  {
    item_code: "CUA-HOANG-DE",
    name: "Cua hoàng đế",
    item_type: "SIMPLE",
    group: GROUP_CRAB,
    price: 950000,
    // Luôn hết hàng: ca cố định cho QA (02b §1.6).
    mock_stock: 0,
    image: null,
  },
  {
    item_code: "COMBO-HAISAN-GD",
    name: "Combo hải sản gia đình",
    item_type: "BUNDLE",
    group: GROUP_COMBO,
    price: 450000,
    mock_stock: 15,
    // A4-AC8: ảnh của COMBO, không tự lấy ảnh thành phần (dù CA-BASA-PHILE ở trên đang image:null).
    image: mockImage("rgb(21 127 61)", "Combo"),
    bundle_components: [
      { item_code: "CA-BASA-PHILE", name: "Cá basa phi lê", qty_per_bundle: "1", unit: "kg" },
      { item_code: "TOM-SU-TUOI", name: "Tôm sú tươi", qty_per_bundle: "0.5", unit: "kg" },
      { item_code: "MUC-ONG", name: "Mực ống", qty_per_bundle: "0.5", unit: "kg" },
    ],
  },
  {
    item_code: "COMBO-LAU-HAISAN",
    name: "Combo lẩu hải sản",
    item_type: "BUNDLE",
    group: GROUP_COMBO,
    price: 380000,
    // Combo sắp hết (ráp được 2 bộ, dưới ngưỡng 3).
    mock_stock: 2,
    // A4-AC8: combo chưa có ảnh riêng -> khung mặc định (không mượn ảnh Tôm sú/Mực ống/Nghêu).
    image: null,
    bundle_components: [
      { item_code: "TOM-SU-TUOI", name: "Tôm sú tươi", qty_per_bundle: "0.3", unit: "kg" },
      { item_code: "MUC-ONG", name: "Mực ống", qty_per_bundle: "0.3", unit: "kg" },
      { item_code: "NGHEU-TRANG", name: "Nghêu trắng", qty_per_bundle: "0.5", unit: "kg" },
    ],
  },
];

// Kho đơn cho mock (02b §1.6) — lưu vào localStorage vì luồng cổng thanh toán đưa khách sang một "trang khác"
// (giả lập bằng điều hướng trình duyệt thật) rồi quay về, mỗi lần như vậy nạp lại toàn bộ JS.
// SĐT KHÔNG được lưu ở đâu: chỉ lưu băm (`phone_key`), để ngay cả dữ liệu giả cũng không nằm nguyên văn trong storage.
// Đơn mẫu `SO000000-MOCK…` được dựng lại theo giờ hiện tại mỗi lần đọc, chỉ phần đã bị thay đổi (vd. vừa trả tiền) mới được lưu.
type MockOrderLine = { item_code: string; name: string; unit: SaleUnit; qty: number; amount: number };

type MockOrder = {
  order_code: string;
  phone_key: string;
  request_id: string | null;
  lines: MockOrderLine[];
  total: number;
  placed_at: number;
  hold_until: number;
  /** Thời điểm (epoch ms) mô phỏng "tiền về" — chỉ mock dùng, vẫn sống sót qua điều hướng thật. */
  pay_confirm_at: number | null;
  paid_at: number | null;
  delivered_at: number | null;
  status: "BOOKED" | "PROCESSING" | "COMPLETED" | "CANCELLED" | "AUTO_CANCELLED";
  /** Trạng thái phiếu giao (CONFIRMING…FAILED); null = chưa có phiếu. */
  delivery_code: string | null;
  cancel: { scope: "full" | "partial"; reason_code: string; amount: number } | null;
  late_payment: boolean;
  /** Số lần mở cổng thanh toán còn phải báo lỗi (ca D1 lỗi mở cổng). */
  checkout_fails: number;
};

const ORDERS_STORAGE_KEY = "cangcaloc_mock_orders_v4";
const MOCK_HOLD_MINUTES = 30;
const MOCK_PAYMENT_PENDING_MINUTES = 5;
const MOCK_HOTLINE = "0900000000";
const MIN = 60 * 1000;

/** Băm FNV-1a 32 bit: đủ để so khớp SĐT trong mock mà không lưu số thật. */
function phoneKey(phone: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < phone.length; i++) {
    h ^= phone.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16);
}

/** "+84 900 000 001" | "0900000001" -> "0900000001". */
function normalizePhone(raw: string): string {
  const digits = raw.replace(/[\s.\-()]/g, "");
  return digits.startsWith("+84") ? `0${digits.slice(3)}` : digits.startsWith("84") && digits.length === 11 ? `0${digits.slice(2)}` : digits;
}

const MOCK_SEED_PHONE_KEY = phoneKey("0900000001");

function seedLines(): MockOrderLine[] {
  return [
    { item_code: "MUC-ONG", name: "Mực ống", unit: "kg", qty: 1.5, amount: 270000 },
    { item_code: "COMBO-HAISAN-GD", name: "Combo hải sản gia đình", unit: "combo", qty: 1, amount: 450000 },
  ];
}

const SEED_SUBTOTAL = 720000;

function seedOrder(code: string, now: number, over: Partial<MockOrder>): MockOrder {
  return {
    order_code: code,
    phone_key: MOCK_SEED_PHONE_KEY,
    request_id: null,
    lines: seedLines(),
    total: SEED_SUBTOTAL,
    placed_at: now - 20 * MIN,
    hold_until: now + 10 * MIN,
    pay_confirm_at: null,
    paid_at: null,
    delivered_at: null,
    status: "BOOKED",
    delivery_code: null,
    cancel: null,
    late_payment: false,
    checkout_fails: 0,
    ...over,
  };
}

/** 12 đơn mẫu, mỗi `state` (bảng E6) một đơn; tra bằng SĐT giả 0900000001. */
function seedOrders(now: number): MockOrder[] {
  const paid = { status: "PROCESSING" as const, paid_at: now - 15 * MIN, hold_until: now + 10 * MIN };
  return [
    seedOrder("SO000000-MOCKA1", now, { placed_at: now - 6 * MIN, hold_until: now + 24 * MIN }),
    seedOrder("SO000000-MOCKA2", now, { placed_at: now - 31 * MIN, hold_until: now - 1 * MIN }),
    seedOrder("SO000000-MOCKA3", now, { status: "AUTO_CANCELLED", placed_at: now - 2 * 60 * MIN, hold_until: now - 90 * MIN }),
    seedOrder("SO000000-MOCKA4", now, {
      ...paid,
      status: "CANCELLED",
      delivery_code: "CANCELLED",
      cancel: { scope: "full", reason_code: "DAMAGED_WHEN_PACKING", amount: SEED_SUBTOTAL },
    }),
    seedOrder("SO000000-MOCKA5", now, {
      ...paid,
      status: "CANCELLED",
      delivery_code: "CANCELLED",
      cancel: { scope: "full", reason_code: "UNREACHABLE_AUTO", amount: SEED_SUBTOTAL },
    }),
    seedOrder("SO000000-MOCKA6", now, {
      status: "AUTO_CANCELLED",
      placed_at: now - 3 * 60 * MIN,
      hold_until: now - 150 * MIN,
      late_payment: true,
      cancel: { scope: "full", reason_code: "PAID_AFTER_EXPIRY", amount: SEED_SUBTOTAL },
    }),
    seedOrder("SO000000-MOCKA7", now, { ...paid, delivery_code: "CONFIRMING" }),
    seedOrder("SO000000-MOCKA8", now, { ...paid, delivery_code: "READY" }),
    seedOrder("SO000000-MOCKA9", now, { ...paid, delivery_code: "DELIVERING" }),
    seedOrder("SO000000-MOCKB1", now, { ...paid, delivery_code: "FAILED" }),
    seedOrder("SO000000-MOCKB2", now, {
      ...paid,
      status: "COMPLETED",
      delivery_code: "COMPLETED",
      delivered_at: now - 2 * 60 * MIN,
    }),
    seedOrder("SO000000-MOCKB3", now, {
      ...paid,
      delivery_code: "PREPARING",
      cancel: { scope: "partial", reason_code: "PARTIAL", amount: 270000 },
    }),
    // Đơn còn hạn nhưng mở cổng thanh toán lỗi lần đầu (câu "Chưa mở được trang thanh toán. Thử lại.").
    seedOrder("SO000000-MOCKB4", now, { placed_at: now - 4 * MIN, hold_until: now + 26 * MIN, checkout_fails: 1 }),
  ];
}

function readStoredOrders(): MockOrder[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(ORDERS_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as MockOrder[]) : [];
  } catch {
    return [];
  }
}

function writeStoredOrders(orders: MockOrder[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(ORDERS_STORAGE_KEY, JSON.stringify(orders));
  } catch {
    // localStorage không khả dụng — mock vẫn chạy trong phiên hiện tại, chỉ không sống sót qua điều hướng thật.
  }
}

/** Đơn đã lưu đè lên đơn mẫu cùng mã; đơn mẫu chưa bị đụng tới thì dựng lại theo giờ hiện tại. */
function allOrders(now: number): MockOrder[] {
  const stored = readStoredOrders();
  const storedCodes = new Set(stored.map((o) => o.order_code));
  return [...seedOrders(now).filter((o) => !storedCodes.has(o.order_code)), ...stored];
}

function saveOrder(order: MockOrder): void {
  const stored = readStoredOrders().filter((o) => o.order_code !== order.order_code);
  stored.push(order);
  writeStoredOrders(stored.slice(-30));
}

/** Xử lý "tới hạn" một cách lười, đúng như job nền thật: tiền về giả lập, hết giờ giữ hàng. Trả `true` nếu đổi. */
function settleOrder(o: MockOrder, now: number): boolean {
  let changed = false;
  if (o.status === "BOOKED" && o.pay_confirm_at != null && now >= o.pay_confirm_at) {
    o.status = "PROCESSING";
    o.paid_at = o.pay_confirm_at;
    o.pay_confirm_at = null;
    o.delivery_code = "CONFIRMING";
    changed = true;
  }
  return changed;
}

type MockState = OrderState;

function stateOf(o: MockOrder, now: number): MockState {
  if (o.status === "BOOKED") return now < o.hold_until ? "awaiting_payment" : "hold_expired";
  if (o.status === "AUTO_CANCELLED") return o.late_payment ? "cancelled" : "expired";
  if (o.status === "CANCELLED") return "cancelled";
  if (o.status === "COMPLETED") return "completed";
  if (o.delivery_code === "DELIVERING") return "delivering";
  if (o.delivery_code === "FAILED") return "delivery_failed";
  return "preparing";
}

const STATUS_LABELS: Record<string, string> = {
  awaiting_payment: "Chờ thanh toán",
  hold_expired: "Chờ thanh toán",
  expired: "Đã huỷ vì quá giờ thanh toán",
  cancelled: "Đã huỷ",
  delivering: "Đang giao",
  delivery_failed: "Giao không thành công",
  completed: "Đã giao",
};

const CANCEL_LABELS: Record<string, string> = {
  DAMAGED_WHEN_PACKING: "Hàng không đạt khi soạn",
  UNREACHABLE_AUTO: "Không liên lạc được để xác nhận đơn",
  PAID_AFTER_EXPIRY: "Hết giờ giữ hàng, tiền về sau",
  PARTIAL: "Một phần đơn không giao được",
};

function deliveryOf(code: string | null): OrderDelivery | null {
  switch (code) {
    case "CONFIRMING":
      return { step: "preparing", step_label: "Chờ vựa gọi xác nhận" };
    case "PREPARING":
      return { step: "preparing", step_label: "Đang soạn hàng" };
    case "READY":
      return { step: "preparing", step_label: "Đã soạn xong, chờ giao" };
    case "DELIVERING":
      return { step: "delivering", step_label: "Đang giao" };
    case "COMPLETED":
      return { step: "delivered", step_label: "Đã giao" };
    case "FAILED":
      return { step: "failed", step_label: "Giao chưa thành công, vựa sẽ liên hệ lại" };
    default:
      return null;
  }
}

function vndText(amount: number): string {
  return `${Math.round(amount).toLocaleString("vi-VN")}đ`;
}

function mockLookupToken(orderCode: string): string {
  return `mock-token.${typeof window !== "undefined" ? window.btoa(orderCode) : orderCode}`;
}

function toWireLookup(o: MockOrder, now: number): OrderLookupResult {
  const state = stateOf(o, now);
  const delivery = deliveryOf(o.delivery_code);
  const noDiscount: OrderDiscount = { source: null, code: null, amount: "0" };
  let cancel_notice: CancelNotice | null = null;
  if (o.cancel) {
    cancel_notice = {
      scope: o.cancel.scope,
      reason_code: o.cancel.reason_code,
      reason_label: CANCEL_LABELS[o.cancel.reason_code] ?? "Cá Về đã huỷ đơn này",
      cancelled_amount: String(o.cancel.amount),
      message: `Cá Về sẽ gọi vào số điện thoại đặt hàng trong 1 ngày làm việc để trả lại ${vndText(o.cancel.amount)}.`,
      hotline: MOCK_HOTLINE,
      policy_url: "/pages/?slug=doi-tra#xu-ly-tien",
    };
  }
  const label =
    state === "preparing"
      ? o.delivery_code === "CONFIRMING"
        ? "Đã thanh toán – chờ vựa gọi xác nhận"
        : "Đang chuẩn bị hàng"
      : STATUS_LABELS[state];
  return {
    order_code: o.order_code,
    status: o.status,
    state,
    status_label: label,
    placed_at: new Date(o.placed_at).toISOString(),
    paid_at: o.paid_at ? new Date(o.paid_at).toISOString() : null,
    delivered_at: o.delivered_at ? new Date(o.delivered_at).toISOString() : null,
    booked_expires_at: o.status === "BOOKED" ? new Date(o.hold_until).toISOString() : null,
    server_now: new Date(now).toISOString(),
    hold_minutes: MOCK_HOLD_MINUTES,
    payment_pending_minutes: MOCK_PAYMENT_PENDING_MINUTES,
    delivery: state === "cancelled" || state === "expired" || state === "hold_expired" || state === "awaiting_payment" ? null : delivery,
    lines: o.lines.map((l) => ({
      item_code: l.item_code,
      name: l.name,
      unit: l.unit,
      qty: String(l.qty),
      amount: String(l.amount),
    })),
    subtotal: String(o.lines.reduce((sum, l) => sum + l.amount, 0)),
    discount: noDiscount,
    total_amount: String(o.total),
    cancel_notice,
    late_payment: o.late_payment,
    lookup_token: mockLookupToken(o.order_code),
  };
}

function delay<T>(value: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export async function mockGetCatalog(): Promise<CatalogResponse> {
  // Thứ tự `items`: tên nhóm, rồi mã (contract 02b §3.1). `groups` chỉ gồm nhóm có món.
  const items = [...MOCK_CATALOG]
    .sort(
      (x, y) =>
        x.group.name.localeCompare(y.group.name, "vi") || x.item_code.localeCompare(y.item_code)
    )
    .map(toWireItem);
  const groups = new Map<string, { slug: string; name: string; item_count: number }>();
  for (const it of items) {
    const g = groups.get(it.group.slug);
    if (g) g.item_count += 1;
    else groups.set(it.group.slug, { ...it.group, item_count: 1 });
  }
  return delay({ groups: [...groups.values()], items });
}

export async function mockGetCatalogItem(itemCode: string): Promise<CatalogItemDetail | null> {
  const found = MOCK_CATALOG.find((i) => i.item_code === itemCode);
  return delay(found ? toWireDetail(found) : null);
}

function genOrderCode(): string {
  // Dạng SO + ngày theo giờ VN (YYMMDD) + 6 ký tự (02b §3.3), không theo múi giờ máy.
  const [y, m, d] = todayInVietnam().split("-");
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let tail = "";
  for (let i = 0; i < 6; i++) tail += alphabet[Math.floor(Math.random() * alphabet.length)];
  return `SO${y.slice(2)}${m}${d}-${tail}`;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function toWireCreate(o: MockOrder, now: number): CreateOrderResponse {
  const lookup = toWireLookup(o, now);
  return {
    order_code: o.order_code,
    status: o.status,
    subtotal: lookup.subtotal,
    discount: lookup.discount,
    total_amount: lookup.total_amount,
    booked_expires_at: new Date(o.hold_until).toISOString(),
    server_now: lookup.server_now,
    hold_minutes: MOCK_HOLD_MINUTES,
    lines: lookup.lines,
    lookup_token: lookup.lookup_token,
  };
}

/**
 * Tạo đơn giả (02b §3.3). Ca cố định cho QA: tên chứa `#timeout` (ghi đơn rồi ném lỗi mạng; gửi lại cùng
 * `client_request_id` trả đơn cũ), `#throttle` (429), `#policy` (409), `#closed` (503 Shop tạm ngưng).
 */
export async function mockCreateOrder(payload: CreateOrderPayload): Promise<CreateOrderResponse> {
  const name = payload.customer?.name ?? "";
  if (name.includes("#closed")) {
    throw new ApiError("Shop tạm chưa nhận đơn.", 503, "SHOP_CLOSED");
  }
  const fields: Record<string, string> = {};
  const phone = normalizePhone(payload.customer?.phone ?? "");
  if (!UUID_RE.test(payload.client_request_id ?? "")) fields.client_request_id = "Mã yêu cầu không hợp lệ.";
  if (!name.trim() || name.length > 100) fields.name = "Nhập họ tên người nhận";
  if (!/^0\d{9}$/.test(phone)) fields.phone = "Số điện thoại cần 10 chữ số, bắt đầu bằng 0";
  if (!payload.delivery_address?.trim() || payload.delivery_address.length > 500) {
    fields.delivery_address = "Nhập địa chỉ giao hàng hoặc chọn trên bản đồ";
  }
  if (!payload.items?.length) fields.items = "Giỏ hàng đang trống";
  if (payload.privacy_consent && payload.privacy_consent.accepted !== true) {
    fields.consent = "Đánh dấu đồng ý ở trên để đặt hàng.";
  }
  if (Object.keys(fields).length > 0) {
    throw new ApiError("Thông tin đặt hàng chưa hợp lệ.", 400, "VALIDATION", { code: "VALIDATION", fields });
  }

  const now = Date.now();
  const existing = allOrders(now).find((o) => o.request_id === payload.client_request_id);
  if (existing) return delay(toWireCreate(existing, now));

  if (name.includes("#policy")) {
    throw new ApiError("Chính sách vừa cập nhật, vui lòng xem và đồng ý lại.", 409, "POLICY_CHANGED", {
      current: { version: 4, version_id: 930, slug: "quyen-rieng-tu" },
    });
  }
  if (name.includes("#throttle")) {
    throw new ApiError("Bạn thao tác quá nhanh. Vui lòng thử lại sau 60 giây.", 429, "throttled");
  }

  // Số lượng sai bước (BR-BH-22): liệt kê mọi dòng sai.
  const invalid: InvalidQtyLine[] = [];
  for (const line of payload.items) {
    const item = MOCK_CATALOG.find((i) => i.item_code === line.item_code);
    if (!item) continue;
    const isBundle = item.item_type === "BUNDLE";
    const q = Math.round(Number(line.qty) * 1000);
    const step = isBundle ? 1000 : 500;
    if (!Number.isFinite(q) || q < 1000 || q % step !== 0) {
      invalid.push({ item_code: item.item_code, min_qty: "1", qty_step: isBundle ? "1" : "0.5" });
    }
  }
  if (invalid.length > 0) {
    throw new ApiError("Số lượng không hợp lệ.", 400, "INVALID_QTY", { code: "INVALID_QTY", lines: invalid });
  }

  // Hết hàng (BR-BH-24): chỉ trả `out` hoặc `short`, không có số kg.
  const short: OutOfStockLine[] = [];
  let total = 0;
  const lines: MockOrderLine[] = [];
  for (const line of payload.items) {
    const item = MOCK_CATALOG.find((i) => i.item_code === line.item_code);
    const qty = Number(line.qty);
    if (!item || item.mock_stock < 1) {
      short.push({ item_code: line.item_code, stock_level: "out" });
      continue;
    }
    if (qty > item.mock_stock) {
      short.push({ item_code: item.item_code, stock_level: "short" });
      continue;
    }
    const amount = Math.round(item.price * qty);
    total += amount;
    lines.push({
      item_code: item.item_code,
      name: item.name,
      unit: item.item_type === "BUNDLE" ? "combo" : "kg",
      qty,
      amount,
    });
  }
  if (short.length > 0) {
    throw new ApiError("Một số món vừa hết hàng.", 400, "OUT_OF_STOCK", { code: "OUT_OF_STOCK", lines: short });
  }

  const order: MockOrder = {
    order_code: genOrderCode(),
    phone_key: phoneKey(phone),
    request_id: payload.client_request_id,
    lines,
    total,
    placed_at: now,
    hold_until: now + MOCK_HOLD_MINUTES * MIN,
    pay_confirm_at: null,
    paid_at: null,
    delivered_at: null,
    status: "BOOKED",
    delivery_code: null,
    cancel: null,
    late_payment: false,
    checkout_fails: 0,
  };
  saveOrder(order);

  // Mất phản hồi sau khi máy chủ đã ghi đơn (C4): lần gửi lại cùng mã yêu cầu sẽ trả đơn này.
  if (name.includes("#timeout")) throw new TypeError("Failed to fetch");
  return delay(toWireCreate(order, now));
}

/** Tra đơn giả (02b §3.4). `null` = 404 một câu chung. Token `mock-expired…` -> 401 TOKEN_EXPIRED. */
export async function mockLookupOrder(input: OrderLookupInput): Promise<OrderLookupResult | null> {
  const now = Date.now();
  const code = (input.order_code ?? "").trim().toUpperCase();
  if (input.token) {
    if (input.token.startsWith("mock-expired")) {
      throw new ApiError("Phiên xem đơn đã hết hạn. Nhập số điện thoại để xem lại.", 401, "TOKEN_EXPIRED");
    }
    if (input.token !== mockLookupToken(code)) return delay(null);
  } else if (!input.phone) {
    throw new ApiError("Thông tin tra đơn chưa hợp lệ.", 400, "VALIDATION");
  }
  const record = allOrders(now).find((o) => o.order_code === code);
  if (!record) return delay(null);
  if (!input.token && phoneKey(normalizePhone(input.phone ?? "")) !== record.phone_key) return delay(null);
  if (settleOrder(record, now)) saveOrder(record);
  return delay(toWireLookup(record, now));
}

// Lập bộ tham số cổng thanh toán (BR-TT-01/13/14/17). Hình dạng `fields` (mảng có thứ tự) khớp SDK cổng
// thật. Mock KHÔNG dùng URL trong `fields` để điều hướng (static export không có route nhận POST) — xem
// `goToMockGateway` ở features/checkout/gateway.ts.
export async function mockStartCheckoutSession(orderCode: string): Promise<PaymentCheckoutSession> {
  const now = Date.now();
  const record = allOrders(now).find((o) => o.order_code === orderCode);
  if (!record) throw new ApiError("Không tìm thấy đơn.", 404, "ORDER_NOT_FOUND");
  if (record.checkout_fails > 0) {
    record.checkout_fails -= 1;
    saveOrder(record);
    throw new ApiError("Chưa mở được trang thanh toán. Thử lại.", 400, "CHECKOUT_UNAVAILABLE", {
      code: "CHECKOUT_UNAVAILABLE",
      reason: "MOCK",
    });
  }
  if (settleOrder(record, now)) saveOrder(record);
  if (stateOf(record, now) !== "awaiting_payment") {
    throw new ApiError("Chưa mở được trang thanh toán. Thử lại.", 400, "CHECKOUT_UNAVAILABLE", {
      code: "CHECKOUT_UNAVAILABLE",
      reason: "NOT_PAYABLE",
    });
  }

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const returnBase = `${origin}/shop/orders?code=${encodeURIComponent(orderCode)}`;

  return delay({
    checkout_url: "https://pay-sandbox.example.invalid/v1/checkout/init",
    environment: "SANDBOX",
    fields: [
      { name: "merchant", value: "MOCK_MERCHANT" },
      { name: "operation", value: "pay" },
      { name: "payment_method", value: "BANK_TRANSFER" },
      { name: "order_amount", value: String(record.total) },
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

// Chỉ mock dùng: giả lập "tiền sẽ về sau `delayMs`" (`null` = không bao giờ về, để thử màn chờ quá 5 phút).
// Ghi thẳng vào localStorage (không dùng setTimeout) để sống sót qua việc điều hướng thật sang trang "cổng" rồi quay về.
export function mockMarkPaymentPending(orderCode: string, delayMs: number | null): void {
  const now = Date.now();
  const record = allOrders(now).find((o) => o.order_code === orderCode);
  if (!record) return;
  record.pay_confirm_at = delayMs === null ? null : now + delayMs;
  saveOrder(record);
}
