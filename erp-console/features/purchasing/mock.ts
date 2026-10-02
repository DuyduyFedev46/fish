import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { todayInVietnam } from "@/shared/lib/format";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import type { Me } from "@/features/auth/types";
import type { GuidanceData } from "@/features/guidance/types";
import { mockCostsOfBatches, mockInvoicesOfReceipt } from "@/features/accounting/mock";
import type {
  CancelPurchaseReceiptResponse,
  PurchaseReceiptSummary,
  ReceiptCost,
  ReceiptDetail,
  ReceiptInvoice,
  ReceiptLine,
  ReceiptRow,
  ReceiveBatchesPayload,
  ReceiveBatchesResponse,
  SubmitReceiptResponse,
  Supplier,
} from "./types";

export const MOCK_SUPPLIERS: Supplier[] = [
  { id: 1, name: "Đầu mối Cảng cá Phan Thiết", phone: "0901234567", is_active: true },
  { id: 2, name: "Vựa cá Lagi (Anh Ba)", phone: "0912345678", is_active: true },
  { id: 3, name: "Hợp tác xã Đánh bắt Vũng Tàu", phone: "0987654321", is_active: true },
  { id: 4, name: "Ghe Tư Hải", phone: "0900000904", is_active: true },
  { id: 5, name: "Vựa Bà Năm", phone: "0900000905", is_active: true },
  { id: 6, name: "Tàu Phước Lộc 07", phone: "0900000906", is_active: true },
];

export function mockListSuppliers(_req: MockRequest): { status: number; body: { results: Supplier[] } } {
  return {
    status: 200,
    body: { results: MOCK_SUPPLIERS },
  };
}

// ---- Phiếu nhập (R10) ----
// Dữ liệu mẫu khớp với lô của features/inventory/mock.ts (mã lô, nhà cung cấp, trạng thái), dùng cùng id phiếu 89 - 103.
// Kho dữ liệu nằm trong bộ nhớ trang: tải lại là về seed.
// Quyền theo BE: đọc = view_purchasereceipt; `purchase_amount`, `rate`, `landed_unit_cost`, `costs`, `allocated_amount` chỉ khi
// người xem có view_costprice; `invoices` (kèm số tiền) chỉ khi có view_purchaseinvoice.

const DAY = 86_400_000;
const PAGE_SIZE = 20;
const FORBIDDEN: MockResponse = { status: 403, body: { detail: "Bạn không có quyền để thực hiện thao tác này." } };
const NOT_FOUND: MockResponse = { status: 404, body: { detail: "Không tìm thấy." } };
const err = (status: number, code: string, detail: string): MockResponse => ({ status, body: { code, detail } });
const can = (me: Me, perm: string) => me.permissions.includes(perm);

const WAREHOUSE_NAME: Record<number, string> = { 1: "Kho lạnh Bến Đá", 2: "Kho mát chợ Vũng Tàu" };
const STAFF_NAME: Record<number, string> = { 1: "Lộc", 2: "Chị Hạnh", 3: "Anh Tâm" };
const STATUS_LABEL: Record<string, string> = { DRAFT: "Nháp", SUBMITTED: "Đã ghi nhận", CANCELLED: "Đã huỷ" };
const STATUSES = Object.keys(STATUS_LABEL);

type MockLine = {
  id: number;
  item: number;
  item_code: string;
  item_name: string;
  qty: number;
  rate: number;
  shelf_life_days: number | null;
  batch: number | null;
  batch_code: string | null;
  batch_status: string | null;
  expiry_date: string | null;
};
type MockEvent = { at: string; label: string; actor: string };
type MockReceipt = {
  id: number;
  supplier: number;
  warehouse: number;
  received_date: string;
  status: string;
  created_by: number;
  created_at: string;
  note: string;
  lines: MockLine[];
  events: MockEvent[];
};

