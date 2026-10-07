// Mock module audit — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
//   GET /api/audit-logs/?page=&actor_kind=&action=&actor=&date_from=&date_to=&q=   (S03; Lô 17a thêm ngày + q; quyền accounts.view_auditlog = Chủ + Quản lý)
// Đúng contract BE: `actor_display` = TÊN ĐĂNG NHẬP (dòng AI: "ai:<tên đăng nhập>", dòng hệ thống: "system"),
// `ai_actor` = mã số người dùng, `changes` bỏ khoá giá vốn khi người xem không có `view_costprice`.
// Dữ liệu GIẢ: chỉ mã chứng từ / mã đề xuất, KHÔNG có tên/SĐT/địa chỉ khách (bất biến 9).

import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { MOCK_UNAUTHORIZED, mockRequireUser, mockUsers } from "@/features/auth/mock";
import { dateKeyInVietnam } from "@/shared/lib/format";
import type { AuditLogRow } from "./types";

const VIEW_PERM = "accounts.view_auditlog";
const COST_PERM = "inventory.view_costprice";
const PAGE_SIZE = 20;

/** Khoá giá vốn BE bỏ khỏi `changes` khi thiếu quyền (apps/common/cost_keys.py) — mock bỏ giống hệt để e2e thử được. */
const COST_KEYS = new Set(["purchase_rate", "landed_unit_cost", "unit_cost", "rate", "purchase_cost", "total_cost", "profit", "margin", "inventory_value"]);

function redact(changes: Record<string, unknown> | null): Record<string, unknown> | null {
  if (!changes) return null;
  return Object.fromEntries(Object.entries(changes).filter(([k]) => !COST_KEYS.has(k)));
}

type Seed = [
  id: number,
  time: string,
  kind: AuditLogRow["actor_kind"],
  username: string | null,
  aiOf: string | null,
  action: string,
  model: string,
  objectId: number | null,
  objectRepr: string | null,
  changes: Record<string, unknown> | null,
  note: string | null,
  proposal: string | null,
];

