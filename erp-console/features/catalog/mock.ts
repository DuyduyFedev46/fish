// Mock module catalog — CHỈ chạy khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Dựng JSON theo contract THỰC TẾ BE R14 (backend/apps/catalog/items, pricing) + A2 (ảnh mặt hàng):
//   GET   /api/catalog/items/?item_group=&is_active=&item_type=&has_image=&page=   (8 dòng/trang ở mock để luyện "Tải thêm")
//   GET   /api/catalog/items/{id}/    POST /items/    PATCH /items/{id}/    POST /items/{id}/image/
//   POST  /api/catalog/bundle-lines/
//   GET   /api/catalog/item-prices/?item=<id>      POST /item-prices/
//   GET   /api/catalog/price-lists/                GET/POST /pricing-rules/    PATCH /pricing-rules/{id}/
//   GET   /api/catalog/item-groups/                POST /item-groups/
//   GET   /api/guidance/item/{id}/                 (chỉ phần `timeline`)
//
// Luật mock (mô phỏng BE, FE KHÔNG dùng lại các luật này):
//  - Xem mặt hàng/nhóm cần catalog.view_item / view_itemgroup. Giá, bảng giá, ưu đãi cần view_itemprice / view_pricelist /
//    view_pricingrule (NV kho không có → 403). Mọi ghi chỉ Chủ có (add/change_*); Quản lý chỉ xem.
//  - `current_price` chỉ có key khi người xem có view_itemprice; chưa có giá hiệu lực = null.
//  - Đặt giá (BR-DM-03): đóng giá đang hiệu lực ở ngày liền trước `valid_from`; chồng lấn giá bắt đầu cùng ngày hoặc muộn hơn
//    → 400 BR-DM-03; đóng giá cũ làm mất đuôi → 400 BR-DM-03. Giá <= 0 → 400 {rate}. Đến ngày < từ ngày → 400 {valid_upto}.
//    Chế độ "priceUsed": mọi lần đặt giá nhận 400 PRICE_USED_BY_ORDERS (giá đã áp vào đơn) với câu của BE.
//  - Ưu đãi theo mặt hàng cần mặt hàng + số kg tối thiểu; theo đơn cần giá trị đơn tối thiểu; mức giảm > 0, phần trăm <= 100.
//  - Nhóm hàng trùng tên → 400 {name:["Tên này đã có."]}. Mã mặt hàng trùng → 400 {code:[…]}. Combo thành phần không được là combo.
//  - Không có DELETE (405).
//
// Dữ liệu CHỈ nằm trong bộ nhớ trang (mất khi tải lại), không có dữ liệu cá nhân. Công cụ thử trong DevTools (chỉ có ở mock):
//   window.__caveMock.catalog("ok" | "fail" | "empty" | "forbidden" | "detailfail" | "savefail" | "priceUsed" | "pricesfail")
//   — chế độ; lưu localStorage (chỉ tên chế độ), giữ qua tải lại.   window.__caveMock.resetCatalog() — về dữ liệu seed.
//
// Cách thử lỗi khi tải ảnh (đặt TÊN TỆP khi chọn file, không phân biệt hoa/thường):
//   - tên chứa "loi-luu-tru"  -> 503 BR-DM-16 (kho ảnh lỗi, A2-AC11)
//   - tên chứa "mat-mang"     -> mô phỏng rớt mạng giữa chừng (A2-AC12): trả status 0, không có body
// Cách thử 409 (A2-AC13, "ghi đè"): gõ đúng chữ TEST_CONFLICT vào ô "Mô tả ảnh (alt text)".
// Định dạng/dung lượng/độ phân giải được KIỂM THẬT trên tệp đã chọn (đọc byte đầu để biết JPEG/PNG/WebP thật).
// Ảnh mẫu sinh BẰNG CODE lúc chạy (SVG data URI) — KHÔNG commit tệp ảnh nào vào repo (BR-DM-16).

import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import type { Me } from "@/features/auth/types";
import type { GuidanceData, GuidanceTimelineEntry } from "@/features/guidance/types";
import { beError } from "@/shared/lib/beErrors.mock";
import { dateKeyInVietnam, todayInVietnam, vnd } from "@/shared/lib/format";
import type { MockRequest, MockResponse, Paginated } from "@/shared/lib/http";
import { fold } from "@/shared/lib/search";
import { addDays } from "./catalogModel";
import { CATALOG_PERM as P } from "./permissions";
import type {
  BundleLine,
  CatalogItem,
  CatalogItemImage,
  ImageWarning,
  ItemGroup,
  ItemPrice,
  PriceList,
  PricingRule,
  UploadImageResponse,
} from "./types";

const MAX_BYTES = 10 * 1024 * 1024; // ITEM_IMAGE_MAX_BYTES mặc định (02-stories.md)
const MIN_SIDE_WARN = 600; // ITEM_IMAGE_MIN_SIDE_WARN mặc định
const MODE_KEY = "cave_erp_mock_catalog_mode";
// PAGE_SIZE thấp CỐ Ý (không phải 50 như BE thật) để "Tải thêm" luyện được ngay cả với seed nhỏ.
const PAGE_SIZE = 8;

