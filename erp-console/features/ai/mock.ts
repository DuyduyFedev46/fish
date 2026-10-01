// Mock module AI — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Mock endpoint theo contract 02b-tech-design.md mục 6:
//   GET  /api/ai/status/                        (S05 — luôn 200, ai_enabled đọc cờ mock)
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
import { ROLE } from "@/shared/lib/roles";
import type { AuditLogRow } from "./types";

const AI_ON_KEY = "cave_erp_mock_ai";

/** Cờ AI toàn cục của mock (server thật: Chủ tắt AI → mọi `step.ai` = null). Dùng cả ở features/guidance/mock. */
export function aiEnabled(): boolean {
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
      budget: me.groups.includes(ROLE.owner) ? { spent_vnd: 0, limit_vnd: 200000, status: "ok" } : null,
    },
  };
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
    row(128, "2026-09-27T09:41:00+07:00", "ai", "ai:Chị Hạnh", ai(ql), "propose", "commands", null, null, null, "Đề xuất lệnh receive_batches (chờ xác nhận)", "P-010"),
    row(127, "2026-09-27T09:43:00+07:00", "user", "Lộc", null, "confirm_proposal", "commands", 10, "P-010", null, "Xác nhận đề xuất AI P-010", "P-010"),
    row(126, "2026-09-27T09:30:00+07:00", "user", "Lộc", null, "create", "sales_refund", 8, "HT-20260927-003", null, "Lập phiếu hoàn", null),
    row(125, "2026-09-27T09:12:00+07:00", "system", "Hệ thống", null, "payment_matched", "payment_transaction", 41, "FT2626700017", null, "Giao dịch khớp đơn SO-20260927-033", null),
    row(124, "2026-09-27T08:55:00+07:00", "user", "Lộc", null, "confirm_payment", "sales_order", 1033, "SO-20260927-033", null, "Xác nhận tiền về tay", null),
    row(123, "2026-09-27T08:40:00+07:00", "user", "Anh Tâm", null, "create", "purchase_receipt", 19, "PN-20260927-002", null, "Nhập lô tại cảng", null),
    row(122, "2026-09-27T08:22:00+07:00", "ai", "ai:Anh Tâm", ai(kho), "propose", "commands", null, null, null, "Đề xuất lệnh receive_batches (chờ xác nhận)", "P-009"),
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
