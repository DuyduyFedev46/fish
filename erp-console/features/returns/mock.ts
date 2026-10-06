// Mock module Hàng hoàn về kho (ED-26) — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Dựng JSON theo contract THỰC TẾ BE Lô 9 / R9 (backend/apps/inventory/returns):
//   GET   /api/inventory/returns/?status=&month=&page=   GET /{id}/   POST /   POST /{id}/approve/   POST /{id}/cancel/   POST /{id}/delete/
//   GET   /api/guidance/return/{id}/
//
// Luật mock (mô phỏng BE, FE KHÔNG dùng lại các luật này):
//  - GET/POST cần inventory.view_returntostock / add_returntostock (thiếu → 403). approve cần inventory.approve_returntostock.
//  - Người chỉ thuộc delivery_staff (hasLimitedCourierScope) chỉ thấy phiếu của phiếu giao gán cho mình; phiếu người khác → 404.
//  - POST: phiếu giao không có/ngoài phạm vi → 404; lô không thuộc phiếu → 400 RETURN_BATCH_NOT_IN_NOTE;
//    tổng kg đã ghi nhận (cả Chờ duyệt lẫn Đã duyệt) + kg mới > kg đã giao → 400 RETURN_QTY_EXCEEDS kèm delivered_qty / already_returned_qty.
//  - POST: lô đã chốt → 400 RETURN_BATCH_CLOSED (chế độ "batchclosed" giả lập); ghi chú có dãy 9 chữ số trở lên → 400 {note: [câu]}
//    như BE (QA Lô 9 B1; chế độ "noterejected" giả lập BE từ chối mọi ghi chú để thử khi FE đã chặn trước).
//  - cancel (#8): cần add_returntostock (cổng chung); rồi phải có approve/change_returntostock hoặc là người tạo phiếu, không thì 403 (câu của BE);
//    chỉ phiếu Chờ duyệt, đã duyệt/đã huỷ → 409 STALE_STATE. Phiếu huỷ không tính vào số kg đã hoàn.
//  - delete (#8): chỉ Chủ (khác → 403, kiểm trước phạm vi); Chờ duyệt/Đã huỷ → 200 {status:"deleted"} rồi 404; Đã duyệt → 400 RETURN_DELETE_NOT_ALLOWED;
//    `available_actions` có "delete" cho Chủ. Công cụ thử: window.__caveMock.returnsStaleDelete(id) → lần xoá kế tiếp 409 STALE_STATE.
//  - approve: thiếu decision → 400 RETURN_DECISION_REQUIRED; phiếu đã duyệt → 409 STALE_STATE (không có updated_at).
//  - Dòng của chi tiết phiếu giao có `batch_pk` (id lô) và `returned_qty` (kg đã hoàn của lô trên phiếu, Chờ duyệt + Đã duyệt), đăng ký vào
//    mock Giao hàng qua `registerDeliveryLineExtras` (đúng contract "BE cho Lô 9").
//  - Phiếu giao mock (id 33, 34, 36, 38, 39) là phiếu của module Giao hàng; bảng số kg đã giao ở đây khớp `lines` bên đó.
//
// Dữ liệu chỉ nằm trong bộ nhớ trang (mất khi tải lại): không ghi ghi chú/tên vào storage (bất biến 9). Chế độ thử lưu localStorage (không chứa dữ liệu khách).
// Công cụ thử trong DevTools (chỉ có ở mock):
//   window.__caveMock.returns("ok" | "fail" | "empty" | "forbidden" | "detailfail" | "batchclosed" | "noterejected")   — chế độ; giữ qua tải lại
//   window.__caveMock.returnsAddHidden(noteId, kg)   — máy khác hoàn thêm kg (không hiện ở danh sách) để thử lỗi vượt kg
//   window.__caveMock.returnsMarkApproved(id)   — duyệt phiếu "từ máy khác" để thử 409 ở lần Duyệt kế tiếp

import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import type { Me } from "@/features/auth/types";
import type { GuidanceData, GuidanceTimelineEntry } from "@/features/guidance/types";
import type { MockRequest, MockResponse, Paginated } from "@/shared/lib/http";
import { kg } from "@/shared/lib/format";
import { registerDeliveryLineExtras } from "@/features/deliveries/mock";
import { ROLE } from "@/shared/lib/roles";
import { hasLimitedCourierScope } from "@/shared/lib/personalData";
import { hasLongDigitRun } from "./returnsModel";
import type { ReturnItem } from "./types";