type Mode = "ok" | "fail" | "empty" | "forbidden" | "detailfail" | "savefail" | "priceUsed" | "pricesfail";
const MODES: readonly Mode[] = ["fail", "empty", "forbidden", "detailfail", "savefail", "priceUsed", "pricesfail"];
function mode(): Mode {
  try {
    const v = typeof window === "undefined" ? null : window.localStorage.getItem(MODE_KEY);
    return MODES.includes(v as Mode) ? (v as Mode) : "ok";
  } catch {
    return "ok";
  }
}

const has = (me: Me, p: string) => me.permissions.includes(p);
const err = (status: number, code: string, detail: string): MockResponse => ({ status, body: { detail, code } });
const FORBIDDEN = err(403, "FORBIDDEN", "Bạn không được cấp quyền để thực hiện hành động này.");
const NOT_FOUND = err(404, "NOT_FOUND", "Không tìm thấy.");
const SERVER_ERROR = err(500, "SERVER_ERROR", "Máy chủ đang bận. Thử lại sau.");
const NOT_ALLOWED = err(405, "METHOD_NOT_ALLOWED", "Phương thức không được chấp nhận.");

const RATE_MESSAGE = "Giá bán phải lớn hơn 0. Hãy nhập lại giá bán.";
const MIN_QTY_MESSAGE = "Số kg tối thiểu phải lớn hơn 0. Hãy nhập lại số kg tối thiểu.";
const DISCOUNT_VALUE_MESSAGE = "Mức giảm phải lớn hơn 0. Hãy nhập lại mức giảm.";
const REQUIRED = "Trường này không được để trống.";
const PRICE_USED_MESSAGE =
  "Giá này đã áp vào đơn hàng, không sửa được. Hãy đặt giá mới bắt đầu từ ngày mai. Muốn ngừng bán ngay thì tạm ẩn mặt hàng.";

// ---------------------------------------------------------------- dữ liệu mẫu

type AuditEntry = { at: string; kind: string; label: string; by: string };
type StoredItem = Omit<CatalogItem, "current_price" | "bundle_lines" | "group_name"> & { audit: AuditEntry[] };
type StoredLine = Omit<BundleLine, "component_code" | "component_name">;
type Store = {
  items: StoredItem[];
  lines: StoredLine[];
  groups: Omit<ItemGroup, "parent_name" | "item_count">[];
  priceLists: PriceList[];
  prices: Omit<ItemPrice, "item_name" | "item_code">[];
  rules: Omit<PricingRule, "item_name">[];
};

/** btoa() chỉ nhận Latin-1 — chữ có dấu tiếng Việt (vd "Ghẹ") cần mã hoá UTF-8 trước. */
function toBase64Utf8(text: string): string {
  if (typeof TextEncoder !== "undefined" && typeof window !== "undefined") {
    const bytes = new TextEncoder().encode(text);
    let binary = "";
    bytes.forEach((b) => (binary += String.fromCharCode(b)));
    return window.btoa(binary);
  }
  return Buffer.from(text, "utf-8").toString("base64");
}

function svgDataUri(background: string, label: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240"><rect width="240" height="240" fill="${background}"/><text x="120" y="128" font-size="26" text-anchor="middle" fill="white" font-family="sans-serif" font-weight="600">${label}</text></svg>`;
  return `data:image/svg+xml;base64,${toBase64Utf8(svg)}`;
}

function urlsOf(src: string): { thumb: string; card: string; detail: string } {
  return { thumb: src, card: src, detail: src };
}

/** Data URI hỏng (không phải ảnh thật, giải mã lỗi ngay, không cần mạng) — để thử khung mặc định khi ảnh lỗi. */
const BROKEN_URLS = urlsOf("data:image/webp;base64,AAAAAAAAAAAAAAAAAAAAAAAA");

/** Ngày thuần theo giờ VN, cách hôm nay `days` ngày (âm = quá khứ). */
function dayOffset(days: number): string {
  return dateKeyInVietnam(new Date(Date.now() + days * 86_400_000));
}
function dayBefore(isoDate: string): string {
  return addDays(isoDate, -1);
}
function agoIso(days: number, hour = 9): string {
  const d = new Date(Date.now() - days * 86_400_000);
  d.setUTCHours(hour - 7, 0, 0, 0);
  return d.toISOString();
}

