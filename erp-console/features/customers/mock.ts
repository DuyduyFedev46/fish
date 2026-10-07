// Mock module Khách hàng (ED-14) — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Dựng JSON theo contract THỰC TẾ BE Lô 6 / B2 (03-dev-notes.md "Lô 6 — BE (B2)"):
//   POST  /api/sales/customer-directory/search/               thân {q, ordering, page} (Lô bổ sung A #11: từ khoá không nằm trong URL)
//   GET   /api/sales/customer-directory/?q=&ordering=&page=   (còn để tương thích; 20 dòng/trang, DRF {count,next,previous,results})
//   GET   /api/sales/customer-directory/{id}/                 (thêm default_address, created_at, first_order_at, orders[50], refunds[50])
//   PATCH /api/sales/customer-directory/{id}/                 name / phone / default_address / note (chuỗi)
//   GET   /api/guidance/customer/{id}/                        chỉ phần `timeline` (cùng quyền xem danh bạ)
//
// Luật mock (mô phỏng BE, FE KHÔNG dùng lại các luật này):
//  - GET cần sales.view_customer_list (thiếu → 403 TRƯỚC khi tra bản ghi); PATCH cần thêm sales.change_customer.
//  - `q` khớp tên bỏ dấu, hoặc SĐT khi có từ 4 chữ số trở lên (BE không dò danh bạ bằng "0", "09").
//  - `ordering` chỉ nhận last_order_at · order_count · total_spent · name · created_at (có thể thêm "-"); mặc định -last_order_at,
//    khách chưa có đơn xếp cuối. Khoá lạ → quay về mặc định (như BE).
//  - total_spent = tổng đơn KHÔNG huỷ, trừ phiếu hoàn tiền REFUNDED của các đơn đó (đơn đã huỷ loại cả khoản hoàn). cancelled_count = đơn huỷ + tự huỷ.
//  - PATCH: thân rỗng → 400 INPUT_EMPTY; khoá khác → 400 INPUT_NOT_ALLOWED; không phải chuỗi / quá dài → 400 {field:[...]}.
//    phone: chuẩn hoá (+84/84 → 0), sai dạng → 400 INVALID_PHONE, trùng khách khác → 400 CUSTOMER_PHONE_TAKEN (câu lỗi không lặp lại số).
//
// Dữ liệu CHỈ nằm trong bộ nhớ trang (mất khi tải lại): không ghi tên/SĐT/địa chỉ vào localStorage/sessionStorage (bất biến 9),
// kể cả dữ liệu giả, để e2e quét storage được sạch. Tên giả "Khách Thử A…", SĐT giả 0900000xxx.
// Công cụ thử trong DevTools (chỉ có ở mock):
//   window.__caveMock.customers("ok" | "fail" | "empty" | "forbidden" | "detailfail" | "patchfail") — chế độ (localStorage, giữ qua tải lại; không chứa dữ liệu khách)

import { ENUMS } from "@/shared/lib/enums";
import type { MockRequest, MockResponse, Paginated } from "@/shared/lib/http";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import type { Me } from "@/features/auth/types";
import { fold } from "@/shared/lib/search";
import type { GuidanceData, GuidanceTimelineEntry } from "@/features/guidance/types";
import { normalizePhone } from "./customersModel";
import type { CustomerDetail, CustomerListItem, CustomerOrderRow, CustomerRefundRow } from "./types";

const MODE_KEY = "cave_erp_mock_customers_mode";
const PAGE_SIZE = 20;
const PERM_VIEW = "sales.view_customer_list";
const PERM_CHANGE = "sales.change_customer";
const MIN_PHONE_DIGITS = 4;
const EDITABLE = ["name", "phone", "default_address", "note"] as const;
const MAX_LEN: Record<(typeof EDITABLE)[number], number> = { name: 200, phone: 40, default_address: 1000, note: 1000 };

