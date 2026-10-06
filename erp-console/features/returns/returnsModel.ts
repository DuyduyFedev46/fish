// Phần thuần (không React) của module Hàng hoàn về kho (ED-26) — để vitest kiểm được. Không ghi dữ liệu ra log, URL hay máy.
import type { PathStep } from "@/shared/ui/detail/StatusPath";
import { ApiError } from "@/shared/lib/http";
import { todayInVietnam } from "@/shared/lib/format";
import { RETURNS_MSG as M } from "./messages";
import type { BatchChoice, QtyExceedsExtras, ReturnItem, ReturnableLine } from "./types";

export const PERM_APPROVE_RETURN = "inventory.approve_returntostock";
export const PERM_ADD_RETURN = "inventory.add_returntostock";
export const PERM_CHANGE_RETURN = "inventory.change_returntostock";

export const NOTE_MAX = 500;
const QTY_DECIMALS = 3;

export const PATH_STEPS: PathStep[] = [
  { key: "DRAFT", label: "Chờ duyệt" },
  { key: "APPROVED", label: "Đã duyệt" },
];

// ---- Đọc id từ URL ----

/** `?id=12` → 12; thiếu hoặc không phải số nguyên dương → null. */
export function parseReturnId(search: string): number | null {
  const raw = new URLSearchParams(search).get("id");
  if (!raw || !/^\d{1,12}$/.test(raw)) return null;
  const n = Number(raw);
  return n > 0 ? n : null;
}

// ---- Hiển thị ----

/** Số phút ở ngoài kho lạnh → "55 phút", "1 giờ 10 phút", "2 giờ". Thiếu mốc → "—". */
export function outsideText(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined || !Number.isFinite(minutes) || minutes < 0) return "—";
  const total = Math.round(minutes);
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (h === 0) return `${m} phút`;
  return m === 0 ? `${h} giờ` : `${h} giờ ${m} phút`;
}

/** Quá 2 giờ ngoài kho lạnh thì tô màu cảnh báo (UI-RULES: "Ngoài kho lạnh" > 2 giờ dùng token warn, board W5f). Đúng 2 giờ chưa tô. */
export const OUTSIDE_WARN_MINUTES = 120;
export function isOutsideLong(minutes: number | null | undefined): boolean {
  return minutes !== null && minutes !== undefined && Number.isFinite(minutes) && minutes > OUTSIDE_WARN_MINUTES;
}

/** 12 tháng gần nhất (mới → cũ) cho ô chọn tháng. */
export function recentMonths(now = new Date(), count = 12): { value: string; label: string }[] {
  const [y, m] = todayInVietnam(now).slice(0, 7).split("-").map(Number);
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(Date.UTC(y, m - 1 - i, 1));
    const yy = d.getUTCFullYear();
    const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
    return { value: `${yy}-${mm}`, label: `Tháng ${mm}/${yy}` };
  });
}

/** Tháng hiện tại YYYY-MM theo giờ Việt Nam. */
export function currentMonth(now = new Date()): string {
  return todayInVietnam(now).slice(0, 7);
}

/** Lọc phía máy theo ô tìm: mã phiếu, phiếu giao, lô, mặt hàng (bỏ hoa thường). Từ khoá không đi đâu khác. */
export function matchesQuery(r: Pick<ReturnItem, "code" | "delivery_note_code" | "batch_code" | "item_name">, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [r.code, r.delivery_note_code ?? "", r.batch_code, r.item_name].some((v) => v.toLowerCase().includes(q));
}

export function pendingCount(rows: readonly Pick<ReturnItem, "status">[]): number {
  return rows.filter((r) => r.status === "DRAFT").length;
}

// ---- Thanh trạng thái ----