function seed(): Store {
  const item = (
    id: number,
    code: string,
    name: string,
    group: number,
    type: "SIMPLE" | "BUNDLE",
    active: boolean,
    image: CatalogItemImage | null,
    description = "",
  ): StoredItem => ({
    id,
    code,
    name,
    item_group: group,
    item_type: type,
    stock_uom: "Kg",
    shelf_life_in_days: type === "BUNDLE" ? 3 : 5,
    has_batch_no: true,
    has_expiry_date: true,
    is_active: active,
    description,
    image,
    audit: [{ at: agoIso(60 - id), kind: "item_created", label: "Tạo mặt hàng", by: "Lộc" }],
  });
  const items: StoredItem[] = [
    item(1, "CA-THU", "Cá thu cắt khúc", 3, "SIMPLE", true, {
      id: "img_seed_cathu",
      alt: "Cá thu cắt khúc",
      is_illustration: false,
      urls: urlsOf(svgDataUri("royalblue", "Cá thu")),
      uploaded_at: "2026-09-20T08:10:00+07:00",
    }),
    item(2, "CA-BASA", "Cá basa phi lê", 3, "SIMPLE", true, null),
    item(3, "TOM-SU", "Tôm sú tươi", 5, "SIMPLE", true, {
      id: "img_seed_tomsu",
      alt: "",
      is_illustration: true,
      urls: BROKEN_URLS,
      uploaded_at: "2026-09-18T09:00:00+07:00",
    }),
    item(4, "MUC-ONG", "Mực ống", 6, "SIMPLE", true, null),
    item(5, "GHEO-BIEN", "Ghẹ biển", 7, "SIMPLE", false, {
      id: "img_seed_gheo",
      alt: "Ghẹ biển",
      is_illustration: false,
      urls: urlsOf(svgDataUri("seagreen", "Ghẹ")),
      uploaded_at: "2026-09-10T07:30:00+07:00",
    }),
    item(6, "COMBO-LAU", "Combo lẩu hải sản", 9, "BUNDLE", true, null, "Tôm, mực, cá thu cho nồi lẩu 3–4 người"),
    item(7, "CA-CHEM", "Cá chẽm phi lê", 3, "SIMPLE", true, null),
    item(8, "MUC-LA", "Mực lá Phan Thiết", 6, "SIMPLE", true, null),
    item(9, "TOM-THE", "Tôm thẻ", 5, "SIMPLE", true, null),
    item(10, "BACH-TUOC", "Bạch tuộc tươi", 6, "SIMPLE", true, null),
    item(11, "CUA-CM", "Cua Cà Mau", 7, "SIMPLE", true, null),
  ];
  const lines: StoredLine[] = [
    { id: 1, bundle: 6, component: 3, qty_per_bundle: "0.300" },
    { id: 2, bundle: 6, component: 4, qty_per_bundle: "0.300" },
    { id: 3, bundle: 6, component: 1, qty_per_bundle: "0.400" },
  ];
  const groups = [
    { id: 1, name: "Hải sản tươi", parent: null },
    { id: 3, name: "Cá", parent: 1 },
    { id: 5, name: "Tôm", parent: 1 },
    { id: 6, name: "Mực", parent: 1 },
    { id: 7, name: "Cua ghẹ", parent: 1 },
    { id: 9, name: "Combo", parent: null },
  ];
  const priceLists: PriceList[] = [{ id: 1, name: "Bảng giá bán lẻ", currency: "VND", is_default: true }];
  let priceId = 0;
  const price = (item: number, rate: number, from: number, upto: number | null) => ({
    id: ++priceId,
    price_list: 1,
    item,
    rate: `${rate}.00`,
    valid_from: dayOffset(from),
    valid_upto: upto === null ? null : dayOffset(upto),
  });
  const prices = [
    price(1, 205000, -90, -31),
    price(1, 220000, -30, null),
    price(2, 95000, -45, null),
    price(3, 380000, -20, null),
    price(5, 310000, -100, null),
    price(6, 480000, -48, -33),
    price(6, 450000, -32, -19),
    price(6, 420000, -18, null),
    price(7, 185000, -12, null),
    price(8, 150000, -12, null),
    price(9, 260000, -12, null),
    price(10, 175000, -12, null),
    price(11, 420000, -12, null),
  ];
  const rules: Store["rules"] = [
    {
      id: 1, name: "Mua từ 5 kg cá thu giảm 5%", is_active: true, apply_on: "ITEM", item: 1, min_qty: "5.000", min_amount: null,
      discount_type: "PERCENT", discount_value: "5.00", valid_from: dayOffset(-10), valid_upto: dayOffset(20),
    },
    {
      id: 2, name: `Đơn từ ${vnd(500000)} giảm ${vnd(20000)}`, is_active: true, apply_on: "ORDER", item: null, min_qty: null, min_amount: "500000.00",
      discount_type: "AMOUNT", discount_value: "20000.00", valid_from: null, valid_upto: null,
    },
    {
      id: 3, name: "Khuyến mãi cuối tuần cũ", is_active: false, apply_on: "ITEM", item: 3, min_qty: "3.000", min_amount: null,
      discount_type: "AMOUNT", discount_value: "10000.00", valid_from: dayOffset(-60), valid_upto: dayOffset(-30),
    },
  ];
  return { items, lines, groups, priceLists, prices, rules };
}

let STORE: Store | null = null;
const store = (): Store => (STORE ??= seed());

// ---------------------------------------------------------------- hiển thị

const groupName = (id: number) => store().groups.find((g) => g.id === id)?.name ?? "";
const itemById = (id: number) => store().items.find((i) => i.id === id);

/** Giá hiệu lực hôm nay: bảng mặc định, bắt đầu muộn nhất (BR-DM-02). */
function currentPrice(itemId: number): CatalogItem["current_price"] {
  const today = todayInVietnam();
  const live = store()
    .prices.filter((p) => p.item === itemId && p.valid_from <= today && (p.valid_upto === null || p.valid_upto >= today))
    .sort((a, b) => b.valid_from.localeCompare(a.valid_from) || b.id - a.id);
  const top = live[0];
  return top ? { rate: top.rate, valid_from: top.valid_from, valid_upto: top.valid_upto } : null;
}

function viewItem(it: StoredItem, me: Me): CatalogItem {
  const { audit: _audit, ...rest } = it;
  const lines: BundleLine[] = store()
    .lines.filter((l) => l.bundle === it.id)
    .map((l) => ({ ...l, component_code: itemById(l.component)?.code ?? "", component_name: itemById(l.component)?.name ?? "" }));
  const out: CatalogItem = { ...rest, group_name: groupName(it.item_group), bundle_lines: lines };
  if (has(me, P.viewItemPrice)) out.current_price = currentPrice(it.id);
  return out;
}