// [mã mặt hàng, tên, kg, giá mua/kg, id lô, mã lô, trạng thái lô, hạn dùng (ngày sau), số ngày bảo quản]
type LineSeed = [string, string, number, number, number | null, string | null, string | null, number | null, number | null];
// [id phiếu, nhà cung cấp, kho, ngày nhập (trước), trạng thái, người tạo, dòng nhập]
type ReceiptSeed = [number, number, number, number, string, number, LineSeed[]];
const SEEDS: ReceiptSeed[] = [
  [104, 4, 1, 0, "DRAFT", 2, [["CA-THU-NC", "Cá thu nguyên con", 30, 140000, null, null, null, null, 30], ["MUC-ONG", "Mực ống", 18, 190000, null, null, null, null, 21]]],
  [103, 5, 2, 1, "SUBMITTED", 3, [["SO-DIEP", "Sò điệp", 14.2, 81000, 12, "L0923-SO01", "DRAFT", 5, 6]]],
  [102, 6, 1, 2, "SUBMITTED", 3, [["TOM-SU-30", "Tôm sú size 30", 20, 261000, 11, "L0922-TS02", "DRAFT", 26, 28]]],
  [101, 4, 1, 3, "SUBMITTED", 2, [["CA-THU-NC", "Cá thu nguyên con", 40, 142000, 10, "L0921-CT02", "SELLING", 28, 31]]],
  [100, 5, 1, 3, "SUBMITTED", 3, [["MUC-ONG", "Mực ống", 12, 191000, 9, "L0921-MU03", "SOLD_OUT", 18, 21]]],
  [99, 4, 1, 4, "SUBMITTED", 3, [["CA-CHIM-TR", "Cá chim trắng", 19, 169000, 8, "L0920-CC01", "SELLING", 12, 16]]],
  [98, 6, 1, 5, "SUBMITTED", 3, [["CA-NGU-LOIN", "Cá ngừ đại dương loin", 50.75, 198000, 7, "L0919-CN01", "SELLING", 30, 35]]],
  [97, 6, 1, 6, "SUBMITTED", 1, [["CA-HONG-DO", "Cá hồng đỏ", 26.4, 135500, 6, "L0918-CH01", "SELLING", 25, 31]]],
  [96, 5, 2, 6, "SUBMITTED", 3, [["GHE-XANH", "Ghẹ xanh", 14.8, 258000, 5, "L0918-GX01", "SELLING", 2, 8]]],
  [95, 4, 1, 7, "SUBMITTED", 3, [["CA-BOP-CK", "Cá bớp cắt khúc", 38, 151000, 4, "L0917-CB01", "SELLING", 21, 28]]],
  [94, 6, 1, 8, "SUBMITTED", 2, [["TOM-SU-20", "Tôm sú size 20", 30, 305000, 3, "L0916-TS01", "SELLING", 9, 17]]],
  [93, 5, 1, 9, "SUBMITTED", 3, [["MUC-LA", "Mực lá câu", 16, 229500, 2, "L0915-MU02", "NEAR_EXPIRY", 1, 10]]],
  [92, 4, 1, 10, "SUBMITTED", 3, [["CA-THU-PL", "Cá thu phi lê", 25, 175000, 1, "L0914-CT01", "NEAR_EXPIRY", 4, 14]]],
  [91, 4, 1, 12, "SUBMITTED", 3, [["CA-THU-PL", "Cá thu phi lê", 15.5, 175000, 901, "L0908-CT00", "EXPIRED", -2, 10]]],
  [90, 5, 1, 11, "SUBMITTED", 3, [["MUC-LA", "Mực lá câu", 10, 229500, 902, "L0909-MU00", "EXPIRED", -1, 10]]],
  [89, 6, 1, 10, "SUBMITTED", 3, [["TOM-SU-20", "Tôm sú size 20", 8, 305000, 903, "L0910-TS00", "EXPIRED", -1, 10]]],
  [88, 5, 1, 15, "CANCELLED", 3, [["CA-BOP-CK", "Cá bớp cắt khúc", 10, 150000, null, null, null, null, 28]]],
];

let receipts: MockReceipt[] | null = null;
let nextReceiptId = 105;
let nextLineId = 1000;
let nextBatchId = 2001;

const dayKey = (daysFromNow: number) => todayInVietnam(new Date(Date.now() + daysFromNow * DAY));
const nameOfSupplier = (id: number) => MOCK_SUPPLIERS.find((x) => x.id === id)?.name ?? `Nhà cung cấp ${id}`;
const dec3 = (n: number) => n.toFixed(3);

