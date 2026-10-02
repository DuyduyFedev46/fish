// Mock module Nhà cung cấp (ED-22, Lô 11) — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Dựng JSON theo contract THỰC TẾ BE Lô 11 / B3 (03-dev-notes.md "Lô 11 — BE"):
//   GET   /api/purchasing/suppliers/?q=&supplier_type=&is_active=&page=   (50 dòng/trang, tên rồi id)
//   GET   /api/purchasing/suppliers/{id}/     POST /suppliers/     PATCH /suppliers/{id}/     DELETE/PUT → 405
//   GET   /api/purchasing/receipts/?supplier=<id>&page=      (R10, 20 dòng/trang, -received_date,-id)
//   GET   /api/inventory/batches/?supplier=<id>&has_stock=1  (R5)
//   GET   /api/guidance/supplier/{id}/                       (chỉ phần `timeline`)
//
// Luật mock (mô phỏng BE, FE KHÔNG dùng lại các luật này):
//  - GET cần purchasing.view_supplier (thiếu → 403); POST cần add_supplier, PATCH cần change_supplier (Chủ + Quản lý; NV kho không).
//  - Phiếu nhập cần purchasing.view_purchasereceipt, lô cần inventory.view_batch (thiếu → 403, trang vẫn dùng được).
//  - `purchase_total` và `purchase_amount` CHỈ có key khi người xem có inventory.view_costprice (Chủ); người khác không có key.
//  - receipt_count / last_received_at / purchase_total chỉ tính phiếu SUBMITTED; chưa có phiếu → 0 / null / "0.00".
//  - Tên trùng (bỏ hoa thường) → 400 {name:["Đã có nhà cung cấp trùng tên này."]}; chế độ "racename" giả lập hai người lưu cùng lúc:
//    400 {detail, code:"SUPPLIER_NAME_TAKEN"} (không có khoá name).
//  - Tên rỗng/quá 200 ký tự, số điện thoại quá 20 ký tự, loại lạ → 400 {field:[...]}. Lọc lạ → 400 INVALID_FILTER. `q` quá 100 ký tự → 400.
//
// Dữ liệu CHỈ nằm trong bộ nhớ trang (mất khi tải lại) và không ghi gì vào storage ngoài chế độ thử.
// Công cụ thử trong DevTools (chỉ có ở mock):
//   window.__caveMock.suppliers("ok" | "fail" | "empty" | "forbidden" | "detailfail" | "savefail" | "racename" | "receiptsfail" | "batchesfail")
//   — chế độ; lưu localStorage (không chứa dữ liệu nhà cung cấp), giữ qua tải lại.

import type { MockRequest, MockResponse, Paginated } from "@/shared/lib/http";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import type { Me } from "@/features/auth/types";
import type { GuidanceData, GuidanceTimelineEntry } from "@/features/guidance/types";
import { dateKeyInVietnam } from "@/shared/lib/format";
import { fold } from "@/shared/lib/search";
import type { Supplier, SupplierBatchRow, SupplierReceiptRow, SupplierType } from "./types";

const MODE_KEY = "cave_erp_mock_suppliers_mode";
const PAGE_SIZE = 50;
const RECEIPT_PAGE_SIZE = 20;
const PERM_VIEW = "purchasing.view_supplier";
const PERM_ADD = "purchasing.add_supplier";
const PERM_CHANGE = "purchasing.change_supplier";
const PERM_RECEIPTS = "purchasing.view_purchasereceipt";
const PERM_BATCHES = "inventory.view_batch";
const PERM_COST = "inventory.view_costprice";

type Mode = "ok" | "fail" | "empty" | "forbidden" | "detailfail" | "savefail" | "racename" | "receiptsfail" | "batchesfail";
const MODES: readonly Mode[] = ["fail", "empty", "forbidden", "detailfail", "savefail", "racename", "receiptsfail", "batchesfail"];
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
const NOT_FOUND = err(404, "NOT_FOUND", "Không tìm thấy nhà cung cấp.");
const SERVER_ERROR = err(500, "SERVER_ERROR", "Máy chủ đang bận. Thử lại sau.");
const NAME_TAKEN = "Đã có nhà cung cấp trùng tên này.";