function viewGroup(g: Store["groups"][number]): ItemGroup {
  return {
    ...g,
    parent_name: g.parent ? groupName(g.parent) : null,
    item_count: store().items.filter((i) => i.item_group === g.id).length,
  };
}

function viewPrice(p: Store["prices"][number]): ItemPrice {
  const it = itemById(p.item);
  return { ...p, item_name: it?.name ?? "", item_code: it?.code ?? "" };
}

function viewRule(r: Store["rules"][number]): PricingRule {
  return { ...r, item_name: r.item ? (itemById(r.item)?.name ?? null) : null };
}

function paged<T>(rows: T[], query: URLSearchParams, size: number): Paginated<T> {
  const page = Math.max(1, Number(query.get("page")) || 1);
  return {
    count: rows.length,
    next: page * size < rows.length ? `?page=${page + 1}` : null,
    previous: page > 1 ? `?page=${page - 1}` : null,
    results: rows.slice((page - 1) * size, page * size),
  };
}

function bodyOf(req: MockRequest): Record<string, unknown> {
  const raw = req.body;
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return {};
    }
  }
  return raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
}

const text = (v: unknown) => (typeof v === "string" ? v.trim() : "");
const numberOf = (v: unknown): number | null => {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};
const dateOf = (v: unknown): string | null => (typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : null);

function audit(it: StoredItem, kind: string, label: string, me: Me) {
  it.audit.push({ at: new Date().toISOString(), kind, label, by: me.display_name });
}

function filterError(name: string): MockResponse {
  return err(400, "INVALID_FILTER", `Tham số ${name} phải là 1 hoặc 0.`);
}

const boolFilter = (raw: string | null): boolean | null | "bad" => {
  const v = (raw || "").trim().toLowerCase();
  if (!v) return null;
  if (["1", "true", "yes"].includes(v)) return true;
  if (["0", "false", "no"].includes(v)) return false;
  return "bad";
};

// ---------------------------------------------------------------- mặt hàng

function listItems(me: Me, query: URLSearchParams): MockResponse {
  const m = mode();
  if (m === "fail") return SERVER_ERROR;
  const active = boolFilter(query.get("is_active"));
  const hasImage = boolFilter(query.get("has_image"));
  if (active === "bad") return filterError("is_active");
  if (hasImage === "bad") return filterError("has_image");
  const type = (query.get("item_type") || "").trim();
  if (type && type !== "SIMPLE" && type !== "BUNDLE") return err(400, "INVALID_FILTER", "Tham số item_type có giá trị không hợp lệ.");
  const group = (query.get("item_group") || "").trim();
  let rows = m === "empty" ? [] : [...store().items];
  if (group) rows = rows.filter((i) => String(i.item_group) === group);
  if (active !== null) rows = rows.filter((i) => i.is_active === active);
  if (hasImage !== null) rows = rows.filter((i) => (i.image !== null) === hasImage);
  if (type) rows = rows.filter((i) => i.item_type === type);
  rows.sort((a, b) => a.code.localeCompare(b.code));
  const body = paged(rows.map((i) => viewItem(i, me)), query, PAGE_SIZE);
  return { status: 200, body };
}

function validateItem(body: Record<string, unknown>, partial: boolean, selfId: number | null): MockResponse | null {
  const f: Record<string, string[]> = {};
  if (!partial || "code" in body) {
    const code = text(body.code);
    if (!code) f.code = [REQUIRED];
    else if (code.length > 40) f.code = ["Đảm bảo trường này có không quá 40 ký tự."];
    else if (store().items.some((i) => i.id !== selfId && fold(i.code) === fold(code))) f.code = ["Mã này đã được dùng cho một mặt hàng khác."];
  }
  if (!partial || "name" in body) {
    const name = text(body.name);
    if (!name) f.name = [REQUIRED];
    else if (name.length > 200) f.name = ["Đảm bảo trường này có không quá 200 ký tự."];
  }
  if (!partial) {
    if (!store().groups.some((g) => g.id === numberOf(body.item_group))) f.item_group = ["Chọn nhóm hàng."];
    if (body.item_type !== "SIMPLE" && body.item_type !== "BUNDLE") f.item_type = ["Giá trị không hợp lệ."];
  }
  if ("shelf_life_in_days" in body) {
    const n = numberOf(body.shelf_life_in_days);
    if (n === null || n < 0 || !Number.isInteger(n)) f.shelf_life_in_days = ["Nhập số ngày là số nguyên không âm."];
  }
  if ("is_active" in body && typeof body.is_active !== "boolean") f.is_active = ["Giá trị không hợp lệ."];
  return Object.keys(f).length ? { status: 400, body: f } : null;
}

