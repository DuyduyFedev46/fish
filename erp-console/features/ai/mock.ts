// Mock module AI — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Mock toàn bộ endpoint Lô 1–2 theo contract 02b-tech-design.md mục 3, để FE làm song song với BE:
//   GET  /api/ai/status/                        (S05 — luôn 200, ai_enabled đọc cờ mock)
//   GET  /api/commands/catalog/                 (S01 — 12 lệnh active, lọc theo min_permissions)
//   POST /api/commands/execute/                 (S02 — 410 khi AI tắt, cấm kênh, Tầng 2 → sinh đề xuất)
//   POST /api/commands/propose/ · GET/POST /api/commands/proposals/<id>/[/confirm/]
//   GET  /api/audit-logs/                       (S03 — màn Nhật ký hoạt động, module features/audit dùng)
// Dữ liệu GIẢ — không chứa tên/SĐT/địa chỉ khách; changes/note chỉ có mã đơn/mã lệnh/mã đề xuất (S03-AC4, bất biến 9).
//
// Cờ: localStorage "cave_erp_mock_ai"="on" → ai_enabled (MẶC ĐỊNH TẮT — để e2e cũ vẫn thấy khung chờ
// "Trợ lý đang được nối, sắp có" và không phát sinh request). Bật nhanh trong DevTools:
//   window.__caveMock.ai("on" | "off")   — bật/tắt cờ AI (localStorage)
//   window.__caveMock.aiConsent(true)    — đặt cờ đã đồng ý tải model

import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { MOCK_UNAUTHORIZED, mockRequireUser, mockUsers } from "@/features/auth/mock";
import { setAiConsent } from "./consent";
import type { AuditLogRow, CommandSpec } from "./types";

const AI_ON_KEY = "cave_erp_mock_ai";

function aiEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(AI_ON_KEY) === "on";
  } catch {
    return false;
  }
}

function qs(req: MockRequest): URLSearchParams {
  return new URL(req.path, "http://mock").searchParams;
}

/** Lỗi theo contract S02: body dùng key `error` (+ `br_code`), khác dạng `{detail}` của beError. */
function cmdError(status: number, body: { error: string; br_code?: string }): MockResponse {
  return { status, body };
}

const AI_OFF = cmdError(410, { error: "AI_DISABLED" });
const UNKNOWN = cmdError(404, { error: "COMMAND_UNKNOWN" });

// ================= S05 — /api/ai/status/ =================

/** GET /api/ai/status/ — luôn 200; `model` từ env override (S17 chưa chốt → null); budget chỉ chu. */
export function mockStatus(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const name = process.env.NEXT_PUBLIC_AI_MODEL_NAME;
  const url = process.env.NEXT_PUBLIC_AI_MODEL_GGUF_URL;
  return {
    status: 200,
    body: {
      ai_enabled: aiEnabled(),
      cloud_enabled: false,
      model: name && url ? { name, version: "dev", gguf_url: url } : null,
      budget: me.groups.includes("chu") ? { spent_vnd: 0, limit_vnd: 200000, status: "ok" } : null,
    },
  };
}

// ================= S01 — registry lệnh (Phụ lục B, 12 lệnh active) =================

/** input_schema cho nhap_lo — theo S07 (chỉ trường dữ liệu, không trường giá vốn ra ngoài). */
const NHAP_LO_SCHEMA = {
  type: "object",
  required: ["supplier_id", "lines"],
  properties: {
    supplier_id: { type: "integer", description: "ID nhà cung cấp" },
    received_date: { type: "string", description: "Ngày nhận (YYYY-MM-DD)" },
    warehouse_id: { type: "integer", description: "ID kho" },
    lines: {
      type: "array",
      items: {
        type: "object",
        required: ["item_id", "quantity", "purchase_rate"],
        properties: {
          item_id: { type: "integer" },
          quantity: { type: "number" },
          unit: { type: "string" },
          purchase_rate: { type: "number" },
          batch_no: { type: "string" },
          shelf_life_days: { type: "integer" },
          expiry_date: { type: "string" },
        },
      },
    },
  },
};

const LOOKUP_SCHEMA = {
  type: "object",
  properties: {
    ma_hang: { type: "string", description: "Mã mặt hàng (vd CA-001)" },
    ma_lo: { type: "string", description: "Mã lô (vd B-01)" },
    ma_don: { type: "string", description: "Mã đơn (vd SO-20260927-041)" },
  },
};

