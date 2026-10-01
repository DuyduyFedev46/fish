// Hàm thuần của màn Giao hàng / Việc giao của tôi (không React, để vitest). Không ghi dữ liệu khách ra log, URL hay máy.
import type { PathStep } from "@/shared/ui/detail/StatusPath";
import { ENUMS } from "@/shared/lib/enums";
import type { DeliveryFailureReason, DeliveryNoteItem } from "./types";

export const PATH_STEPS: PathStep[] = [
  { key: "CONFIRMING", label: "Chờ xác nhận" },
  { key: "PREPARING", label: "Soạn hàng" },
  { key: "READY", label: "Chờ lấy hàng" },
  { key: "DELIVERING", label: "Đang giao" },
  { key: "COMPLETED", label: "Hoàn tất" },
];

/** Thanh trạng thái: FAILED hỏng sau bước Đang giao; CANCELLED là kết thúc xấu không có bước đã qua. */
export function pathOf(note: Pick<DeliveryNoteItem, "status">): { current: string; badEnd: { label: string; after?: string } | null } {
  if (note.status === "FAILED") return { current: "DELIVERING", badEnd: { label: "Giao thất bại", after: "DELIVERING" } };
  if (note.status === "CANCELLED") return { current: "CANCELLED", badEnd: { label: "Đã huỷ theo đơn" } };
  return { current: note.status, badEnd: null };
}

/** Việc tiếp theo (câu hoàn chỉnh) cho dải "Tiếp theo" của StatusPath. */
export function nextStepText(note: Pick<DeliveryNoteItem, "status" | "assigned_to" | "failed_attempts">): string | null {
  switch (note.status) {
    case "CONFIRMING":
      return "Gọi xác nhận với khách";
    case "PREPARING":
      return "In tem, đóng gói, rồi bấm Đã đóng gói";
    case "READY":
      return note.assigned_to ? "Người giao nhận hàng đi giao" : "Giao phiếu cho người giao";
    case "DELIVERING":
      return "Giao xong hoặc báo giao thất bại";
    case "FAILED":
      return note.failed_attempts >= 2 ? "Chủ hoặc Quản lý quyết định cách xử lý" : "Giao lại cho khách";
    default:
      return null;
  }
}

const ORDER = ["CONFIRMING", "PREPARING", "READY", "DELIVERING", "COMPLETED"];
const DONE_LABEL: Record<string, string> = {
  CONFIRMING: "Tạo phiếu",
  PREPARING: "Xác nhận với khách",
  READY: "Đóng gói",
  DELIVERING: "Lên xe",
  COMPLETED: "Giao xong",
};

/** Các việc đã làm theo trạng thái hiện tại (nhãn ngắn). */
export function doneSteps(note: Pick<DeliveryNoteItem, "status">): string[] {
  const at = note.status === "FAILED" ? ORDER.indexOf("DELIVERING") + 1 : ORDER.indexOf(note.status);
  if (at < 0) return [];
  return ORDER.slice(0, at + (note.status === "COMPLETED" ? 1 : 0)).map((k) => DONE_LABEL[k]);
}

export function hasAction(note: Pick<DeliveryNoteItem, "available_actions">, action: string): boolean {
  return note.available_actions.includes(action);
}

/** F2o chỉ hiện khi phiếu chưa lên xe VÀ người xem có quyền (BE đưa "assign" vào `available_actions`). */
export function canAssign(note: Pick<DeliveryNoteItem, "status" | "available_actions">): boolean {
  return (note.status === "CONFIRMING" || note.status === "PREPARING" || note.status === "READY") && hasAction(note, "assign");
}

export const FAILURE_REASON_KEYS = Object.keys(ENUMS.deliveryFailureReason) as DeliveryFailureReason[];

/**
 * BE (`has_long_digit_run`): ghi chú không được chứa dãy 9 chữ số trở lên (SĐT, số tài khoản), kể cả khi các chữ số
 * bị ngăn bằng khoảng trắng, dấu chấm, gạch ngang, gạch dưới hay dấu gạch chéo ("0912 345 678", "091.234.5678").
 */
export function hasLongDigitRun(text: string, minLen = 9): boolean {
  if (!text) return false;
  const cleaned = text.replace(/[\s.\-_/]/g, "");
  return new RegExp(`\\d{${minLen},}`).test(cleaned);
}
export const FAILURE_NOTE_MAX = 200;