export function nextStepText(r: Pick<ReturnItem, "status" | "outside_minutes" | "batch_code">): string | null {
  if (r.status !== "DRAFT") return null;
  const outside = r.outside_minutes === null ? "" : `Hàng ở ngoài kho lạnh ${outsideText(r.outside_minutes)}. `;
  return `${outside}Chọn tái nhập vào lô ${r.batch_code} hoặc huỷ bỏ, ghi lỗ.`;
}

export function doneSteps(r: Pick<ReturnItem, "status" | "decision">): string[] {
  const out = ["Ghi số kg", "Ghi giờ về kho"];
  if (r.status === "CANCELLED") out.push("Huỷ phiếu");
  if (r.status === "APPROVED") out.push(r.decision === "WRITE_OFF" ? "Huỷ bỏ, ghi lỗ" : "Tái nhập vào lô");
  return out;
}

/** Nút Duyệt chỉ cho người có quyền duyệt và phiếu còn Chờ duyệt. */
export function canApprove(permissions: readonly string[] | undefined, r: Pick<ReturnItem, "status">): boolean {
  return !!permissions?.includes(PERM_APPROVE_RETURN) && r.status === "DRAFT";
}

/**
 * "Huỷ phiếu hoàn": phiếu còn Chờ duyệt, người xem qua được cổng chung của BE (`add_returntostock`, TLA-FE-L4) rồi có quyền duyệt
 * hoặc sửa phiếu, hoặc là người tạo phiếu. Cổng chung quan trọng từ Lô 14: Chủ có thể tắt "Ghi hàng hoàn về kho" của một nhóm
 * còn quyền duyệt, khi đó BE trả 403 nên FE phải ẩn mục.
 * Đây là luật BE (#8); FE chỉ ẩn mục để khỏi bấm vô ích, BE vẫn là lớp chặn thật (403).
 */
export function canCancel(me: { id: number; permissions: readonly string[] } | null | undefined, r: Pick<ReturnItem, "status" | "created_by">): boolean {
  if (!me || r.status !== "DRAFT") return false;
  const perms = me.permissions;
  if (!perms.includes(PERM_ADD_RETURN)) return false;
  if (perms.includes(PERM_APPROVE_RETURN) || perms.includes(PERM_CHANGE_RETURN)) return true;
  return r.created_by !== null && r.created_by === me.id;
}

/** Nút "Xoá phiếu hoàn": chỉ khi BE báo `delete` trong `available_actions` (BE quyết theo Chủ + trạng thái, FE không tự đoán). */
export function canDelete(r: Pick<ReturnItem, "available_actions">): boolean {
  return !!r.available_actions?.includes("delete");
}

export function canCreate(permissions: readonly string[] | undefined): boolean {
  return !!permissions?.includes(PERM_ADD_RETURN);
}

// ---- Số kg ----

/** "1,5" hoặc "1.5" → "1.5". Trả null nếu không phải số dương, có quá 3 chữ số thập phân hoặc có ký tự lạ. */
export function normalizeQty(input: string): string | null {
  const t = input.trim().replace(/\s/g, "").replace(",", ".");
  if (!/^\d{1,9}(\.\d{1,3})?$/.test(t)) return null;
  const n = Number(t);
  if (!Number.isFinite(n) || n <= 0) return null;
  return t;
}

/** Hiển thị số kg chuỗi thập phân → số, làm tròn 3 chữ số để phép trừ không dính sai số nhị phân. */
export function round3(n: number): number {
  return Math.round(n * 10 ** QTY_DECIMALS) / 10 ** QTY_DECIMALS;
}

export function remainingQty(delivered: number, alreadyReturned: number): number {
  return Math.max(0, round3(delivered - alreadyReturned));
}

// ---- Ghi chú: không số điện thoại (bất biến 9) ----

/** Dãy 9 chữ số trở lên (kể cả khi ngăn bằng khoảng trắng, chấm, gạch) coi là số điện thoại / số tài khoản. */
export function hasLongDigitRun(text: string, minLen = 9): boolean {
  if (!text) return false;
  return new RegExp(`\\d{${minLen},}`).test(text.replace(/[\s.\-_/]/g, ""));
}

