// Mock Kiểm kê (ED-28) — chạy khi NEXT_PUBLIC_USE_MOCK=1. Dựng theo contract THẬT của BE
// (backend/apps/inventory/stocktake/{api,serializers,services,queries}.py), có trạng thái để e2e đi hết vòng đời:
// nhập số → sửa số → duyệt bởi người khác, và đủ các lỗi: 409 STALE_STATE, 400 RECON_LINE_INVALID / BR-KK-04 (kèm `line_index`),
// BR-KK-02 / BR-KK-08 (không tự duyệt), RECON_EMPTY, RECON_STOCK_INSUFFICIENT, RECON_NOT_DRAFT.
//
// BR-KK-09 (đề xuất, chờ Duy chốt): duyệt áp ĐÚNG chênh lệch đã chụp lúc nhập số (counted − system_qty đã chụp), không tính lại theo
// tồn hiện tại. Mock làm đúng như BE để màn không hứa quá tay.
//
// Trạng thái lưu localStorage (`cave_erp_mock_stocktake`) để đổi người đăng nhập vẫn thấy cùng một phiếu (như một BE thật).
// Chỉ có tên NHÂN VIÊN, không có dữ liệu khách. Công cụ thử qua `window.__caveMock` (xem cuối file).
import { mockRequireUser } from "@/features/auth/mock";
import type { GuidanceData } from "@/features/guidance/types";
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { PERM } from "@/shared/lib/nav";
import { toMilli } from "./stocktakeUi";
import type { StocktakeAction, StocktakeDetail, StocktakeLine, StocktakeStatus } from "./types";

const KEY = "cave_erp_mock_stocktake";
const MAX_REASON = 500;
const MAX_LINES = 500;

type MockBatch = { id: number; batch_id: string; item_name: string; warehouse: number; warehouse_name: string; qty_available: string };
type MockLine = { batch: number; system_qty: string; counted_qty: string; reason: string };
type MockEvent = { at: string; label: string; actor: string };
type MockRec = {
  id: number;
  count_date: string;
  status: StocktakeStatus;
  note: string;
  created_by: { id: number; display_name: string };
  approved_by: { id: number; display_name: string } | null;
  approved_at: string | null;
  updated_at: string;
  last_actor: string;
  /** Id người đã sửa số đếm (BR-KK-08). */
  edited_by: number[];
  lines: MockLine[];
  events: MockEvent[];
};
type State = { recs: MockRec[]; batches: MockBatch[]; warehouses: { id: number; name: string }[] };

const TAM = { id: 3, display_name: "Anh Tâm" };
const HANH = { id: 2, display_name: "Chị Hạnh" };
const LOC = { id: 1, display_name: "Lộc" };