function c(
  name: string,
  channel: CommandSpec["channel"],
  sensitivity: CommandSpec["sensitivity"],
  min_permissions: string[],
  description: string,
  opts: {
    needs_confirmation?: boolean;
    forbidden_channel?: null | "ai";
    input?: Record<string, unknown>;
    output?: Record<string, unknown>;
  } = {},
): CommandSpec {
  return {
    name,
    channel,
    sensitivity,
    min_permissions,
    input_schema: opts.input ?? LOOKUP_SCHEMA,
    output_schema: opts.output ?? { type: "object" },
    description,
    needs_confirmation: opts.needs_confirmation ?? false,
    forbidden_channel: opts.forbidden_channel ?? null,
  };
}

const CATALOG: CommandSpec[] = [
  c("nhap_lo", "local", "cao", ["purchasing.add_purchasereceipt"], "Nhập lô hàng mua tại cảng", {
    needs_confirmation: true,
    input: NHAP_LO_SCHEMA,
  }),
  c("tra_ton", "local", "trung_binh", ["inventory.view_batch"], "Tra tồn kho theo mặt hàng"),
  c("tra_lo", "local", "cao", ["inventory.view_batch"], "Tra lô theo hạn dùng, nơi để, số lượng"),
  c("tra_hang", "local", "thap", ["catalog.view_item"], "Tra thông tin mặt hàng và giá niêm yết"),
  c("tra_don", "local", "trung_binh", ["sales.view_salesorder"], "Tra trạng thái đơn và tiền đã nhận"),
  c("bao_cao_ton_kho", "cloud", "thap", ["reports.view_dashboard"], "Báo cáo tồn kho theo nhóm hàng"),
  c("bao_cao_lo", "cloud", "cao", ["reports.view_profitreport"], "Báo cáo lãi lỗ theo lô"),
  c("bao_cao_ky", "cloud", "cao", ["reports.view_profitreport"], "Báo cáo lãi lỗ theo kỳ"),
  c("chot_lo", "local", "cao", ["inventory.close_batch"], "Chốt lô — ngừng bán, đối soát lãi lỗ", {
    forbidden_channel: "ai",
  }),
  c("tao_phieu_hoan", "local", "cao", ["sales.create_refund"], "Lập phiếu hoàn tiền cho đơn", {
    needs_confirmation: true,
  }),
  c("xac_nhan_hoan", "local", "cao", ["sales.confirm_refund"], "Xác nhận đã chuyển khoản hoàn tiền", {
    forbidden_channel: "ai",
  }),
  c("xac_nhan_thanh_toan_tay", "local", "cao", ["sales.confirm_payment_manual"], "Xác nhận tiền về tay cho đơn", {
    forbidden_channel: "ai",
  }),
  c("goi_y_fefo", "local", "thap", ["inventory.view_batch"], "Gợi ý xuất lô theo hạn dùng sớm nhất (FEFO)"),
];

/** GET /api/commands/catalog/ — chỉ lệnh active, lọc theo min_permissions của người gọi (S01-AC2). */
export function mockCatalog(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const commands = CATALOG.filter((spec) => spec.min_permissions.every((p) => me.permissions.includes(p)));
  return { status: 200, body: { commands } };
}

// ================= S02 — execute / propose / proposals =================

function findCmd(name: string): CommandSpec | undefined {
  return CATALOG.find((s) => s.name === name);
}

/** Đề xuất giữ trong bộ nhớ phiên (mock) — đủ cho luồng demo propose → confirm. */
const PROPOSALS = new Map<
  number,
  { id: number; command: string; args: Record<string, unknown>; reason: string; channel: "ai_local" | "ai_cloud"; expires_at: string; by: string }
>();
let proposalSeq = 10;

function makeProposal(command: string, args: Record<string, unknown>, reason: string, by: string): MockResponse {
  const id = ++proposalSeq;
  const expires = new Date(Date.now() + 15 * 60 * 1000).toISOString();
  PROPOSALS.set(id, {
    id,
    command,
    args,
    reason,
    channel: "ai_local",
    expires_at: expires,
    by,
  });
  return { status: 200, body: { proposal_id: id, expires_at: expires } };
}