type Mode = "ok" | "fail" | "empty" | "forbidden" | "detailfail" | "patchfail";
function mode(): Mode {
  try {
    const v = typeof window === "undefined" ? null : window.localStorage.getItem(MODE_KEY);
    return v === "fail" || v === "empty" || v === "forbidden" || v === "detailfail" || v === "patchfail" ? v : "ok";
  } catch {
    return "ok";
  }
}

type Audit = { at: string; fields: string[] };
type Person = {
  id: number;
  name: string;
  phone: string;
  default_address: string;
  note: string;
  created_at: string;
  orders: CustomerOrderRow[];
  refunds: CustomerRefundRow[];
  audit: Audit[];
};

const ORDER_LABEL: Record<string, string> = {
  BOOKED: "Giữ chỗ",
  PAID: "Đã thanh toán",
  PROCESSING: "Đang xử lý",
  COMPLETED: "Hoàn tất",
  CANCELLED: "Đã huỷ",
  AUTO_CANCELLED: "Hết giờ giữ chỗ",
};
const REFUND_LABEL: Record<string, string> = Object.fromEntries(Object.entries(ENUMS.refundStatus).map(([k, v]) => [k, v.label]));
const CANCELLED = new Set(["CANCELLED", "AUTO_CANCELLED"]);

const LETTERS = "ABCDEGHKLMNPQRSTUVXYZ"; // 21 chữ cái; sau đó gắn thêm số để đủ 27 khách
const DAY = 86_400_000;
// Số đơn của từng khách (chỉ số 0 = khách mẫu A của bản thiết kế; khách thứ 9 chưa mua gì).
const ORDER_COUNTS = [6, 3, 2, 9, 1, 4, 2, 1, 0, 5, 3, 2, 1, 1, 7, 2, 3, 1, 2, 4, 1, 2, 1, 3, 2, 1, 1];
const NOTES = ["Giao trước 11 giờ", "", "Đơn tự huỷ, đã hoàn tiền", "Mua cho quán, lấy số lượng lớn", "", "Hay đổi giờ nhận", "", "Đơn đã huỷ, đã hoàn tiền"];

function pad(n: number, w: number): string {
  return String(n).padStart(w, "0");
}

function seed(): Person[] {
  const now = Date.now();
  const out: Person[] = [];
  let orderId = 301;
  let refundId = 71;
  for (let i = 0; i < ORDER_COUNTS.length; i++) {
    const label = i < LETTERS.length ? LETTERS[i] : `${LETTERS[i - LETTERS.length]}2`;
    const orders: CustomerOrderRow[] = [];
    const refunds: CustomerRefundRow[] = [];
    const count = ORDER_COUNTS[i];
    for (let k = 0; k < count; k++) {
      // Đơn mới nhất trước; khách i cách nhau theo i để thứ tự "đơn gần nhất" khác thứ tự id.
      const at = now - (i * 1.7 + k * 9.3 + 0.2) * DAY;
      const created = new Date(at);
      const code = `SO${pad(created.getUTCFullYear() % 100, 2)}${pad(created.getUTCMonth() + 1, 2)}${pad(created.getUTCDate(), 2)}-${orderId.toString(16).toUpperCase().padStart(6, "0")}`;
      let status = k === 0 && i % 4 === 0 ? "BOOKED" : "COMPLETED";
      if (count >= 3 && k === 3) status = i % 2 === 0 ? "CANCELLED" : "AUTO_CANCELLED";
      const amount = 260000 + ((i * 7 + k * 3) % 6) * 65000;
      orders.push({ id: orderId, code, status, status_label: ORDER_LABEL[status], total_amount: `${amount}.00`, created_at: created.toISOString() });
      if (status === "CANCELLED") {
        // Đơn đã trả tiền rồi huỷ → phiếu hoàn tiền toàn phần (bị loại khỏi tổng đã mua).
        refunds.push({ id: refundId++, order_code: code, status: "REFUNDED", status_label: REFUND_LABEL.REFUNDED, amount: `${amount}.00`, created_at: new Date(at + 3 * 3600_000).toISOString() });
      }
      if (i === 2 && k === 0) {
        // Khách C: hoàn một phần trên đơn không huỷ (trừ vào tổng đã mua).
        refunds.push({ id: refundId++, order_code: code, status: "REFUNDED", status_label: REFUND_LABEL.REFUNDED, amount: "60000.00", created_at: new Date(at + 5 * 3600_000).toISOString() });
      }
      orderId++;
    }
    out.push({
      id: i + 1,
      name: `Khách Thử ${label}`,
      phone: `0900000${pad(100 + i * 13, 3)}`,
      default_address: i % 3 === 0 ? `Địa chỉ giả ${label}, đường số ${i + 1}` : "",
      note: NOTES[i % NOTES.length],
      created_at: new Date(now - (60 + i * 4) * DAY).toISOString(),
      orders,
      refunds,
      audit: i === 0 ? [{ at: new Date(now - 50 * DAY).toISOString(), fields: ["note"] }] : [],
    });
  }
  return out;
}