function itemsRoutes(me: Me, req: MockRequest, pathname: string, query: URLSearchParams): MockResponse | null {
  if (!has(me, P.viewItem) || mode() === "forbidden") return FORBIDDEN;
  if (pathname === "/api/catalog/items/") {
    if (req.method === "POST") {
      if (!has(me, P.addItem)) return FORBIDDEN;
      if (mode() === "savefail") return SERVER_ERROR;
      const body = bodyOf(req);
      const bad = validateItem(body, false, null);
      if (bad) return bad;
      const id = Math.max(0, ...store().items.map((i) => i.id)) + 1;
      const it: StoredItem = {
        id,
        code: text(body.code),
        name: text(body.name),
        item_group: Number(body.item_group),
        item_type: body.item_type === "BUNDLE" ? "BUNDLE" : "SIMPLE",
        stock_uom: "Kg",
        shelf_life_in_days: numberOf(body.shelf_life_in_days) ?? 365,
        has_batch_no: body.has_batch_no !== false,
        has_expiry_date: body.has_expiry_date !== false,
        is_active: body.is_active !== false,
        description: typeof body.description === "string" ? body.description : "",
        image: null,
        audit: [],
      };
      audit(it, "item_created", "Tạo mặt hàng", me);
      store().items.push(it);
      return { status: 201, body: viewItem(it, me) };
    }
    if (req.method !== "GET") return NOT_ALLOWED;
    return listItems(me, query);
  }
  const one = /^\/api\/catalog\/items\/(\d+)\/$/.exec(pathname);
  if (!one) return null;
  const it = itemById(Number(one[1]));
  if (req.method === "PATCH") {
    if (!has(me, P.changeItem)) return FORBIDDEN;
    if (!it) return NOT_FOUND;
    if (mode() === "savefail") return SERVER_ERROR;
    const body = bodyOf(req);
    const bad = validateItem(body, true, it.id);
    if (bad) return bad;
    if (typeof body.name === "string" && text(body.name) !== it.name) {
      it.name = text(body.name);
      audit(it, "item_updated", "Đổi tên mặt hàng", me);
    }
    if (typeof body.description === "string" && body.description !== it.description) {
      it.description = body.description;
      audit(it, "item_updated", "Sửa mô tả mặt hàng", me);
    }
    if (typeof body.is_active === "boolean" && body.is_active !== it.is_active) {
      it.is_active = body.is_active;
      audit(it, "item_updated", body.is_active ? "Hiện lại trên Shop" : "Ẩn khỏi Shop", me);
    }
    return { status: 200, body: viewItem(it, me) };
  }
  if (req.method !== "GET") return NOT_ALLOWED;
  if (mode() === "detailfail") return SERVER_ERROR;
  return it ? { status: 200, body: viewItem(it, me) } : NOT_FOUND;
}

function bundleLineRoute(me: Me, req: MockRequest): MockResponse {
  if (req.method !== "POST") return NOT_ALLOWED;
  if (!has(me, P.addBundleLine)) return FORBIDDEN;
  if (mode() === "savefail") return SERVER_ERROR;
  const body = bodyOf(req);
  const bundle = itemById(Number(body.bundle));
  const component = itemById(Number(body.component));
  const f: Record<string, string[]> = {};
  if (!bundle || bundle.item_type !== "BUNDLE") f.bundle = ["Chỉ mặt hàng loại BUNDLE mới có công thức."];
  if (!component) f.component = ["Chọn thành phần."];
  else if (component.item_type === "BUNDLE") f.component = ["Thành phần không được là combo."];
  else if (store().lines.some((l) => l.bundle === Number(body.bundle) && l.component === component.id)) f.component = ["Thành phần này đã có trong công thức."];
  const qty = numberOf(body.qty_per_bundle);
  if (qty === null || qty < 0.001) f.qty_per_bundle = ["Định mức phải từ 0,001 kg trở lên."];
  if (Object.keys(f).length || !bundle || !component || qty === null) return { status: 400, body: f };
  const line: StoredLine = {
    id: Math.max(0, ...store().lines.map((l) => l.id)) + 1,
    bundle: bundle.id,
    component: component.id,
    qty_per_bundle: qty.toFixed(3),
  };
  store().lines.push(line);
  return { status: 201, body: { ...line, component_code: component.code, component_name: component.name } satisfies BundleLine };
}

function timelineRoute(id: number): MockResponse {
  const it = itemById(id);
  if (!it) return NOT_FOUND;
  const entries: GuidanceTimelineEntry[] = it.audit.map((a) => ({
    at: a.at,
    kind: a.kind,
    label: a.label,
    doc: "item",
    actor: { kind: "user", display: a.by },
  }));
  const data: GuidanceData = {
    doc: { type: "item", id: it.id, code: it.code, status: null, status_label: null },
    next_steps: [],
    warnings: [],
    timeline: entries.sort((a, b) => Date.parse(a.at) - Date.parse(b.at)).slice(-50),
    related: [],
  };
  return { status: 200, body: data };
}

// ---------------------------------------------------------------- nhóm hàng

