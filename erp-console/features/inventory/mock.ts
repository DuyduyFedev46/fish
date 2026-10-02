// Mock module inventory — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1. Dữ liệu bịa, không có thông tin khách.
// Lô 7 (ED-23/24/25/29): kho 16 lô trong bộ nhớ trang, MỘT nguồn cho cả danh sách lô (R5), chi tiết lô, sổ nhập xuất (R6),
// kho (R7), phiếu điều chỉnh tồn (R7b), đơn theo lô (R3) và lãi lỗ lô. Thao tác mở bán / trả nhà cung cấp / huỷ phần tồn / chốt
// đổi kho này và GHI THÊM dòng vào sổ nhập xuất, nên sau thao tác mọi màn thấy cùng một số.
//   - 3 lô Quá hạn còn tồn (id 901–903) giữ nguyên từ P8 Lô 5 (SR-15/SR-16): L0908-CT00 sạch, L0909-MU00 đang giữ chỗ, L0910-TS00 sạch.
//   - `purchase_rate`/`landed_unit_cost` chỉ có khi người đăng nhập có inventory.view_costprice (loc), y như BE.
// Trạng thái nằm trong bộ nhớ trang (tải lại trang = về seed), nên mỗi lần chạy e2e đều bắt đầu từ seed.
// Công cụ thử trong DevTools (chỉ có ở mock):
//   window.__caveMock.expiredSetQty("L0908-CT00", 4)   — đổi tồn "phía máy chủ" mà màn đang mở chưa biết (thử 400 tồn đã đổi)
//   window.__caveMock.expiredSetStatus("L0908-CT00", "CANCELLED") — đổi trạng thái "phía máy chủ" (giả lập tab khác đã huỷ/chốt/mở bán)
//   window.__caveMock.expiredState()                  — xem tồn/trạng thái các lô
//   window.__caveMock.expiredReset()                  — về lại seed
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { dateKeyInVietnam, kg, todayInVietnam } from "@/shared/lib/format";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import type { Me } from "@/features/auth/types";
import type { GuidanceData, GuidanceNextStep, GuidanceTimelineEntry } from "@/features/guidance/types";
import type { LedgerEntry, MovementType } from "@/features/ledger/types";
import type { BatchApiRow, BatchProfitReport, OrderUsingBatch, StockEntry, Warehouse } from "./types";

// ---- Kho lô ----

type LotStatus = "DRAFT" | "SELLING" | "NEAR_EXPIRY" | "SOLD_OUT" | "EXPIRED" | "CANCELLED" | "CLOSED";

type MockLot = {
  id: number;
  batch_id: string;
  item_code: string;
  item: string;
  supplier: string;
  warehouse_id: number;
  received_days_ago: number;
  /** Số ngày tới hạn dùng; âm = đã quá hạn. */
  expiry_days_ahead: number;
  qty_available: number;
  qty_reserved: number;
  status: LotStatus;
  cost: number;
  /** Số kg đã bán (chỉ để dựng sổ nhập xuất và tính doanh thu mock). */
  sold: number;
  receipt_id: number | null;
  closed_at: string | null;
  /** Hết hàng nhưng chưa có hoá đơn mua → chốt lô bị chặn. */
  missing_purchase_invoice?: boolean;
};

type MockEntry = {
  id: number;
  lot_id: number;
  type: MovementType;
  qty: number;
  display: string;
  link: { kind: string; id: number } | null;
  at: number;
  by: string;
};

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
const COLD = 1;
const COOL = 2;

const WAREHOUSE_SEED = [
  { id: COLD, name: "Kho lạnh Bến Đá", is_group: false },
  { id: COOL, name: "Kho mát chợ Vũng Tàu", is_group: false },
  { id: 3, name: "Cụm kho phía Nam", is_group: true },
];

