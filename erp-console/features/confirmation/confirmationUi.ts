// Hàm thuần của màn Gọi xác nhận (không React, để vitest). Không ghi tên, số điện thoại, địa chỉ ra log, URL hay máy.
// Số điện thoại hiện đúng chuỗi BE trả (đủ số khi trong phạm vi, `phone_masked` khi ngoài phạm vi): FE không tự cắt hay ghép số.
import type { PathStep } from "@/shared/ui/detail/StatusPath";
import { dateTime, vnd } from "@/shared/lib/format";
import type { CallResult, ConfirmationQueueDetail, ConfirmationQueueItem } from "./types";
import { CALL_RESULT_OPTIONS } from "./types";

/** Đường dẫn trang chi tiết: chỉ mang id số (không mang tên, SĐT, địa chỉ). */
export function detailHref(noteId: number): string {
  return `/confirmation/detail/?id=${noteId}`;
}

/** id từ `?id=`: chỉ nhận số nguyên dương. */
export function idFromSearch(value: string | null): number | null {
  if (!value || !/^\d{1,9}$/.test(value)) return null;
  const n = Number(value);
  return n > 0 ? n : null;
}

/** Số để gọi: chỉ giữ chữ số và dấu +; quá ngắn → null (không dựng link tel: sai). */
export function telHref(phone: string | null | undefined): string | null {
  if (!phone) return null;
  const digits = phone.replace(/[^\d+]/g, "");
  return digits.replace(/\D/g, "").length >= 8 ? `tel:${digits}` : null;
}

export function hasAction(item: { available_actions: string[] }, action: string): boolean {
  return item.available_actions.includes(action);
}

/** Các kết quả cuộc gọi người xem được ghi, theo đúng thứ tự của AC2 (lấy từ `available_actions` dạng `call:<KẾT QUẢ>`). */
export function callResultsOf(actions: string[]): CallResult[] {
  const allowed = new Set(actions.filter((a) => a.startsWith("call:")).map((a) => a.slice(5)));
  return CALL_RESULT_OPTIONS.filter((o) => allowed.has(o.value)).map((o) => o.value);
}

/** Các quyết định Quản lý được đưa ra (từ `available_actions` dạng `decide:<QUYẾT ĐỊNH>`). */
export function decisionsOf(actions: string[]): Array<"DELIVER_WITHOUT_CONFIRM" | "EXTEND" | "CANCEL"> {
  const order = ["DELIVER_WITHOUT_CONFIRM", "EXTEND", "CANCEL"] as const;
  return order.filter((d) => actions.includes(`decide:${d}`));
}

/**
 * BE (`has_long_digit_run`): ghi chú không được chứa dãy 9 chữ số trở lên (SĐT, số tài khoản), kể cả khi các chữ số
 * bị ngăn bằng khoảng trắng, dấu chấm, gạch ngang, gạch dưới hay dấu gạch chéo ("0912 345 678", "091.234.5678").
 */
export function hasLongDigitRun(text: string, minLen = 9): boolean {
  if (!text) return false;
  const cleaned = text.replace(/[\s.\-_/]/g, "");
  return new RegExp(`\\d{${minLen},}`).test(cleaned);
}

export const CALL_NOTE_MAX = 200;
export const NOTE_PII_MESSAGE = "Ghi chú không được chứa số điện thoại hay số tài khoản. Xoá số đó rồi gửi lại.";

/** Lỗi của ghi chú tự do (cuộc gọi, lý do): quá dài hoặc chứa dãy số dài. null = hợp lệ. */
export function noteError(text: string, max = CALL_NOTE_MAX): string | null {
  const t = text.trim();
  if (t.length > max) return `Ghi chú tối đa ${max} ký tự.`;
  if (t && hasLongDigitRun(t)) return NOTE_PII_MESSAGE;
  return null;
}

