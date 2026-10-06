// Logic THUẦN của màn Nhật ký (ED-41 / W3f): nhãn thao tác, tên người làm, người duyệt, tóm tắt "Thay đổi", lọc phía máy.
// Không React, không gọi API -> test bằng vitest. Quy tắc an toàn dữ liệu (bất biến 1 + 9):
//  - "Thay đổi" CHỈ in những khoá trong danh sách trắng (trạng thái, số lượng, số tiền, giá bán, đang làm, nhóm quyền).
//    Mọi khoá khác (kể cả giá vốn/lãi lỗ, tên, SĐT, địa chỉ) bị bỏ, không bao giờ in JSON thô.
//  - Không ghi tên đăng nhập/giá trị nào ra console hay storage; chỉ hiện trên trang.

import { ENUMS, type EnumTable } from "@/shared/lib/enums";
import { dateKeyInVietnam, vnd } from "@/shared/lib/format";
import { GROUP_LABEL } from "@/shared/lib/groups";
import type { AuditActorKind, AuditLogRow } from "./types";

/** Một tên cho một thao tác (UI-RULES §3). Khoá = `action` thật của BE (+ vài động từ chung và lệnh AI). */
export const AUDIT_ACTION_LABELS: Readonly<Record<string, string>> = {
  // kho / lô
  publish_batch: "Mở bán lô",
  close_batch: "Chốt lô",
  cancel_expired_batch: "Huỷ lô hết hạn",
  return_batch_to_supplier: "Trả lô về nhà cung cấp",
  return_to_warehouse: "Trả hàng về kho",
  create_and_submit_receipt: "Nhập lô mua tại cảng",
  cancel_purchase_receipt: "Huỷ phiếu nhập",
  recompute_landed_cost: "Tính lại giá vốn",
  create_warehouse: "Thêm kho",
  create_stockreconciliation: "Tạo phiếu kiểm kê",
  update_stockreconciliation: "Sửa phiếu kiểm kê",
  submit_stockreconciliation: "Gửi duyệt kiểm kê",
  return_stockreconciliation_to_draft: "Trả phiếu kiểm kê về nháp",
  approve_stockreconciliation: "Duyệt kiểm kê",
  approve_returntostock: "Duyệt phiếu trả về kho",
  cancel_returntostock: "Huỷ phiếu trả về kho",
  label_voided: "Huỷ tem",
  supplier_create: "Thêm nhà cung cấp",
  supplier_update: "Sửa nhà cung cấp",
  // bán hàng / tiền
  cancel_paid_order: "Huỷ đơn đã thanh toán",
  cancel_unpaid_expired: "Tự huỷ đơn hết giờ giữ chỗ",
  order_auto_cancelled: "Tự huỷ đơn hết giờ giữ chỗ",
  auto_cancel: "Tự huỷ đơn hết giờ giữ chỗ",
  order_auto_cancel_blocked: "Chặn tự huỷ đơn",
  confirm_payment_manual: "Xác nhận thanh toán thủ công",
  confirm_payment: "Xác nhận thanh toán thủ công",
  attach_payment: "Gắn tiền về vào đơn",
  auto_confirm_exact_match: "Tự xác nhận tiền về khớp đơn",
  resolve_payment: "Xử lý tiền về lệch",
  escalate_unmatched_payment: "Chuyển Chủ xử lý tiền lệch",
  split_overpaid_payment: "Tách khoản chuyển thừa",
  create_refund: "Lập phiếu hoàn",
  confirm_refund: "Xác nhận hoàn tiền",
  mark_refund_failed: "Ghi hoàn tiền thất bại",
  retry_refund: "Thử hoàn lại",
  issue_credit_note: "Lập hoá đơn điều chỉnh",
  update_customer: "Sửa thông tin khách",
  recipient_changed: "Đổi thông tin nhận hàng",
  create_itemprice: "Đặt giá bán",
  update_itemprice: "Sửa giá bán",
  close_itemprice: "Đóng giá bán",
  // giao hàng
  assign_deliverynote: "Gán phiếu giao",
  delivery_advance_status: "Chuyển trạng thái giao",
  delivery_call_recorded: "Ghi cuộc gọi xác nhận",
  delivery_confirmed: "Khách xác nhận giao",
  delivery_unconfirmed: "Khách chưa xác nhận giao",
  delivery_confirm_skipped: "Bỏ qua bước gọi xác nhận",
  delivery_escalated: "Chuyển Quản lý xử lý giao",
  delivery_extended: "Gia hạn giao",
  delivery_mark_failed: "Ghi giao thất bại",
  // nội dung
  content_submit: "Gửi duyệt nội dung",
  content_return: "Trả nội dung về nháp",
  content_unpublish: "Gỡ nội dung",
  item_image_remove: "Gỡ ảnh mặt hàng",
  // nhân sự / tài khoản
  staff_create: "Thêm nhân viên",
  staff_update: "Sửa hồ sơ nhân viên",
  staff_groups_change: "Đổi nhóm quyền",
  staff_password_reset: "Đặt lại mật khẩu",
  staff_deactivate: "Cho nghỉ",
  staff_reactivate: "Cho làm lại",
  password_change_self: "Đổi mật khẩu",
  logout: "Đăng xuất",
  demo_remove: "Xoá dữ liệu mẫu",
  // AI
  ai_config_update: "Đổi cài đặt AI",
  ai_config_kill: "Tắt trợ lý AI",
  ai_policy_update: "Đổi chính sách AI",
  execute_command: "AI chạy lệnh",
  propose: "AI đề xuất",
  confirm_proposal: "Duyệt đề xuất AI",
  reject_proposal: "Từ chối đề xuất AI",
  // động từ chung
  create: "Tạo mới",
  update: "Sửa",
  publish: "Mở bán",
};