// [id, mã lô, mã mặt hàng, tên mặt hàng, nhà cung cấp, kho, ngày nhập (trước), hạn (sau), tồn, giữ chỗ, trạng thái, giá vốn/kg, đã bán, id phiếu nhập]
type SeedRow = [number, string, string, string, string, number, number, number, number, number, LotStatus, number, number, number | null];
const SEED_ROWS: SeedRow[] = [
  [1, "L0914-CT01", "CA-THU-PL", "Cá thu phi lê", "Ghe Tư Hải", COLD, 10, 4, 18.5, 2, "NEAR_EXPIRY", 182000, 6.5, 92],
  [2, "L0915-MU02", "MUC-LA", "Mực lá câu", "Vựa Bà Năm", COLD, 9, 1, 12, 1.5, "NEAR_EXPIRY", 236500, 4, 93],
  [3, "L0916-TS01", "TOM-SU-20", "Tôm sú size 20", "Tàu Phước Lộc 07", COLD, 8, 9, 25.25, 0, "SELLING", 312000, 7, 94],
  [4, "L0917-CB01", "CA-BOP-CK", "Cá bớp cắt khúc", "Ghe Tư Hải", COLD, 7, 21, 30, 4, "SELLING", 158000, 8, 95],
  [5, "L0918-GX01", "GHE-XANH", "Ghẹ xanh", "Vựa Bà Năm", COOL, 6, 2, 9.8, 0.8, "SELLING", 265000, 5, 96],
  [6, "L0918-CH01", "CA-HONG-DO", "Cá hồng đỏ", "Tàu Phước Lộc 07", COLD, 6, 25, 22.4, 0, "SELLING", 142500, 4, 97],
  [7, "L0919-CN01", "CA-NGU-LOIN", "Cá ngừ đại dương loin", "Tàu Phước Lộc 07", COLD, 5, 30, 41.75, 6.5, "SELLING", 205000, 9, 98],
  [8, "L0920-CC01", "CA-CHIM-TR", "Cá chim trắng", "Ghe Tư Hải", COLD, 4, 12, 16, 0, "SELLING", 176000, 3, 99],
  [9, "L0921-MU03", "MUC-ONG", "Mực ống", "Vựa Bà Năm", COLD, 3, 18, 0, 0, "SOLD_OUT", 198000, 12, 100],
  [10, "L0921-CT02", "CA-THU-NC", "Cá thu nguyên con", "Ghe Tư Hải", COLD, 3, 28, 35, 3, "SELLING", 149000, 5, 101],
  [11, "L0922-TS02", "TOM-SU-30", "Tôm sú size 30", "Tàu Phước Lộc 07", COLD, 2, 26, 20, 0, "DRAFT", 268000, 0, 102],
  [12, "L0923-SO01", "SO-DIEP", "Sò điệp", "Vựa Bà Năm", COOL, 1, 5, 14.2, 0, "DRAFT", 88000, 0, 103],
  [13, "L0901-CB00", "CA-BOP-CK", "Cá bớp cắt khúc", "Ghe Tư Hải", COLD, 23, -2, 0, 0, "CLOSED", 151000, 20, null],
  [901, "L0908-CT00", "CA-THU-PL", "Cá thu phi lê", "Ghe Tư Hải", COLD, 12, -2, 6.5, 0, "EXPIRED", 182000, 9, 91],
  [902, "L0909-MU00", "MUC-LA", "Mực lá câu", "Vựa Bà Năm", COLD, 11, -1, 4, 1.5, "EXPIRED", 236500, 6, 90],
  [903, "L0910-TS00", "TOM-SU-20", "Tôm sú size 20", "Tàu Phước Lộc 07", COLD, 10, -1, 3, 0, "EXPIRED", 312000, 5, 89],
];

/** Dòng nhập xuất ngoài nhập/bán của một số lô: [mã lô, loại, kg (có dấu), chứng từ hiển thị, liên kết]. */
type ExtraRow = [string, MovementType, number, string, { kind: string; id: number } | null];
const EXTRA_ROWS: ExtraRow[] = [
  ["L0914-CT01", "RECONCILE", -0.4, "KK-13", { kind: "stocktake", id: 13 }],
  ["L0918-GX01", "CANCEL_RESTORE", 1.2, "SO260929-B6D720", { kind: "order", id: 6001 }],
  ["L0916-TS01", "RETURN_RESTOCK", 0.8, "RT-21", { kind: "return", id: 21 }],
  ["L0901-CB00", "WRITE_OFF", -1.1, "L0901-CB00", { kind: "batch", id: 13 }],
];

const STAFF_RECEIVER = "Tâm";

let lots: MockLot[] | null = null;
let entries: MockEntry[] = [];
let warehouses = WAREHOUSE_SEED.map((w) => ({ ...w }));
let nextEntryId = 1;
let nextReturnId = 1;
let nextWarehouseId = 10;
type ReturnResult = { batch_id: string; status: string; qty_available: string; returned_qty: string; return_id: number };
const returns = new Map<string, ReturnResult>();

const round3 = (n: number) => Math.round(n * 1000) / 1000;
const pad = (n: number, len = 2) => String(n).padStart(len, "0");

/** Mã hoá đơn bán dạng INV<yymmdd>-<6 ký tự hex> (giống mã thật), suy từ ngày + số thứ tự để ổn định. */
function invoiceCode(at: number, seed: number): string {
  const key = dateKeyInVietnam(new Date(at)).replace(/-/g, "").slice(2);
  return `INV${key}-${((seed * 2654435761) >>> 0).toString(16).toUpperCase().padStart(8, "0").slice(0, 6)}`;
}