const SEEDS: Seed[] = [
  [136, "2026-09-27T10:40:00+07:00", "system", null, null, "delivery_advance_status", "delivery.DeliveryNote", 78, "GH-20260927-022", { status: ["DELIVERING", "FAILED"] }, "Giao thất bại", null],
  [135, "2026-09-27T10:36:00+07:00", "user", "kho1", null, "label_printed", "delivery.DeliveryNote", 78, "GH-20260927-022", null, "In tem giao", null],
  [134, "2026-09-27T10:32:00+07:00", "ai", null, "kho1", "execute_command", "commands", null, null, null, "Lệnh tra_ton", "P-012"],
  [133, "2026-09-27T10:28:00+07:00", "ai", null, "loc", "execute_command", "commands", null, null, null, "Lệnh tra_don", "P-011"],
  [132, "2026-09-27T10:29:00+07:00", "user", "loc", null, "confirm_proposal", "commands", 11, "P-011", null, "Duyệt đề xuất AI P-011", "P-011"],
  [131, "2026-09-27T10:20:00+07:00", "system", null, null, "order_auto_cancelled", "sales.SalesOrder", 1004, "SO-20260927-038", { status: ["BOOKED", "AUTO_CANCELLED"] }, "Hết giờ giữ chỗ", null],
  [130, "2026-09-27T10:14:00+07:00", "user", "kho1", null, "close_batch", "inventory.Batch", 3, "B-03", { status: ["ACTIVE", "CLOSED"], unit_cost: [41000, 41000] }, "Chốt lô", null],
  [129, "2026-09-27T09:58:00+07:00", "user", "ql1", null, "publish_batch", "inventory.Batch", 2, "B-02", { status: ["DRAFT", "ACTIVE"], purchase_rate: [38000, 38000] }, "Mở bán lô", null],
  [128, "2026-09-27T09:41:00+07:00", "ai", null, "ql1", "propose", "commands", null, null, null, "Đề xuất nhập lô (chờ duyệt)", "P-010"],
  [127, "2026-09-27T09:43:00+07:00", "user", "loc", null, "confirm_proposal", "commands", 10, "P-010", null, "Duyệt đề xuất AI P-010", "P-010"],
  [126, "2026-09-27T09:30:00+07:00", "user", "loc", null, "create_refund", "sales.Refund", 8, "HT-20260927-003", { amount: { to: 125000 } }, "Lập phiếu hoàn tiền", null],
  [125, "2026-09-27T09:12:00+07:00", "system", null, null, "auto_confirm_exact_match", "sales.PaymentTransaction", 41, "FT2626700017", null, "Tiền về khớp đơn SO-20260927-033", null],
  [124, "2026-09-27T08:55:00+07:00", "user", "loc", null, "confirm_payment_manual", "sales.SalesOrder", 1033, "SO-20260927-033", { status: ["BOOKED", "PAID"] }, "Xác nhận tiền về tay", null],
  [123, "2026-09-27T08:40:00+07:00", "user", "kho1", null, "create_and_submit_receipt", "purchasing.PurchaseReceipt", 19, "PN-20260927-002", { line_count: 3 }, "Nhập lô tại cảng", null],
  [122, "2026-09-27T08:22:00+07:00", "ai", null, "kho1", "propose", "commands", null, null, null, "Đề xuất nhập lô (chờ duyệt)", "P-009"],
  [121, "2026-09-27T08:25:00+07:00", "user", "loc", null, "confirm_proposal", "commands", 9, "P-009", null, "Duyệt đề xuất AI P-009", "P-009"],
  [120, "2026-09-27T08:02:00+07:00", "user", "giao1", null, "delivery_advance_status", "delivery.DeliveryNote", 77, "GH-20260927-021", { status: ["READY", "DELIVERING"] }, "Bắt đầu giao", null],
  [119, "2026-09-27T07:48:00+07:00", "system", null, null, "cancel_expired_batch", "inventory.Batch", 1, "B-01", null, "Lô hết hạn dùng", null],
  [118, "2026-09-27T07:30:00+07:00", "ai", null, "loc", "execute_command", "commands", null, null, null, "Lệnh goi_y_fefo", "P-008"],
  [117, "2026-09-27T07:15:00+07:00", "user", "cs2", null, "recipient_changed", "sales.SalesOrder", 1029, "SO-20260927-029", null, "Đổi thông tin nhận hàng", null],
  [116, "2026-09-26T18:44:00+07:00", "user", "loc", null, "staff_groups_change", "user", 5, null, { groups: { from: ["warehouse_staff"], to: ["warehouse_staff", "delivery_staff"] } }, "Đổi nhóm quyền", null],
  [115, "2026-09-26T18:30:00+07:00", "user", "ql1", null, "approve_stockreconciliation", "inventory.StockReconciliation", 5, "KK-20260926-001", { line_count: 4, loss_amount: 90000 }, "Duyệt kiểm kê", null],
  [114, "2026-09-26T17:58:00+07:00", "user", "kho1", null, "create_stockreconciliation", "inventory.StockReconciliation", 5, "KK-20260926-001", { line_count: 4 }, "Tạo phiếu kiểm kê", null],
  [113, "2026-09-26T17:20:00+07:00", "ai", null, "kho1", "execute_command", "commands", null, null, null, "Lệnh tra_lo", "P-007"],
  [112, "2026-09-26T16:55:00+07:00", "user", "loc", null, "staff_password_reset", "user", 4, null, null, "Đặt lại mật khẩu", null],
  [111, "2026-09-26T16:10:00+07:00", "user", "ql1", null, "update_itemprice", "catalog.ItemPrice", 2, "CA-001", { price: [110000, 115000] }, "Đổi giá niêm yết", null],
];