export const UNKNOWN_ACTION = "Thao tác khác";

/** Nhãn thao tác; mã lạ → "Thao tác khác" (không in mã kỹ thuật). */
export function actionLabel(action: string): string {
  return AUDIT_ACTION_LABELS[action] ?? UNKNOWN_ACTION;
}

/** Các thao tác hay lọc — chọn trong ô "Mọi thao tác" (BE lọc đúng mã `action`). */
export const AUDIT_FILTER_ACTIONS: readonly string[] = [
  "publish_batch",
  "close_batch",
  "create_and_submit_receipt",
  "cancel_paid_order",
  "order_auto_cancelled",
  "confirm_payment_manual",
  "attach_payment",
  "create_refund",
  "confirm_refund",
  "approve_stockreconciliation",
  "update_itemprice",
  "assign_deliverynote",
  "staff_groups_change",
  "staff_password_reset",
  "staff_deactivate",
  "ai_config_update",
  "ai_policy_update",
  "confirm_proposal",
];

/** Thao tác chỉ có nghĩa khi AI bật: ẩn khỏi ô lọc khi cờ AI tắt (SR-HIDE-AI-01). */
export const AI_ONLY_ACTIONS: readonly string[] = ["ai_config_update", "ai_policy_update", "confirm_proposal"];

/** Dòng này do Hệ thống làm? (BE trả actor_kind="system" + "system"). */
export const isSystem = (row: Pick<AuditLogRow, "actor_kind">): boolean => row.actor_kind === "system";

/** Tên người làm để hiện: dòng AI bỏ tiền tố "ai:" (nhãn AI vẽ riêng), dòng Hệ thống → "Hệ thống". */
export function actorName(row: Pick<AuditLogRow, "actor_kind" | "actor_display">): string {
  if (row.actor_kind === "system") return "Hệ thống";
  if (row.actor_kind === "ai") return row.actor_display.replace(/^ai:/, "") || "?";
  return row.actor_display || "?";
}

/** Chữ cái đầu cho ô tròn đại diện (một ký tự, viết hoa). */
export function actorInitial(row: Pick<AuditLogRow, "actor_kind" | "actor_display">): string {
  const name = actorName(row).trim();
  return name ? name.charAt(0).toUpperCase() : "?";
}

const CONFIRM_RE = /^(confirm|approve)_/;

/**
 * Người duyệt: BE chưa có trường riêng (xem 03-dev-notes). Với dòng AI có `proposal_ref`, tìm dòng "duyệt/xác nhận" của một
 * người cùng mã đề xuất trong các dòng đã tải. Không thấy → null (UI in "—").
 */
export function buildApproverMap(rows: readonly AuditLogRow[]): ReadonlyMap<string, string> {
  const map = new Map<string, string>();
  for (const r of rows) {
    if (r.actor_kind === "user" && r.proposal_ref && CONFIRM_RE.test(r.action)) map.set(r.proposal_ref, actorName(r));
  }
  return map;
}

export function approverOf(row: AuditLogRow, approvers: ReadonlyMap<string, string>): string | null {
  if (row.actor_kind !== "ai" || !row.proposal_ref) return null;
  return approvers.get(row.proposal_ref) ?? null;
}

