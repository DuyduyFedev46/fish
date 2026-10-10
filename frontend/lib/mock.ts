// Dữ liệu mock cho Shop — dùng khi NEXT_PUBLIC_USE_MOCK=1 hoặc khi backend chưa chạy.
// Cho phép /shop render và thao tác được (xem catalog, đặt hàng, tra cứu đơn) mà
// không cần Django API thật.

import {
  ApiError,
  type BundleComponent,
  type CatalogItem,
  type CatalogItemDetail,
  type CatalogResponse,
  type CreateOrderPayload,
  type ItemImage,
  type OrderCancelNotice,
  type PaymentCheckoutSession,
  type StockLevel,
  type WireCreateOrderResponse,
  type WireOrderStatus,
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
  /** Mã trạng thái phiếu giao (CONFIRMING…CANCELLED); null = chưa có phiếu giao (đơn chưa thanh toán). */
  delivery_code: string | null;
  cancel_notice?: OrderCancelNotice | null;
};

const ORDERS_STORAGE_KEY = "cangcaloc_mock_orders_v3";

// Nhãn Shop của phiếu giao (T24–T30, chưa duyệt, dùng tạm) — khớp bảng BE ở 02b-tech-design.md mục 2.4.
// Khách không bao giờ thấy mã thô; mã lạ → "Đang cập nhật".
const DELIVERY_LABELS: Record<string, string> = {
  CONFIRMING: "Chờ vựa gọi xác nhận",
  PREPARING: "Đang soạn hàng",
  READY: "Đã soạn xong, chờ giao",
  DELIVERING: "Đang giao",
  COMPLETED: "Đã giao",
  FAILED: "Giao chưa thành công, vựa sẽ liên hệ lại",
  CANCELLED: "Đã huỷ",
};
// Nhãn đơn của khách theo bảng 02b §2.6 (W37 S8, mục 4 thuật ngữ đã duyệt): đơn đã trả tiền chỉ có ba nhãn, ứng với phiếu giao.
// Đơn Hoàn tất (phiếu Đã giao) hiện "Hoàn tất"; chưa giao xong hiện "Đang xử lý"; phiếu còn chờ gọi xác nhận có câu riêng.
const PAID_ORDER_LABELS = {
  confirming: "Đã thanh toán – chờ vựa gọi xác nhận",
  processing: "Đang xử lý",
  completed: "Hoàn tất",
} as const;
const deliveryLabelOf = (code: string): string => DELIVERY_LABELS[code] ?? "Đang cập nhật";

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
    delivery_code: "PREPARING",
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
    status_label: "Chờ thanh toán",
    delivery_code: null,
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
    status_label: "Đã huỷ vì quá giờ thanh toán",
    delivery_code: "CANCELLED",
  });
  // Đơn mẫu 4: CS-10 tự huỷ do không liên lạc được kèm hoàn tiền (mã DH-DEMO004, SĐT 5678).
  orders.set("DH-DEMO004", {
    order_code: "DH-DEMO004",
    phone: "0901235678",
    total_amount: 540000,
    lines: [{ item_code: "TOM-SU-TUOI", name: "Tôm sú tươi", qty: 2, amount: 540000 }],
    is_paid: false,
    is_expired: false,
    booked_expires_at: null,
    pay_confirmed_at: null,
    status_label: "Đã huỷ",
    delivery_code: "CANCELLED",
    cancel_notice: {
      reason_code: "UNREACHABLE_AUTO",
      // # CHỜ legal-vn: câu thông báo tự huỷ do không liên lạc được
      message:
        "Cá Về đã gọi số điện thoại đặt hàng 3 lần trong 30 phút nhưng không liên lạc được, nên đơn được huỷ tự động để hoàn tiền cho quý khách.",
      refund: {
        amount: "540000",
        status_label: "Đang chờ hoàn tiền",
        deadline: "2026-10-28",
        refunded_at: null,
      },
      contact: "1900 6868",
    },
  });
  // Đơn mẫu 5–9: một đơn cho mỗi trạng thái phiếu giao còn lại (E2: Shop tra đơn không lộ mã thô).
  const extra: Array<[string, string, string, string]> = [
    ["DH-DEMO005", "0909005001", "CONFIRMING", PAID_ORDER_LABELS.confirming],
    ["DH-DEMO006", "0909005002", "READY", PAID_ORDER_LABELS.processing],
    ["DH-DEMO007", "0909005003", "DELIVERING", PAID_ORDER_LABELS.processing],
    // W37 S8-AC6: đơn Hoàn tất — badge "Hoàn tất", dòng phiếu "Đã giao" (status COMPLETED suy từ phiếu ở toWireOrderStatus).
    ["DH-DEMO008", "0909005004", "COMPLETED", PAID_ORDER_LABELS.completed],
    ["DH-DEMO009", "0909005005", "FAILED", PAID_ORDER_LABELS.processing],
  ];
  for (const [order_code, phone, delivery_code, status_label] of extra) {
    orders.set(order_code, {
      order_code,
      phone,
      total_amount: 120000,
      lines: [{ item_code: "MUC-ONG", name: "Mực ống", qty: 0.5, amount: 120000 }],
      is_paid: true,
      is_expired: false,
      booked_expires_at: null,
      pay_confirmed_at: null,
      status_label,
      delivery_code,
    });
  }
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
    record.delivery_code = "PREPARING";
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
    record.status_label = "Đã huỷ vì quá giờ thanh toán";
    record.delivery_code = "CANCELLED";
    changed = true;
  }

  return { record, changed };
}