function build(): void {
  const now = Date.now();
  nextEntryId = 1;
  nextReturnId = 1;
  returns.clear();
  warehouses = WAREHOUSE_SEED.map((w) => ({ ...w }));
  entries = [];
  lots = SEED_ROWS.map(([id, batch_id, item_code, item, supplier, warehouse_id, recv, exp, avail, res, status, cost, sold, receipt]) => ({
    id,
    batch_id,
    item_code,
    item,
    supplier,
    warehouse_id,
    received_days_ago: recv,
    expiry_days_ahead: exp,
    qty_available: avail,
    qty_reserved: res,
    status,
    cost,
    sold,
    receipt_id: receipt,
    closed_at: status === "CLOSED" ? new Date(now - 2 * DAY).toISOString() : null,
    missing_purchase_invoice: batch_id === "L0921-MU03" || undefined,
  }));
  for (const lot of lots) {
    const extras = EXTRA_ROWS.filter((e) => e[0] === lot.batch_id);
    const extraNet = extras.reduce((s, e) => s + e[2], 0);
    const received = round3(lot.qty_available + lot.sold - extraNet);
    const receivedAt = now - lot.received_days_ago * DAY - 3 * HOUR;
    entries.push({
      id: nextEntryId++,
      lot_id: lot.id,
      type: "RECEIPT",
      qty: received,
      display: lot.receipt_id ? `PR-${lot.receipt_id}` : lot.batch_id,
      link: lot.receipt_id ? { kind: "receipt", id: lot.receipt_id } : { kind: "batch", id: lot.id },
      at: receivedAt,
      by: STAFF_RECEIVER,
    });
    const span = now - receivedAt - HOUR;
    const parts = lot.sold > 0 ? (lot.sold > 5 ? 3 : 2) : 0;
    let left = lot.sold;
    for (let i = 0; i < parts; i += 1) {
      const qty = i === parts - 1 ? left : round3(lot.sold / parts);
      left = round3(left - qty);
      const at = receivedAt + Math.round(((i + 1) / (parts + 1)) * span) + HOUR;
      entries.push({
        id: nextEntryId++,
        lot_id: lot.id,
        type: "SALE",
        qty: -qty,
        display: invoiceCode(at, lot.id * 10 + i),
        link: { kind: "invoice", id: lot.id * 10 + i },
        at,
        by: "",
      });
    }
    extras.forEach(([, type, qty, display, link], i) => {
      entries.push({
        id: nextEntryId++,
        lot_id: lot.id,
        type,
        qty,
        display,
        link,
        at: receivedAt + Math.round(((i + 1) / (extras.length + 2)) * span) + 2 * HOUR,
        by: type === "RECONCILE" ? "Hà" : STAFF_RECEIVER,
      });
    });
  }
}

function state(): MockLot[] {
  if (!lots) build();
  return lots as MockLot[];
}

const dec3 = (n: number) => n.toFixed(3);
const fmtKg = (n: number) => n.toFixed(3).replace(".", ",");
const err = (status: number, code: string, detail: string): MockResponse => ({ status, body: { code, detail } });
const FORBIDDEN: MockResponse = { status: 403, body: { detail: "Bạn không có quyền để thực hiện thao tác này." } };
const NOT_FOUND: MockResponse = { status: 404, body: { detail: "Không tìm thấy." } };

const can = (me: Me, perm: string) => me.permissions.includes(perm);
/** Chủ = có quyền huỷ phần tồn lô quá hạn (BE cấp cho nhóm owner; auth/mock đã chép đúng). */
const isOwner = (me: Me) => can(me, "inventory.cancel_expired_batch");

function isoDay(daysFromNow: number): string {
  // Ngày theo giờ VN (SR-25), không theo múi giờ máy. VN không đổi giờ mùa hè nên cộng N×24h = N ngày.
  return todayInVietnam(new Date(Date.now() + daysFromNow * DAY));
}

function findLot(ref: string | number): MockLot | undefined {
  let text = String(ref);
  try {
    text = decodeURIComponent(text);
  } catch {
    // giữ nguyên
  }
  return state().find((l) => String(l.id) === text || l.batch_id === text);
}

function warehouseName(id: number): string {
  return warehouses.find((w) => w.id === id)?.name ?? "";
}

function parseQuery(path: string): URLSearchParams {
  return new URLSearchParams(path.split("?")[1] || "");
}

function paginate<T>(rows: T[], page: number, size: number, path: string): MockResponse {
  const start = (page - 1) * size;
  const base = path.split("?")[0];
  const next = start + size < rows.length ? `${base}?page=${page + 1}` : null;
  return { status: 200, body: { count: rows.length, next, previous: page > 1 ? `${base}?page=${page - 1}` : null, results: rows.slice(start, start + size) } };
}

function pageOf(q: URLSearchParams): number {
  const n = Number(q.get("page") || 1);
  return Number.isInteger(n) && n >= 1 ? n : 1;
}

/** Số lô Quá hạn còn tồn — con số ở thẻ Cần chú ý `expired_batches_open` (features/overview/mock.ts). */
export function mockExpiredOpenCount(): number {
  return state().filter((l) => l.status === "EXPIRED" && l.qty_available > 0).length;
}

const STATUS_LABEL: Record<LotStatus, string> = {
  DRAFT: "Nháp",
  SELLING: "Đang bán",
  NEAR_EXPIRY: "Cận hạn",
  SOLD_OUT: "Hết hàng",
  EXPIRED: "Quá hạn",
  CANCELLED: "Đã huỷ",
  CLOSED: "Đã chốt",
};