/** AC3: giờ hẹn phải ở tương lai; câu lỗi nêu mốc tối thiểu theo giờ Việt Nam. `iso` = giờ đã đổi sang ISO (rỗng = chưa chọn). */
export function callbackError(iso: string, now: Date = new Date()): string | null {
  if (!iso) return `Chọn thời điểm sau ${dateTime(now)}.`;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t) || t <= now.getTime()) return `Chọn thời điểm sau ${dateTime(now)}.`;
  return null;
}

/** Giờ gia hạn: ở tương lai và tối đa 24 giờ kể từ bây giờ (quy tắc mặc định của BE; BE vẫn là lớp chặn thật). */
export const EXTEND_MAX_HOURS = 24;
export function extendError(iso: string, now: Date = new Date()): string | null {
  const base = callbackError(iso, now);
  if (base) return base;
  const limit = now.getTime() + EXTEND_MAX_HOURS * 3600_000;
  if (new Date(iso).getTime() > limit) return `Chỉ gia hạn tối đa ${EXTEND_MAX_HOURS} giờ, chọn thời điểm trước ${dateTime(new Date(limit))}.`;
  return null;
}

// ---- Thanh trạng thái (board W1c2): Chờ gọi > Cần quyết định > Hoàn tất, khớp với chip của việc gọi ----
export const PATH_STEPS: PathStep[] = [
  { key: "WAITING", label: "Chờ gọi" },
  { key: "DECIDE", label: "Cần quyết định" },
  { key: "DONE", label: "Hoàn tất" },
];

type PathItem = Pick<ConfirmationQueueItem, "note_status" | "confirm_state">;

/**
 * PENDING và CALLBACK (chip "Chờ gọi", "Hẹn gọi lại") ở bước Chờ gọi; ESCALATED ở bước Cần quyết định;
 * REFUND_CALL (đơn đã huỷ, gọi báo hoàn tiền) là kết thúc xấu sau bước Cần quyết định; hết việc gọi (không còn trạng thái) là Hoàn tất.
 */
export function pathOf(item: PathItem): { current: string; badEnd: { label: string; after?: string } | null } {
  switch (item.confirm_state) {
    case "PENDING":
    case "CALLBACK":
      return { current: "WAITING", badEnd: null };
    case "ESCALATED":
      return { current: "DECIDE", badEnd: null };
    case "REFUND_CALL":
      return { current: "DECIDE", badEnd: { label: "Gọi báo hoàn tiền", after: "DECIDE" } };
    default:
      break;
  }
  if (item.note_status === "CANCELLED") return { current: "WAITING", badEnd: { label: "Đã huỷ theo đơn", after: "WAITING" } };
  if (item.note_status === "CONFIRMING") return { current: "WAITING", badEnd: null };
  return { current: "DONE", badEnd: null };
}

/** Việc tiếp theo (câu hoàn chỉnh). `canDecide` = người xem có quyền quyết định (CSKH thì không). */
export function nextStepText(item: PathItem & Partial<Pick<ConfirmationQueueItem, "decide_deadline">>, canDecide = true): string | null {
  switch (item.confirm_state) {
    case "PENDING":
      return "Gọi khách xác nhận đơn";
    case "CALLBACK":
      return "Gọi lại khách đúng giờ đã hẹn";
    case "ESCALATED": {
      if (!canDecide) return "Chủ hoặc Quản lý quyết định cách xử lý";
      const by = item.decide_deadline ? ` trước ${dateTime(item.decide_deadline)}` : "";
      return `Chọn giao không xác nhận, gia hạn gọi thêm hoặc huỷ đơn${by}`;
    }
    case "REFUND_CALL":
      return "Gọi báo khách đơn đã huỷ và sẽ được hoàn tiền";
    default:
      break;
  }
  if (item.note_status === "CONFIRMING") return "Gọi khách xác nhận đơn";
  if (item.note_status === "PREPARING") return "Kho soạn hàng";
  return null;
}

export function doneSteps(item: Pick<ConfirmationQueueItem, "attempts" | "paid_at">): string[] {
  const out: string[] = [];
  if (item.paid_at) out.push("Khách trả tiền");
  if (item.attempts > 0) out.push(`Gọi ${item.attempts} lần`);
  return out;
}