// Trả đúng KIỂU TRÊN DÂY (số dạng chuỗi, không có is_paid/is_expired) — giống hệt cấu trúc
// `ShopOrderLookupView` thật trả, để `lib/api.ts` dùng chung một hàm map cho cả mock lẫn
// API thật. Khác BE thật ở 2 chỗ (có ghi chú rõ): mock trả thêm `name` mỗi dòng và
// `booked_expires_at` — BE thật hôm nay chưa có 2 field này ở tra đơn (xem lib/types.ts).
function toWireOrderStatus(record: MockOrderRecord): WireOrderStatus {
  const fulfilment =
    (record.delivery_code === "CANCELLED" && !record.is_expired)
      ? "CANCELLED"
      : record.is_paid
      ? "CONFIRMING"
      : record.is_expired
      ? "CANCELLED"
      : "BOOKED";

  return {
    order_code: record.order_code,
    status: record.is_paid ? (record.delivery_code === "COMPLETED" ? "COMPLETED" : "PROCESSING") : record.is_expired ? "AUTO_CANCELLED" : record.cancel_notice ? "CANCELLED" : "BOOKED",
    status_label: record.status_label,
    fulfilment,
    total_amount: String(record.total_amount),
    lines: record.lines.map((l) => ({
      item_code: l.item_code,
      name: l.name,
      qty: String(l.qty),
      amount: String(l.amount),
    })),
    delivery: record.delivery_code ? { status: record.delivery_code, status_label: deliveryLabelOf(record.delivery_code) } : null,
    cancel_notice: record.cancel_notice ?? null,
    ...(record.booked_expires_at ? { booked_expires_at: record.booked_expires_at } : {}),
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
  // Ngày theo giờ VN (SR-25 AC4), không theo múi giờ máy.
  const [y, m, d] = todayInVietnam().split("-");
  const rand = Math.floor(1000 + Math.random() * 9000);
  return `DH-${y.slice(2)}${m}${d}-${rand}`;
}

export async function mockCreateOrder(
  payload: CreateOrderPayload
): Promise<WireCreateOrderResponse> {
  // Giả lập cho QA kiểm thử các case đặc biệt (GL-03)
  if (payload.customer?.name === "MOCK_409") {
    throw new ApiError("Chính sách vừa cập nhật, vui lòng xem và đồng ý lại.", 409, "POLICY_CHANGED", {
      current: { version: 4, version_id: 930, slug: "chinh-sach-bao-mat" },
    });
  }
  if (payload.customer?.name === "MOCK_503") {
    throw new ApiError("Shop tạm chưa nhận đơn.", 503, "BR-BH-17");
  }
  if (payload.privacy_consent && payload.privacy_consent.accepted !== true) {
    throw new ApiError("Vui lòng đồng ý chính sách xử lý dữ liệu cá nhân.", 400, "BR-BH-17");
  }

  let total = 0;
  const lines: MockOrderLine[] = [];
  for (const line of payload.items) {
    const item = MOCK_CATALOG.find((i) => i.item_code === line.item_code);
    if (!item) {
      throw new Error(`Mặt hàng không tồn tại: ${line.item_code}`);
    }
    if (line.qty > item.mock_stock) {
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
    status_label: "Chờ thanh toán",
    delivery_code: null,
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