function receivedQty(l: MockLot): number {
  return entries.find((e) => e.lot_id === l.id && e.type === "RECEIPT")?.qty ?? l.qty_available;
}

function toApiRow(l: MockLot, canCost: boolean): BatchApiRow {
  const row: BatchApiRow = {
    id: l.id,
    batch_id: l.batch_id,
    item: l.id,
    item_code: l.item_code,
    item_name: l.item,
    supplier: l.id,
    supplier_name: l.supplier,
    warehouse: l.warehouse_id,
    warehouse_name: warehouseName(l.warehouse_id),
    received_date: isoDay(-l.received_days_ago),
    expiry_date: isoDay(l.expiry_days_ahead),
    qty_received: dec3(receivedQty(l)),
    qty_available: dec3(l.qty_available),
    qty_reserved: dec3(l.qty_reserved),
    qty_sellable: dec3(Math.max(0, l.qty_available - l.qty_reserved)),
    status: l.status,
    status_label: STATUS_LABEL[l.status],
    closed_at: l.closed_at,
    receipt: l.receipt_id ? { id: l.receipt_id, code: `PR-${l.receipt_id}` } : null,
  };
  if (canCost) {
    row.purchase_rate = String(l.cost - 7000);
    row.landed_unit_cost = String(l.cost);
  }
  return row;
}

/** GET /api/inventory/batches/ (R5): lô còn bán được trước, hạn sớm trước; lô đã đóng cuối. */
export function mockBatchList(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "inventory.view_batch")) return FORBIDDEN;
  const q = parseQuery(req.path);
  const status = q.get("status");
  if (status && !(status in STATUS_LABEL)) return err(400, "INVALID_FILTER", "Trạng thái lô không hợp lệ.");
  const warehouse = q.get("warehouse");
  if (warehouse && !/^\d+$/.test(warehouse)) return err(400, "INVALID_FILTER", "Bộ lọc kho không hợp lệ.");
  const hasStock = ["1", "true"].includes((q.get("has_stock") || "").toLowerCase());
  const closedLast = (l: MockLot) => (l.status === "CLOSED" || l.status === "CANCELLED" ? 1 : 0);
  const rows = state()
    .filter((l) => (!status || l.status === status) && (!warehouse || String(l.warehouse_id) === warehouse) && (!hasStock || l.qty_available > 0))
    .sort((a, b) => closedLast(a) - closedLast(b) || a.expiry_days_ahead - b.expiry_days_ahead || a.id - b.id)
    .map((l) => toApiRow(l, me.can_view_cost));
  return paginate(rows, pageOf(q), 50, req.path);
}

/** GET /api/inventory/batches/<id hoặc mã>/. */
export function mockBatchDetail(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "inventory.view_batch")) return FORBIDDEN;
  const ref = req.path.split("?")[0].replace(/\/$/, "").split("/").pop() || "";
  const lot = findLot(ref);
  return lot ? { status: 200, body: toApiRow(lot, me.can_view_cost) } : NOT_FOUND;
}

// ---- Sổ nhập xuất (R6) — handler nằm ở features/ledger/mock.ts, kho dữ liệu ở đây ----

const MOVEMENT_LABEL: Record<MovementType, string> = {
  RECEIPT: "Nhập lô",
  SALE: "Bán ra",
  RETURN_RESTOCK: "Hàng hoàn tái nhập",
  RECONCILE: "Điều chỉnh kiểm kê",
  WRITE_OFF: "Ghi lỗ, huỷ hàng",
  CANCEL_RESTORE: "Hoàn kho do huỷ đơn",
  SUPPLIER_RETURN: "Trả nhà cung cấp",
};
export const MOCK_MOVEMENT_TYPES: string[] = Object.keys(MOVEMENT_LABEL);

/** Toàn bộ sổ, mới nhất trước, đã có `balance_after` (tồn của lô sau dòng đó). */
export function mockLedgerRows(): LedgerEntry[] {
  const all = state();
  const balance = new Map<number, number>();
  const ascending = [...entries].sort((a, b) => a.at - b.at || a.id - b.id);
  const rows = ascending.map((e) => {
    const lot = all.find((l) => l.id === e.lot_id) as MockLot;
    const after = round3((balance.get(lot.id) ?? 0) + e.qty);
    balance.set(lot.id, after);
    const row: LedgerEntry = {
      id: e.id,
      batch: lot.id,
      batch_code: lot.batch_id,
      item: lot.id,
      item_name: lot.item,
      warehouse: lot.warehouse_id,
      warehouse_name: warehouseName(lot.warehouse_id),
      movement_type: e.type,
      type_label: MOVEMENT_LABEL[e.type],
      qty_change: dec3(e.qty),
      balance_after: dec3(after),
      reference: e.display,
      reference_display: e.display,
      reference_link: e.link,
      created_at: new Date(e.at).toISOString(),
      created_by: e.by ? 7 : null,
      created_by_name: e.by,
    };
    return row;
  });
  return rows.reverse();
}