/** Cột "Lý do" của hàng chờ: lý do chuyển quyết định (BE trả sẵn nhãn); dòng gọi báo hoàn tiền ghi "Hoàn <số tiền>" như board W1c. */
export function reasonText(item: Pick<ConfirmationQueueItem, "confirm_state" | "escalation_label" | "total_amount" | "refund">): string {
  if (item.confirm_state === "REFUND_CALL") return `Hoàn ${vnd(item.refund?.amount ?? item.total_amount)}`;
  return item.escalation_label || "—";
}

/** Người gọi gần nhất của phiếu (theo giờ ghi cuộc gọi); null khi chưa có cuộc gọi hoặc người ghi đã nghỉ việc. */
export function lastCallerName(calls: ConfirmationQueueDetail["calls"]): string | null {
  if (calls.length === 0) return null;
  const latest = calls.reduce((a, b) => (new Date(b.at).getTime() >= new Date(a.at).getTime() ? b : a));
  return latest.by?.display_name || null;
}

/** Mốc "Hạn gọi" của dòng theo trạng thái: hẹn gọi lại → giờ hẹn; chờ quyết định → hạn quyết định; chờ gọi → hết cửa sổ gọi. */
export function dueAt(item: Pick<ConfirmationQueueItem, "confirm_state" | "callback_at" | "decide_deadline" | "window_ends_at" | "next_call_after">): string | null {
  switch (item.confirm_state) {
    case "CALLBACK":
      return item.callback_at;
    case "ESCALATED":
      return item.decide_deadline;
    case "PENDING":
      return item.next_call_after ?? item.window_ends_at;
    default:
      return null;
  }
}

/** Phiếu đang có người giữ (mềm) tại thời điểm `now`? */
export function claimActive(item: Pick<ConfirmationQueueItem, "claimed_by" | "claimed_until">, now: number = Date.now()): boolean {
  return Boolean(item.claimed_by && item.claimed_until && new Date(item.claimed_until).getTime() > now);
}

/** Phiếu đang bị người khác giữ (mềm) tại thời điểm `now`? `meId` = id người xem. */
export function claimedByOther(item: Pick<ConfirmationQueueItem, "claimed_by" | "claimed_until">, meId: number | null | undefined, now: number = Date.now()): boolean {
  if (!item.claimed_by || !item.claimed_until) return false;
  if (new Date(item.claimed_until).getTime() <= now) return false;
  return item.claimed_by.id !== meId;
}

/** Tìm trên các dòng đã tải: mã đơn, tên khách, hàng. Số điện thoại chỉ so khi dòng thuộc phạm vi (BE mới trả số thật). */
export function matches(row: Pick<ConfirmationQueueItem, "order_code" | "customer_name" | "lines_summary" | "phone" | "recipient_name">, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  const hay = [row.order_code, row.customer_name, row.recipient_name, row.lines_summary, row.phone].filter(Boolean).join(" ").toLowerCase();
  if (hay.includes(needle)) return true;
  const digits = needle.replace(/\D/g, "");
  return digits.length >= 4 && (row.phone ?? "").replace(/\D/g, "").includes(digits);
}

/** "Hàng" của bảng: chỉ tên mặt hàng ("Tôm sú 2 kg · Mực 1 kg" → "Tôm sú · Mực"). */
export function lineNames(summary: string | null | undefined): string {
  if (!summary) return "";
  return summary
    .split(" · ")
    .map((part) => part.replace(/\s+[\d.,]+\s*kg$/i, "").trim())
    .filter(Boolean)
    .join(" · ");
}

export function loadedOnlyNote(loaded: number): string {
  return `Chỉ tìm trong ${loaded} đơn đã tải. Bấm Tải thêm để tìm tiếp.`;
}