function eventsFor(status: string, createdAt: number, by: number): MockEvent[] {
  const actor = STAFF_NAME[by] ?? "Hệ thống";
  const out: MockEvent[] = [{ at: new Date(createdAt).toISOString(), label: "Tạo phiếu nhập", actor }];
  if (status !== "DRAFT") out.push({ at: new Date(createdAt + 120_000).toISOString(), label: "Ghi nhận phiếu nhập và nhập lô", actor });
  if (status === "CANCELLED") out.push({ at: new Date(createdAt + DAY).toISOString(), label: "Huỷ phiếu nhập", actor });
  return out;
}

function store(): MockReceipt[] {
  if (!receipts) {
    const now = Date.now();
    receipts = SEEDS.map(([id, supplier, warehouse, ago, status, by, lines]) => {
      const createdAt = now - ago * DAY - 3_600_000;
      return {
        id,
        supplier,
        warehouse,
        received_date: dayKey(-ago),
        status,
        created_by: by,
        created_at: new Date(createdAt).toISOString(),
        note: "",
        lines: lines.map(([code, name, qty, rate, batch, batchCode, batchStatus, expiry, shelf], i) => ({
          id: id * 10 + i,
          item: id * 10 + i,
          item_code: code,
          item_name: name,
          qty,
          rate,
          shelf_life_days: shelf,
          batch,
          batch_code: batchCode,
          batch_status: batchStatus,
          expiry_date: expiry === null ? null : dayKey(expiry),
        })),
        events: eventsFor(status, createdAt, by),
      };
    });
  }
  return receipts;
}

const lineAmount = (l: MockLine) => Math.round(l.qty * l.rate);
const totalQty = (r: MockReceipt) => r.lines.reduce((sum, l) => sum + l.qty, 0);
const purchaseAmount = (r: MockReceipt) => r.lines.reduce((sum, l) => sum + lineAmount(l), 0);
const batchIds = (r: MockReceipt) => r.lines.flatMap((l) => (l.batch ? [l.batch] : []));

function toRow(r: MockReceipt, me: Me): ReceiptRow {
  const names = r.lines.map((l) => l.item_name);
  const row: ReceiptRow = {
    id: r.id,
    code: `PR-${r.id}`,
    supplier: r.supplier,
    supplier_name: nameOfSupplier(r.supplier),
    warehouse: r.warehouse,
    warehouse_name: WAREHOUSE_NAME[r.warehouse] ?? "",
    received_date: r.received_date,
    status: r.status,
    status_label: STATUS_LABEL[r.status] ?? r.status,
    created_by: r.created_by,
    created_by_name: STAFF_NAME[r.created_by] ?? "",
    created_at: r.created_at,
    note: r.note,
    items_summary: names.length > 2 ? `${names.slice(0, 2).join(", ")} và ${names.length - 2} mặt hàng khác` : names.join(", "),
    line_count: r.lines.length,
    total_qty: dec3(totalQty(r)),
    batch_codes: r.lines.flatMap((l) => (l.batch_code ? [l.batch_code] : [])),
    invoice: (() => {
      const first = mockInvoicesOfReceipt(r.id)[0];
      return first ? { id: first.id } : null;
    })(),
  };
  if (me.can_view_cost) row.purchase_amount = String(purchaseAmount(r));
  return row;
}

function toDetail(r: MockReceipt, me: Me): ReceiptDetail {
  const costed = mockCostsOfBatches(batchIds(r));
  const allocatedPerBatch = new Map<number, number>();
  for (const { cost } of costed) {
    for (const a of cost.allocations) allocatedPerBatch.set(a.batch, (allocatedPerBatch.get(a.batch) ?? 0) + Number(a.allocated_amount));
  }
  const lines: ReceiptLine[] = r.lines.map((l) => {
    const line: ReceiptLine = {
      id: l.id,
      item: l.item,
      item_code: l.item_code,
      item_name: l.item_name,
      qty: dec3(l.qty),
      shelf_life_days: l.shelf_life_days,
      batch: l.batch,
      batch_code: l.batch_code,
      batch_status: l.batch_status,
      expiry_date: l.expiry_date,
    };
    if (me.can_view_cost) {
      line.rate = String(l.rate);
      line.purchase_amount = String(lineAmount(l));
      line.landed_unit_cost = l.batch ? String(Math.round(l.rate + (allocatedPerBatch.get(l.batch) ?? 0) / l.qty)) : null;
    }
    return line;
  });
  const detail: ReceiptDetail = { ...toRow(r, me), lines };
  if (can(me, "purchasing.view_purchaseinvoice")) {
    detail.invoices = mockInvoicesOfReceipt(r.id).map<ReceiptInvoice>((i) => ({
      id: i.id,
      code: i.code,
      invoice_date: i.invoice_date,
      is_paid: i.is_paid,
      amount: String(Math.round(Number(i.amount))),
    }));
  }
  if (me.can_view_cost) {
    detail.costs = costed.map<ReceiptCost>(({ cost, allocated, batchCount }) => ({
      id: cost.id,
      cost_type: cost.cost_type,
      cost_type_label: cost.cost_type_label,
      allocation_method: cost.allocation_method,
      allocation_method_label: cost.allocation_method_label,
      incurred_date: cost.incurred_date,
      amount: String(Math.round(Number(cost.amount))),
      allocated_amount: String(Math.round(allocated)),
      batch_count: batchCount,
    }));
    detail.allocated_amount = String(Math.round(costed.reduce((sum, c) => sum + c.allocated, 0)));
  }
  return detail;
}