function seed(): State {
  const batches: MockBatch[] = [
    { id: 101, batch_id: "L0914-CT01", item_name: "Cá thu phi lê", warehouse: 1, warehouse_name: "Kho lạnh Bến Đá", qty_available: "18.500" },
    { id: 102, batch_id: "L0915-MU02", item_name: "Mực lá câu", warehouse: 1, warehouse_name: "Kho lạnh Bến Đá", qty_available: "12.000" },
    { id: 103, batch_id: "L0916-TS01", item_name: "Tôm sú size 20", warehouse: 1, warehouse_name: "Kho lạnh Bến Đá", qty_available: "25.250" },
    { id: 104, batch_id: "L0917-CB01", item_name: "Cá bớp cắt khúc", warehouse: 1, warehouse_name: "Kho lạnh Bến Đá", qty_available: "30.000" },
    { id: 105, batch_id: "L0919-CN01", item_name: "Cá ngừ đại dương loin", warehouse: 1, warehouse_name: "Kho lạnh Bến Đá", qty_available: "41.750" },
    { id: 201, batch_id: "L0923-SO01", item_name: "Sò điệp", warehouse: 2, warehouse_name: "Kho mát chợ Vũng Tàu", qty_available: "14.200" },
    { id: 202, batch_id: "L0922-TS02", item_name: "Tôm sú size 30", warehouse: 2, warehouse_name: "Kho mát chợ Vũng Tàu", qty_available: "20.000" },
  ];
  const warehouses = [
    { id: 1, name: "Kho lạnh Bến Đá" },
    { id: 2, name: "Kho mát chợ Vũng Tàu" },
    { id: 3, name: "Kho dự phòng" }, // không có lô còn tồn: thử trạng thái rỗng của form
  ];
  const ev = (at: string, label: string, actor: string): MockEvent => ({ at, label, actor });
  const recs: MockRec[] = [
    {
      id: 17, count_date: "2026-10-01", status: "DRAFT", note: "Phiếu trống để thử", created_by: TAM, approved_by: null, approved_at: null,
      updated_at: "2026-10-01T09:00:00.000+07:00", last_actor: TAM.display_name, edited_by: [], lines: [],
      events: [ev("2026-10-01T09:00:00+07:00", "Nhập số kiểm kê", TAM.display_name)],
    },
    {
      id: 16, count_date: "2026-10-01", status: "DRAFT", note: "Đếm đầu ca", created_by: TAM, approved_by: null, approved_at: null,
      updated_at: "2026-10-01T07:30:00.000+07:00", last_actor: TAM.display_name, edited_by: [],
      lines: [
        { batch: 201, system_qty: "14.200", counted_qty: "14.200", reason: "" },
        { batch: 202, system_qty: "20.000", counted_qty: "19.700", reason: "" },
      ],
      events: [ev("2026-10-01T07:30:00+07:00", "Nhập số kiểm kê", TAM.display_name)],
    },
    {
      id: 15, count_date: "2026-10-01", status: "DRAFT", note: "", created_by: HANH, approved_by: null, approved_at: null,
      updated_at: "2026-10-01T07:10:00.000+07:00", last_actor: HANH.display_name, edited_by: [],
      lines: [{ batch: 202, system_qty: "20.000", counted_qty: "19.800", reason: "" }],
      events: [ev("2026-10-01T07:10:00+07:00", "Nhập số kiểm kê", HANH.display_name)],
    },
    {
      id: 14, count_date: "2026-10-01", status: "DRAFT", note: "Đếm lại tủ đông số 2 sau khi rã đá", created_by: TAM, approved_by: null, approved_at: null,
      updated_at: "2026-10-01T07:34:00.000+07:00", last_actor: TAM.display_name, edited_by: [],
      lines: [
        { batch: 101, system_qty: "18.500", counted_qty: "18.100", reason: "" },
        { batch: 102, system_qty: "12.000", counted_qty: "11.600", reason: "Rút nước, đá tan" },
        { batch: 104, system_qty: "30.000", counted_qty: "30.300", reason: "Lần xuất 27/09/2026 ghi dư 0,3 kg" },
      ],
      events: [ev("2026-10-01T07:30:00+07:00", "Nhập số kiểm kê", TAM.display_name)],
    },
    {
      id: 13, count_date: "2026-09-24", status: "APPROVED", note: "", created_by: TAM, approved_by: LOC, approved_at: "2026-09-24T10:00:00+07:00",
      updated_at: "2026-09-24T10:00:00.000+07:00", last_actor: LOC.display_name, edited_by: [],
      lines: [
        { batch: 103, system_qty: "26.150", counted_qty: "25.250", reason: "" },
        { batch: 105, system_qty: "41.750", counted_qty: "41.750", reason: "" },
      ],
      events: [
        ev("2026-09-24T08:00:00+07:00", "Nhập số kiểm kê", TAM.display_name),
        ev("2026-09-24T10:00:00+07:00", "Duyệt kiểm kê và cân đối sổ kho", LOC.display_name),
      ],
    },
    {
      id: 12, count_date: "2026-09-17", status: "APPROVED", note: "", created_by: TAM, approved_by: HANH, approved_at: "2026-09-17T10:00:00+07:00",
      updated_at: "2026-09-17T10:00:00.000+07:00", last_actor: HANH.display_name, edited_by: [],
      lines: [{ batch: 101, system_qty: "19.600", counted_qty: "18.500", reason: "" }],
      events: [
        ev("2026-09-17T08:00:00+07:00", "Nhập số kiểm kê", TAM.display_name),
        ev("2026-09-17T10:00:00+07:00", "Duyệt kiểm kê và cân đối sổ kho", HANH.display_name),
      ],
    },
  ];
  return { recs, batches, warehouses };
}

