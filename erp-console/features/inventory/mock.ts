// Mock module inventory — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1. Cùng seed với overview/orders.
// `unit_cost` chỉ có khi người đăng nhập có inventory.view_costprice (loc) — y như BE (S8-AC2/AC3).
//
// P8 Lô 5 (SR-15/SR-16): thêm 2 lô Quá hạn còn tồn (dữ liệu bịa, không có thông tin khách) + trạng thái trong bộ nhớ để thử:
//   - GET  /api/inventory/batches/?status=EXPIRED            (danh sách phân trang DRF)
//   - POST /api/inventory/batches/<id>/cancel-expired/       (body tuỳ chọn {confirm_qty}) — theo 02b §5.4
//   - POST /api/inventory/batches/<id>/return-to-supplier/   — theo 02b §5.4 (200 KHÔNG có tiền NCC hoàn)
//   - POST /api/inventory/batches/<id>/close/
//   - guidance của lô (mockExpiredBatchGuidance, do features/guidance/mock.ts gọi)
// Trạng thái nằm trong bộ nhớ trang (tải lại trang = về seed), nên mỗi lần chạy e2e đều bắt đầu từ seed.
// Công cụ thử trong DevTools (chỉ có ở mock):
//   window.__caveMock.expiredSetQty("LO-…", 4)   — đổi tồn "phía máy chủ" mà màn đang mở chưa biết (thử 400 tồn đã đổi)
//   window.__caveMock.expiredState()             — xem tồn/trạng thái các lô quá hạn
//   window.__caveMock.expiredReset()             — về lại seed
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { todayInVietnam } from "@/shared/lib/format";
import { dashboardSummaryMockResponse } from "@/shared/lib/dashboardSummary.mock";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import type { Me } from "@/features/auth/types";
import { ROLE } from "@/shared/lib/roles";
import type { GuidanceData, GuidanceNextStep } from "@/features/guidance/types";
import type { BatchApiRow } from "./types";

export function mockInventory(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  return dashboardSummaryMockResponse({
    username: me.username,
    can_cost: me.can_view_cost,
    can_view_dashboard: me.permissions.includes("reports.view_dashboard"),
  });
}

// ---- Lô quá hạn còn tồn ----

type MockLot = {
  id: number;
  batch_id: string;
  item_code: string;
  item: string;
  supplier: string;
  warehouse: string;
  received_days_ago: number;
  expired_days_ago: number;
  qty_available: number;
  qty_reserved: number;
  status: "EXPIRED" | "CANCELLED" | "CLOSED";
  cost: number;
};

// Chủ = nhóm chu (tài khoản mock `loc` — GROUP_PERMS của chu trong auth/mock chưa liệt kê quyền tuỳ biến nên xét theo nhóm).
const isOwner = (me: Me) => me.groups.includes(ROLE.owner) || me.username === "loc";

const seed = (): MockLot[] => [
  { id: 901, batch_id: "L0908-CT00", item_code: "CA-THU-PL", item: "Cá thu phi lê", supplier: "Ghe Tư Hải", warehouse: "Kho lạnh Bến Đá",
    received_days_ago: 12, expired_days_ago: 2, qty_available: 6.5, qty_reserved: 0, status: "EXPIRED", cost: 182000 },
  { id: 902, batch_id: "L0909-MU00", item_code: "MUC-LA", item: "Mực lá câu", supplier: "Vựa Bà Năm", warehouse: "Kho lạnh Bến Đá",
    received_days_ago: 11, expired_days_ago: 1, qty_available: 4, qty_reserved: 1.5, status: "EXPIRED", cost: 236500 },
  { id: 903, batch_id: "L0910-TS00", item_code: "TOM-SU-20", item: "Tôm sú size 20", supplier: "Tàu Phước Lộc 07", warehouse: "Kho lạnh Bến Đá",
    received_days_ago: 10, expired_days_ago: 1, qty_available: 3, qty_reserved: 0, status: "EXPIRED", cost: 312000 },
];

let lots: MockLot[] | null = null;
const returns = new Map<string, { batch_id: string; status: string; qty_available: string; returned_qty: string; return_id: number }>();
let nextReturnId = 1;

function state(): MockLot[] {
  if (!lots) lots = seed();
  return lots;
}

const fmtKg = (n: number) => n.toFixed(3).replace(".", ",");
const dec3 = (n: number) => n.toFixed(3);
const err = (status: number, code: string, detail: string): MockResponse => ({ status, body: { code, detail } });
const FORBIDDEN: MockResponse = { status: 403, body: { detail: "Bạn không có quyền để thực hiện thao tác này." } };

function isoDay(daysAgo: number): string {
  // Ngày theo giờ VN (SR-25), không theo múi giờ máy. VN không đổi giờ mùa hè nên lùi N×24h = lùi N ngày.
  return todayInVietnam(new Date(Date.now() - daysAgo * 86_400_000));
}