function addEntry(lot: MockLot, type: MovementType, qty: number, display: string, link: MockEntry["link"], by: string): void {
  entries.push({ id: nextEntryId++, lot_id: lot.id, type, qty, display, link, at: Date.now(), by });
}

// ---- Kho (R7) ----

function warehouseRow(w: { id: number; name: string; is_group: boolean }): Warehouse {
  const mine = state().filter((l) => l.warehouse_id === w.id && l.qty_available > 0);
  return {
    id: w.id,
    name: w.name,
    is_group: w.is_group,
    is_group_label: w.is_group ? "Nhóm kho" : "Kho",
    active_batch_count: mine.length,
    total_qty: dec3(round3(mine.reduce((s, l) => s + l.qty_available, 0))),
  };
}

export function mockWarehouses(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "inventory.view_warehouse")) return FORBIDDEN;
  state();
  const rows = [...warehouses].sort((a, b) => a.name.localeCompare(b.name, "vi")).map(warehouseRow);
  return paginate(rows, pageOf(parseQuery(req.path)), 50, req.path);
}

/** POST /api/inventory/warehouses/ — chỉ Chủ. Lỗi theo `warehouse_services.create_warehouse`. */
export function mockAddWarehouse(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "inventory.add_warehouse")) return FORBIDDEN;
  state();
  const body = (req.body || {}) as { name?: string; is_group?: boolean };
  const name = (body.name || "").split(/\s+/).filter(Boolean).join(" ");
  if (!name) return err(400, "WAREHOUSE_NAME_REQUIRED", "Nhập tên kho.");
  if (name.length > 120) return err(400, "WAREHOUSE_NAME_TOO_LONG", "Tên kho tối đa 120 ký tự.");
  if (warehouses.some((w) => w.name.toLowerCase() === name.toLowerCase())) return err(400, "WAREHOUSE_NAME_TAKEN", "Tên kho đã có, chọn tên khác.");
  const created = { id: nextWarehouseId++, name, is_group: Boolean(body.is_group) };
  warehouses.push(created);
  return { status: 201, body: warehouseRow(created) };
}

// ---- Phiếu điều chỉnh tồn (R7b, chỉ đọc) ----

function stockEntrySeed(): StockEntry[] {
  const now = Date.now();
  const rows: Array<[number, string, string, number, string, string, number]> = [
    [3, "ADJUSTMENT", "L0914-CT01", -0.4, "Cá mềm thịt, loại bỏ khi sơ chế.", "Hà", 1.2],
    [4, "MATERIAL_RECEIPT", "L0916-TS01", 2, "Nhận thêm hàng bù từ ghe.", "Tâm", 2.1],
    [5, "ADJUSTMENT", "L0917-CB01", -0.25, "Hao hụt khi cân lại.", "Tâm", 3.4],
    [6, "ADJUSTMENT", "L0918-GX01", -0.6, "Ghẹ chết, bỏ.", "Hà", 4.2],
    [7, "MATERIAL_RECEIPT", "L0919-CN01", 1.5, "Nhập bổ sung theo biên bản giao.", "Tâm", 5.5],
    [8, "ADJUSTMENT", "L0915-MU02", -0.3, "Mực dập, loại bỏ.", "Hà", 6.1],
  ];
  return rows.map(([id, purpose, code, qty, reason, by, daysAgo]) => {
    const lot = SEED_ROWS.find((r) => r[1] === code) as SeedRow;
    return {
      id,
      code: `SE-${id}`,
      purpose,
      purpose_label: purpose === "ADJUSTMENT" ? "Điều chỉnh" : "Nhập vật tư",
      batch: lot[0],
      batch_code: code,
      item_name: lot[3],
      qty_change: dec3(qty),
      reason,
      created_by: 7,
      created_by_name: by,
      created_at: new Date(now - daysAgo * DAY).toISOString(),
    };
  });
}

export function mockStockEntries(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "inventory.view_stockentry")) return FORBIDDEN;
  const q = parseQuery(req.path);
  const purposes = (q.get("purpose") || "").split(",").filter(Boolean);
  if (purposes.some((p) => p !== "ADJUSTMENT" && p !== "MATERIAL_RECEIPT")) return err(400, "INVALID_FILTER", "Mục đích không hợp lệ.");
  const from = q.get("date_from") || "";
  const to = q.get("date_to") || "";
  if ([from, to].some((d) => d && !/^\d{4}-\d{2}-\d{2}$/.test(d))) return err(400, "INVALID_FILTER", "Ngày không hợp lệ.");
  const rows = stockEntrySeed().filter((e) => {
    const day = dateKeyInVietnam(e.created_at);
    return (!purposes.length || purposes.includes(e.purpose)) && (!from || day >= from) && (!to || day <= to);
  });
  return paginate(rows, pageOf(q), 20, req.path);
}

// ---- Đơn theo lô (R3) và lãi lỗ lô ----

function lotPrice(l: MockLot): number {
  return Math.round((l.cost * 1.42) / 1000) * 1000;
}