function checkExecute(req: MockRequest, me: { permissions: string[] }, body: { command: string; args?: Record<string, unknown>; channel: string }, allowUi: boolean): MockResponse | null {
  const spec = findCmd(body.command);
  if (!spec) return UNKNOWN;
  const channel = String(body.channel || "");
  const isAi = channel === "ai_local" || channel === "ai_cloud";
  if (isAi && !aiEnabled()) return AI_OFF; // S02-AC7
  if (allowUi && channel !== "ui" && !isAi) return cmdError(400, { error: "CHANNEL_INVALID", br_code: "BR-AI-02" });
  if (spec.forbidden_channel === "ai" && isAi) {
    return cmdError(403, { error: "Lệnh này cấm chạy qua kênh AI — làm trên màn hình thường.", br_code: "BR-AI-07" });
  }
  // Router chặn ngược kênh (S02-AC6): lệnh local chỉ kênh ui/ai_local, lệnh cloud chỉ kênh ai_cloud
  if (isAi && spec.channel === "local" && channel === "ai_cloud") {
    return cmdError(400, { error: "Lệnh chạy trên máy không gửi được qua kênh cloud.", br_code: "BR-AI-02" });
  }
  if (isAi && spec.channel === "cloud" && channel === "ai_local") {
    return cmdError(400, { error: "Lệnh cloud không chạy được trên máy.", br_code: "BR-AI-02" });
  }
  if (!spec.min_permissions.every((p) => me.permissions.includes(p))) {
    return cmdError(403, { error: "Bạn không có quyền chạy lệnh này.", br_code: "BR-PQ-12" });
  }
  if (spec.name === "nhap_lo") {
    const a = (body.args || {}) as { supplier_id?: unknown; lines?: unknown };
    if (typeof a.supplier_id !== "number" || !Array.isArray(a.lines) || a.lines.length === 0) {
      return cmdError(400, { error: "nhap_lo cần supplier_id và lines (theo input_schema).", br_code: "BR-AI-01" });
    }
  }
  return null;
}

/** POST /api/commands/execute/ — kênh AI + lệnh cần xác nhận → trả bản nháp đề xuất (S02-AC2). */
export function mockExecute(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const body = (req.body || {}) as { command: string; args?: Record<string, unknown>; channel: string };
  const err = checkExecute(req, me, body, true);
  if (err) return err;
  const spec = findCmd(body.command)!;
  const isAi = body.channel === "ai_local" || body.channel === "ai_cloud";
  if (isAi && spec.needs_confirmation) return makeProposal(body.command, body.args || {}, "", me.username);
  return { status: 200, body: { command: body.command, result: { ok: true } } };
}

/** POST /api/commands/propose/ — luôn sinh bản nháp, không thực thi. */
export function mockPropose(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const body = (req.body || {}) as { command: string; args?: Record<string, unknown>; reason: string; channel: string };
  const err = checkExecute(req, me, { ...body, channel: body.channel || "ai_local" }, false);
  if (err) return err;
  return makeProposal(body.command, body.args || {}, body.reason || "", me.username);
}