function findLot(ref: string | number): MockLot | undefined {
  return state().find((l) => String(l.id) === String(ref) || l.batch_id === String(ref));
}

/** Số lô Quá hạn còn tồn — con số ở thẻ Cần chú ý `expired_batches_open` (features/overview/mock.ts). */
export function mockExpiredOpenCount(): number {
  return state().filter((l) => l.status === "EXPIRED" && l.qty_available > 0).length;
}

const STATUS_LABEL: Record<MockLot["status"], string> = { EXPIRED: "Quá hạn", CANCELLED: "Đã huỷ", CLOSED: "Đã chốt" };

function toApiRow(l: MockLot, canCost: boolean): BatchApiRow {
  const row: BatchApiRow = {
    id: l.id,
    batch_id: l.batch_id,
    item: l.id,
    item_code: l.item_code,
    item_name: l.item,
    supplier: l.id,
    supplier_name: l.supplier,
    warehouse: 1,
    warehouse_name: l.warehouse,
    status_label: STATUS_LABEL[l.status],
    received_date: isoDay(l.received_days_ago),
    expiry_date: isoDay(l.expired_days_ago),
    qty_available: dec3(l.qty_available),
    qty_reserved: dec3(l.qty_reserved),
    status: l.status,
  };
  if (canCost) row.landed_unit_cost = String(l.cost);
  return row;
}

/** GET /api/inventory/batches/?status=… — danh sách phân trang DRF. Lô mock chỉ có ở trạng thái Quá hạn/Đã huỷ/Đã chốt. */
export function mockBatchList(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!me.permissions.includes("inventory.view_batch") && !me.permissions.includes("reports.view_dashboard")) return FORBIDDEN;
  const q = new URLSearchParams(req.path.split("?")[1] || "");
  const status = q.get("status");
  const hasStock = q.get("has_stock") === "1"; // như BE: chỉ lô còn tồn (qty_available > 0)
  const rows = state()
    .filter((l) => (!status || l.status === status) && (!hasStock || l.qty_available > 0))
    .map((l) => toApiRow(l, me.can_view_cost));
  return { status: 200, body: { count: rows.length, next: null, previous: null, results: rows } };
}

type ProcessMissing = { code: string; text: string };

/** Mô phỏng `check_process_expired_stock` (02b §5.3) + quyền Chủ. */
function processMissing(me: Me, lot: MockLot): ProcessMissing[] {
  const out: ProcessMissing[] = [];
  if (!isOwner(me)) out.push({ code: "BR-PQ-12", text: "Chỉ Chủ được xác nhận xử lý phần tồn lô quá hạn." });
  if (lot.qty_reserved > 0)
    out.push({ code: "BR-LO-07", text: `Còn ${fmtKg(lot.qty_reserved)} kg đang giữ chỗ của 1 đơn — chờ đơn xử lý xong.` });
  return out;
}

function step(key: string, label: string, missing: ProcessMissing[], command: string, br: string, why: string): GuidanceNextStep {
  return {
    key,
    label,
    actor: "user",
    allowed: missing.length === 0,
    who: ["Chủ"],
    missing,
    deadline: null,
    why: { br, text: why },
    command,
    ai: null,
  };
}

/** Guidance `GET /api/guidance/batch/<id>/` cho lô mock quá hạn; null = không phải lô của module này (guidance mock trả mặc định). */
export function mockExpiredBatchGuidance(docId: string, req: MockRequest): MockResponse | null {
  const lot = findLot(docId);
  if (!lot) return null;
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const label = lot.status === "EXPIRED" ? "Quá hạn" : lot.status === "CANCELLED" ? "Đã huỷ" : "Đã chốt";
  const steps: GuidanceNextStep[] = [];
  if (lot.status === "EXPIRED") {
    if (lot.qty_available > 0) {
      const miss = processMissing(me, lot);
      steps.push(
        step("cancel_expired", "Xác nhận Đã huỷ phần tồn", miss, "inventory.batch.cancel_expired", "BR-LO-07",
          "Phần tồn quá hạn phải được xử lý: huỷ (ghi lỗ) hoặc trả nhà cung cấp."),
        step("return_to_supplier", "Xác nhận Đã trả NCC", miss, "inventory.batch.return_to_supplier", "BR-MH-08",
          "Ghi số kg đã trả nhà cung cấp; có thể chia nhiều lần."),
        step("close", "Chốt lô", [
          ...(isOwner(me) ? [] : [{ code: "BR-PQ-12", text: "Chỉ Chủ được chốt lô." }]),
          { code: "BR-LO-04", text: "Chốt lô yêu cầu tồn = 0 — xử lý hết phần tồn (Đã huỷ hoặc Đã trả NCC) trước." },
        ], "inventory.batch.close", "BR-LO-04", "Lô chỉ chốt khi không còn tồn.")
      );
    } else {
      steps.push(
        step("close", "Chốt lô", isOwner(me) ? [] : [{ code: "BR-PQ-12", text: "Chỉ Chủ được chốt lô." }],
          "inventory.batch.close", "BR-LO-04", "Lô hết tồn, có thể chốt.")
      );
    }
  }
  const data: GuidanceData = {
    doc: { type: "batch", id: docId, code: lot.batch_id, status: lot.status, status_label: label },
    next_steps: steps,
    warnings:
      lot.status === "EXPIRED" && lot.qty_available > 0
        ? [{ code: "GW-LO-07", text: `Lô quá hạn còn ${fmtKg(lot.qty_available)} kg tồn — cần xác nhận Đã huỷ hoặc Đã trả NCC.` }]
        : [],
    timeline: [
      {
        at: new Date(Date.now() - lot.received_days_ago * 86_400_000).toISOString(),
        kind: "batch_created",
        label: "Nhập lô",
        doc: "batch",
        actor: { kind: "system", display: "Hệ thống" },
      },
    ],
    related: [],
  };
  return { status: 200, body: data };
}