type Person = { id: number; name: string; supplier_type: SupplierType; phone: string; note: string; is_active: boolean; audit: { at: string; label: string; by: string }[] };
type Receipt = SupplierReceiptRow & { amount: string; by: string };
type Batch = SupplierBatchRow & { supplier: number };

const TYPE_LABEL: Record<SupplierType, string> = { INDIVIDUAL: "Cá nhân", COMPANY: "Doanh nghiệp" };

function agoIso(days: number, hour = 9): string {
  const d = new Date(Date.now() - days * 86_400_000);
  d.setUTCHours(hour - 7, 0, 0, 0);
  return d.toISOString();
}
function dayStr(days: number): string {
  return dateKeyInVietnam(new Date(Date.now() - days * 86_400_000));
}

function seedPeople(): Person[] {
  const p = (id: number, name: string, t: SupplierType, phone: string, note: string, active = true): Person => ({ id, name, supplier_type: t, phone, note, is_active: active, audit: [{ at: agoIso(60 - id), label: "Thêm nhà cung cấp", by: "Lộc" }] });
  return [
    p(1, "Đầu mối Cảng cá Phan Thiết", "COMPANY", "0901234567", "Giao hàng trước 5 giờ sáng."),
    p(2, "Vựa cá Lagi (Anh Ba)", "INDIVIDUAL", "0912345678", ""),
    p(3, "Hợp tác xã Đánh bắt Vũng Tàu", "COMPANY", "0987654321", "Có hoá đơn đỏ."),
    p(4, "Anh Sáu Cửa Lò", "INDIVIDUAL", "0933000444", "Chuyên mực và bạch tuộc."),
    p(5, "Công ty Hải sản Nam Bộ", "COMPANY", "0283999000", ""),
    p(6, "Chị Tư Hòn Rơm", "INDIVIDUAL", "0944000555", "Hay nhập tôm sú.", false),
    p(7, "Vựa Phước Hải", "INDIVIDUAL", "", "Chưa nhập lần nào."),
  ];
}

function seedReceipts(): Receipt[] {
  let id = 0;
  const r = (supplier: number, days: number, status: string, items: string, lines: number, qty: string, amount: string): Receipt => {
    id += 1;
    return {
      id,
      code: `PR-${id}`,
      supplier,
      received_date: dayStr(days),
      created_at: agoIso(days, 5),
      status,
      status_label: status === "SUBMITTED" ? "Đã ghi nhận" : status === "DRAFT" ? "Nháp" : "Đã huỷ",
      items_summary: items,
      line_count: lines,
      total_qty: qty,
      purchase_amount: amount,
      amount,
      by: "Anh Tâm",
    };
  };
  return [
    r(1, 2, "SUBMITTED", "Cá chẽm, Tôm sú", 2, "120.000", "14326000.00"),
    r(1, 6, "SUBMITTED", "Mực lá", 1, "45.500", "6825000.00"),
    r(1, 11, "SUBMITTED", "Cá thu", 1, "80.000", "7200000.00"),
    r(1, 15, "SUBMITTED", "Bạch tuộc, Mực lá", 2, "60.000", "9100000.00"),
    r(1, 1, "DRAFT", "Cá chẽm", 1, "30.000", "3000000.00"),
    r(2, 4, "SUBMITTED", "Cá thu", 1, "55.000", "4950000.00"),
    r(2, 9, "CANCELLED", "Cá chẽm", 1, "20.000", "2400000.00"),
    r(3, 20, "SUBMITTED", "Tôm sú loại 1", 1, "40.000", "8800000.00"),
    r(4, 8, "SUBMITTED", "Bạch tuộc", 1, "25.000", "3750000.00"),
    r(5, 30, "SUBMITTED", "Cua Cà Mau", 1, "18.000", "5400000.00"),
    r(6, 75, "SUBMITTED", "Tôm sú", 1, "35.000", "7000000.00"),
  ];
}