/** GET /api/commands/proposals/<id>/ */
export function mockGetProposal(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const m = req.path.match(/\/proposals\/(\d+)\//);
  const p = m ? PROPOSALS.get(Number(m[1])) : undefined;
  if (!p) return cmdError(404, { error: "PROPOSAL_NOT_FOUND" });
  return { status: 200, body: { id: p.id, command: p.command, args: p.args, reason: p.reason, channel: p.channel, status: "pending", created_by_display: p.by, created_at: p.expires_at, expires_at: p.expires_at } };
}

/** POST /api/commands/proposals/<id>/confirm/ — quá TTL 15 phút → 410 PROPOSAL_EXPIRED. */
export function mockConfirmProposal(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const m = req.path.match(/\/proposals\/(\d+)\/confirm\/?$/);
  const p = m ? PROPOSALS.get(Number(m[1])) : undefined;
  if (!p) return cmdError(404, { error: "PROPOSAL_NOT_FOUND" });
  if (new Date(p.expires_at).getTime() < Date.now()) return cmdError(410, { error: "PROPOSAL_EXPIRED" });
  PROPOSALS.delete(p.id);
  return { status: 200, body: { command: p.command, result: { ok: true } } };
}

// ================= S03 — /api/audit-logs/ (màn Nhật ký hoạt động) =================
// Contract: quyền accounts.view_auditlog (chu + quan_ly); nv_kho/nv_giao → 403 (S03-AC5).
// Dòng AI: actor_display = "ai:<tên user>" (S03-AC2). changes/note CHỈ chứa mã đơn/mã lệnh/mã đề xuất (S03-AC4).

const AI_PERM = "accounts.view_auditlog";

type MockUserRef = { id: number; username: string; display_name: string };

function buildRows(): AuditLogRow[] {
  const users = mockUsers();
  const u = (username: string) => users.find((x) => x.username === username);
  const loc = u("loc");
  const kho = u("kho1");
  const ql = u("ql1");
  const row = (
    id: number,
    time: string,
    kind: AuditLogRow["actor_kind"],
    display: string,
    aiActor: AuditLogRow["ai_actor"],
    action: string,
    modelName: string,
    objectId: number | null,
    objectRepr: string | null,
    changes: Record<string, unknown> | null,
    note: string | null,
    proposalRef: string | null,
  ): AuditLogRow => ({ id, created_at: time, actor_kind: kind, actor_display: display, ai_actor: aiActor, action, model_name: modelName, object_id: objectId, object_repr: objectRepr, changes, note, proposal_ref: proposalRef });
  const ai = (u: MockUserRef | undefined) => (u ? { id: u.id, username: u.username, display_name: u.display_name } : null);
  const rows: AuditLogRow[] = [
    row(134, "2026-09-27T10:32:00+07:00", "ai", "ai:Anh Tâm", ai(kho), "execute_command", "commands", null, null, null, "Lệnh tra_ton (ma_hang=CA-001)", "P-012"),
    row(133, "2026-09-27T10:28:00+07:00", "ai", "ai:Lộc", ai(loc), "execute_command", "commands", null, null, null, "Lệnh tra_don (ma_don=SO-20260927-041)", "P-011"),
    row(132, "2026-09-27T10:29:00+07:00", "user", "Lộc", null, "confirm_proposal", "commands", 11, "P-011", null, "Xác nhận đề xuất AI P-011", "P-011"),
    row(131, "2026-09-27T10:20:00+07:00", "system", "Hệ thống", null, "auto_cancel", "sales_order", 1004, "SO-20260927-038", null, "Đơn tự huỷ vì quá hạn thanh toán", null),
    row(130, "2026-09-27T10:14:00+07:00", "user", "Anh Tâm", null, "update", "batch", 3, "B-03 · Cá thu", { quantity: [10, 8] }, "Xuất bán 2 kg theo FEFO", null),
    row(129, "2026-09-27T09:58:00+07:00", "user", "Chị Hạnh", null, "publish", "batch", 2, "B-02 · Cá hồi", null, "Mở bán lô", null),
    row(128, "2026-09-27T09:41:00+07:00", "ai", "ai:Chị Hạnh", ai(ql), "propose", "commands", null, null, null, "Đề xuất lệnh nhap_lo (chờ xác nhận)", "P-010"),
    row(127, "2026-09-27T09:43:00+07:00", "user", "Lộc", null, "confirm_proposal", "commands", 10, "P-010", null, "Xác nhận đề xuất AI P-010", "P-010"),
    row(126, "2026-09-27T09:30:00+07:00", "user", "Lộc", null, "create", "sales_refund", 8, "HT-20260927-003", null, "Lập phiếu hoàn", null),
    row(125, "2026-09-27T09:12:00+07:00", "system", "Hệ thống", null, "payment_matched", "payment_transaction", 41, "FT2626700017", null, "Giao dịch khớp đơn SO-20260927-033", null),
    row(124, "2026-09-27T08:55:00+07:00", "user", "Lộc", null, "confirm_payment", "sales_order", 1033, "SO-20260927-033", null, "Xác nhận tiền về tay", null),
    row(123, "2026-09-27T08:40:00+07:00", "user", "Anh Tâm", null, "create", "purchase_receipt", 19, "PN-20260927-002", null, "Nhập lô tại cảng", null),
    row(122, "2026-09-27T08:22:00+07:00", "ai", "ai:Anh Tâm", ai(kho), "propose", "commands", null, null, null, "Đề xuất lệnh nhap_lo (chờ xác nhận)", "P-009"),
    row(121, "2026-09-27T08:25:00+07:00", "user", "Lộc", null, "confirm_proposal", "commands", 9, "P-009", null, "Xác nhận đề xuất AI P-009", "P-009"),
    row(120, "2026-09-27T08:02:00+07:00", "user", "Anh Phúc", null, "update", "delivery_note", 77, "GH-20260927-021", { status: ["PREPARING", "DELIVERING"] }, "Bắt đầu giao", null),
    row(119, "2026-09-27T07:48:00+07:00", "system", "Hệ thống", null, "expiry_warning", "batch", 1, "B-01 · Cá thu", null, "Lô còn 1 ngày hết hạn dùng", null),
    row(118, "2026-09-27T07:30:00+07:00", "ai", "ai:Lộc", ai(loc), "execute_command", "commands", null, null, null, "Lệnh goi_y_fefo", "P-008"),
    row(117, "2026-09-27T07:15:00+07:00", "user", "Chị Hạnh", null, "update", "sales_order", 1029, "SO-20260927-029", null, "Sửa đơn", null),
    row(116, "2026-09-26T18:44:00+07:00", "user", "Lộc", null, "close_batch", "batch", 1, "B-01 · Cá thu", null, "Chốt lô cuối ngày", null),
    row(115, "2026-09-26T18:30:00+07:00", "system", "Hệ thống", null, "stocktake_approved", "stock_reconciliation", 5, "KK-20260926-001", null, "Duyệt kiểm kê", null),
    row(114, "2026-09-26T17:58:00+07:00", "user", "Anh Tâm", null, "create", "stock_reconciliation", 5, "KK-20260926-001", null, "Tạo phiếu kiểm kê", null),
    row(113, "2026-09-26T17:20:00+07:00", "ai", "ai:Anh Tâm", ai(kho), "execute_command", "commands", null, null, null, "Lệnh tra_lo (ma_lo=B-01)", "P-007"),
    row(112, "2026-09-26T16:55:00+07:00", "user", "Lộc", null, "create", "batch", 6, "B-06 · Cá chim", null, "Mở bán lô mới", null),
    row(111, "2026-09-26T16:10:00+07:00", "user", "Chị Hạnh", null, "update", "catalog_item", 2, "CA-001 · Cá thu", { price: [110000, 115000] }, "Đổi giá niêm yết", null),
  ];
  return rows;
}

/** GET /api/audit-logs/?page=&actor_kind=&action= — 20 dòng/trang, mới → cũ. Thiếu quyền → 403 (S03-AC5). */
export function mockAuditLogs(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!me.permissions.includes(AI_PERM)) {
    return { status: 403, body: { detail: "Bạn không được cấp quyền để thực hiện hành động này." } };
  }
  const p = qs(req);
  const kind = (p.get("actor_kind") || "") as "" | AuditLogRow["actor_kind"];
  const action = (p.get("action") || "").trim();
  let rows = buildRows();
  if (kind) rows = rows.filter((r) => r.actor_kind === kind);
  if (action) rows = rows.filter((r) => r.action === action);
  const page = Math.max(1, Number(p.get("page") || "1") || 1);
  const per = 20;
  const count = rows.length;
  const results = rows.slice((page - 1) * per, page * per);
  const q = (extra: string) => {
    const sp = new URLSearchParams();
    if (kind) sp.set("actor_kind", kind);
    if (action) sp.set("action", action);
    if (extra) sp.set("page", extra);
    const s = sp.toString();
    return s ? `?${s}` : "";
  };
  const hasNext = page * per < count;
  return {
    status: 200,
    body: {
      count,
      next: hasNext ? `/api/audit-logs/${q(String(page + 1))}` : null,
      previous: page > 1 ? `/api/audit-logs/${q(String(page - 1))}` : null,
      results,
    },
  };
}

// ---- Công cụ thử trong DevTools (chỉ có ở mock) ----
if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    ai: (mode: "on" | "off") => {
      try {
        if (mode === "on") window.localStorage.setItem(AI_ON_KEY, "on");
        else window.localStorage.removeItem(AI_ON_KEY);
      } catch {
        /* storage chặn → giữ nguyên */
      }
      return aiEnabled();
    },
    aiConsent: (v: boolean) => setAiConsent(v),
  };
}