/** POST cancel-expired / close. `confirm_qty` (chuỗi thập phân) khác tồn thật → 400 BR-LO-07 (SR-15-AC5). */
export function mockBatchAction(kind: "cancel-expired" | "close", batchId: string | number, req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const lot = findLot(batchId);
  if (!lot) return { status: 404, body: { detail: "Không tìm thấy." } };
  if (!isOwner(me)) return FORBIDDEN;
  if (lot.status === "CLOSED") return err(400, "BR-LO-05", "Lô đã chốt.");
  if (kind === "close") {
    if (lot.qty_available > 0) return err(400, "BR-LO-04", `Chốt lô yêu cầu tồn = 0 (còn ${fmtKg(lot.qty_available)} kg).`);
    lot.status = "CLOSED";
  } else {
    if (lot.status !== "EXPIRED") return err(400, "BR-LO-07", "Chỉ huỷ phần tồn của lô Quá hạn.");
    if (lot.qty_reserved > 0)
      return err(400, "BR-LO-07", `Còn ${fmtKg(lot.qty_reserved)} kg đang giữ chỗ của 1 đơn — chờ đơn xử lý xong.`);
    const body = (req.body || {}) as { confirm_qty?: string };
    if (body.confirm_qty !== undefined && Number(body.confirm_qty) !== lot.qty_available)
      return err(400, "BR-LO-07", `Tồn đã đổi (${fmtKg(lot.qty_available)} kg) — tải lại.`);
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
  if (!lot) return { status: 404, body: { detail: "Không tìm thấy." } };
  if (!isOwner(me)) return FORBIDDEN;
  const body = (req.body || {}) as { qty?: string; supplier_refund_amount?: string; note?: string; request_id?: string };

  if (body.request_id && returns.has(body.request_id)) return { status: 200, body: returns.get(body.request_id) };

  if (lot.status === "CLOSED") return err(400, "BR-LO-05", "Lô đã chốt.");
  if (lot.status !== "EXPIRED" || lot.qty_available <= 0) return err(400, "BR-LO-07", "Chỉ xác nhận trả NCC cho lô Quá hạn còn tồn.");
  if (lot.qty_reserved > 0)
    return err(400, "BR-LO-07", `Còn ${fmtKg(lot.qty_reserved)} kg đang giữ chỗ của 1 đơn — chờ đơn xử lý xong.`);
  const qty = Number(body.qty);
  if (!Number.isFinite(qty) || qty <= 0 || qty > lot.qty_available)
    return err(400, "BR-MH-08", `Số kg trả phải lớn hơn 0 và không vượt tồn ${fmtKg(lot.qty_available)} kg.`);
  const refund = Number(body.supplier_refund_amount || 0);
  if (!Number.isFinite(refund) || refund < 0) return err(400, "BR-MH-08", "Tiền NCC hoàn không được âm.");
  if (/\d{8,}/.test(body.note || "")) return err(400, "BR-MH-08", "Ghi chú không được chứa dãy số dài (tránh nhập số điện thoại).");

  lot.qty_available = Math.round((lot.qty_available - qty) * 1000) / 1000;
  const result = {
    batch_id: lot.batch_id,
    status: lot.status,
    qty_available: dec3(lot.qty_available),
    returned_qty: dec3(qty),
    return_id: nextReturnId++,
  };
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
    expiredState: () => state().map((l) => ({ batch_id: l.batch_id, status: l.status, qty_available: l.qty_available, qty_reserved: l.qty_reserved })),
    expiredReset: () => {
      lots = seed();
      returns.clear();
      return "Đã về seed";
    },
  };
}