function load(): State {
  if (typeof window === "undefined") return seed();
  try {
    const raw = window.localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as State;
  } catch {
    // dữ liệu mock hỏng: gieo lại
  }
  return seed();
}
function save(state: State) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // bỏ qua: mock chỉ để thử
  }
}

type Me = NonNullable<ReturnType<typeof mockRequireUser>>;
const can = (me: Me, perm: string) => me.permissions.includes(perm);
const PERM_ADD = PERM.addStockReconciliation;
const PERM_CHANGE = PERM.changeStockReconciliation;
const PERM_APPROVE = "inventory.approve_stockreconciliation";

const BLOCKED_LABELS: Record<string, string> = {
  "BR-KK-02": "Bạn là người nhập số của phiếu này nên không tự duyệt được.",
  "BR-KK-08": "Bạn đã sửa số đếm của phiếu này nên không duyệt được. Nhờ người khác duyệt.",
};

function fail(status: number, detail: string, code?: string, extra: Record<string, unknown> = {}): MockResponse {
  return { status, body: { detail, ...(code ? { code } : {}), ...extra } };
}

function milliToWire(milli: number): string {
  return (milli / 1000).toFixed(3);
}

function bump(rec: MockRec, actor: string) {
  const prev = Date.parse(rec.updated_at);
  const now = Date.now();
  rec.updated_at = new Date(now > prev ? now : prev + 1).toISOString();
  rec.last_actor = actor;
}

function pathOf(req: unknown): string {
  const r = req as { path?: string; url?: string } | null | undefined;
  return String(r?.path ?? r?.url ?? "");
}

function bodyOf(req: MockRequest): Record<string, unknown> {
  const raw = req.body;
  if (raw && typeof raw === "object") return raw as Record<string, unknown>;
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return {};
    }
  }
  return {};
}

function blockedCode(rec: MockRec, me: Me): string | null {
  if (rec.status !== "DRAFT" || !can(me, PERM_APPROVE)) return null;
  if (rec.created_by.id === me.id) return "BR-KK-02";
  if (rec.edited_by.includes(me.id)) return "BR-KK-08";
  return null;
}

function lineView(state: State, line: MockLine, index: number): StocktakeLine {
  const batch = state.batches.find((b) => b.id === line.batch);
  const diff = (toMilli(line.counted_qty) ?? 0) - (toMilli(line.system_qty) ?? 0);
  return {
    id: index + 1,
    batch: line.batch,
    batch_code: batch?.batch_id ?? `L${line.batch}`,
    item_name: batch?.item_name ?? "",
    warehouse_name: batch?.warehouse_name ?? "",
    system_qty: line.system_qty,
    counted_qty: line.counted_qty,
    difference_qty: milliToWire(diff),
    reason: line.reason,
  };
}