export const FAILURE_NOTE_MESSAGES = {
  reasonRequired: "Chọn lý do giao thất bại.",
  noteRequired: "Chọn lý do Khác thì phải ghi chú ngắn.",
  notePii: "Ghi chú không được chứa số điện thoại hay dãy số dài. Xoá số đó rồi gửi lại.",
  noteTooLong: `Ghi chú tối đa ${FAILURE_NOTE_MAX} ký tự.`,
};

/** Kiểm tại chỗ trước khi gửi (BE vẫn là lớp chặn thật). Trả lỗi theo ô hoặc null. */
export function validateFailureInput(reason: string, note: string): { field: "reason" | "note"; message: string } | null {
  if (!reason || !FAILURE_REASON_KEYS.includes(reason as DeliveryFailureReason)) return { field: "reason", message: FAILURE_NOTE_MESSAGES.reasonRequired };
  const text = note.trim();
  if (text.length > FAILURE_NOTE_MAX) return { field: "note", message: FAILURE_NOTE_MESSAGES.noteTooLong };
  if (reason === "OTHER" && !text) return { field: "note", message: FAILURE_NOTE_MESSAGES.noteRequired };
  if (text && hasLongDigitRun(text)) return { field: "note", message: FAILURE_NOTE_MESSAGES.notePii };
  return null;
}

/** Mã lỗi 400 của B5 → ô bị lỗi. */
export function failureFieldOfCode(code: string | undefined): "reason" | "note" | null {
  if (code === "DELIVERY_FAILURE_REASON_REQUIRED") return "reason";
  if (code === "DELIVERY_FAILURE_NOTE_REQUIRED" || code === "DELIVERY_FAILURE_NOTE_PII" || code === "DELIVERY_FAILURE_NOTE_INVALID") return "note";
  return null;
}

/** Số để gọi: chỉ giữ chữ số và dấu +; quá ngắn → null (không dựng link tel: sai). */
export function telHref(phone: string | null | undefined): string | null {
  if (!phone) return null;
  const digits = phone.replace(/[^\d+]/g, "");
  return digits.replace(/\D/g, "").length >= 8 ? `tel:${digits}` : null;
}

export type MineGroupKey = "DELIVERING" | "READY" | "FAILED" | "COMPLETED";
export const MINE_GROUPS: Array<{ key: MineGroupKey; title: string }> = [
  { key: "DELIVERING", title: "Đang giao" },
  { key: "READY", title: "Chờ lấy hàng" },
  { key: "FAILED", title: "Giao thất bại" },
  { key: "COMPLETED", title: "Đã xong" },
];

/** Chia phiếu của tôi vào 4 nhóm theo thứ tự việc cần làm; phiếu ở trạng thái khác (vd đã huỷ) bị bỏ. */
export function groupMine<T extends Pick<DeliveryNoteItem, "status">>(rows: T[]): Record<MineGroupKey, T[]> {
  const out: Record<MineGroupKey, T[]> = { DELIVERING: [], READY: [], FAILED: [], COMPLETED: [] };
  for (const r of rows) if (r.status in out) out[r.status as MineGroupKey].push(r);
  return out;
}

/** Đường dẫn trang chi tiết phiếu giao: chỉ mang id số (không mang tên, SĐT, địa chỉ). */
export function detailHref(id: number): string {
  return `/deliveries/detail/?id=${id}`;
}

/** id từ `?id=`: chỉ nhận số nguyên dương. */
export function idFromSearch(value: string | null): number | null {
  if (!value || !/^\d{1,9}$/.test(value)) return null;
  const n = Number(value);
  return n > 0 ? n : null;
}

/**
 * "Hàng" của thẻ/bảng: chỉ tên mặt hàng, mỗi trường một giá trị. BE ghi kèm số kg từng dòng ("Tôm sú 2.000 kg · Mực 1.000 kg"),
 * số kg nằm ở trường "Số kg" nên tách bỏ ở đây (cũng tránh dạng "2.000" bị đọc thành hai nghìn).
 */
export function lineNames(summary: string | null | undefined): string {
  if (!summary) return "";
  return summary
    .split(" · ")
    .map((part) => part.replace(/\s+[\d.,]+\s*kg$/i, "").trim())
    .filter(Boolean)
    .join(" · ");
}

/** Câu báo khi lọc/tìm không ra mà còn trang chưa tải (bộ lọc chỉ chạy trên các phiếu đã tải). */
export function loadedOnlyNote(loaded: number): string {
  return `Chỉ tìm trong ${loaded} phiếu đã tải. Bấm Tải thêm để tìm tiếp.`;
}