/** GET /api/sales/orders/?batch=<id>. Mỗi dòng bán ra của lô là một đơn Hoàn tất; lô đang giữ chỗ có thêm một đơn Giữ chỗ. */
export function mockOrdersByBatch(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "sales.view_salesorder")) return FORBIDDEN;
  const q = parseQuery(req.path);
  const batch = q.get("batch");
  if (!batch || !/^\d+$/.test(batch)) return err(400, "INVALID_FILTER", "Bộ lọc lô không hợp lệ.");
  const lot = findLot(batch);
  if (!lot) return paginate([], 1, 20, req.path);
  const rows: OrderUsingBatch[] = entries
    .filter((e) => e.lot_id === lot.id && e.type === "SALE")
    .sort((a, b) => b.at - a.at)
    .map((e) => ({
      id: 7000 + e.id,
      code: `SO${dateKeyInVietnam(new Date(e.at)).replace(/-/g, "").slice(2)}-${e.display.slice(-6)}`,
      status: "COMPLETED",
      total_amount: String(Math.round(Math.abs(e.qty) * lotPrice(lot))),
      created_at: new Date(e.at).toISOString(),
    }));
  if (lot.qty_reserved > 0) {
    rows.unshift({
      id: 7000 + lot.id,
      code: `SO${todayInVietnam().replace(/-/g, "").slice(2)}-${pad(lot.id, 3)}A2C`,
      status: "BOOKED",
      total_amount: String(Math.round(lot.qty_reserved * lotPrice(lot))),
      created_at: new Date(Date.now() - 20 * 60_000).toISOString(),
    });
  }
  return paginate(rows, 1, 20, req.path);
}

/** GET /api/reports/batch/<mã lô>/ — chỉ Chủ (reports.view_profitreport). */
export function mockBatchProfit(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "reports.view_profitreport")) return FORBIDDEN;
  const ref = req.path.split("?")[0].replace(/\/$/, "").split("/").pop() || "";
  const lot = findLot(ref);
  if (!lot) return { status: 404, body: { detail: "Không tìm thấy lô." } };
  const received = receivedQty(lot);
  const revenue = Math.round(lot.sold * lotPrice(lot));
  const lossQty = Math.max(0, round3(received - lot.sold - lot.qty_available));
  const totalCost = Math.round(received * lot.cost);
  const report: BatchProfitReport = {
    batch_id: lot.batch_id,
    provisional: lot.status !== "CLOSED",
    qty_received: dec3(received),
    qty_sold: dec3(lot.sold),
    shrinkage_qty: dec3(lossQty),
    landed_unit_cost: String(lot.cost),
    revenue: String(revenue),
    total_cost: String(totalCost),
    profit: String(revenue - totalCost),
  };
  return { status: 200, body: report };
}

// ---- Guidance của lô (do features/guidance/mock.ts gọi) ----

type StepMissing = { code: string; text: string };

const NO_PERMISSION: StepMissing = { code: "BR-PQ-12", text: "Chỉ Chủ được thực hiện." };

function step(
  key: string,
  label: string,
  actor: "user" | "system",
  who: string[],
  missing: StepMissing[],
  command: string | null,
  br: string,
  why: string,
  deadline: string | null = null,
): GuidanceNextStep {
  return { key, label, actor, allowed: actor === "user" && missing.length === 0, who, missing, deadline, why: { br, text: why }, command, ai: null };
}

function timelineOf(lot: MockLot): GuidanceTimelineEntry[] {
  const mine = entries.filter((e) => e.lot_id === lot.id).sort((a, b) => a.at - b.at || a.id - b.id);
  const out: GuidanceTimelineEntry[] = [];
  const user = (display: string) => ({ kind: "user" as const, display: display || "Hệ thống" });
  for (const e of mine) {
    const at = new Date(e.at).toISOString();
    if (e.type === "RECEIPT") out.push({ at, kind: "batch_created", label: `Nhập lô ${kg(e.qty)} từ ${e.display}`, doc: "batch", actor: user(e.by) });
    else if (e.type === "RECONCILE") out.push({ at, kind: "stocktake", label: `Kiểm kê ${e.display} điều chỉnh ${kg(e.qty)}`, doc: "batch", actor: user(e.by) });
    else if (e.type === "WRITE_OFF") out.push({ at, kind: "write_off", label: `Huỷ phần tồn ${kg(-e.qty)}, ghi lỗ`, doc: "batch", actor: user(e.by) });
    else if (e.type === "SUPPLIER_RETURN") out.push({ at, kind: "supplier_return", label: `Trả nhà cung cấp ${kg(-e.qty)} (${e.display})`, doc: "batch", actor: user(e.by) });
    else if (e.type === "RETURN_RESTOCK") out.push({ at, kind: "restock", label: `Hàng hoàn tái nhập ${kg(e.qty)}`, doc: "batch", actor: user(e.by) });
  }
  const first = mine[0]?.at ?? Date.now();
  if (lot.status !== "DRAFT") out.push({ at: new Date(first + 35 * 60_000).toISOString(), kind: "published", label: "Mở bán trên Shop", doc: "batch", actor: user("Hà") });
  if (lot.status === "EXPIRED") out.push({ at: new Date(Date.now() - 12 * HOUR).toISOString(), kind: "expired", label: "Hệ thống chuyển lô sang Quá hạn", doc: "batch", actor: { kind: "system", display: "Hệ thống" } });
  return out;
}