function view(state: State, rec: MockRec, me: Me): StocktakeDetail {
  const lines = rec.lines.map((l, i) => lineView(state, l, i));
  const diffs = lines.map((l) => toMilli(l.difference_qty) ?? 0);
  const short = diffs.filter((d) => d < 0);
  const over = diffs.filter((d) => d > 0);
  const actions: StocktakeAction[] = [];
  const code = blockedCode(rec, me);
  if (rec.status === "DRAFT") {
    if (can(me, PERM_CHANGE)) actions.push("edit_lines");
    if (can(me, PERM_APPROVE) && code === null) actions.push("approve");
  }
  return {
    id: rec.id,
    code: `KK-${rec.id}`,
    count_date: rec.count_date,
    status: rec.status,
    status_label: rec.status === "DRAFT" ? "Chờ duyệt" : "Đã duyệt",
    note: rec.note,
    created_by: rec.created_by,
    approved_by: rec.approved_by,
    approved_at: rec.approved_at,
    updated_at: rec.updated_at,
    updated_by_name: rec.last_actor,
    warehouse_names: Array.from(new Set(lines.map((l) => l.warehouse_name))).sort(),
    line_count: lines.length,
    short_count: short.length,
    over_count: over.length,
    match_count: diffs.length - short.length - over.length,
    short_qty: milliToWire(-short.reduce((a, b) => a + b, 0)),
    over_qty: milliToWire(over.reduce((a, b) => a + b, 0)),
    net_difference: milliToWire(diffs.reduce((a, b) => a + b, 0)),
    available_actions: actions,
    approve_blocked_reason: code ? { code, label: BLOCKED_LABELS[code] } : null,
    lines,
  };
}

/** Kiểm dòng như `_prepare_lines` của BE. Trả lỗi 400 (kèm line_index) hoặc danh sách dòng đã chụp tồn. */
function prepareLines(state: State, raw: unknown): MockResponse | MockLine[] {
  if (!Array.isArray(raw) || raw.length === 0) return fail(400, "Cần ít nhất một dòng số đếm.", "RECON_LINE_INVALID");
  if (raw.length > MAX_LINES) return fail(400, `Tối đa ${MAX_LINES} dòng mỗi phiếu.`, "RECON_LINE_INVALID");
  const seen = new Set<number>();
  const out: MockLine[] = [];
  for (let index = 0; index < raw.length; index++) {
    const row = raw[index] as { batch?: unknown; counted_qty?: unknown; reason?: unknown };
    const err = (msg: string, code = "RECON_LINE_INVALID") => fail(400, `Dòng ${index + 1}: ${msg}`, code, { line_index: index });
    const batchId = typeof row?.batch === "number" ? row.batch : Number(row?.batch);
    if (!Number.isInteger(batchId) || batchId <= 0) return err("Chọn một lô hợp lệ.");
    if (seen.has(batchId)) return err("lô này đã có ở dòng trên, mỗi lô chỉ đếm một lần.");
    seen.add(batchId);
    const batch = state.batches.find((b) => b.id === batchId);
    if (!batch) return err("không tìm thấy lô.");
    const counted = toMilli(String(row.counted_qty ?? ""));
    if (counted === null) return err("Số đếm phải là số kg, tối đa 3 chữ số thập phân.");
    if (counted < 0) return err("số đếm phải từ 0 kg trở lên.");
    const reason = String(row.reason ?? "").trim();
    if (reason.length > MAX_REASON) return err(`lý do tối đa ${MAX_REASON} ký tự.`);
    const system = toMilli(batch.qty_available) ?? 0;
    const diff = counted - system;
    if (diff > 0 && !reason) {
      return err(`lô ${batch.batch_id} đếm nhiều hơn sổ ${milliToWire(diff)} kg, cần ghi lý do (BR-KK-04).`, "BR-KK-04");
    }
    out.push({ batch: batchId, system_qty: batch.qty_available, counted_qty: milliToWire(counted), reason });
  }
  return out;
}

function isResponse(x: MockResponse | MockLine[]): x is MockResponse {
  return !Array.isArray(x);
}

