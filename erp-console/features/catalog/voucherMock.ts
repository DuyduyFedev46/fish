// Mock mã giảm giá — CHỈ chạy khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này qua mock.ts).
// Dựng JSON đúng contract 02b §3.9 (SHOP-3b-02). Luật mô phỏng BE, FE KHÔNG dùng lại các luật này:
//  - Mọi endpoint cần catalog.manage_voucher (thiếu → 403). Không có DELETE (405).
//  - `status` do mock tính theo thứ tự: paused, expired, used_up, scheduled, running.
//  - Tạo mã: mã IN HOA 4-20 chữ/số, không trùng, không dãy ≥ 9 chữ số; PERCENT cần max_discount; AMOUNT bỏ qua max_discount;
//    `starts_at < ends_at`; `customer_terms` ≤ 300, không dãy ≥ 9 chữ số. Lỗi 400 `VALIDATION` kèm `fields` {trường: câu}.
//  - Sửa (BR-DM-22): `code`, `kind` luôn khoá (FIELD_LOCKED). Trước `starts_at` sửa tự do phần còn lại. Từ `starts_at` chỉ name,
//    ends_at (chỉ lùi về sau), total_uses (chỉ tăng), min_order_amount (chỉ giảm), value (chỉ tăng), max_discount (chỉ tăng);
//    trường khác → FIELD_LOCKED, ngược hướng → UNFAVORABLE_CHANGE (câu theo 02b).
//  - Tắt: `reason` BUDGET|INCIDENT|OTHER bắt buộc, OTHER bắt buộc `note` (≤ 200, không dãy ≥ 9 chữ số). Bật: hết hạn → EXPIRED, hết lượt → USED_UP.
//  - `redemptions` chỉ có order_code, discount_amount, at, state. Không có tên, SĐT, địa chỉ.
// Dữ liệu chỉ nằm trong bộ nhớ trang (mất khi tải lại), toàn dữ liệu giả.

import type { Me } from "@/features/auth/types";
import type { MockRequest, MockResponse, Paginated } from "@/shared/lib/http";
import { CATALOG_PERM as P } from "./permissions";
import type { Voucher, VoucherDisableReason, VoucherRedemption, VoucherStatus } from "./types";

const PAGE_SIZE = 20;
const REDEMPTION_PAGE_SIZE = 5;

const err = (status: number, code: string, detail: string, extra: Record<string, unknown> = {}): MockResponse => ({ status, body: { detail, code, ...extra } });
const FORBIDDEN = err(403, "FORBIDDEN", "Bạn không được cấp quyền để thực hiện hành động này.");
const NOT_FOUND = err(404, "NOT_FOUND", "Không tìm thấy.");
const SERVER_ERROR = err(500, "SERVER_ERROR", "Máy chủ đang bận. Thử lại sau.");
const NOT_ALLOWED = err(405, "METHOD_NOT_ALLOWED", "Phương thức không được chấp nhận.");
const UNFAVORABLE = "Mã đang chạy chỉ sửa được theo hướng có lợi cho khách. Tắt mã này và tạo mã mới.";
const LOCKED = "Mã đã tạo thì không đổi được mã hoặc kiểu giảm. Tạo mã mới nếu cần.";

const DAY = 24 * 60 * 60 * 1000;
const iso = (ms: number) => new Date(ms).toISOString();

function seed(now: number): Voucher[] {
  const base = {
    disabled_reason: "" as const,
    disabled_note: "",
    is_active: true,
    held_count: 0,
    customer_terms: "",
    created_at: iso(now - 30 * DAY),
    max_discount: null as string | null,
    min_order_amount: "0",
  };
  return [
    {
      ...base,
      id: 1,
      code: "CAVE10",
      name: "Khai trương tháng 10",
      kind: "PERCENT",
      value: "10",
      max_discount: "100000",
      min_order_amount: "300000",
      starts_at: iso(now - 10 * DAY),
      ends_at: iso(now + 20 * DAY),
      total_uses: 100,
      used_count: 30,
      held_count: 2,
      status: "running",
      customer_terms: "Áp dụng cho đơn đặt trên web.",
    },
    {
      ...base,
      id: 2,
      code: "GIAM50K",
      name: "Giảm 50 nghìn cuối tuần",
      kind: "AMOUNT",
      value: "50000",
      min_order_amount: "500000",
      starts_at: iso(now + 5 * DAY),
      ends_at: iso(now + 12 * DAY),
      total_uses: 50,
      used_count: 0,
      status: "scheduled",
    },
    {
      ...base,
      id: 3,
      code: "TETSALE",
      name: "Khuyến mãi cũ",
      kind: "PERCENT",
      value: "5",
      max_discount: "30000",
      starts_at: iso(now - 40 * DAY),
      ends_at: iso(now - 5 * DAY),
      total_uses: 200,
      used_count: 74,
      status: "expired",
    },
    {
      ...base,
      id: 4,
      code: "FLASH20",
      name: "Giờ vàng",
      kind: "PERCENT",
      value: "20",
      max_discount: "80000",
      min_order_amount: "400000",
      starts_at: iso(now - 7 * DAY),
      ends_at: iso(now + 7 * DAY),
      total_uses: 20,
      used_count: 18,
      held_count: 2,
      status: "used_up",
    },
    {
      ...base,
      id: 5,
      code: "NGANSACH",
      name: "Tạm dừng vì ngân sách",
      kind: "AMOUNT",
      value: "30000",
      starts_at: iso(now - 15 * DAY),
      ends_at: iso(now + 15 * DAY),
      total_uses: 80,
      used_count: 41,
      is_active: false,
      disabled_reason: "BUDGET",
      disabled_note: "",
      status: "paused",
    },
  ];
}