export function validateNote(text: string): string | null {
  if (text.length > NOTE_MAX) return M.errNoteTooLong;
  if (hasLongDigitRun(text)) return M.errNotePii;
  return null;
}

// ---- Lỗi BE ----

/** Bỏ phần "(BR-HV-01)" khỏi câu BE: màn không hiện mã quy tắc. */
export function stripRuleCode(message: string): string {
  return message.replace(/\s*\(\s*BR-[A-Z]+-\d+\s*\)/g, "").replace(/\s*BR-[A-Z]+-\d+:?\s*/g, " ").replace(/\s+/g, " ").trim();
}

export type CreateField = "deliveryNote" | "batch" | "qty" | "note";

/** Số liệu kèm RETURN_QTY_EXCEEDS, đã ép sang số; không có/hỏng → null. */
export function qtyExceedsOf(err: unknown): { delivered: number; already: number } | null {
  if (!(err instanceof ApiError) || err.code !== "RETURN_QTY_EXCEEDS") return null;
  const d = (err.details && typeof err.details === "object" ? err.details : {}) as Partial<QtyExceedsExtras>;
  const delivered = Number(d.delivered_qty);
  const already = Number(d.already_returned_qty);
  if (!Number.isFinite(delivered) || !Number.isFinite(already)) return null;
  return { delivered, already };
}

/** Câu lỗi dưới ô số kg khi vượt số đã giao: "Đã giao 2 kg, đã hoàn 1,5 kg, chỉ còn hoàn được 0,5 kg." */
export function exceedsMessage(delivered: number, already: number, fmt: (n: number) => string): string {
  const left = remainingQty(delivered, already);
  return `Số kg hoàn vượt số đã giao của lô. Đã giao ${fmt(delivered)}, đã hoàn ${fmt(already)}, chỉ còn hoàn được ${fmt(left)}.`;
}

/** Lỗi 400 theo ô của DRF là mảng câu (hoặc một câu): lấy câu đầu, bỏ mã quy tắc; không có câu chữ thì null. */
function firstFieldMessage(value: unknown): string | null {
  const first = Array.isArray(value) ? value[0] : value;
  if (typeof first !== "string") return null;
  return stripRuleCode(first) || null;
}

/** Lỗi tạo phiếu → ô cần hiện lỗi + câu tiếng Việt. Mã lạ: hiện câu BE đã bỏ mã quy tắc, không gắn ô nào. */
export function createErrorOf(err: unknown, fmt: (n: number) => string): { field: CreateField | null; message: string } {
  if (err instanceof ApiError) {
    const ex = qtyExceedsOf(err);
    if (ex) return { field: "qty", message: exceedsMessage(ex.delivered, ex.already, fmt) };
    if (err.code === "RETURN_BATCH_NOT_IN_NOTE") return { field: "batch", message: "Lô này không nằm trong phiếu giao. Hàng hoàn phải về đúng lô gốc." };
    if (err.code === "RETURN_BATCH_CLOSED") return { field: "batch", message: "Lô này đã chốt, không nhập thêm hàng hoàn vào lô." };
    if (err.code === "RETURN_NOTE_STATUS") return { field: "deliveryNote", message: "Chỉ nhập hàng hoàn khi phiếu giao đang giao hoặc giao thất bại." };
    if (err.status === 404) return { field: "deliveryNote", message: "Không tìm thấy phiếu giao. Tải lại danh sách rồi chọn lại." };
    if (err.status === 400 && err.details && typeof err.details === "object") {
      const d = err.details as Record<string, unknown>;
      if (d.qty) return { field: "qty", message: M.errQtyInvalid };
      if (d.note) return { field: "note", message: firstFieldMessage(d.note) ?? M.errNotePii };
    }
    return { field: null, message: stripRuleCode(err.message) || "Chưa gửi được. Kiểm tra mạng rồi bấm Thử lại." };
  }
  return { field: null, message: err instanceof Error && err.message ? stripRuleCode(err.message) : "Chưa gửi được. Kiểm tra mạng rồi bấm Thử lại." };
}