/** Câu toast sau khi ghi một cuộc gọi, theo kết quả BE trả. */
export function callToast(result: CallResult, res: { confirm_state: string | null; attempts: number; duplicate: boolean }, maxAttempts: number, callbackAt?: string | null): string {
  if (res.duplicate) return "Cuộc gọi này đã được ghi trước đó.";
  if (result === "CONFIRMED") return "Đã xác nhận. Đơn chuyển sang Soạn hàng.";
  if (result === "NOTIFIED") return "Đã ghi báo hoàn tiền cho khách.";
  if (result === "CALLBACK") return callbackAt ? `Đã hẹn gọi lại lúc ${dateTime(callbackAt)}.` : "Đã hẹn gọi lại.";
  if (res.confirm_state === "ESCALATED") return "Đã ghi cuộc gọi. Đơn chuyển cho Chủ hoặc Quản lý quyết định.";
  if (result === "UNREACHABLE") return `Đã ghi không nghe máy (lần ${res.attempts}/${maxAttempts}).`;
  return "Đã ghi kết quả cuộc gọi.";
}

// ---- F2j: đổi người nhận / địa chỉ ----
export const RECIPIENT_NAME_MAX = 100;
export const ADDRESS_MAX = 255;

export type RecipientDraft = { name: string; phone: string; address: string };
export type RecipientErrors = Partial<Record<keyof RecipientDraft, string>>;

/** Số điện thoại Việt Nam: 10 chữ số bắt đầu bằng 0 (cho phép dấu cách, chấm, gạch; hoặc +84). BE vẫn là lớp chặn thật. */
export function isPhoneValid(phone: string): boolean {
  const d = phone.replace(/[\s.\-]/g, "").replace(/^\+84/, "0");
  return /^0\d{9}$/.test(d);
}

export function validateRecipient(draft: RecipientDraft): RecipientErrors {
  const e: RecipientErrors = {};
  if (!draft.name.trim()) e.name = "Nhập tên người nhận.";
  else if (draft.name.trim().length > RECIPIENT_NAME_MAX) e.name = `Tên tối đa ${RECIPIENT_NAME_MAX} ký tự.`;
  if (!draft.phone.trim()) e.phone = "Nhập số điện thoại người nhận.";
  else if (!isPhoneValid(draft.phone)) e.phone = "Số điện thoại chưa đúng. Nhập 10 chữ số, bắt đầu bằng 0.";
  if (!draft.address.trim()) e.address = "Nhập địa chỉ giao hàng.";
  else if (draft.address.trim().length > ADDRESS_MAX) e.address = `Địa chỉ tối đa ${ADDRESS_MAX} ký tự.`;
  return e;
}

/** Chỉ gửi trường đã đổi (so với lúc mở hộp). Trống = không đổi gì. */
export function recipientChanges(before: RecipientDraft, after: RecipientDraft): { recipient_name?: string; recipient_phone?: string; delivery_address?: string } {
  const out: { recipient_name?: string; recipient_phone?: string; delivery_address?: string } = {};
  if (after.name.trim() !== before.name.trim()) out.recipient_name = after.name.trim();
  if (after.phone.trim() !== before.phone.trim()) out.recipient_phone = after.phone.trim();
  if (after.address.trim() !== before.address.trim()) out.delivery_address = after.address.trim();
  return out;
}

/** Tên trường lỗi của BE (DRF) → ô của hộp. */
export const RECIPIENT_FIELD_OF: Record<string, keyof RecipientDraft> = { recipient_name: "name", recipient_phone: "phone", delivery_address: "address" };

// ---- F2k: quyết định đơn chưa xác nhận ----
export const DECIDE_REASON_MAX = 200;
export const CANCEL_REASON_CODES: Array<{ value: "UNREACHABLE" | "CUSTOMER_CHANGED_MIND" | "OTHER"; label: string }> = [
  { value: "UNREACHABLE", label: "Không liên lạc được khách" },
  { value: "CUSTOMER_CHANGED_MIND", label: "Khách đổi ý" },
  { value: "OTHER", label: "Lý do khác" },
];