/** Guidance `GET /api/guidance/batch/<id>/` cho lô mock; null = không phải lô của module này (guidance mock trả mặc định). */
export function mockExpiredBatchGuidance(docId: string, req: MockRequest): MockResponse | null {
  const lot = findLot(docId);
  if (!lot) return null;
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const owner = isOwner(me);
  const steps: GuidanceNextStep[] = [];
  const reservedMissing: StepMissing[] =
    lot.qty_reserved > 0 ? [{ code: "BR-LO-07", text: `Còn ${fmtKg(lot.qty_reserved)} kg đang giữ chỗ của 1 đơn — chờ đơn xử lý xong.` }] : [];
  const closeMissing: StepMissing[] = [
    ...(owner ? [] : [{ code: "BR-PQ-12", text: "Chỉ Chủ được chốt lô." }]),
    ...(lot.qty_available > 0 ? [{ code: "BR-LO-04", text: `Chốt lô yêu cầu tồn = 0 — còn ${fmtKg(lot.qty_available)} kg, xử lý hết phần tồn trước.` }] : []),
    ...(lot.qty_available <= 0 && lot.missing_purchase_invoice ? [{ code: "BR-LO-04", text: "Lô chưa có hoá đơn mua, chưa chốt được." }] : []),
  ];
  if (lot.status === "DRAFT") {
    steps.push(
      step("publish", "Mở bán lô", "user", ["Quản lý", "Chủ"], can(me, "inventory.publish_batch") ? [] : [{ code: "BR-PQ-12", text: "Chỉ Quản lý hoặc Chủ được mở bán." }], "inventory.batch.publish", "BR-MH-05", "Lô nháp chỉ bán được sau khi mở bán."),
    );
  } else if (lot.status === "SELLING") {
    steps.push(step("auto_near_expiry", "Hệ thống sẽ chuyển Cận hạn", "system", ["Hệ thống"], [], null, "BR-LO-06", "Lô gần hết hạn tự chuyển Cận hạn.", new Date(Date.now() + 5 * DAY).toISOString()));
  } else if (lot.status === "NEAR_EXPIRY") {
    steps.push(step("auto_expire", "Hệ thống sẽ chuyển Quá hạn", "system", ["Hệ thống"], [], null, "BR-LO-06", "Quá hạn dùng thì lô tự chuyển Quá hạn.", new Date(Date.now() + Math.max(1, lot.expiry_days_ahead) * DAY).toISOString()));
  } else if (lot.status === "EXPIRED" && lot.qty_available > 0) {
    const miss = [...(owner ? [] : [NO_PERMISSION]), ...reservedMissing];
    steps.push(
      step("cancel_expired", "Huỷ phần tồn, ghi lỗ", "user", ["Chủ"], miss, "inventory.batch.cancel_expired", "BR-LO-07", "Phần tồn quá hạn phải được xử lý: huỷ (ghi lỗ) hoặc trả nhà cung cấp."),
      step("return_to_supplier", "Trả nhà cung cấp", "user", ["Chủ"], miss, "inventory.batch.return_to_supplier", "BR-MH-08", "Ghi số kg đã trả nhà cung cấp; có thể chia nhiều lần."),
    );
  }
  if (lot.status === "SELLING" || lot.status === "NEAR_EXPIRY" || lot.status === "SOLD_OUT" || lot.status === "EXPIRED") {
    steps.push(step("close", "Chốt lô", "user", ["Chủ"], closeMissing, "inventory.batch.close", "BR-LO-04", "Lô chỉ chốt khi không còn tồn."));
  }
  const data: GuidanceData = {
    doc: { type: "batch", id: docId, code: lot.batch_id, status: lot.status, status_label: STATUS_LABEL[lot.status] },
    next_steps: steps,
    warnings:
      lot.status === "EXPIRED" && lot.qty_available > 0
        ? [{ code: "GW-LO-07", text: `Lô quá hạn còn ${fmtKg(lot.qty_available)} kg tồn — cần huỷ phần tồn hoặc trả nhà cung cấp.` }]
        : [],
    timeline: timelineOf(lot),
    related: [],
  };
  return { status: 200, body: data };
}

// ---- Thao tác ----