let vouchers: Voucher[] | null = null;
function store(): Voucher[] {
  vouchers ??= seed(Date.now());
  return vouchers;
}

/** Về dữ liệu seed (công cụ thử trong DevTools). */
export function resetVouchers(): void {
  vouchers = null;
}

function statusOf(v: Voucher, now: number): VoucherStatus {
  if (!v.is_active) return "paused";
  if (now >= Date.parse(v.ends_at)) return "expired";
  if (v.used_count + v.held_count >= v.total_uses) return "used_up";
  if (now < Date.parse(v.starts_at)) return "scheduled";
  return "running";
}

function view(v: Voucher): Voucher {
  return { ...v, status: statusOf(v, Date.now()) };
}

const hasLongDigitRun = (text: string) => /\d{9,}/.test(text.replace(/[\s.\-]/g, ""));
const bodyOf = (req: MockRequest): Record<string, unknown> => (req.body && typeof req.body === "object" ? (req.body as Record<string, unknown>) : {});
const text = (v: unknown) => (typeof v === "string" ? v.trim() : "");
const numberOf = (v: unknown): number | null => {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

function paged<T>(rows: T[], query: URLSearchParams, size: number): Paginated<T> {
  const page = Math.max(1, Number(query.get("page")) || 1);
  const start = (page - 1) * size;
  const url = (p: number) => `/api/mock/?page=${p}`;
  return {
    count: rows.length,
    next: start + size < rows.length ? url(page + 1) : null,
    previous: page > 1 ? url(page - 1) : null,
    results: rows.slice(start, start + size),
  };
}

function validation(fields: Record<string, string>): MockResponse {
  return err(400, "VALIDATION", "Thông tin mã giảm giá chưa hợp lệ.", { fields });
}

function validateCreate(body: Record<string, unknown>, existing: Voucher[]): { fields: Record<string, string>; ok: Voucher | null } {
  const f: Record<string, string> = {};
  const code = text(body.code).replace(/\s+/g, "").toUpperCase();
  if (!/^[A-Z0-9]{4,20}$/.test(code)) f.code = "Mã gồm 4 đến 20 chữ hoa hoặc số, không dấu.";
  else if (hasLongDigitRun(code)) f.code = "Không dùng dãy từ 9 chữ số liên tiếp trong mã.";
  else if (existing.some((v) => v.code === code)) f.code = "Mã này đã có. Chọn mã khác.";
  const name = text(body.name);
  if (!name) f.name = "Trường này không được để trống.";
  const kind = body.kind === "AMOUNT" ? "AMOUNT" : body.kind === "PERCENT" ? "PERCENT" : null;
  if (!kind) f.kind = "Giá trị không hợp lệ.";
  const value = numberOf(body.value);
  const cap = numberOf(body.max_discount);
  if (value === null || value <= 0) f.value = "Mức giảm phải lớn hơn 0.";
  else if (kind === "PERCENT" && value > 50) f.value = "Phần trăm giảm tối đa là 50.";
  else if (kind === "AMOUNT" && !Number.isInteger(value)) f.value = "Số tiền giảm là số nguyên đồng.";
  if (kind === "PERCENT" && (cap === null || cap <= 0)) f.max_discount = "Mã giảm phần trăm cần mức giảm tối đa.";
  const min = numberOf(body.min_order_amount) ?? 0;
  if (min < 0) f.min_order_amount = "Đơn tối thiểu không âm.";
  const uses = numberOf(body.total_uses);
  if (uses === null || uses < 1 || !Number.isInteger(uses)) f.total_uses = "Tổng số lượt dùng tối thiểu là 1.";
  const starts = Date.parse(String(body.starts_at ?? ""));
  const ends = Date.parse(String(body.ends_at ?? ""));
  if (!Number.isFinite(starts)) f.starts_at = "Chọn giờ bắt đầu.";
  if (!Number.isFinite(ends)) f.ends_at = "Chọn giờ kết thúc.";
  else if (Number.isFinite(starts) && ends <= starts) f.ends_at = "Giờ kết thúc phải sau giờ bắt đầu.";
  const terms = text(body.customer_terms);
  if (terms.length > 300) f.customer_terms = "Tối đa 300 ký tự.";
  else if (hasLongDigitRun(terms)) f.customer_terms = "Không ghi số điện thoại trong điều kiện.";
  if (Object.keys(f).length || !kind || value === null || uses === null) return { fields: f, ok: null };
  return {
    fields: f,
    ok: {
      id: 0,
      code,
      name,
      kind,
      value: String(value),
      max_discount: kind === "PERCENT" && cap !== null ? String(cap) : null,
      min_order_amount: String(min),
      starts_at: new Date(starts).toISOString(),
      ends_at: new Date(ends).toISOString(),
      total_uses: uses,
      used_count: 0,
      held_count: 0,
      status: "scheduled",
      is_active: true,
      disabled_reason: "",
      disabled_note: "",
      customer_terms: terms,
      created_at: new Date().toISOString(),
    },
  };
}

function patchVoucher(v: Voucher, body: Record<string, unknown>): MockResponse {
  const keys = Object.keys(body);
  const locked = keys.filter((k) => k === "code" || k === "kind");
  if (locked.length) return err(400, "FIELD_LOCKED", LOCKED, { fields: locked });
  const now = Date.now();
  const started = now >= Date.parse(v.starts_at);
  if (started) {
    const allowed = new Set(["name", "ends_at", "total_uses", "min_order_amount", "value", "max_discount"]);
    const blocked = keys.filter((k) => !allowed.has(k));
    if (blocked.length) return err(400, "FIELD_LOCKED", "Mã đã bắt đầu chạy nên không sửa được các trường này.", { fields: blocked });
    const bad: string[] = [];
    if ("ends_at" in body && Date.parse(String(body.ends_at)) < Date.parse(v.ends_at)) bad.push("ends_at");
    if ("total_uses" in body && Number(body.total_uses) < v.total_uses) bad.push("total_uses");
    if ("min_order_amount" in body && Number(body.min_order_amount) > Number(v.min_order_amount)) bad.push("min_order_amount");
    if ("value" in body && Number(body.value) < Number(v.value)) bad.push("value");
    if ("max_discount" in body && Number(body.max_discount) < Number(v.max_discount ?? 0)) bad.push("max_discount");
    if (bad.length) return err(400, "UNFAVORABLE_CHANGE", UNFAVORABLE, { fields: bad });
  }
  if ("name" in body) {
    if (!text(body.name)) return validation({ name: "Trường này không được để trống." });
    v.name = text(body.name);
  }
  if ("value" in body) v.value = String(Number(body.value));
  if ("max_discount" in body) v.max_discount = v.kind === "PERCENT" ? String(Number(body.max_discount)) : null;
  if ("min_order_amount" in body) v.min_order_amount = String(Number(body.min_order_amount));
  if ("ends_at" in body) {
    const ends = Date.parse(String(body.ends_at));
    const starts = "starts_at" in body ? Date.parse(String(body.starts_at)) : Date.parse(v.starts_at);
    if (!Number.isFinite(ends) || ends <= starts) return validation({ ends_at: "Giờ kết thúc phải sau giờ bắt đầu." });
    v.ends_at = new Date(ends).toISOString();
  }
  if ("starts_at" in body) {
    const starts = Date.parse(String(body.starts_at));
    if (!Number.isFinite(starts) || starts >= Date.parse(v.ends_at)) return validation({ starts_at: "Giờ bắt đầu phải trước giờ kết thúc." });
    v.starts_at = new Date(starts).toISOString();
  }
  if ("total_uses" in body) {
    const uses = Number(body.total_uses);
    if (!Number.isInteger(uses) || uses < 1) return validation({ total_uses: "Tổng số lượt dùng tối thiểu là 1." });
    v.total_uses = uses;
  }
  if ("customer_terms" in body) {
    const terms = text(body.customer_terms);
    if (terms.length > 300) return validation({ customer_terms: "Tối đa 300 ký tự." });
    if (hasLongDigitRun(terms)) return validation({ customer_terms: "Không ghi số điện thoại trong điều kiện." });
    v.customer_terms = terms;
  }
  return { status: 200, body: view(v) };
}

function redemptionsOf(v: Voucher, query: URLSearchParams): MockResponse {
  const total = v.used_count + v.held_count;
  const shown = Math.min(total, 12); // mock chỉ dựng tối đa 12 dòng để luyện "Tải thêm"
  const rows: VoucherRedemption[] = [];
  for (let i = 0; i < shown; i++) {
    const held = i < v.held_count;
    rows.push({
      order_code: `SO261011-${String(v.id).padStart(2, "0")}${String(i).padStart(2, "0")}AB`,
      discount_amount: String(25000 + ((i * 7000) % 60000)),
      at: new Date(Date.now() - (i + 1) * 3 * 60 * 60 * 1000).toISOString(),
      state: held ? "held" : i % 6 === 5 ? "released" : "used",
    });
  }
  return { status: 200, body: { ...paged(rows, query, REDEMPTION_PAGE_SIZE), count: shown } };
}

export function mockVoucherRoutes(me: Me, req: MockRequest, pathname: string, query: URLSearchParams, mode: string): MockResponse {
  if (!me.permissions.includes(P.manageVoucher) || mode === "forbidden") return FORBIDDEN;
  if (req.method === "DELETE") return NOT_ALLOWED;
  const list = store();
  const act = /^\/api\/catalog\/vouchers\/(\d+)\/(disable|enable|redemptions)\/$/.exec(pathname);
  const one = /^\/api\/catalog\/vouchers\/(\d+)\/$/.exec(pathname);
  const id = Number((act ?? one)?.[1]);

  if (pathname === "/api/catalog/vouchers/") {
    if (req.method === "POST") {
      if (mode === "savefail") return SERVER_ERROR;
      const { fields, ok } = validateCreate(bodyOf(req), list);
      if (!ok) return validation(fields);
      const created = { ...ok, id: Math.max(0, ...list.map((v) => v.id)) + 1 };
      list.push(created);
      return { status: 201, body: view(created) };
    }
    if (req.method !== "GET") return NOT_ALLOWED;
    if (mode === "fail") return SERVER_ERROR;
    const status = (query.get("status") || "").trim();
    if (status && !["running", "scheduled", "paused", "expired", "used_up"].includes(status)) return err(400, "INVALID_FILTER", "Tham số status có giá trị không hợp lệ.");
    let rows = mode === "empty" ? [] : list.map(view);
    if (status) rows = rows.filter((v) => v.status === status);
    rows.sort((a, b) => b.id - a.id);
    return { status: 200, body: paged(rows, query, PAGE_SIZE) };
  }

  const v = list.find((x) => x.id === id);
  if (!v) return NOT_FOUND;
  if (one) {
    if (req.method === "GET") return mode === "fail" || mode === "detailfail" ? SERVER_ERROR : { status: 200, body: view(v) };
    if (req.method === "PATCH") return mode === "savefail" ? SERVER_ERROR : patchVoucher(v, bodyOf(req));
    return NOT_ALLOWED;
  }
  if (act?.[2] === "redemptions") return req.method === "GET" ? (mode === "fail" ? SERVER_ERROR : redemptionsOf(v, query)) : NOT_ALLOWED;
  if (req.method !== "POST") return NOT_ALLOWED;
  if (mode === "savefail") return SERVER_ERROR;
  if (act?.[2] === "disable") {
    const body = bodyOf(req);
    const reason = body.reason as VoucherDisableReason;
    const note = text(body.note);
    const f: Record<string, string> = {};
    if (!["BUDGET", "INCIDENT", "OTHER"].includes(reason)) f.reason = "Chọn lý do tắt mã.";
    if (reason === "OTHER" && !note) f.note = "Lý do khác thì cần ghi chú ngắn.";
    if (note.length > 200) f.note = "Ghi chú tối đa 200 ký tự.";
    else if (hasLongDigitRun(note)) f.note = "Không ghi dãy từ 9 chữ số liên tiếp trong ghi chú.";
    if (Object.keys(f).length) return validation(f);
    v.is_active = false;
    v.disabled_reason = reason;
    v.disabled_note = note;
    return { status: 200, body: view(v) };
  }
  // enable
  if (Date.now() >= Date.parse(v.ends_at)) return err(400, "EXPIRED", "Mã đã hết hạn nên không bật lại được. Tạo mã mới.");
  if (v.used_count + v.held_count >= v.total_uses) return err(400, "USED_UP", "Mã đã hết lượt dùng nên không bật lại được. Tăng số lượt hoặc tạo mã mới.");
  v.is_active = true;
  v.disabled_reason = "";
  v.disabled_note = "";
  return { status: 200, body: view(v) };
}