let memory: Person[] | null = null;
function load(): Person[] {
  if (!memory) memory = seed();
  return memory;
}

const has = (me: Me, p: string) => me.permissions.includes(p);

function stats(p: Person) {
  const live = p.orders.filter((o) => !CANCELLED.has(o.status));
  const cancelledCodes = new Set(p.orders.filter((o) => CANCELLED.has(o.status)).map((o) => o.code));
  const refunded = p.refunds.filter((r) => r.status === "REFUNDED" && !cancelledCodes.has(r.order_code)).reduce((s, r) => s + Number(r.amount), 0);
  const total = live.reduce((s, o) => s + Number(o.total_amount), 0) - refunded;
  const times = p.orders.map((o) => Date.parse(o.created_at));
  return {
    order_count: p.orders.length,
    cancelled_count: p.orders.length - live.length,
    total_spent: `${total}.00`,
    first_order_at: times.length ? new Date(Math.min(...times)).toISOString() : null,
    last_order_at: times.length ? new Date(Math.max(...times)).toISOString() : null,
  };
}

function listItem(p: Person): CustomerListItem {
  const s = stats(p);
  return { id: p.id, name: p.name, phone: p.phone, order_count: s.order_count, total_spent: s.total_spent, cancelled_count: s.cancelled_count, last_order_at: s.last_order_at, note: p.note };
}

function detail(p: Person): CustomerDetail {
  const s = stats(p);
  const byNewest = <T extends { created_at: string; id: number }>(rows: T[]) => [...rows].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.id - a.id).slice(0, 50);
  return { ...listItem(p), default_address: p.default_address, created_at: p.created_at, first_order_at: s.first_order_at, orders: byNewest(p.orders), refunds: byNewest(p.refunds) };
}

const NOT_FOUND: MockResponse = { status: 404, body: { detail: "Không tìm thấy." } };
const FORBIDDEN: MockResponse = { status: 403, body: { detail: "Bạn không được cấp quyền để thực hiện hành động này." } };

function parsePath(path: string): { id: number | null; query: URLSearchParams; search: boolean } {
  const [p, q = ""] = path.split("?");
  const m = /^\/api\/sales\/customer-directory\/(?:(\d+|search)\/)?$/.exec(p);
  const search = !!m && m[1] === "search";
  return { id: m && m[1] && !search ? Number(m[1]) : null, query: new URLSearchParams(q), search };
}

const SORTERS: Record<string, (a: CustomerListItem, b: CustomerListItem) => number> = {
  last_order_at: (a, b) => Date.parse(a.last_order_at as string) - Date.parse(b.last_order_at as string),
  order_count: (a, b) => a.order_count - b.order_count,
  total_spent: (a, b) => Number(a.total_spent) - Number(b.total_spent),
  name: (a, b) => a.name.localeCompare(b.name, "vi"),
  created_at: (a, b) => a.id - b.id, // id tăng theo ngày tạo trong seed
};

type SearchInput = { q: string; ordering: string; page: number };