const MODE_KEY = "cave_erp_mock_returns_mode";
const PAGE_SIZE = 20;
const PERM_VIEW = "inventory.view_returntostock";
const PERM_ADD = "inventory.add_returntostock";
const PERM_APPROVE = "inventory.approve_returntostock";
const PERM_CHANGE = "inventory.change_returntostock";

type Mode = "ok" | "fail" | "empty" | "forbidden" | "detailfail" | "batchclosed" | "noterejected";
function mode(): Mode {
  try {
    const v = typeof window === "undefined" ? null : window.localStorage.getItem(MODE_KEY);
    return v === "fail" || v === "empty" || v === "forbidden" || v === "detailfail" || v === "batchclosed" || v === "noterejected" ? v : "ok";
  } catch {
    return "ok";
  }
}

const has = (me: Me | null, perm: string) => !!me && me.permissions.includes(perm);
const err = (status: number, code: string, detail: string, extra: Record<string, unknown> = {}): MockResponse => ({ status, body: { detail, code, ...extra } });
const FORBIDDEN = err(403, "FORBIDDEN", "Bạn không có quyền xem hàng hoàn về kho.");
const NOT_FOUND = err(404, "NOT_FOUND", "Không tìm thấy phiếu hàng hoàn.");

/** Id lô giả theo mã lô (khớp `lines[].batch_id` của phiếu giao mock). */
const BATCH_PK: Record<string, number> = {
  "CA-CHEM-260927-GH78": 201,
  "BACH-TUOC-260925-JK90": 202,
  "MUC-LA-260925-CD34E": 203,
  "TOM-SU-1-260920-AB12C": 204,
  "CUA-CM-Y4-260926-EF56": 205,
  "CA-THU-260928-VT01": 206,
  "CA-THU-260918-VT02": 207,
};
const BATCH_CODE: Record<number, { code: string; item: string }> = {
  201: { code: "CA-CHEM-260927-GH78", item: "Cá chẽm phi lê" },
  202: { code: "BACH-TUOC-260925-JK90", item: "Bạch tuộc tươi" },
  203: { code: "MUC-LA-260925-CD34E", item: "Mực lá Phan Thiết" },
  204: { code: "TOM-SU-1-260920-AB12C", item: "Tôm sú loại 1" },
};

type NoteFact = { code: string; order: string; courierId: number; batch: number; delivered: number };
/** Phiếu giao mock còn đi giao hoặc giao thất bại (id → dữ kiện). courierId khớp `assigned_to` của module Giao hàng. */
const NOTES: Record<number, NoteFact> = {
  33: { code: "GH-HD-0033-DELI", order: "DH-260928-0003", courierId: 14, batch: 201, delivered: 1 },
  34: { code: "GH-HD-0034-FAIL", order: "DH-260928-0004", courierId: 14, batch: 202, delivered: 2 },
  36: { code: "GH-HD-0036-DELI", order: "DH-260928-0006", courierId: 4, batch: 203, delivered: 2 },
  38: { code: "GH-HD-0038-FAIL", order: "DH-260928-0008", courierId: 4, batch: 204, delivered: 1 },
  39: { code: "GH-HD-0039-DELI", order: "DH-260928-0009", courierId: 7, batch: 201, delivered: 1.2 },
};

const COURIER_NAME: Record<number, string> = { 4: "Anh Phúc", 7: "Anh Lâm", 14: "Anh Khoa" };

function monthAgoIso(minutesAgo: number): string {
  return new Date(Date.now() - minutesAgo * 60_000).toISOString();
}