function listFor(state: State, me: Me, query: URLSearchParams) {
  const statuses = (query.get("status") || "").split(",").filter(Boolean);
  const warehouse = query.get("warehouse");
  let recs = [...state.recs].sort((a, b) => b.id - a.id);
  if (statuses.length) recs = recs.filter((r) => statuses.includes(r.status));
  if (warehouse) recs = recs.filter((r) => r.lines.some((l) => state.batches.find((b) => b.id === l.batch)?.warehouse === Number(warehouse)));
  const results = recs.map((r) => {
    const { lines: _lines, ...item } = view(state, r, me);
    void _lines;
    return item;
  });
  return { count: results.length, next: null, previous: null, results };
}

export function mockStocktakeApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return fail(401, "Chưa đăng nhập.");
  const [path, qs = ""] = pathOf(req).split("?");
  const query = new URLSearchParams(qs);
  const state = load();

  // ---- kho + lô (đầu vào form)
  if (path === "/api/inventory/warehouses/") {
    if (!can(me, "inventory.view_warehouse")) return fail(403, "Bạn không có quyền xem kho.");
    const results = state.warehouses.map((w) => ({ id: w.id, name: w.name, is_group: false }));
    return { status: 200, body: { count: results.length, next: null, previous: null, results } };
  }
  if (path === "/api/inventory/batches/") {
    if (!can(me, "inventory.view_batch")) return fail(403, "Bạn không có quyền xem lô.");
    const wh = query.get("warehouse");
    const stockOnly = ["1", "true"].includes((query.get("has_stock") || "").toLowerCase());
    const results = state.batches.filter((b) => (!wh || b.warehouse === Number(wh)) && (!stockOnly || (toMilli(b.qty_available) ?? 0) > 0));
    return { status: 200, body: { count: results.length, next: null, previous: null, results } };
  }

  // ---- dòng thời gian (guidance `stocktake`)
  const guide = path.match(/^\/api\/guidance\/stocktake\/(\d+)\/$/);
  if (guide) {
    if (!can(me, PERM.viewStockReconciliation)) return fail(403, "Bạn không có quyền xem lịch sử này.", "FORBIDDEN");
    const rec = state.recs.find((r) => r.id === Number(guide[1]));
    if (!rec) return fail(404, "Không tìm thấy.", "NOT_FOUND");
    const data: GuidanceData = {
      doc: { type: "stocktake", id: rec.id, code: `KK-${rec.id}`, status: null, status_label: null },
      next_steps: [],
      warnings: [],
      timeline: rec.events.map((e) => ({ at: e.at, kind: "audit", label: e.label, doc: "", actor: { kind: "user", display: e.actor } })),
      related: [],
    };
    return { status: 200, body: data };
  }

  // ---- phiếu kiểm kê
  const m = path.match(/^\/api\/inventory\/reconciliations\/(?:(\d+)\/(?:(lines|approve)\/)?)?$/);
  if (!m) return fail(404, "Không tìm thấy.");
  const [, idText, tail] = m;
  if (!can(me, PERM.viewStockReconciliation)) return fail(403, "Bạn không có quyền xem kiểm kê.");

  if (!idText) {
    if (req.method === "GET") return { status: 200, body: listFor(state, me, query) };
    if (req.method !== "POST") return fail(405, "Phương thức không hỗ trợ.");
    if (!can(me, PERM_ADD)) return fail(403, "Bạn không có quyền lập phiếu kiểm kê.");
    const body = bodyOf(req);
    const countDate = typeof body.count_date === "string" ? body.count_date : "";
    if (!/^\d{4}-\d{2}-\d{2}$/.test(countDate)) return fail(400, "Chọn ngày kiểm kê.", "business_error", { count_date: ["Chọn ngày kiểm kê."] });
    let lines: MockLine[] = [];
    if ("lines" in body) {
      const prepared = prepareLines(state, body.lines);
      if (isResponse(prepared)) return prepared;
      lines = prepared;
    }
    const id = Math.max(0, ...state.recs.map((r) => r.id)) + 1;
    const now = new Date().toISOString();
    const rec: MockRec = {
      id, count_date: countDate, status: "DRAFT", note: typeof body.note === "string" ? body.note : "",
      created_by: { id: me.id, display_name: me.display_name }, approved_by: null, approved_at: null,
      updated_at: now, last_actor: me.display_name, edited_by: [], lines,
      events: [{ at: now, label: "Nhập số kiểm kê", actor: me.display_name }],
    };
    state.recs.push(rec);
    save(state);
    return { status: 201, body: view(state, rec, me) };
  }

  const rec = state.recs.find((r) => r.id === Number(idText));
  if (!rec) return fail(404, "Không tìm thấy phiếu kiểm kê.");

  if (!tail) {
    if (req.method === "GET") return { status: 200, body: view(state, rec, me) };
    if (req.method !== "PATCH" && req.method !== "PUT") return fail(405, "Phương thức không hỗ trợ.");
    if (!can(me, PERM_CHANGE)) return fail(403, "Bạn không có quyền sửa phiếu kiểm kê.");
    if (rec.status !== "DRAFT") return fail(400, "Phiếu kiểm kê đã duyệt, không sửa được.", "RECON_NOT_DRAFT");
    const body = bodyOf(req);
    if ("lines" in body) return fail(400, "Dòng số đếm sửa qua POST …/lines/, không sửa qua phiếu.", "RECON_USE_LINES_ENDPOINT");
    if (typeof body.count_date === "string") rec.count_date = body.count_date;
    if (typeof body.note === "string") rec.note = body.note;
    bump(rec, me.display_name);
    rec.events.push({ at: rec.updated_at, label: "Sửa thông tin phiếu", actor: me.display_name });
    save(state);
    return { status: 200, body: view(state, rec, me) };
  }

  if (req.method !== "POST") return fail(405, "Phương thức không hỗ trợ.");

  if (tail === "lines") {
    if (!can(me, PERM_CHANGE)) return fail(403, "Bạn không có quyền sửa phiếu kiểm kê.");
    if (rec.status !== "DRAFT") return fail(400, "Phiếu kiểm kê đã duyệt, không sửa được.", "RECON_NOT_DRAFT");
    const body = bodyOf(req);
    if (typeof body.expected_updated_at !== "string") return fail(400, "Thiếu expected_updated_at.", "EXPECTED_UPDATED_AT_REQUIRED");
    if (Date.parse(body.expected_updated_at) !== Date.parse(rec.updated_at)) {
      return fail(409, "Phiếu vừa được người khác cập nhật, tải lại để xem.", "STALE_STATE", { updated_at: rec.updated_at, updated_by_name: rec.last_actor });
    }
    const prepared = prepareLines(state, body.lines);
    if (isResponse(prepared)) return prepared;
    rec.lines = prepared;
    if (!rec.edited_by.includes(me.id)) rec.edited_by.push(me.id);
    bump(rec, me.display_name);
    rec.events.push({ at: rec.updated_at, label: "Sửa số đếm", actor: me.display_name });
    save(state);
    return { status: 200, body: view(state, rec, me) };
  }

  // approve
  if (!can(me, PERM_APPROVE)) return fail(403, "Bạn không có quyền duyệt kiểm kê.");
  if (rec.status !== "DRAFT") return fail(400, "Phiếu kiểm kê đã được duyệt.");
  if (rec.created_by.id === me.id) return fail(400, "Người duyệt kiểm kê phải khác người nhập số (BR-KK-02).");
  if (rec.edited_by.includes(me.id)) {
    return fail(400, "Bạn đã nhập hoặc sửa số đếm của phiếu này nên không duyệt được, cần người khác duyệt (BR-KK-08).", "BR-KK-08");
  }
  if (rec.lines.length === 0) return fail(400, "Phiếu chưa có dòng số đếm nào, không duyệt được.", "RECON_EMPTY");
  // BR-KK-09: áp chênh lệch đã chụp; kiểm hết trước khi ghi để cả phiếu hoặc không gì cả (giao dịch của BE).
  const next = new Map<number, number>();
  for (let i = 0; i < rec.lines.length; i++) {
    const line = rec.lines[i];
    const batch = state.batches.find((b) => b.id === line.batch);
    if (!batch) continue;
    const diff = (toMilli(line.counted_qty) ?? 0) - (toMilli(line.system_qty) ?? 0);
    const after = (next.get(batch.id) ?? toMilli(batch.qty_available) ?? 0) + diff;
    if (after < 0) {
      return fail(400, `Dòng ${i + 1}: tồn lô ${batch.batch_id} không đủ để áp chênh lệch đã đếm. Hãy đếm lại.`, "RECON_STOCK_INSUFFICIENT", { line_index: i });
    }
    next.set(batch.id, after);
  }
  for (const [id, milli] of next) {
    const batch = state.batches.find((b) => b.id === id);
    if (batch) batch.qty_available = milliToWire(milli);
  }
  rec.status = "APPROVED";
  rec.approved_by = { id: me.id, display_name: me.display_name };
  rec.approved_at = new Date().toISOString();
  bump(rec, me.display_name);
  rec.events.push({ at: rec.updated_at, label: "Duyệt kiểm kê và cân đối sổ kho", actor: me.display_name });
  save(state);
  return { status: 200, body: view(state, rec, me) };
}

