// Hàm thuần của màn Mã giảm giá (SHOP-3b-02, 02b §3.9, BR-DM-22): kiểm form, nháp ↔ thân gửi, khoá trường khi mã đã chạy,
// đọc lỗi theo trường của BE. Không gọi mạng, không đụng DOM nên chạy được dưới vitest.
// Giờ nhập là GIỜ VIỆT NAM (ô `datetime-local`) và đổi sang ISO bằng `vnInputToIso` (shared/lib/format.ts); giờ hiển thị từ ISO cũng qua format.ts.

import { ApiError } from "@/shared/lib/http";
import { dateKeyInVietnam, dateTime, timeHM, vnd, vnInputToIso } from "@/shared/lib/format";
import { formatMoneyInput } from "@/shared/lib/moneyInput";
import { moneyDigits, parseAmount, parseDecimal } from "./catalogModel";
import { VOUCHER_MSG as M } from "./messages";
import type { Voucher, VoucherInput, VoucherKind, VoucherPatch } from "./types";

// ---------------------------------------------------------------- hiển thị

/** "10" | "10.00" → "10"; số thập phân thật ("7.5") giữ nguyên. */
export function percentText(value: string): string {
  const n = Number(value);
  return Number.isFinite(n) ? String(n) : value;
}

/** Mức giảm của một mã: "10%, tối đa 50.000 đ" hoặc "50.000 đ". */
export function voucherDiscountText(v: Pick<Voucher, "kind" | "value" | "max_discount">): string {
  if (v.kind === "PERCENT") return v.max_discount ? M.percentOf(percentText(v.value), vnd(v.max_discount)) : `${percentText(v.value)}%`;
  return vnd(v.value);
}

/** "dd/mm/yyyy hh:mm đến dd/mm/yyyy hh:mm" theo giờ VN. */
export function voucherPeriodText(v: Pick<Voucher, "starts_at" | "ends_at">): string {
  return M.periodText(dateTime(v.starts_at), dateTime(v.ends_at));
}

// ---------------------------------------------------------------- nháp form

export type VoucherDraft = {
  code: string;
  name: string;
  kind: VoucherKind;
  value: string;
  maxDiscount: string;
  minOrderAmount: string;
  startsAt: string;
  endsAt: string;
  totalUses: string;
  customerTerms: string;
};
export type VoucherErrors = Partial<Record<keyof VoucherDraft, string>>;

export function emptyVoucherDraft(): VoucherDraft {
  return { code: "", name: "", kind: "PERCENT", value: "", maxDiscount: "", minOrderAmount: "", startsAt: "", endsAt: "", totalUses: "", customerTerms: "" };
}

/** ISO UTC → giá trị ô `datetime-local` theo giờ VN ("2026-10-15T08:00"). */
export function isoToVnInput(iso: string): string {
  const day = dateKeyInVietnam(iso);
  return day ? `${day}T${timeHM(iso)}` : "";
}

/** Mã sạch như BE chuẩn hoá: bỏ khoảng trắng, IN HOA. */
export function normalizeCode(raw: string): string {
  return raw.replace(/\s+/g, "").toUpperCase();
}

export function draftOfVoucher(v: Voucher): VoucherDraft {
  return {
    code: v.code,
    name: v.name,
    kind: v.kind,
    value: v.kind === "AMOUNT" ? formatMoneyInput(v.value) : percentText(v.value),
    maxDiscount: v.max_discount ? formatMoneyInput(v.max_discount) : "",
    minOrderAmount: formatMoneyInput(v.min_order_amount),
    startsAt: isoToVnInput(v.starts_at),
    endsAt: isoToVnInput(v.ends_at),
    totalUses: String(v.total_uses),
    customerTerms: v.customer_terms,
  };
}

/** Dãy ≥ 9 chữ số liên tiếp (giống `has_long_digit_run` của BE): chặn số điện thoại lọt vào chữ công khai. */
export function hasLongDigitRun(text: string): boolean {
  return /\d{9,}/.test(text.replace(/[\s.\-]/g, ""));
}

const CODE_RE = /^[A-Z0-9]{4,20}$/;

function intOf(raw: string): number | null {
  const t = raw.trim();
  return /^\d+$/.test(t) ? Number(t) : null;
}