function summaryOf(r: MockReceipt): PurchaseReceiptSummary {
  return {
    id: r.id,
    supplier: r.supplier,
    warehouse: r.warehouse,
    received_date: r.received_date,
    status: r.status,
    created_by: r.created_by,
    note: r.note,
    lines: r.lines.map((l) => ({
      id: l.id,
      item: l.item,
      item_code: l.item_code,
      qty: dec3(l.qty),
      shelf_life_days: l.shelf_life_days,
      batch: l.batch,
    })),
  };
}

function idOfPath(path: string, tail: RegExp): number | null {
  const m = path.match(tail);
  return m ? Number(m[1]) : null;
}

const MONTH = /^\d{4}-\d{2}$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** GET /api/purchasing/receipts/ (R10). */
export function mockReceiptList(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "purchasing.view_purchasereceipt")) return FORBIDDEN;
  const q = new URLSearchParams(req.path.split("?")[1] ?? "");
  let rows = [...store()];
  const status = q.get("status");
  if (status) {
    const list = status.split(",").map((x) => x.trim()).filter(Boolean);
    if (list.some((x) => !STATUSES.includes(x))) return err(400, "INVALID_FILTER", "Tham số status có giá trị không hợp lệ.");
    rows = rows.filter((r) => list.includes(r.status));
  }
  const supplier = q.get("supplier");
  if (supplier) {
    if (!/^\d+$/.test(supplier)) return err(400, "INVALID_FILTER", "Tham số supplier phải là số.");
    rows = rows.filter((r) => r.supplier === Number(supplier));
  }
  const month = q.get("month");
  if (month) {
    if (!MONTH.test(month)) return err(400, "INVALID_FILTER", "Tham số month phải có dạng YYYY-MM.");
    rows = rows.filter((r) => r.received_date.startsWith(month));
  }
  const from = q.get("date_from");
  if (from) {
    if (!DATE.test(from)) return err(400, "INVALID_FILTER", "Tham số date_from phải có dạng YYYY-MM-DD.");
    rows = rows.filter((r) => r.received_date >= from);
  }
  const to = q.get("date_to");
  if (to) {
    if (!DATE.test(to)) return err(400, "INVALID_FILTER", "Tham số date_to phải có dạng YYYY-MM-DD.");
    rows = rows.filter((r) => r.received_date <= to);
  }
  const hasInvoice = q.get("has_invoice");
  if (hasInvoice) {
    if (!["0", "1"].includes(hasInvoice)) return err(400, "INVALID_FILTER", "Tham số has_invoice chỉ nhận 1 hoặc 0.");
    rows = rows.filter((r) => (mockInvoicesOfReceipt(r.id).length > 0) === (hasInvoice === "1"));
  }
  rows.sort((a, b) => (a.received_date < b.received_date ? 1 : a.received_date > b.received_date ? -1 : b.id - a.id));
  const page = Math.max(1, Number(q.get("page")) || 1);
  const start = (page - 1) * PAGE_SIZE;
  return {
    status: 200,
    body: {
      count: rows.length,
      next: start + PAGE_SIZE < rows.length ? `?page=${page + 1}` : null,
      previous: page > 1 ? `?page=${page - 1}` : null,
      results: rows.slice(start, start + PAGE_SIZE).map((r) => toRow(r, me)),
    },
  };
}