function groupRoutes(me: Me, req: MockRequest, query: URLSearchParams): MockResponse {
  if (!has(me, P.viewItemGroup) || mode() === "forbidden") return FORBIDDEN;
  if (req.method === "POST") {
    if (!has(me, P.addItemGroup)) return FORBIDDEN;
    if (mode() === "savefail") return SERVER_ERROR;
    const body = bodyOf(req);
    const name = text(body.name);
    const parent = numberOf(body.parent);
    const f: Record<string, string[]> = {};
    if (!name) f.name = [REQUIRED];
    else if (name.length > 120) f.name = ["Đảm bảo trường này có không quá 120 ký tự."];
    else if (store().groups.some((g) => fold(g.name) === fold(name))) f.name = ["Tên này đã có."];
    if (parent !== null && !store().groups.some((g) => g.id === parent)) f.parent = ["Nhóm cha không tồn tại."];
    if (Object.keys(f).length) return { status: 400, body: f };
    const g = { id: Math.max(0, ...store().groups.map((x) => x.id)) + 1, name, parent };
    store().groups.push(g);
    return { status: 201, body: viewGroup(g) };
  }
  if (req.method !== "GET") return NOT_ALLOWED;
  if (mode() === "fail") return SERVER_ERROR;
  const rows = mode() === "empty" ? [] : [...store().groups].sort((a, b) => a.name.localeCompare(b.name, "vi"));
  return { status: 200, body: paged(rows.map(viewGroup), query, 50) };
}

// ---------------------------------------------------------------- giá và ưu đãi

function overlaps(aFrom: string, aUpto: string | null, bFrom: string, bUpto: string | null): boolean {
  return (bUpto === null || aFrom <= bUpto) && (aUpto === null || bFrom <= aUpto);
}

function setPrice(me: Me, req: MockRequest): MockResponse {
  if (!has(me, P.addItemPrice)) return FORBIDDEN;
  if (mode() === "savefail") return SERVER_ERROR;
  const body = bodyOf(req);
  const itemId = numberOf(body.item);
  const listId = numberOf(body.price_list);
  const rate = numberOf(body.rate);
  const from = dateOf(body.valid_from);
  const upto = body.valid_upto === null || body.valid_upto === "" || body.valid_upto === undefined ? null : dateOf(body.valid_upto);
  const f: Record<string, string[]> = {};
  if (itemId === null || !itemById(itemId)) f.item = ["Chọn mặt hàng."];
  if (listId === null || !store().priceLists.some((l) => l.id === listId)) f.price_list = ["Chọn bảng giá."];
  if (rate === null || rate <= 0) f.rate = [RATE_MESSAGE];
  if (!from) f.valid_from = ["Chọn ngày bắt đầu."];
  if (body.valid_upto && !upto) f.valid_upto = ["Ngày không hợp lệ."];
  if (from && upto && upto < from) f.valid_upto = ["Ngày kết thúc phải sau hoặc bằng ngày bắt đầu. Hãy chọn lại ngày kết thúc."];
  if (Object.keys(f).length || itemId === null || listId === null || rate === null || !from) return { status: 400, body: f };

  const mine = store().prices.filter((p) => p.item === itemId && p.price_list === listId);
  const toClose: typeof mine = [];
  for (const other of mine) {
    if (!overlaps(from, upto, other.valid_from, other.valid_upto)) continue;
    if (other.valid_from >= from) {
      return err(
        400,
        "BR-DM-03",
        "Khoảng hiệu lực chồng lấn với một giá đã có của mặt hàng này (BR-DM-03). Chọn ngày bắt đầu sau ngày bắt đầu của giá đang áp dụng, hoặc sửa giá hiện có.",
      );
    }
    if (upto !== null && (other.valid_upto === null || other.valid_upto > upto)) {
      return err(
        400,
        "BR-DM-03",
        'Giá đang áp dụng còn hiệu lực sau ngày kết thúc bạn chọn, nếu đặt thì sau ngày đó mặt hàng không còn giá (BR-DM-03). Hãy để trống "đến ngày", hoặc chọn ngày kết thúc không ngắn hơn giá đang áp dụng.',
      );
    }
    toClose.push(other);
  }
  if (mode() === "priceUsed") return err(400, "PRICE_USED_BY_ORDERS", PRICE_USED_MESSAGE);
  const created = {
    id: Math.max(0, ...store().prices.map((p) => p.id)) + 1,
    price_list: listId,
    item: itemId,
    rate: rate.toFixed(2),
    valid_from: from,
    valid_upto: upto,
  };
  for (const old of toClose) old.valid_upto = dayBefore(from);
  store().prices.push(created);
  const it = itemById(itemId);
  if (it) audit(it, "price_set", `Đặt giá ${vnd(rate)}`, me);
  return { status: 201, body: viewPrice(created) };
}

function priceRoutes(me: Me, req: MockRequest, query: URLSearchParams): MockResponse {
  if (!has(me, P.viewItemPrice) || mode() === "forbidden") return FORBIDDEN;
  if (req.method === "POST") return setPrice(me, req);
  if (req.method !== "GET") return NOT_ALLOWED;
  if (mode() === "pricesfail" || mode() === "fail") return SERVER_ERROR;
  const item = (query.get("item") || "").trim();
  let rows = [...store().prices];
  if (item) rows = rows.filter((p) => String(p.item) === item);
  rows.sort((a, b) => b.valid_from.localeCompare(a.valid_from) || b.id - a.id);
  return { status: 200, body: paged(rows.map(viewPrice), query, 50) };
}