/** Cùng luật với serializer BE (§3.9). Trần phần trăm do BE kiểm (tham số VOUCHER_MAX_PERCENT), FE chỉ chặn quá 100. */
export function validateVoucher(draft: VoucherDraft): VoucherErrors {
  const e: VoucherErrors = {};
  const code = normalizeCode(draft.code);
  if (!CODE_RE.test(code)) e.code = M.codeFormat;
  else if (hasLongDigitRun(code)) e.code = M.codeDigits;
  if (!draft.name.trim()) e.name = M.nameRequired;
  else if (draft.name.trim().length > 200) e.name = M.nameTooLong;

  if (draft.kind === "PERCENT") {
    const pct = parseDecimal(draft.value);
    if (!draft.value.trim()) e.value = M.valueRequired;
    else if (pct === null || pct <= 0) e.value = M.valuePositive;
    else if (pct > 100) e.value = M.valuePercentMax;
    const cap = parseAmount(draft.maxDiscount);
    if (cap.kind !== "ok" || Number(cap.digits) <= 0) e.maxDiscount = M.maxDiscountRequired;
  } else {
    const amount = parseAmount(draft.value);
    if (amount.kind === "empty") e.value = M.valueRequired;
    else if (amount.kind !== "ok" || Number(amount.digits) <= 0) e.value = M.valueAmountInteger;
  }

  if (draft.minOrderAmount.trim()) {
    const min = parseAmount(draft.minOrderAmount);
    if (min.kind !== "ok") e.minOrderAmount = M.minOrderInvalid;
  }
  const uses = intOf(draft.totalUses);
  if (uses === null || uses < 1) e.totalUses = M.totalUsesInvalid;

  const starts = vnInputToIso(draft.startsAt);
  const ends = vnInputToIso(draft.endsAt);
  if (!starts) e.startsAt = M.startsRequired;
  if (!ends) e.endsAt = M.endsRequired;
  else if (starts && ends <= starts) e.endsAt = M.endsBeforeStart;

  if (draft.customerTerms.length > 300) e.customerTerms = M.termsTooLong;
  else if (hasLongDigitRun(draft.customerTerms)) e.customerTerms = M.termsDigits;
  return e;
}

/** Thân tạo mã. Đã qua `validateVoucher`: tiền là chuỗi chữ số, không đi qua Number. */
export function voucherInputOf(draft: VoucherDraft): VoucherInput {
  const digits = (raw: string) => moneyDigits(raw) ?? "0";
  const percent = draft.kind === "PERCENT";
  return {
    code: normalizeCode(draft.code),
    name: draft.name.trim(),
    kind: draft.kind,
    value: percent ? String(parseDecimal(draft.value) ?? 0) : digits(draft.value),
    max_discount: percent ? digits(draft.maxDiscount) : null,
    min_order_amount: draft.minOrderAmount.trim() ? digits(draft.minOrderAmount) : "0",
    starts_at: vnInputToIso(draft.startsAt),
    ends_at: vnInputToIso(draft.endsAt),
    total_uses: intOf(draft.totalUses) ?? 1,
    customer_terms: draft.customerTerms.trim(),
  };
}

// ---------------------------------------------------------------- sửa mã (BR-DM-22)

/** Mã đã tới `starts_at` (đang chạy, hết hạn, hết lượt, đã tắt sau khi chạy) hay chưa: quyết định trường nào được sửa. */
export function hasStarted(v: Pick<Voucher, "starts_at">, nowMs: number): boolean {
  const t = Date.parse(v.starts_at);
  return Number.isFinite(t) && nowMs >= t;
}

export type VoucherField = keyof VoucherDraft;

/** Trường khoá: `code`, `kind` luôn khoá khi sửa; từ `starts_at` chỉ còn name, ends_at, total_uses, min_order_amount, value, max_discount. */
export function lockedFields(v: Pick<Voucher, "starts_at">, nowMs: number): Set<VoucherField> {
  const locked = new Set<VoucherField>(["code", "kind"]);
  if (hasStarted(v, nowMs)) {
    locked.add("startsAt");
    locked.add("customerTerms");
  }
  return locked;
}

/** Số tiền nguyên đồng từ ô tiền ("1.500.000" → 1500000). */
function moneyNum(raw: string): number | null {
  const d = moneyDigits(raw);
  return d === null ? null : Number(d);
}

/**
 * Với mã đã chạy: chỉ cho đổi theo hướng có lợi cho khách (ends_at lùi về sau, total_uses tăng, min_order giảm, value tăng,
 * max_discount tăng). Trả lỗi theo trường; BE vẫn là nơi quyết định (`UNFAVORABLE_CHANGE`).
 */