// ---- "Thay đổi": chỉ khoá trong danh sách trắng ----

const STATUS_TABLES: EnumTable[] = [
  ENUMS.salesOrderStatus,
  ENUMS.refundStatus,
  ENUMS.deliveryStatus,
  ENUMS.batchStatus,
  ENUMS.stockReconciliationStatus,
  ENUMS.returnToStockStatus,
];

function statusLabel(value: unknown): string | null {
  if (typeof value !== "string" || !value) return null;
  for (const t of STATUS_TABLES) if (t && t[value]) return t[value].label;
  return null;
}

const GROUP_RE = /^[a-z_]+$/;

function groupsText(value: unknown): string | null {
  if (!Array.isArray(value)) return null;
  const names = value.filter((g): g is string => typeof g === "string" && GROUP_RE.test(g)).map((g) => GROUP_LABEL[g] ?? null);
  if (names.some((n) => n === null)) return null;
  return names.length ? names.join(", ") : "không nhóm nào";
}

const num = (v: unknown): number | null => {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) return Number(v);
  return null;
};

/** `{from,to}` / `[từ, đến]` / `{to}` → cặp (từ?, đến). null nếu không đúng dạng. */
function pair(v: unknown): { from?: unknown; to: unknown } | null {
  if (Array.isArray(v) && v.length === 2) return { from: v[0], to: v[1] };
  if (v && typeof v === "object" && "to" in (v as Record<string, unknown>)) {
    const o = v as { from?: unknown; to: unknown };
    return "from" in o ? { from: o.from, to: o.to } : { to: o.to };
  }
  return null;
}

function arrow(from: string | null, to: string): string {
  return from ? `${from} → ${to}` : `→ ${to}`;
}

/** Danh sách các đoạn chữ ngắn ("Trạng thái: Giữ chỗ → Đã thanh toán"). Rỗng = không có gì được phép hiện. */
export function changeSummary(changes: Record<string, unknown> | null | undefined): string[] {
  if (!changes || typeof changes !== "object" || Array.isArray(changes)) return [];
  const out: string[] = [];
  for (const [key, raw] of Object.entries(changes)) {
    const p = pair(raw);
    if (!p) continue;
    if (key === "status") {
      const to = statusLabel(p.to);
      if (to) out.push(`Trạng thái: ${arrow(statusLabel(p.from), to)}`);
    } else if (key === "quantity") {
      const to = num(p.to);
      if (to !== null) out.push(`Số lượng: ${arrow(num(p.from) !== null ? String(num(p.from)) : null, String(to))}`);
    } else if (key === "amount") {
      const to = num(p.to);
      if (to !== null) out.push(`Số tiền: ${arrow(num(p.from) !== null ? vnd(num(p.from)) : null, vnd(to))}`);
    } else if (key === "price") {
      const to = num(p.to);
      if (to !== null) out.push(`Giá bán: ${arrow(num(p.from) !== null ? vnd(num(p.from)) : null, vnd(to))}`);
    } else if (key === "is_active") {
      if (typeof p.to === "boolean") out.push(`Trạng thái: ${p.to ? "Đang làm" : "Đã nghỉ"}`);
    } else if (key === "groups") {
      const to = groupsText(p.to);
      if (to) out.push(`Nhóm quyền: ${arrow(groupsText(p.from), to)}`);
    }
  }
  return out;
}

// ---- Lọc phía máy (BE chưa có lọc ngày / tìm mã) ----

export type AuditLocalFilter = { query: string; from: string; to: string };

/** Ngày (yyyy-mm-dd, giờ VN) của dòng nằm trong [from, to]; ô trống = không chặn. Tìm mã: chứng từ hoặc mã đề xuất. */
export function matchesLocal(row: AuditLogRow, f: AuditLocalFilter): boolean {
  const q = f.query.trim().toLowerCase();
  if (q) {
    const hay = `${row.object_repr ?? ""} ${row.proposal_ref ?? ""}`.toLowerCase();
    if (!hay.includes(q)) return false;
  }
  if (f.from || f.to) {
    const day = dateKeyInVietnam(row.created_at);
    if (f.from && day < f.from) return false;
    if (f.to && day > f.to) return false;
  }
  return true;
}

export const KIND_OPTIONS: { key: "" | AuditActorKind; label: string }[] = [
  { key: "", label: "Tất cả" },
  { key: "user", label: "Người" },
  { key: "ai", label: "AI" },
  { key: "system", label: "Hệ thống" },
];