/** GET /api/purchasing/receipts/{id}/. */
export function mockReceiptDetail(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "purchasing.view_purchasereceipt")) return FORBIDDEN;
  const id = idOfPath(req.path, /\/receipts\/(\d+)\/?(?:\?|$)/);
  const r = id ? store().find((x) => x.id === id) : undefined;
  return r ? { status: 200, body: toDetail(r, me) } : NOT_FOUND;
}

/** GET /api/guidance/receipt/{id}/: chỉ dòng thời gian, nhãn không chứa giá hay tên nhà cung cấp. */
export function mockReceiptGuidance(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "purchasing.view_purchasereceipt")) return FORBIDDEN;
  const id = idOfPath(req.path, /\/guidance\/receipt\/(\d+)\/?/);
  const r = id ? store().find((x) => x.id === id) : undefined;
  if (!r) return NOT_FOUND;
  const data: GuidanceData = {
    doc: { type: "receipt", id: r.id, code: `PR-${r.id}`, status: null, status_label: null },
    next_steps: [],
    warnings: [],
    timeline: r.events.map((e) => ({
      at: e.at,
      kind: "audit",
      label: e.label,
      doc: "",
      actor: { kind: "user" as const, display: e.actor },
    })),
    related: [],
  };
  return { status: 200, body: data };
}

function makeLots(r: MockReceipt): string[] {
  const codes: string[] = [];
  const stamp = r.received_date.replace(/-/g, "").slice(2);
  for (const l of r.lines) {
    if (l.batch) continue;
    l.batch = nextBatchId++;
    l.batch_code = `${l.item_code}-${stamp}-${l.batch}`;
    l.batch_status = "DRAFT";
    l.expiry_date = dayKey(l.shelf_life_days ?? 60);
    codes.push(l.batch_code);
  }
  return codes;
}

/** POST /api/purchasing/receipts/{id}/submit/: ghi nhận phiếu Nháp, sinh lô. */
export function mockSubmitReceipt(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "purchasing.change_purchasereceipt")) return FORBIDDEN;
  const id = idOfPath(req.path, /\/receipts\/(\d+)\/submit\/?/);
  const r = id ? store().find((x) => x.id === id) : undefined;
  if (!r) return NOT_FOUND;
  if (r.status !== "DRAFT") return err(400, "BR-MH-02", "Chỉ ghi nhận được phiếu nhập đang ở trạng thái Nháp.");
  const codes = makeLots(r);
  r.status = "SUBMITTED";
  r.events.push({ at: new Date().toISOString(), label: "Ghi nhận phiếu nhập và nhập lô", actor: me.display_name });
  const body: SubmitReceiptResponse = { receipt: summaryOf(r), batches_created: codes };
  return { status: 200, body };
}

// ---- Nhập lô tại cảng và huỷ (giữ nguyên hành vi cũ của Lô trước) ----

let mockBatchSeq = 100;
export const mockReceiptsStore = new Map<number, ReceiveBatchesResponse>();