function validateRule(body: Record<string, unknown>): { fields: Record<string, string[]>; ok: PricingRule | null } {
  const f: Record<string, string[]> = {};
  const name = text(body.name);
  if (!name) f.name = [REQUIRED];
  const applyOn = body.apply_on === "ORDER" ? "ORDER" : body.apply_on === "ITEM" ? "ITEM" : null;
  if (!applyOn) f.apply_on = ["Giá trị không hợp lệ."];
  const item = numberOf(body.item);
  const minQty = numberOf(body.min_qty);
  const minAmount = numberOf(body.min_amount);
  const value = numberOf(body.discount_value);
  const type = body.discount_type === "PERCENT" ? "PERCENT" : body.discount_type === "AMOUNT" ? "AMOUNT" : null;
  if (!type) f.discount_type = ["Giá trị không hợp lệ."];
  const from = body.valid_from ? dateOf(body.valid_from) : null;
  const upto = body.valid_upto ? dateOf(body.valid_upto) : null;
  if (from && upto && upto < from) f.valid_upto = ["Ngày kết thúc phải sau hoặc bằng ngày bắt đầu. Hãy chọn lại ngày kết thúc."];
  if (applyOn === "ITEM") {
    if (item === null || !itemById(item)) f.item = ["Ưu đãi theo mặt hàng phải chọn mặt hàng."];
    if (minQty === null) f.min_qty = ["Nhập số kg tối thiểu cho ưu đãi theo mặt hàng."];
  } else if (applyOn === "ORDER" && minAmount === null) {
    f.min_amount = ["Nhập giá trị đơn tối thiểu cho ưu đãi theo đơn."];
  }
  if (minQty !== null && minQty <= 0) f.min_qty = [MIN_QTY_MESSAGE];
  if (value === null) f.discount_value = [REQUIRED];
  else if (value <= 0) f.discount_value = [DISCOUNT_VALUE_MESSAGE];
  else if (type === "PERCENT" && value > 100) f.discount_value = ["Phần trăm giảm không được lớn hơn 100. Hãy nhập lại từ 0 đến 100."];
  if (Object.keys(f).length || !applyOn || !type || value === null) return { fields: f, ok: null };
  return {
    fields: f,
    ok: {
      id: 0,
      name,
      is_active: body.is_active !== false,
      apply_on: applyOn,
      item: applyOn === "ITEM" ? item : null,
      item_name: null,
      min_qty: applyOn === "ITEM" && minQty !== null ? minQty.toFixed(3) : null,
      min_amount: applyOn === "ORDER" && minAmount !== null ? minAmount.toFixed(2) : null,
      discount_type: type,
      discount_value: value.toFixed(2),
      valid_from: from,
      valid_upto: upto,
    },
  };
}

function ruleRoutes(me: Me, req: MockRequest, pathname: string, query: URLSearchParams): MockResponse {
  if (!has(me, P.viewPricingRule) || mode() === "forbidden") return FORBIDDEN;
  const one = /^\/api\/catalog\/pricing-rules\/(\d+)\/$/.exec(pathname);
  if (req.method === "POST" && !one) {
    if (!has(me, P.addPricingRule)) return FORBIDDEN;
    if (mode() === "savefail") return SERVER_ERROR;
    const { fields, ok } = validateRule(bodyOf(req));
    if (!ok) return { status: 400, body: fields };
    const rule = { ...ok, id: Math.max(0, ...store().rules.map((r) => r.id)) + 1 };
    const { item_name: _name, ...stored } = rule;
    store().rules.push(stored);
    return { status: 201, body: viewRule(stored) };
  }
  if (req.method === "PATCH" && one) {
    if (!has(me, P.changePricingRule)) return FORBIDDEN;
    const rule = store().rules.find((r) => r.id === Number(one[1]));
    if (!rule) return NOT_FOUND;
    if (mode() === "savefail") return SERVER_ERROR;
    const body = bodyOf(req);
    if (typeof body.is_active === "boolean") rule.is_active = body.is_active;
    return { status: 200, body: viewRule(rule) };
  }
  if (req.method !== "GET") return NOT_ALLOWED;
  if (mode() === "fail") return SERVER_ERROR;
  const active = boolFilter(query.get("is_active"));
  if (active === "bad") return filterError("is_active");
  const applyOn = (query.get("apply_on") || "").trim();
  if (applyOn && applyOn !== "ITEM" && applyOn !== "ORDER") return err(400, "INVALID_FILTER", "Tham số apply_on có giá trị không hợp lệ.");
  let rows = mode() === "empty" ? [] : [...store().rules];
  if (active !== null) rows = rows.filter((r) => r.is_active === active);
  if (applyOn) rows = rows.filter((r) => r.apply_on === applyOn);
  return { status: 200, body: paged(rows.map(viewRule), query, 50) };
}

function priceListRoutes(me: Me, req: MockRequest): MockResponse {
  if (!has(me, P.viewPriceList) || mode() === "forbidden") return FORBIDDEN;
  if (req.method !== "GET") return NOT_ALLOWED;
  return { status: 200, body: { count: store().priceLists.length, next: null, previous: null, results: store().priceLists } };
}

export function mockCatalogApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const [pathname, qs = ""] = req.path.split("?");
  const query = new URLSearchParams(qs);

  const guide = /^\/api\/guidance\/item\/(\d+)\/$/.exec(pathname);
  if (guide) return has(me, P.viewItem) ? timelineRoute(Number(guide[1])) : FORBIDDEN;
  if (pathname === "/api/catalog/bundle-lines/") return bundleLineRoute(me, req);
  if (pathname === "/api/catalog/item-groups/") return groupRoutes(me, req, query);
  if (pathname === "/api/catalog/price-lists/") return priceListRoutes(me, req);
  if (pathname === "/api/catalog/item-prices/") return priceRoutes(me, req, query);
  if (pathname === "/api/catalog/pricing-rules/" || /^\/api\/catalog\/pricing-rules\/\d+\/$/.test(pathname)) return ruleRoutes(me, req, pathname, query);
  const hit = itemsRoutes(me, req, pathname, query);
  return hit ?? err(404, "NOT_FOUND", "Không tìm thấy endpoint.");
}