export function unfavorableChanges(original: Voucher, draft: VoucherDraft): VoucherErrors {
  const e: VoucherErrors = {};
  const endsNow = vnInputToIso(draft.endsAt);
  if (endsNow && Date.parse(endsNow) < Date.parse(original.ends_at)) e.endsAt = M.unfavorable;
  const usesNow = intOf(draft.totalUses);
  if (usesNow !== null && usesNow < original.total_uses) e.totalUses = M.unfavorable;
  const minNow = moneyNum(draft.minOrderAmount || "0");
  if (minNow !== null && minNow > Number(original.min_order_amount)) e.minOrderAmount = M.unfavorable;
  const valueNow = draft.kind === "PERCENT" ? parseDecimal(draft.value) : moneyNum(draft.value);
  if (valueNow !== null && valueNow < Number(original.value)) e.value = M.unfavorable;
  const capNow = moneyNum(draft.maxDiscount);
  if (capNow !== null && original.max_discount && capNow < Number(original.max_discount)) e.maxDiscount = M.unfavorable;
  return e;
}

/** Thân PATCH: chỉ trường khác bản gốc (không gửi trường không đổi, nhất là trường khoá). Rỗng nghĩa là chưa đổi gì. */
export function voucherPatchOf(original: Voucher, draft: VoucherDraft, nowMs: number): VoucherPatch {
  const next = voucherInputOf(draft);
  const locked = lockedFields(original, nowMs);
  const patch: VoucherPatch = {};
  if (next.name !== original.name) patch.name = next.name;
  if (Number(next.value) !== Number(original.value)) patch.value = next.value;
  if (next.kind === "PERCENT" && Number(next.max_discount ?? 0) !== Number(original.max_discount ?? 0)) patch.max_discount = next.max_discount;
  if (Number(next.min_order_amount) !== Number(original.min_order_amount)) patch.min_order_amount = next.min_order_amount;
  if (Date.parse(next.ends_at) !== Date.parse(original.ends_at)) patch.ends_at = next.ends_at;
  if (next.total_uses !== original.total_uses) patch.total_uses = next.total_uses;
  if (!locked.has("startsAt") && Date.parse(next.starts_at) !== Date.parse(original.starts_at)) patch.starts_at = next.starts_at;
  if (!locked.has("customerTerms") && next.customer_terms !== original.customer_terms) patch.customer_terms = next.customer_terms;
  return patch;
}

// ---------------------------------------------------------------- lỗi của BE

const SERVER_FIELD: Record<string, VoucherField> = {
  code: "code",
  name: "name",
  kind: "kind",
  value: "value",
  max_discount: "maxDiscount",
  min_order_amount: "minOrderAmount",
  starts_at: "startsAt",
  ends_at: "endsAt",
  total_uses: "totalUses",
  customer_terms: "customerTerms",
};

/**
 * Lỗi theo trường (khoá = tên trường BE) từ thân 400: `VALIDATION` có `fields` dạng object {tên trường: câu lỗi};
 * `UNFAVORABLE_CHANGE`/`FIELD_LOCKED` có `fields` dạng mảng tên trường kèm `detail` chung (gắn `detail` vào từng trường đó).
 */
export function serverFieldMessages(err: unknown): Record<string, string> {
  if (!(err instanceof ApiError) || err.status !== 400 || !err.details || typeof err.details !== "object") return {};
  const fields = (err.details as { fields?: unknown }).fields;
  const out: Record<string, string> = {};
  if (Array.isArray(fields)) {
    for (const name of fields) if (typeof name === "string") out[name] = err.message;
  } else if (fields && typeof fields === "object") {
    for (const [name, v] of Object.entries(fields as Record<string, unknown>)) {
      const first = Array.isArray(v) ? v[0] : v;
      if (typeof first === "string" && first.trim()) out[name] = first;
    }
  }
  return out;
}

/** Như `serverFieldMessages` nhưng đổi tên trường BE sang khoá của nháp form; khoá lạ bỏ qua. */
export function voucherServerErrors(err: unknown): VoucherErrors {
  const out: VoucherErrors = {};
  for (const [name, message] of Object.entries(serverFieldMessages(err))) {
    const key = SERVER_FIELD[name];
    if (key) out[key] = message;
  }
  return out;
}

// ---------------------------------------------------------------- tắt mã

export type DisableDraft = { reason: "" | "BUDGET" | "INCIDENT" | "OTHER"; note: string };
export type DisableErrors = Partial<Record<keyof DisableDraft, string>>;

export function validateDisable(draft: DisableDraft): DisableErrors {
  const e: DisableErrors = {};
  if (!draft.reason) e.reason = M.disableReasonRequired;
  if (draft.reason === "OTHER" && !draft.note.trim()) e.note = M.disableNoteRequired;
  if (draft.note.length > 200) e.note = M.disableNoteTooLong;
  else if (hasLongDigitRun(draft.note)) e.note = M.disableNoteDigits;
  return e;
}