/** Lỗi duyệt (không phải xung đột) → câu hiển thị ở đầu hộp. */
export function approveErrorText(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "RETURN_DECISION_REQUIRED") return M.approveDecisionRequired;
    if (err.status === 403) return "Bạn không có quyền duyệt phiếu hàng hoàn.";
    if (err.status === 404) return "Không tìm thấy phiếu hàng hoàn.";
    return stripRuleCode(err.message) || "Chưa duyệt được. Bấm Thử lại.";
  }
  return err instanceof Error && err.message ? stripRuleCode(err.message) : "Chưa duyệt được. Bấm Thử lại.";
}

// ---- Lô trên phiếu giao (F2m) ----

/** `returned_qty` chuỗi thập phân → số; thiếu hoặc hỏng → null (chưa biết). */
export function returnedOf(line: Pick<ReturnableLine, "returned_qty">): number | null {
  if (line.returned_qty === undefined || line.returned_qty === null || line.returned_qty === "") return null;
  const n = Number(line.returned_qty);
  return Number.isFinite(n) && n >= 0 ? round3(n) : null;
}

/**
 * Gộp các dòng cùng mã lô của phiếu giao thành một lựa chọn; số kg đã giao của lô = tổng các dòng.
 * `returned_qty` của BE đã là tổng cả lô và mọi dòng cùng lô mang cùng số, nên lấy một lần, không cộng dồn.
 */
export function batchChoices(lines: readonly ReturnableLine[]): BatchChoice[] {
  const map = new Map<string, BatchChoice>();
  for (const line of lines) {
    const prev = map.get(line.batch_id);
    const qty = Number(line.qty_kg) || 0;
    if (prev) {
      prev.delivered = round3(prev.delivered + qty);
      if (prev.returned === null) prev.returned = returnedOf(line);
    } else {
      map.set(line.batch_id, { key: line.batch_id, label: `${line.item_name} · ${line.batch_id}`, delivered: round3(qty), returned: returnedOf(line), line });
    }
  }
  return [...map.values()];
}

/** Dòng số liệu dưới ô Lô: "Đã giao 2 kg, đã hoàn 1,5 kg, còn hoàn được 0,5 kg." Chưa biết số đã hoàn thì chỉ có "Đã giao". */
export function qtyFactsText(delivered: number, returned: number | null, fmt: (n: number) => string): string {
  if (returned === null) return M.deliveredQty(fmt(delivered));
  return `${M.deliveredQty(fmt(delivered))}, ${M.returnedQty(fmt(returned))}, ${M.remainingQty(fmt(remainingQty(delivered, returned)))}`;
}

/**
 * Chặn tại chỗ khi số nhập vượt số còn hoàn được (BE vẫn là lớp chặn thật). Trả câu lỗi dưới ô số kg, hoặc null nếu hợp lệ.
 * `returned` chưa biết (null) thì coi là 0: chỉ chặn khi vượt số đã giao.
 */
export function qtyOverRemaining(qty: string, delivered: number, returned: number | null, fmt: (n: number) => string): string | null {
  const n = Number(qty);
  if (!Number.isFinite(n)) return null;
  const done = returned ?? 0;
  return round3(n) > remainingQty(delivered, done) ? exceedsMessage(delivered, done, fmt) : null;
}

/**
 * Alert đầu hộp chỉ dành cho lỗi lần gửi KHÔNG gắn được vào ô nào. Lỗi đã gắn vào ô thì dù người dùng sửa ô (xoá lỗi dưới ô)
 * cũng không được nhảy lên đầu hộp (TL9-M2).
 */
export function showSubmitAlert(submitError: string | null, attachedToField: boolean): boolean {
  return Boolean(submitError) && !attachedToField;
}