// Công cụ thử trong DevTools/e2e (chỉ có ở mock):
//   window.__caveMock.stocktakeReset()                 — gieo lại dữ liệu kiểm kê
//   window.__caveMock.stocktakeEditByOther(id, {batch?, counted?, note?}) — người khác vừa sửa phiếu này (thêm/đổi số một lô, đổi ghi chú); lần lưu kế tiếp gặp 409 STALE_STATE
//   window.__caveMock.stocktakeSetStock(batchId, kg)   — đổi tồn hiện tại của lô (thử RECON_STOCK_INSUFFICIENT / BR-KK-09)
//   window.__caveMock.stocktakeStock(batchId)          — đọc tồn hiện tại của lô
if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    stocktakeReset: () => {
      save(seed());
      return "Đã gieo lại dữ liệu kiểm kê.";
    },
    stocktakeEditByOther: (id: number, extra?: { batch?: number; counted?: number; note?: string }) => {
      const state = load();
      const rec = state.recs.find((r) => r.id === id);
      if (!rec) return "Không có phiếu";
      if (extra?.note !== undefined) rec.note = extra.note;
      if (extra?.batch !== undefined) {
        // Người kia thêm (hoặc đổi số) một lô: dòng này là bản của máy chủ mà "Tải lại" phải đưa lên màn.
        const batch = state.batches.find((b) => b.id === extra.batch);
        if (batch) {
          const line = { batch: batch.id, system_qty: batch.qty_available, counted_qty: milliToWire(Math.round((extra.counted ?? 0) * 1000)), reason: "Người kia nhập" };
          rec.lines = [...rec.lines.filter((l) => l.batch !== batch.id), line];
        }
      }
      if (!rec.edited_by.includes(99)) rec.edited_by.push(99);
      bump(rec, "Chị Lan");
      rec.events.push({ at: rec.updated_at, label: "Sửa số đếm", actor: "Chị Lan" });
      save(state);
      return `Phiếu ${id}: Chị Lan vừa sửa lúc ${rec.updated_at}`;
    },
    stocktakeSetStock: (batchId: number, kgValue: number) => {
      const state = load();
      const batch = state.batches.find((b) => b.id === batchId);
      if (!batch) return "Không có lô";
      batch.qty_available = Number(kgValue).toFixed(3);
      save(state);
      return `Lô ${batch.batch_id}: tồn ${batch.qty_available}`;
    },
    stocktakeStock: (batchId: number) => load().batches.find((b) => b.id === batchId)?.qty_available ?? null,
  };
}