function listResponse(input: SearchInput): MockResponse {
  const q = input.q.trim();
  const digits = q.replace(/\D/g, "");
  const raw = input.ordering;
  const desc = raw.startsWith("-");
  const key = desc ? raw.slice(1) : raw;
  const ordering = SORTERS[key] ? raw : "-last_order_at";
  const field = ordering.replace(/^-/, "");
  const sign = ordering.startsWith("-") ? -1 : 1;
  const page = input.page;

  const rows = (mode() === "empty" ? [] : load())
    .map(listItem)
    .filter((c) => {
      if (!q) return true;
      if (fold(c.name).includes(fold(q))) return true;
      return digits.length >= MIN_PHONE_DIGITS && c.phone.includes(digits);
    });
  const withNull = field === "last_order_at";
  rows.sort((a, b) => {
    if (withNull) {
      // Khách chưa có đơn luôn cuối, bất kể chiều sắp xếp (như BE nulls_last).
      if (a.last_order_at === null || b.last_order_at === null) return a.last_order_at === b.last_order_at ? b.id - a.id : a.last_order_at === null ? 1 : -1;
    }
    return sign * SORTERS[field](a, b) || b.id - a.id;
  });
  const start = (page - 1) * PAGE_SIZE;
  if (start >= rows.length && page > 1) return NOT_FOUND; // DRF: trang ngoài phạm vi → 404
  const body: Paginated<CustomerListItem> = {
    count: rows.length,
    next: start + PAGE_SIZE < rows.length ? `?page=${page + 1}` : null,
    previous: page > 1 ? `?page=${page - 1}` : null,
    results: rows.slice(start, start + PAGE_SIZE),
  };
  return { status: 200, body };
}

function badField(field: string, message: string): MockResponse {
  return { status: 400, body: { [field]: [message] } };
}

function patch(p: Person, body: unknown): MockResponse {
  const data = body && typeof body === "object" && !Array.isArray(body) ? (body as Record<string, unknown>) : null;
  if (!data || Object.keys(data).length === 0) return { status: 400, body: { code: "INPUT_EMPTY", detail: "Không có thông tin nào để cập nhật." } };
  if (Object.keys(data).some((k) => !(EDITABLE as readonly string[]).includes(k))) {
    return {
      status: 400,
      body: { code: "INPUT_NOT_ALLOWED", detail: "Chỉ sửa được tên, số điện thoại, địa chỉ giao mặc định và ghi chú." },
    };
  }
  const next: Partial<Record<(typeof EDITABLE)[number], string>> = {};
  for (const k of EDITABLE) {
    if (!(k in data)) continue;
    const v = data[k];
    if (typeof v !== "string") return badField(k, "Not a valid string.");
    let t = v.trim();
    if (t.length > MAX_LEN[k]) return badField(k, `Đảm bảo trường này có không quá ${MAX_LEN[k]} ký tự.`);
    if (k === "phone") {
      t = normalizePhone(t);
      if (!/^0\d{9,10}$/.test(t)) return { status: 400, body: { code: "INVALID_PHONE", detail: "Số điện thoại không hợp lệ." } };
      if (t !== p.phone && load().some((x) => x.id !== p.id && x.phone === t)) {
        return { status: 400, body: { code: "CUSTOMER_PHONE_TAKEN", detail: "Số điện thoại này đã thuộc về một khách hàng khác." } };
      }
    }
    next[k] = t;
  }
  const changed = EDITABLE.filter((k) => k in next && next[k] !== p[k]);
  for (const k of changed) p[k] = next[k] as string;
  if (changed.length) p.audit.push({ at: new Date().toISOString(), fields: [...changed].sort() });
  return { status: 200, body: detail(p) };
}

