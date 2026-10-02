// Phần LOGIC thuần của khối Trợ lý AI trên trang chứng từ (tách ra để vitest, không import React / runtime AI).
import { groupLabel } from "@/shared/lib/groups";
import { kg, vnd } from "@/shared/lib/format";
import type { AiChange, AiProposalView } from "@/shared/ui/detail/AiBlockFrame";
import type { AiActionDetail, AiActionRow } from "../types";

/** Câu hỏi nhanh hiện sẵn trên khối AI của chứng từ (không chứa dữ liệu cá nhân). */
export const DOC_CHAT_CHIPS = ["Tóm tắt lịch sử chứng từ này", "Chứng từ này còn thiếu gì?"];

/** Số giây phải xem đề xuất trước khi được Đồng ý (BR-AI-14). */
export const CONFIRM_WAIT_SECONDS = 3;

type ArgFormat = "text" | "kg" | "vnd";

/**
 * DANH SÁCH CHO PHÉP các khoá `args_preview` được hiện, kèm nhãn và cách định dạng. Khoá không có trong bảng thì KHÔNG hiện:
 * khoá kỹ thuật, giá vốn, và mọi trường chữ TỰ DO (`note`, `reason`, `description`…) vì người dùng/AI có thể ghi tên, SĐT, địa chỉ
 * khách vào đó (bất biến 9; BE cũng xếp `note` vào SCRUB_FREE_TEXT_KEYS nhưng đường xem đề xuất không lọc nên FE không được hiện).
 * Thêm khoá mới phải là khoá CÓ CẤU TRÚC (mã, số lượng, tiền không phải giá vốn), không bao giờ là chữ tự do.
 */
const ARG_FIELDS: Record<string, { label: string; format: ArgFormat }> = {
  item_code: { label: "Mã hàng", format: "text" },
  qty: { label: "Số lượng", format: "kg" },
  quantity: { label: "Số lượng", format: "kg" },
  batch_id: { label: "Lô", format: "text" },
  supplier: { label: "Nhà cung cấp", format: "text" },
  warehouse: { label: "Kho", format: "text" },
  refund_amount: { label: "Số tiền hoàn", format: "vnd" },
};

/** Số lượng có đơn vị ("10 kg"), tiền có "đ"; chuỗi không phải số thì bỏ (không hiện chuỗi thô dễ đọc nhầm). */
function formatValue(v: unknown, format: ArgFormat): string | null {
  if (format === "text") {
    if (typeof v === "string") return v.trim() === "" ? null : v;
    if (typeof v === "number" && Number.isFinite(v)) return String(v);
    return null;
  }
  if (typeof v !== "string" && typeof v !== "number") return null;
  const out = format === "kg" ? kg(v) : vnd(v);
  return out === "—" ? null : out;
}

/** `args_preview` → các dòng "nhãn: giá trị" cho khung AI. Chỉ lấy khoá trong danh sách cho phép, giá trị định dạng theo loại. */
export function changesOf(args: Record<string, unknown> | null | undefined): AiChange[] {
  if (!args) return [];
  const out: AiChange[] = [];
  const seen = new Set<string>();
  for (const [key, field] of Object.entries(ARG_FIELDS)) {
    if (seen.has(field.label)) continue; // qty và quantity cùng nhãn: lấy khoá đầu có giá trị
    const text = formatValue(args[key], field.format);
    if (text !== null) {
      out.push({ label: field.label, after: text });
      seen.add(field.label);
    }
  }
  return out;
}

/** Giây còn phải chờ trước khi được Đồng ý; 0 = được. `readyAt` (ms) lấy từ `viewable_from` của BE, không có thì lúc xem + 3 giây. */
export function waitLeft(readyAtMs: number | undefined, nowMs: number): number {
  if (readyAtMs === undefined) return CONFIRM_WAIT_SECONDS;
  return Math.max(0, Math.ceil((readyAtMs - nowMs) / 1000));
}

/** Thời điểm (ms) được phép Đồng ý, tính từ chi tiết đề xuất BE trả (đã ghi `viewed_at`). */
export function readyAtOf(detail: AiActionDetail, fetchedAtMs: number): number {
  const vf = detail.viewable_from ? Date.parse(detail.viewable_from) : NaN;
  return Number.isFinite(vf) ? vf : fetchedAtMs + CONFIRM_WAIT_SECONDS * 1000;
}

/** Hàng đề xuất BE → dữ liệu vẽ của khung. Chỉ PENDING / ESCALATED mới vào đây (các trạng thái khác bị lọc ở API). */
export function toProposalView(row: AiActionRow, waitSeconds: number): AiProposalView | null {
  if (row.status !== "PENDING" && row.status !== "ESCALATED") return null;
  return {
    id: row.id,
    proposedBy: row.owner_display,
    proposedAt: row.created_at,
    title: row.title,
    changes: changesOf(row.args_preview),
    state: row.status,
    assigneeGroup: row.status === "ESCALATED" && row.assignee_group ? groupLabel(row.assignee_group) : null,
    waitSeconds: row.status === "PENDING" ? waitSeconds : 0,
  };
}

/** Tên loại chứng từ cho câu hỏi AI (L8). Loại lạ → "chứng từ". */
const DOC_KIND_LABEL: Record<string, string> = {
  "sales.salesorder": "đơn hàng",
  "sales.refund": "phiếu hoàn",
  "sales.paymenttransaction": "khoản tiền",
  "purchasing.purchasereceipt": "phiếu nhập hàng",
  "inventory.batch": "lô hàng",
};

/**
 * Gắn loại + mã chứng từ vào câu hỏi: "Về đơn hàng SO261002-4B7E20: Tóm tắt lịch sử chứng từ này".
 * Chỉ dùng mã chứng từ (không có tên, SĐT, địa chỉ khách). `targetId` có thể là "SO…,123" (mã và pk): lấy mã đầu tiên.
 * Khi mã không rõ ràng (chỉ là số) vẫn ghi số đó, vì vẫn là mã chứng từ.
 */
export function askWithDocContext(question: string, targetModel: string, targetId: string | number): string {
  const kind = DOC_KIND_LABEL[targetModel] ?? "chứng từ";
  const code = String(targetId).split(",")[0].trim();
  return code ? `Về ${kind} ${code}: ${question}` : question;
}