function make(
  id: number,
  noteId: number,
  qty: string,
  fields: { status: "DRAFT" | "APPROVED" | "CANCELLED"; decision: "PENDING" | "RESTOCK" | "WRITE_OFF"; outside: number; createdMinutesAgo: number; by: number; note?: string; approvedBy?: string },
): ReturnItem {
  const n = NOTES[noteId];
  const b = BATCH_CODE[n.batch];
  const returnedAt = monthAgoIso(fields.createdMinutesAgo);
  const leftAt = new Date(Date.parse(returnedAt) - fields.outside * 60_000).toISOString();
  return {
    id,
    code: `RT-${id}`,
    delivery_note: noteId,
    delivery_note_code: n.code,
    order_code: n.order,
    batch: n.batch,
    batch_code: b.code,
    item_name: b.item,
    qty,
    left_warehouse_at: leftAt,
    returned_at: returnedAt,
    outside_minutes: fields.outside,
    decision: fields.decision,
    decision_label: decisionLabel(fields.decision),
    status: fields.status,
    status_label: statusLabel(fields.status),
    created_by: fields.by,
    created_by_name: COURIER_NAME[fields.by] ?? "Anh Tâm",
    approved_by: fields.approvedBy ? 2 : null,
    approved_by_name: fields.approvedBy ?? "",
    created_at: returnedAt,
    note: fields.note ?? "",
  };
}

function statusLabel(s: ReturnItem["status"]): string {
  return s === "DRAFT" ? "Chờ duyệt" : s === "APPROVED" ? "Đã duyệt" : "Đã huỷ";
}

function decisionLabel(d: string): string {
  return d === "RESTOCK" ? "Tái nhập" : d === "WRITE_OFF" ? "Huỷ bỏ, ghi lỗ" : "Chờ quyết định";
}

/** Kg "máy khác" đã hoàn thêm cho một phiếu giao mà danh sách này không có (chỉ để e2e thử lỗi vượt kg do người khác nhập trước). */
const HIDDEN_RETURNED: Record<number, number> = {};

let DB: ReturnItem[] | null = null;
function db(): ReturnItem[] {
  if (!DB) {
    DB = [
      make(1, 38, "0.500", { status: "DRAFT", decision: "PENDING", outside: 135, createdMinutesAgo: 90, by: 4, note: "Khách không nghe máy" }),
      make(2, 39, "0.700", { status: "DRAFT", decision: "PENDING", outside: 55, createdMinutesAgo: 200, by: 7, note: "Khách từ chối nhận" }),
      make(3, 33, "1.000", { status: "APPROVED", decision: "RESTOCK", outside: 70, createdMinutesAgo: 1500, by: 14, note: "Sai địa chỉ, giao lại", approvedBy: "Chị Hạnh" }),
      make(4, 34, "0.800", { status: "APPROVED", decision: "WRITE_OFF", outside: 245, createdMinutesAgo: 2900, by: 14, note: "Xe hỏng giữa đường", approvedBy: "Chị Hạnh" }),
      make(5, 36, "0.300", { status: "DRAFT", decision: "PENDING", outside: 40, createdMinutesAgo: 30, by: 4 }),
      make(6, 36, "0.200", { status: "CANCELLED", decision: "PENDING", outside: 45, createdMinutesAgo: 600, by: 4, note: "Nhập nhầm lô" }),
    ];
  }
  return DB;
}

/** `available_actions` như BE (#8): approve (quyền duyệt + Chờ duyệt), cancel (Chờ duyệt, theo luật huỷ), delete (chỉ Chủ, Chờ duyệt hoặc Đã huỷ). */
function withActions(me: Me, r: ReturnItem): ReturnItem {
  const actions: string[] = [];
  if (r.status === "DRAFT" && has(me, PERM_APPROVE)) actions.push("approve");
  if (r.status === "DRAFT" && has(me, PERM_ADD) && (has(me, PERM_APPROVE) || has(me, PERM_CHANGE) || r.created_by === me.id)) actions.push("cancel");
  if (me.groups.includes(ROLE.owner) && (r.status === "DRAFT" || r.status === "CANCELLED")) actions.push("delete");
  return { ...r, available_actions: actions };
}

/** Phiếu id đã được "máy khác" xoá/đổi trước: lần xoá kế tiếp trả 409 (chỉ để thử). */
const STALE_DELETE = new Set<number>();

function deleteResponse(me: Me, id: number): MockResponse {
  if (!me.groups.includes(ROLE.owner)) return err(403, "FORBIDDEN", "Chỉ Chủ mới xoá được phiếu hàng hoàn.");
  const r = db().find((x) => x.id === id);
  if (!r || !inScope(me, r)) return NOT_FOUND;
  if (STALE_DELETE.has(id)) return err(409, "STALE_STATE", "Phiếu hàng hoàn vừa được người khác xử lý, hãy tải lại.");
  if (r.status === "APPROVED") return err(400, "RETURN_DELETE_NOT_ALLOWED", "Phiếu hàng hoàn đã duyệt (đã nhập lại kho hoặc ghi lỗ) không xoá được (BR-PQ-10).");
  DB = db().filter((x) => x.id !== id);
  return { status: 200, body: { status: "deleted", id } };
}