export function mockCustomersApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  // Thiếu quyền → 403 TRƯỚC khi tra bản ghi (BE Tầng 2); PATCH đòi thêm change_customer.
  if (!has(me, PERM_VIEW) || mode() === "forbidden") return FORBIDDEN;
  if (req.method === "PATCH" && !has(me, PERM_CHANGE)) return FORBIDDEN;
  if (req.method !== "GET" && req.method !== "PATCH" && req.method !== "POST") {
    return { status: 405, body: { detail: `Phương thức "${req.method}" không được chấp nhận.` } };
  }
  const { id, query, search } = parsePath(req.path);
  if (search) {
    if (req.method !== "POST") return { status: 405, body: { detail: `Phương thức "${req.method}" không được chấp nhận.` } };
    if (mode() === "fail") return { status: 500, body: null };
    const data = req.body && typeof req.body === "object" && !Array.isArray(req.body) ? (req.body as Record<string, unknown>) : {};
    const page = Number(data.page ?? 1);
    if (typeof (data.q ?? "") !== "string" || !Number.isInteger(page) || page < 1) return { status: 400, body: { detail: "Dữ liệu không hợp lệ." } };
    return listResponse({ q: String(data.q ?? ""), ordering: typeof data.ordering === "string" ? data.ordering : "", page });
  }
  if (id === null) {
    if (req.method !== "GET") return { status: 405, body: { detail: `Phương thức "${req.method}" không được chấp nhận.` } };
    if (mode() === "fail") return { status: 500, body: null };
    // Lô 17b-BE (TLA-L3): tìm khách chỉ qua POST search/ (từ khoá là SĐT/tên, không được vào URL). GET có `q` không rỗng → 400 SEARCH_USE_POST, không lặp lại `q`.
    if ((query.get("q") || "").trim()) return { status: 400, body: { detail: "Tìm khách dùng ô tìm trên màn Khách hàng.", code: "SEARCH_USE_POST" } };
    return listResponse({ q: "", ordering: query.get("ordering") || "", page: Math.max(1, Number(query.get("page") || "1") || 1) });
  }
  if (req.method === "POST") return { status: 405, body: { detail: `Phương thức "${req.method}" không được chấp nhận.` } };
  const p = load().find((x) => x.id === id);
  if (!p) return NOT_FOUND;
  if (req.method === "PATCH") return mode() === "patchfail" ? { status: 500, body: null } : patch(p, req.body);
  if (mode() === "detailfail") return { status: 500, body: null };
  return { status: 200, body: detail(p) };
}

/** Timeline của khách (guidance `customer`): đơn đặt, huỷ, phiếu hoàn tiền và các lần sửa hồ sơ. Không có SĐT/địa chỉ trong nhãn. */
export function mockCustomerTimelineApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!has(me, PERM_VIEW) || mode() === "forbidden") return FORBIDDEN;
  const m = /^\/api\/guidance\/customer\/(\d+)\/$/.exec(req.path);
  const p = m ? load().find((x) => x.id === Number(m[1])) : undefined;
  if (!p) return NOT_FOUND;
  const system = { kind: "system" as const, display: "Hệ thống" };
  const entries: GuidanceTimelineEntry[] = [];
  for (const o of p.orders) {
    entries.push({ at: o.created_at, kind: "order_placed", label: `Khách đặt đơn ${o.code}`, doc: "order", actor: system });
    if (CANCELLED.has(o.status)) entries.push({ at: new Date(Date.parse(o.created_at) + 2 * 3600_000).toISOString(), kind: "order_cancelled", label: `Đơn ${o.code} bị huỷ`, doc: "order", actor: system });
  }
  for (const r of p.refunds) entries.push({ at: r.created_at, kind: "refund_done", label: `Hoàn tiền cho đơn ${r.order_code}`, doc: "refund", actor: { kind: "user", display: "Lộc" } });
  for (const a of p.audit) entries.push({ at: a.at, kind: "customer_updated", label: "Cập nhật hồ sơ khách", doc: "customer", actor: { kind: "user", display: "Lộc" } });
  entries.sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
  const data: GuidanceData = {
    doc: { type: "customer", id: p.id, code: `KH-${p.id}`, status: null, status_label: null },
    next_steps: [],
    warnings: [],
    timeline: entries.slice(-50),
    related: [],
  };
  return { status: 200, body: data };
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    customers: (m: Mode) => {
      window.localStorage.setItem(MODE_KEY, m);
      return `Chế độ mock khách hàng: ${m}`;
    },
  };
}