/** POST publish / cancel-expired / close. `confirm_qty` (chuỗi thập phân) khác tồn thật → 400 BR-LO-07. */
export function mockBatchAction(kind: "publish" | "cancel-expired" | "close", batchId: string | number, req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const lot = findLot(batchId);
  if (!lot) return NOT_FOUND;
  if (kind === "publish") {
    if (!can(me, "inventory.publish_batch")) return FORBIDDEN;
    if (lot.status !== "DRAFT") return err(400, "BR-MH-05", "Chỉ mở bán lô đang ở trạng thái Nháp.");
    lot.status = "SELLING";
    return { status: 200, body: { id: lot.id, batch_id: lot.batch_id, status: lot.status, qty_available: dec3(lot.qty_available) } };
  }
  if (kind === "close") {
    if (!can(me, "inventory.close_batch")) return FORBIDDEN;
    if (lot.status === "CLOSED") return err(400, "BR-LO-05", "Lô đã chốt.");
    if (lot.qty_available > 0) return err(400, "BR-LO-04", `Chốt lô yêu cầu tồn = 0 (còn ${fmtKg(lot.qty_available)} kg).`);
    if (lot.missing_purchase_invoice) return err(400, "BR-LO-04", "Lô chưa có hoá đơn mua, chưa chốt được.");
    lot.status = "CLOSED";
    lot.closed_at = new Date().toISOString();
  } else {
    if (!isOwner(me)) return FORBIDDEN;
    if (lot.status === "CLOSED") return err(400, "BR-LO-05", "Lô đã chốt.");
    if (lot.status !== "EXPIRED") return err(400, "BR-LO-03", "Chỉ huỷ được lô Quá hạn.");
    if (lot.qty_reserved > 0) return err(400, "BR-LO-07", `Còn ${fmtKg(lot.qty_reserved)} kg đang giữ chỗ của 1 đơn — chờ đơn xử lý xong.`);
    const body = (req.body || {}) as { confirm_qty?: string };
    if (body.confirm_qty !== undefined && Number(body.confirm_qty) !== lot.qty_available)
      return err(400, "BR-LO-07", `Tồn đã đổi (${fmtKg(lot.qty_available)} kg) — tải lại.`);
    addEntry(lot, "WRITE_OFF", -lot.qty_available, lot.batch_id, { kind: "batch", id: lot.id }, me.display_name);
    lot.qty_available = 0;
    lot.status = "CANCELLED";
  }
  return { status: 200, body: { id: lot.id, batch_id: lot.batch_id, status: lot.status, qty_available: dec3(lot.qty_available) } };
}

/** POST return-to-supplier — contract 02b §5.4. `request_id` trùng → trả lại kết quả cũ, không trừ tồn lần 2. */
export function mockReturnToSupplier(batchId: string | number, req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const lot = findLot(batchId);
  if (!lot) return NOT_FOUND;
  if (!isOwner(me)) return FORBIDDEN;
  const body = (req.body || {}) as { qty?: string; supplier_refund_amount?: string; note?: string; request_id?: string };

  const previous = body.request_id ? returns.get(body.request_id) : undefined;
  if (previous) return { status: 200, body: previous };

  if (lot.status === "CLOSED") return err(400, "BR-LO-05", "Lô đã chốt.");
  if (lot.status !== "EXPIRED" || lot.qty_available <= 0) return err(400, "BR-LO-07", "Chỉ trả nhà cung cấp cho lô Quá hạn còn tồn.");
  if (lot.qty_reserved > 0) return err(400, "BR-LO-07", `Còn ${fmtKg(lot.qty_reserved)} kg đang giữ chỗ của 1 đơn — chờ đơn xử lý xong.`);
  const qty = Number(body.qty);
  if (!Number.isFinite(qty) || qty <= 0 || qty > lot.qty_available)
    return err(400, "BR-MH-08", `Số kg trả phải lớn hơn 0 và không vượt tồn ${fmtKg(lot.qty_available)} kg.`);
  const refund = Number(body.supplier_refund_amount || 0);
  if (!Number.isFinite(refund) || refund < 0) return err(400, "BR-MH-08", "Tiền nhà cung cấp hoàn không được âm.");
  if (/\d{8,}/.test(body.note || "")) return err(400, "BR-MH-08", "Ghi chú không được chứa dãy số dài (tránh nhập số điện thoại).");

  lot.qty_available = round3(lot.qty_available - qty);
  const returnId = nextReturnId++;
  addEntry(lot, "SUPPLIER_RETURN", -qty, `SR-${returnId}`, { kind: "supplier_return", id: returnId }, me.display_name);
  const result: ReturnResult = { batch_id: lot.batch_id, status: lot.status, qty_available: dec3(lot.qty_available), returned_qty: dec3(qty), return_id: returnId };
  if (body.request_id) returns.set(body.request_id, result);
  return { status: 200, body: result };
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    expiredSetQty: (batchId: string, qty: number) => {
      const l = findLot(batchId);
      if (l) l.qty_available = qty;
      return l ? `${l.batch_id}: tồn ${qty} kg` : "Không có lô";
    },
    expiredSetStatus: (batchId: string, status: LotStatus) => {
      const l = findLot(batchId);
      if (l) l.status = status;
      return l ? `${l.batch_id}: ${status}` : "Không có lô";
    },
    expiredState: () => state().map((l) => ({ batch_id: l.batch_id, status: l.status, qty_available: l.qty_available, qty_reserved: l.qty_reserved })),
    expiredReset: () => {
      build();
      return "Đã về seed";
    },
  };
}