/** Phiếu mà người dùng thấy: người giao hạn chế chỉ thấy phiếu của phiếu giao gán cho mình (BR-PQ-12). */
function inScope(me: Me, r: ReturnItem): boolean {
  if (!hasLimitedCourierScope(me)) return true;
  return NOTES[r.delivery_note]?.courierId === me.id;
}

function pathParts(path: string): { pathname: string; query: URLSearchParams } {
  const i = path.indexOf("?");
  return { pathname: i >= 0 ? path.slice(0, i) : path, query: new URLSearchParams(i >= 0 ? path.slice(i + 1) : "") };
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

function monthOf(iso: string): string {
  const d = new Date(Date.parse(iso) + 7 * 3600_000);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

function listResponse(me: Me, query: URLSearchParams): MockResponse {
  const m = mode();
  if (m === "fail") return err(500, "SERVER_ERROR", "Máy chủ đang bận. Thử lại sau.");
  let rows = m === "empty" ? [] : db().filter((r) => inScope(me, r));
  const statuses = (query.get("status") || "").split(",").map((s) => s.trim()).filter(Boolean);
  if (statuses.length) rows = rows.filter((r) => statuses.includes(r.status));
  const month = query.get("month");
  if (month) rows = rows.filter((r) => monthOf(r.created_at) === month);
  rows = [...rows].sort((a, b) => b.id - a.id);
  const page = Math.max(1, Number(query.get("page")) || 1);
  const slice = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const body: Paginated<ReturnItem> = {
    count: rows.length,
    next: page * PAGE_SIZE < rows.length ? `?page=${page + 1}` : null,
    previous: page > 1 ? `?page=${page - 1}` : null,
    results: slice.map((r) => withActions(me, r)),
  };
  return { status: 200, body };
}

function createResponse(me: Me, req: MockRequest): MockResponse {
  if (!has(me, PERM_ADD)) return err(403, "FORBIDDEN", "Bạn không có quyền nhập hàng hoàn.");
  const body = bodyOf(req);
  const noteId = Number(body.delivery_note);
  const batchId = Number(body.batch);
  const fields: Record<string, string[]> = {};
  if (!Number.isInteger(noteId) || noteId <= 0) fields.delivery_note = ["Trường này là bắt buộc."];
  if (!Number.isInteger(batchId) || batchId <= 0) fields.batch = ["Trường này là bắt buộc."];
  const qty = typeof body.qty === "string" || typeof body.qty === "number" ? Number(body.qty) : NaN;
  if (!Number.isFinite(qty) || qty <= 0) fields.qty = ["Số kg phải lớn hơn 0."];
  if (Object.keys(fields).length) return { status: 400, body: fields };
  const note = NOTES[noteId];
  if (!note || (hasLimitedCourierScope(me) && note.courierId !== me.id)) return err(404, "NOT_FOUND", "Không tìm thấy phiếu giao.");
  if (mode() === "batchclosed") return err(400, "RETURN_BATCH_CLOSED", "Lô đã chốt, không ghi nhận hàng hoàn vào lô này.");
  const freeNote = typeof body.note === "string" ? body.note : "";
  if (freeNote && (mode() === "noterejected" || hasLongDigitRun(freeNote))) {
    return { status: 400, body: { note: ["Ghi chú không được chứa dãy số dài (số điện thoại, số tài khoản)."] } };
  }
  if (batchId !== note.batch) return err(400, "RETURN_BATCH_NOT_IN_NOTE", "Lô này không nằm trong phiếu giao, hàng hoàn phải về đúng lô gốc (BR-HV-01).");
  const already = db().filter((r) => r.delivery_note === noteId && r.batch === batchId && r.status !== "CANCELLED").reduce((s, r) => s + Number(r.qty), 0) + (HIDDEN_RETURNED[noteId] ?? 0);
  if (already + qty > note.delivered + 1e-9) {
    return err(400, "RETURN_QTY_EXCEEDS", "Số kg hoàn vượt số đã giao của lô.", {
      delivered_qty: note.delivered.toFixed(3),
      already_returned_qty: already.toFixed(3),
    });
  }
  const id = Math.max(0, ...db().map((r) => r.id)) + 1;
  const nowIso = new Date().toISOString();
  const b = BATCH_CODE[batchId];
  const item: ReturnItem = {
    id,
    code: `RT-${id}`,
    delivery_note: noteId,
    delivery_note_code: note.code,
    order_code: note.order,
    batch: batchId,
    batch_code: b.code,
    item_name: b.item,
    qty: qty.toFixed(3),
    left_warehouse_at: new Date(Date.now() - 150 * 60_000).toISOString(),
    returned_at: nowIso,
    outside_minutes: 150,
    decision: "PENDING",
    decision_label: decisionLabel("PENDING"),
    status: "DRAFT",
    status_label: "Chờ duyệt",
    created_by: me.id,
    created_by_name: me.display_name,
    approved_by: null,
    approved_by_name: "",
    created_at: nowIso,
    note: typeof body.note === "string" ? body.note : "",
  };
  db().push(item);
  return { status: 201, body: withActions(me, item) };
}

function approveResponse(me: Me, id: number, req: MockRequest): MockResponse {
  if (!has(me, PERM_APPROVE)) return err(403, "FORBIDDEN", "Bạn không có quyền duyệt phiếu hàng hoàn.");
  const r = db().find((x) => x.id === id);
  if (!r || !inScope(me, r)) return NOT_FOUND;
  const decision = bodyOf(req).decision;
  if (decision !== "RESTOCK" && decision !== "WRITE_OFF") return err(400, "RETURN_DECISION_REQUIRED", "Phải chọn Tái nhập hoặc Huỷ bỏ trước khi duyệt (BR-HV-02).");
  if (r.status !== "DRAFT") return err(409, "STALE_STATE", "Phiếu hàng hoàn đã được duyệt, hãy tải lại.");
  r.status = "APPROVED";
  r.status_label = "Đã duyệt";
  r.decision = decision;
  r.decision_label = decisionLabel(decision);
  r.approved_by = me.id;
  r.approved_by_name = me.display_name;
  return { status: 200, body: withActions(me, r) };
}

function cancelResponse(me: Me, id: number): MockResponse {
  if (!has(me, PERM_ADD)) return err(403, "FORBIDDEN", "Bạn không có quyền huỷ phiếu hàng hoàn.");
  const r = db().find((x) => x.id === id);
  if (!r || !inScope(me, r)) return NOT_FOUND;
  const mayCancel = has(me, PERM_APPROVE) || has(me, PERM_CHANGE) || r.created_by === me.id;
  if (!mayCancel) return err(403, "FORBIDDEN", "Chỉ người có quyền duyệt hoặc người tạo phiếu mới huỷ được phiếu hàng hoàn.");
  if (r.status !== "DRAFT") return err(409, "STALE_STATE", "Phiếu hàng hoàn đã được xử lý, hãy tải lại.");
  r.status = "CANCELLED";
  r.status_label = statusLabel("CANCELLED");
  cancelledAt[r.id] = new Date().toISOString();
  return { status: 200, body: withActions(me, r) };
}

/** Giờ huỷ của phiếu bị huỷ trong phiên (cho dòng thời gian). */
const cancelledAt: Record<number, string> = {};

function timelineResponse(me: Me, id: number): MockResponse {
  const r = db().find((x) => x.id === id);
  if (!r || !inScope(me, r)) return NOT_FOUND;
  // Nhãn chỉ có mã phiếu, số kg và tên nhân viên: KHÔNG có ghi chú, tên khách (bất biến 9).
  const entries: GuidanceTimelineEntry[] = [];
  if (r.left_warehouse_at) entries.push({ at: r.left_warehouse_at, kind: "delivery_started", label: `Nhận phiếu giao ${r.delivery_note_code ?? ""}`.trim(), doc: "delivery", actor: { kind: "user", display: r.created_by_name } });
  entries.push({ at: r.created_at, kind: "return_created", label: `Nhập hàng hoàn ${kg(r.qty)} về kho`, doc: "return", actor: { kind: "user", display: r.created_by_name } });
  if (r.status === "APPROVED") {
    entries.push({
      at: new Date(Date.parse(r.created_at) + 20 * 60_000).toISOString(),
      kind: "return_approved",
      label: r.decision === "WRITE_OFF" ? "Duyệt huỷ bỏ, ghi lỗ" : "Duyệt tái nhập vào lô",
      doc: "return",
      actor: { kind: "user", display: r.approved_by_name || "Quản lý" },
    });
  }
  if (r.status === "CANCELLED") {
    entries.push({ at: cancelledAt[r.id] ?? new Date(Date.parse(r.created_at) + 10 * 60_000).toISOString(), kind: "return_cancelled", label: "Huỷ phiếu hàng hoàn", doc: "return", actor: { kind: "user", display: "Quản lý" } });
  }
  const data: GuidanceData = { doc: { type: "return", id: r.id, code: r.code, status: r.status, status_label: r.status_label }, next_steps: [], warnings: [], timeline: entries, related: [] };
  return { status: 200, body: data };
}

export function mockReturnsApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const { pathname, query } = pathParts(req.path);

  const guide = /^\/api\/guidance\/return\/(\d+)\/$/.exec(pathname);
  if (guide) {
    if (!has(me, PERM_VIEW) || mode() === "forbidden") return FORBIDDEN;
    return timelineResponse(me, Number(guide[1]));
  }

  if (!has(me, PERM_VIEW) || mode() === "forbidden") return FORBIDDEN;

  if (pathname === "/api/inventory/returns/") {
    if (req.method === "POST") return createResponse(me, req);
    return listResponse(me, query);
  }
  const one = /^\/api\/inventory\/returns\/(\d+)\/(approve\/|cancel\/|delete\/)?$/.exec(pathname);
  if (one) {
    const id = Number(one[1]);
    if (one[2]) {
      if (req.method !== "POST") return err(405, "METHOD_NOT_ALLOWED", "Không hỗ trợ.");
      if (one[2] === "delete/") return deleteResponse(me, id);
      return one[2] === "cancel/" ? cancelResponse(me, id) : approveResponse(me, id, req);
    }
    if (mode() === "detailfail") return err(500, "SERVER_ERROR", "Máy chủ đang bận. Thử lại sau.");
    const r = db().find((x) => x.id === id);
    return r && inScope(me, r) ? { status: 200, body: withActions(me, r) } : NOT_FOUND;
  }
  return err(404, "NOT_FOUND", "Không tìm thấy endpoint.");
}

/** Gắn `batch_pk` + `returned_qty` vào dòng chi tiết phiếu giao của mock Giao hàng (tách hàm để vitest gọi được). */
export function installDeliveryLineExtras(): void {
  registerDeliveryLineExtras((noteId, line) => {
    const batch = BATCH_PK[line.batch_id];
    const returned = db()
      .filter((r) => r.delivery_note === noteId && r.batch === batch && r.status !== "CANCELLED")
      .reduce((sum, r) => sum + Number(r.qty), 0) + (HIDDEN_RETURNED[noteId] ?? 0);
    return { batch_pk: batch, returned_qty: returned.toFixed(3) };
  });
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1") installDeliveryLineExtras();

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    returns: (m: Mode) => {
      window.localStorage.setItem(MODE_KEY, m);
      return `Hàng hoàn về kho (mock): chế độ ${m}`;
    },
    returnsAddHidden: (noteId: number, qty: number) => {
      HIDDEN_RETURNED[noteId] = (HIDDEN_RETURNED[noteId] ?? 0) + qty;
      return `Phiếu giao ${noteId}: máy khác đã hoàn thêm ${qty} kg (mock)`;
    },
    returnsStaleDelete: (id: number) => {
      STALE_DELETE.add(id);
      return `RT-${id}: lần xoá kế tiếp sẽ trả 409 (mock)`;
    },
    returnsMarkApproved: (id: number) => {
      const r = db().find((x) => x.id === id);
      if (!r) return "Không có phiếu này";
      r.status = "APPROVED";
      r.status_label = "Đã duyệt";
      r.decision = "RESTOCK";
      r.decision_label = decisionLabel("RESTOCK");
      r.approved_by_name = "Chị Hạnh";
      return `RT-${id} đã được duyệt từ máy khác (mock)`;
    },
  };
}