/** Chuyển hạt giống thành dòng theo contract BE; id người dùng lấy từ danh sách mock hiện có (để lọc ?actor= khớp). */
function buildRows(canCost: boolean): AuditLogRow[] {
  const users = mockUsers();
  const idOf = (username: string | null) => users.find((u) => u.username === username)?.id ?? null;
  return SEEDS.map(([id, time, kind, username, aiOf, action, model, objectId, objectRepr, changes, note, proposal]) => ({
    id,
    created_at: time,
    actor_kind: kind,
    actor_display: kind === "ai" ? `ai:${aiOf}` : kind === "system" ? "system" : (username as string),
    ai_actor: kind === "ai" ? idOf(aiOf) : null,
    action,
    model_name: model,
    object_id: objectId,
    object_repr: objectRepr,
    changes: canCost ? changes : redact(changes),
    note,
    proposal_ref: proposal,
  }));
}

/** GET /api/audit-logs/ — 20 dòng/trang, mới → cũ. Thiếu quyền → 403 (S03-AC5). `?actor=` sai dạng → 400 INVALID_FILTER. */
export function mockAuditLogs(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!me.permissions.includes(VIEW_PERM)) {
    return { status: 403, body: { detail: "Thiếu quyền xem nhật ký hành động." } };
  }
  const p = new URL(req.path, "http://mock").searchParams;
  const kind = (p.get("actor_kind") || "").trim();
  const action = (p.get("action") || "").trim();
  const actorRaw = p.get("actor");
  let actorId: number | null = null;
  if (actorRaw) {
    if (!/^[1-9]\d*$/.test(actorRaw)) {
      return { status: 400, body: { detail: "Tham số actor phải là mã người dùng (số nguyên dương).", code: "INVALID_FILTER" } };
    }
    actorId = Number(actorRaw);
  }
  // Lô 17a (A3): ngày theo giờ VN, gồm cả hai đầu; `q` 2–40 ký tự [0-9A-Za-z#._-], không có dãy 9 chữ số; câu lỗi không lặp lại q.
  const invalid = (detail: string): MockResponse => ({ status: 400, body: { detail, code: "INVALID_FILTER" } });
  const dayOk = (v: string) => /^\d{4}-\d{2}-\d{2}$/.test(v) && Number(v.slice(0, 4)) >= 2000 && Number(v.slice(0, 4)) <= 2100 && !Number.isNaN(Date.parse(v));
  const from = (p.get("date_from") || "").trim();
  const to = (p.get("date_to") || "").trim();
  if ((from && !dayOk(from)) || (to && !dayOk(to))) return invalid("Ngày phải có dạng YYYY-MM-DD.");
  if (from && to && from > to) return invalid("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.");
  const q = (p.get("q") || "").trim();
  if (p.has("q") && q) {
    if (/\d{9,}/.test(q)) return invalid("Chỉ tìm theo mã chứng từ.");
    if (q.length < 2 || q.length > 40 || !/^[0-9A-Za-z#._-]+$/.test(q)) return invalid("Mã tìm phải dài 2–40 ký tự, chỉ gồm chữ không dấu, số và # . _ -");
  }
  const actorName = actorId === null ? null : mockUsers().find((u) => u.id === actorId)?.username ?? "";
  let rows = buildRows(me.permissions.includes(COST_PERM));
  if (kind) rows = rows.filter((r) => r.actor_kind === kind);
  if (action) rows = rows.filter((r) => r.action === action);
  if (from) rows = rows.filter((r) => dateKeyInVietnam(r.created_at) >= from);
  if (to) rows = rows.filter((r) => dateKeyInVietnam(r.created_at) <= to);
  if (q) rows = rows.filter((r) => `${r.object_repr ?? ""} ${r.proposal_ref ?? ""}`.toLowerCase().includes(q.toLowerCase()));
  // Như BE: ?actor= chỉ lấy dòng do chính người đó làm (không gồm dòng AI thay mặt, không gồm dòng Hệ thống).
  if (actorName !== null) rows = rows.filter((r) => r.actor_kind === "user" && r.actor_display === actorName);
  const page = Math.max(1, Number(p.get("page") || "1") || 1);
  const count = rows.length;
  const next = new URLSearchParams(p);
  next.set("page", String(page + 1));
  return {
    status: 200,
    body: {
      count,
      next: page * PAGE_SIZE < count ? `/api/audit-logs/?${next.toString()}` : null,
      previous: page > 1 ? "/api/audit-logs/" : null,
      results: rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    },
  };
}