// ---------------------------------------------------------------- tải ảnh (A2)

// Kiểm nội dung tệp: đọc byte đầu để biết JPEG/PNG/WebP THẬT (bắt được .txt đổi đuôi .jpg).
async function sniffImageFormat(file: File): Promise<boolean> {
  try {
    const head = new Uint8Array(await file.slice(0, 16).arrayBuffer());
    if (head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff) return true; // JPEG
    if (head[0] === 0x89 && head[1] === 0x50 && head[2] === 0x4e && head[3] === 0x47) return true; // PNG
    if (
      head[0] === 0x52 && head[1] === 0x49 && head[2] === 0x46 && head[3] === 0x46 &&
      head[8] === 0x57 && head[9] === 0x45 && head[10] === 0x42 && head[11] === 0x50
    ) return true; // WebP (RIFF....WEBP)
    return false;
  } catch {
    return false;
  }
}

/** Kích thước thật của ảnh đã chọn — best effort, không chặn luồng nếu trình duyệt không hỗ trợ. */
async function readImageSize(file: File): Promise<{ width: number; height: number } | null> {
  try {
    if (typeof createImageBitmap === "function") {
      const bmp = await createImageBitmap(file);
      const size = { width: bmp.width, height: bmp.height };
      bmp.close?.();
      return size;
    }
  } catch {
    /* không đọc được (định dạng lạ) — bỏ qua cảnh báo kích thước */
  }
  return null;
}

function genImageId(): string {
  return `img_${Math.random().toString(36).slice(2, 10)}`;
}

// ---- POST /api/catalog/items/{id}/image/ ----
export async function mockUploadImage(req: MockRequest): Promise<MockResponse> {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!has(me, P.changeItemImage)) return beError("CATALOG_IMAGE_FORBIDDEN");

  const m = /\/api\/catalog\/items\/(\d+)\/image\/?/.exec(req.path);
  const item = m ? itemById(Number(m[1])) : undefined;
  if (!item) return beError("CATALOG_ITEM_NOT_FOUND");

  const fd = req.body;
  if (!(fd instanceof FormData)) return beError("CATALOG_IMAGE_MISSING_FILE");
  const file = fd.get("file");
  if (!(file instanceof File) || file.size === 0) return beError("CATALOG_IMAGE_MISSING_FILE");

  const altText = String(fd.get("alt_text") ?? "");
  const isIllustration = fd.get("is_illustration") === "true";
  const expectedImageId = String(fd.get("expected_image_id") ?? "");

  // Mã thử lỗi qua tên tệp (xem ghi chú đầu file).
  const lowerName = file.name.toLowerCase();
  if (lowerName.includes("loi-luu-tru")) return beError("CATALOG_IMAGE_STORAGE_ERROR");
  if (lowerName.includes("mat-mang")) return { status: 0, body: null };

  if (altText.length > 125) return beError("CATALOG_IMAGE_ALT_TOO_LONG");
  if (file.size > MAX_BYTES) return beError("CATALOG_IMAGE_TOO_LARGE");
  if (!(await sniffImageFormat(file))) return beError("CATALOG_IMAGE_BAD_FORMAT");

  // A2-AC13: xung đột ghi đè — mã thử qua alt text (không mô phỏng 2 phiên trình duyệt thật được).
  const currentImageId = item.image?.id ?? "";
  if (altText.trim() === "TEST_CONFLICT" || expectedImageId !== currentImageId) {
    return beError("CATALOG_IMAGE_CONFLICT");
  }

  const warnings: ImageWarning[] = [];
  const size = await readImageSize(file);
  if (size && Math.min(size.width, size.height) < MIN_SIDE_WARN) {
    warnings.push({ code: "LOW_RESOLUTION", message: "Ảnh nhỏ hơn 600 px, trên Shop có thể bị mờ." });
  }

  // Xem trước ngay bằng blob URL của tệp thật vừa chọn (chỉ sống trong phiên trình duyệt — đủ cho mock).
  const wasEmpty = !item.image;
  const image: CatalogItemImage = {
    id: genImageId(),
    alt: altText.trim() || item.name,
    is_illustration: isIllustration,
    urls: urlsOf(URL.createObjectURL(file)),
    uploaded_at: new Date().toISOString(),
  };
  item.image = image;
  audit(item, "image_uploaded", wasEmpty ? "Thêm ảnh mặt hàng" : "Thay ảnh mặt hàng", me);

  const body: UploadImageResponse = {
    item_id: item.id,
    item_code: item.code,
    image: { ...image, uploaded_by: me.display_name || me.username },
    warnings,
  };
  return { status: wasEmpty ? 201 : 200, body };
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    catalog: (m: Mode) => {
      window.localStorage.setItem(MODE_KEY, m);
      return `Danh mục (mock): chế độ ${m}`;
    },
    resetCatalog: () => {
      STORE = null;
      window.localStorage.removeItem(MODE_KEY);
      return "Đã về danh mục seed.";
    },
  };
}