function seedBatches(): Batch[] {
  const b = (id: number, supplier: number, code: string, item: string, qty: string, expiryDays: number, status: string): Batch => ({ id, supplier, batch_id: code, item_name: item, qty_available: qty, expiry_date: dayStr(-expiryDays), status });
  return [
    b(201, 1, "CA-CHEM-260927-GH78", "Cá chẽm phi lê", "18.500", 3, "SELLING"),
    b(202, 1, "MUC-LA-260925-CD34E", "Mực lá Phan Thiết", "9.000", 1, "NEAR_EXPIRY"),
    b(203, 1, "CA-THU-260928-VT01", "Cá thu", "42.000", 5, "SELLING"),
    b(204, 2, "CA-THU-260918-VT02", "Cá thu", "6.250", 2, "SELLING"),
    b(205, 4, "BACH-TUOC-260925-JK90", "Bạch tuộc tươi", "12.000", 4, "SELLING"),
  ];
}

let PEOPLE: Person[] | null = null;
let RECEIPTS: Receipt[] | null = null;
let BATCHES: Batch[] | null = null;
const people = () => (PEOPLE ??= seedPeople());
const receipts = () => (RECEIPTS ??= seedReceipts());
const batches = () => (BATCHES ??= seedBatches());

function view(p: Person, me: Me): Supplier {
  const live = receipts().filter((r) => r.supplier === p.id && r.status === "SUBMITTED");
  const total = live.reduce((s, r) => s + Number(r.amount), 0);
  const times = live.map((r) => Date.parse(r.created_at));
  const row: Supplier = {
    id: p.id,
    name: p.name,
    supplier_type: p.supplier_type,
    supplier_type_label: TYPE_LABEL[p.supplier_type],
    phone: p.phone,
    note: p.note,
    is_active: p.is_active,
    receipt_count: live.length,
    last_received_at: times.length ? new Date(Math.max(...times)).toISOString() : null,
  };
  if (has(me, PERM_COST)) row.purchase_total = total.toFixed(2);
  return row;
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

/** Kiểm thân POST/PATCH; trả lỗi theo trường (DRF) hoặc null. `partial` = PATCH (chỉ kiểm khoá có mặt). */
function validate(body: Record<string, unknown>, partial: boolean, selfId: number | null): MockResponse | null {
  const fields: Record<string, string[]> = {};
  if ("name" in body || !partial) {
    const name = typeof body.name === "string" ? body.name.trim() : "";
    if (!name) fields.name = ["Trường này không được để trống."];
    else if (name.length > 200) fields.name = ["Đảm bảo trường này có không quá 200 ký tự."];
    else if (people().some((x) => x.id !== selfId && fold(x.name) === fold(name))) fields.name = [NAME_TAKEN];
  }
  if ("supplier_type" in body && body.supplier_type !== "INDIVIDUAL" && body.supplier_type !== "COMPANY") fields.supplier_type = ["Giá trị không hợp lệ."];
  if ("phone" in body && (typeof body.phone !== "string" || body.phone.length > 20)) fields.phone = ["Đảm bảo trường này có không quá 20 ký tự."];
  if ("note" in body && typeof body.note !== "string") fields.note = ["Not a valid string."];
  if ("is_active" in body && typeof body.is_active !== "boolean") fields.is_active = ["Giá trị không hợp lệ."];
  if (Object.keys(fields).length) return { status: 400, body: fields };
  if (mode() === "racename" && typeof body.name === "string") return err(400, "SUPPLIER_NAME_TAKEN", NAME_TAKEN);
  return null;
}

function listResponse(me: Me, query: URLSearchParams): MockResponse {
  const m = mode();
  if (m === "fail") return SERVER_ERROR;
  const q = (query.get("q") || "").trim();
  if (q.length > 100) return err(400, "INVALID_FILTER", "Từ khoá tìm kiếm tối đa 100 ký tự.");
  const types = (query.get("supplier_type") || "").split(",").map((s) => s.trim()).filter(Boolean);
  if (types.some((t) => t !== "INDIVIDUAL" && t !== "COMPANY")) return err(400, "INVALID_FILTER", "Loại nhà cung cấp không hợp lệ.");
  const activeRaw = (query.get("is_active") || "").toLowerCase();
  if (activeRaw && !["1", "0", "true", "false"].includes(activeRaw)) return err(400, "INVALID_FILTER", "Trạng thái không hợp lệ.");
  let rows = m === "empty" ? [] : [...people()];
  if (q) rows = rows.filter((p) => fold(p.name).includes(fold(q)) || (p.phone && p.phone.includes(q)));
  if (types.length) rows = rows.filter((p) => types.includes(p.supplier_type));
  if (activeRaw) rows = rows.filter((p) => p.is_active === (activeRaw === "1" || activeRaw === "true"));
  rows.sort((a, b) => a.name.localeCompare(b.name, "vi") || a.id - b.id);
  const page = Math.max(1, Number(query.get("page")) || 1);
  const slice = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const body: Paginated<Supplier> = {
    count: rows.length,
    next: page * PAGE_SIZE < rows.length ? `?page=${page + 1}` : null,
    previous: page > 1 ? `?page=${page - 1}` : null,
    results: slice.map((p) => view(p, me)),
  };
  return { status: 200, body };
}

function receiptsResponse(me: Me, query: URLSearchParams): MockResponse {
  if (!has(me, PERM_RECEIPTS)) return FORBIDDEN;
  if (mode() === "receiptsfail") return SERVER_ERROR;
  const supplier = Number(query.get("supplier"));
  let rows = receipts().filter((r) => r.supplier === supplier);
  rows = [...rows].sort((a, b) => b.received_date.localeCompare(a.received_date) || b.id - a.id);
  const page = Math.max(1, Number(query.get("page")) || 1);
  const slice = rows.slice((page - 1) * RECEIPT_PAGE_SIZE, page * RECEIPT_PAGE_SIZE);
  const results: SupplierReceiptRow[] = slice.map((r) => {
    const out: SupplierReceiptRow = {
      id: r.id,
      code: r.code,
      supplier: r.supplier,
      received_date: r.received_date,
      created_at: r.created_at,
      status: r.status,
      status_label: r.status_label,
      items_summary: r.items_summary,
      line_count: r.line_count,
      total_qty: r.total_qty,
    };
    if (has(me, PERM_COST)) out.purchase_amount = r.amount;
    return out;
  });
  const body: Paginated<SupplierReceiptRow> = { count: rows.length, next: page * RECEIPT_PAGE_SIZE < rows.length ? `?page=${page + 1}` : null, previous: page > 1 ? `?page=${page - 1}` : null, results };
  return { status: 200, body };
}

function batchesResponse(me: Me, query: URLSearchParams): MockResponse {
  if (!has(me, PERM_BATCHES)) return FORBIDDEN;
  if (mode() === "batchesfail") return SERVER_ERROR;
  const supplier = Number(query.get("supplier"));
  const rows = batches()
    .filter((b) => b.supplier === supplier && Number(b.qty_available) > 0)
    .sort((a, b) => a.expiry_date.localeCompare(b.expiry_date))
    .map(({ supplier: _s, ...rest }) => rest);
  return { status: 200, body: { count: rows.length, next: null, previous: null, results: rows } satisfies Paginated<SupplierBatchRow> };
}

function timelineResponse(id: number): MockResponse {
  const p = people().find((x) => x.id === id);
  if (!p) return NOT_FOUND;
  const entries: GuidanceTimelineEntry[] = [];
  for (const a of p.audit) entries.push({ at: a.at, kind: "supplier_event", label: a.label, doc: "supplier", actor: { kind: "user", display: a.by } });
  for (const r of receipts().filter((x) => x.supplier === id && x.status === "SUBMITTED")) {
    entries.push({ at: r.created_at, kind: "receipt_submitted", label: `Ghi nhận phiếu nhập ${r.code}`, doc: "receipt", actor: { kind: "user", display: r.by } });
  }
  entries.sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
  const data: GuidanceData = { doc: { type: "supplier", id: p.id, code: String(p.id), status: null, status_label: null }, next_steps: [], warnings: [], timeline: entries.slice(-50), related: [] };
  return { status: 200, body: data };
}

function note(p: Person, label: string, me: Me) {
  p.audit.push({ at: new Date().toISOString(), label, by: me.display_name });
}

export function mockSuppliersApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const [pathname, qs = ""] = req.path.split("?");
  const query = new URLSearchParams(qs);

  if (pathname === "/api/purchasing/receipts/") return receiptsResponse(me, query);
  if (pathname === "/api/inventory/batches/") return batchesResponse(me, query);

  if (!has(me, PERM_VIEW) || mode() === "forbidden") return FORBIDDEN;

  const guide = /^\/api\/guidance\/supplier\/(\d+)\/$/.exec(pathname);
  if (guide) return timelineResponse(Number(guide[1]));

  if (pathname === "/api/purchasing/suppliers/") {
    if (req.method === "POST") {
      if (!has(me, PERM_ADD)) return FORBIDDEN;
      if (mode() === "savefail") return SERVER_ERROR;
      const body = bodyOf(req);
      const bad = validate(body, false, null);
      if (bad) return bad;
      const id = Math.max(0, ...people().map((x) => x.id)) + 1;
      const p: Person = {
        id,
        name: String(body.name).trim(),
        supplier_type: body.supplier_type === "COMPANY" ? "COMPANY" : "INDIVIDUAL",
        phone: typeof body.phone === "string" ? body.phone.trim() : "",
        note: typeof body.note === "string" ? body.note : "",
        is_active: typeof body.is_active === "boolean" ? body.is_active : true,
        audit: [],
      };
      note(p, "Thêm nhà cung cấp", me);
      people().push(p);
      return { status: 201, body: view(p, me) };
    }
    if (req.method !== "GET") return err(405, "METHOD_NOT_ALLOWED", "Không hỗ trợ.");
    return listResponse(me, query);
  }

  const one = /^\/api\/purchasing\/suppliers\/(\d+)\/$/.exec(pathname);
  if (one) {
    const p = people().find((x) => x.id === Number(one[1]));
    if (req.method === "PATCH") {
      if (!has(me, PERM_CHANGE)) return FORBIDDEN;
      if (!p) return NOT_FOUND;
      if (mode() === "savefail") return SERVER_ERROR;
      const body = bodyOf(req);
      const bad = validate(body, true, p.id);
      if (bad) return bad;
      if (typeof body.name === "string") p.name = body.name.trim();
      if (body.supplier_type === "INDIVIDUAL" || body.supplier_type === "COMPANY") p.supplier_type = body.supplier_type;
      if (typeof body.phone === "string") p.phone = body.phone.trim();
      if (typeof body.note === "string") p.note = body.note;
      if (typeof body.is_active === "boolean" && body.is_active !== p.is_active) {
        p.is_active = body.is_active;
        note(p, body.is_active ? "Bật lại hợp tác" : "Ngừng hợp tác", me);
      } else if (["name", "supplier_type", "phone", "note"].some((k) => k in body)) note(p, "Cập nhật thông tin nhà cung cấp", me);
      return { status: 200, body: view(p, me) };
    }
    if (req.method !== "GET") return err(405, "METHOD_NOT_ALLOWED", "Không hỗ trợ.");
    if (mode() === "detailfail") return SERVER_ERROR;
    return p ? { status: 200, body: view(p, me) } : NOT_FOUND;
  }
  return err(404, "NOT_FOUND", "Không tìm thấy endpoint.");
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    suppliers: (m: Mode) => {
      window.localStorage.setItem(MODE_KEY, m);
      return `Nhà cung cấp (mock): chế độ ${m}`;
    },
  };
}