export function mockSubmitReceiveBatches(req: MockRequest): { status: number; body: ReceiveBatchesResponse | { detail: string; code: string } } {
  let body = req.body as ReceiveBatchesPayload | undefined;
  if (typeof body === "string") {
    try {
      body = JSON.parse(body);
    } catch {
      // ignore
    }
  }
  if (!body || !body.lines || body.lines.length === 0) {
    return {
      status: 400,
      body: { detail: "Danh sách mặt hàng nhập không được rỗng.", code: "BR-MH-02" },
    };
  }

  const me = mockRequireUser(req);
  const receiptId = nextReceiptId++;
  const receivedDate = body.received_date || todayInVietnam();

  const batches = body.lines.map((line) => {
    mockBatchSeq += 1;
    const days = line.shelf_life_days || 60;
    const exp = todayInVietnam(new Date(Date.now() + days * 86400 * 1000));
    return {
      batch_id: `${line.item_code}-${receivedDate.replace(/-/g, "").slice(2)}-${mockBatchSeq}`,
      status: "DRAFT",
      expiry_date: exp,
      qty_available: line.qty,
    };
  });

  const resp: ReceiveBatchesResponse = {
    receipt: {
      id: receiptId,
      supplier: body.supplier,
      warehouse: body.warehouse || 1,
      received_date: receivedDate,
      status: "SUBMITTED",
      created_by: me?.id ?? 1,
      lines: body.lines.map((l, idx) => ({
        id: idx + 1,
        item: idx + 1,
        item_code: l.item_code,
        qty: l.qty,
        shelf_life_days: l.shelf_life_days,
        batch: idx + 1,
      })),
    },
    batches,
  };

  mockReceiptsStore.set(receiptId, resp);

  // Phiếu mới cũng hiện ở danh sách và chi tiết Mua hàng.
  const createdAt = Date.now();
  const actor = me?.display_name ?? "Hệ thống";
  const known = new Map<string, string>(store().flatMap((r) => r.lines.map((l) => [l.item_code, l.item_name] as [string, string])));
  store().unshift({
    id: receiptId,
    supplier: body.supplier,
    warehouse: body.warehouse || 1,
    received_date: receivedDate,
    status: "SUBMITTED",
    created_by: me?.id ?? 1,
    created_at: new Date(createdAt).toISOString(),
    note: "",
    lines: body.lines.map((l, idx) => ({
      id: nextLineId++,
      item: nextLineId,
      item_code: l.item_code,
      item_name: known.get(l.item_code) ?? l.item_code,
      qty: Number(l.qty) || 0,
      rate: Number(l.rate) || 0,
      shelf_life_days: l.shelf_life_days ?? null,
      batch: nextBatchId++,
      batch_code: batches[idx].batch_id,
      batch_status: "DRAFT",
      expiry_date: batches[idx].expiry_date,
    })),
    events: [
      { at: new Date(createdAt).toISOString(), label: "Tạo phiếu nhập", actor },
      { at: new Date(createdAt + 1000).toISOString(), label: "Ghi nhận phiếu nhập và nhập lô", actor },
    ],
  });

  return { status: 201, body: resp };
}

/** Lý do không huỷ được phiếu theo luật BE (BR-MH-07); chuỗi rỗng = huỷ được. */
function cancelBlock(r: MockReceipt): string {
  if (r.status === "CANCELLED") return "Phiếu nhập đã bị huỷ.";
  if (mockInvoicesOfReceipt(r.id).length > 0) return "Không thể huỷ phiếu nhập đã gắn hoá đơn mua.";
  if (mockCostsOfBatches(batchIds(r)).length > 0) return "Không thể huỷ phiếu nhập đã phân bổ chi phí mua hàng.";
  const moved = r.lines.find((l) => l.batch_status && l.batch_status !== "DRAFT");
  if (moved) return `Lô ${moved.batch_code} đã chuyển sang trạng thái khác Nháp, không thể huỷ phiếu.`;
  return "";
}

export function mockCancelPurchaseReceipt(req: MockRequest): {
  status: number;
  body: CancelPurchaseReceiptResponse | { detail: string; code?: string };
} {
  const receiptId = idOfPath(req.path, /\/receipts\/(\d+)\/cancel\/?/) ?? 0;
  if (!receiptId) {
    return {
      status: 400,
      body: { detail: "Mã phiếu nhập không hợp lệ.", code: "BR-MH-07" },
    };
  }
  const me = mockRequireUser(req);
  const r = store().find((x) => x.id === receiptId);
  if (!r) return { status: 404, body: { detail: "Không tìm thấy." } };
  if (me && !can(me, "purchasing.change_purchasereceipt")) return { status: 403, body: { detail: "Bạn không có quyền để thực hiện thao tác này." } };
  const reason = cancelBlock(r);
  if (reason) return { status: 400, body: { detail: reason, code: "BR-MH-07" } };

  r.status = "CANCELLED";
  r.lines = r.lines.map((l) => ({ ...l, batch_status: l.batch ? "CANCELLED" : null }));
  r.events.push({ at: new Date().toISOString(), label: "Huỷ phiếu nhập", actor: me?.display_name ?? "Hệ thống" });

  const existing = mockReceiptsStore.get(receiptId);
  if (existing) {
    existing.receipt.status = "CANCELLED";
    existing.batches = existing.batches.map((b) => ({
      ...b,
      status: "CANCELLED",
    }));
  }

  return {
    status: 200,
    body: {
      id: receiptId,
      status: "CANCELLED",
    },
  };
}
