// Hàm thuần của Kiểm kê (không React, để vitest): đọc số kg, chênh lệch, kiểm dòng trước khi gửi, câu lỗi của BE.
// Số kg đi qua "phần nghìn" (số nguyên) để không sai số thập phân khi cộng trừ.
import { kg } from "@/shared/lib/format";
import { ApiError } from "@/shared/lib/http";
import type { StocktakeAction, StocktakeDetail, StocktakeListItem } from "./types";

export const LIST_HREF = "/stocktake/";
export const NEW_HREF = "/stocktake/new/";
export const detailHref = (id: number | string) => `/stocktake/detail/?id=${id}`;
export const editHref = (id: number | string) => `/stocktake/edit/?id=${id}`;

/** `?id=` → số nguyên dương, sai dạng → null (màn hiện "Không tìm thấy"). */
export function idFromSearch(raw: string | null): number | null {
  if (!raw || !/^\d{1,15}$/.test(raw)) return null;
  const n = Number(raw);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}

export const MAX_REASON = 500;

// ---------------------------------------------------------------- số kg
/** "18.500" / "18,5" / "18.5" → phần nghìn (18500). Trống hoặc sai → null. */
export function toMilli(text: string | number | null | undefined): number | null {
  if (text === null || text === undefined) return null;
  const raw = String(text).trim().replace(",", ".");
  if (!/^-?\d+(\.\d+)?$/.test(raw)) return null;
  return Math.round(Number(raw) * 1000);
}

export type CountParse =
  | { kind: "empty" }
  | { kind: "ok"; milli: number; wire: string }
  | { kind: "error"; message: string };

/** Ô "Đếm được (kg)": trống = chưa đếm; số âm / chữ / quá 3 chữ số lẻ = lỗi. `wire` là chuỗi gửi BE ("12.500"). */
export function parseCount(text: string): CountParse {
  const raw = text.trim();
  if (!raw) return { kind: "empty" };
  const norm = raw.replace(",", ".");
  if (/^-/.test(norm)) return { kind: "error", message: "Số đếm phải từ 0 kg trở lên." };
  if (!/^\d+(\.\d+)?$/.test(norm)) return { kind: "error", message: "Nhập số kg, ví dụ 12,5." };
  if (/\.\d{4,}$/.test(norm)) return { kind: "error", message: "Tối đa 3 chữ số sau dấu phẩy." };
  if (norm.replace(".", "").length > 12) return { kind: "error", message: "Số quá lớn." };
  const milli = toMilli(norm) as number;
  return { kind: "ok", milli, wire: (milli / 1000).toFixed(3) };
}

/** Phần nghìn → "12,5" (dấu phẩy, bỏ 0 thừa, nhóm nghìn). */
export function qty(milli: number): string {
  return kg(milli / 1000).replace(/ kg$/, "");
}

/** Chuỗi kg của BE ("18.500") → "18,5"; trống/sai → "—". Không kèm đơn vị: cột đã ghi (kg). */
export function qtyText(value: string | number | null | undefined): string {
  const m = toMilli(value);
  return m === null ? "—" : qty(m);
}

/** Chênh lệch có dấu: "−0,25" · "+0,3" · "0". Dấu trừ thật (U+2212) như design. */
export function signedQty(milli: number | null): string {
  if (milli === null) return "—";
  if (milli === 0) return "0";
  return `${milli < 0 ? "−" : "+"}${qty(Math.abs(milli))}`;
}

export function signedQtyText(value: string | number | null | undefined): string {
  return signedQty(toMilli(value));
}

/** Tông chênh lệch: hụt = đỏ, dư = hổ phách, khớp = mặc định. */
export function diffTone(milli: number | null): "crit" | "warn" | "" {
  if (milli === null || milli === 0) return "";
  return milli < 0 ? "crit" : "warn";
}

// ---------------------------------------------------------------- dòng của form
export type FormRow = {
  /** Khoá ổn định của dòng trong form (id lô). */
  batch: number;
  batchCode: string;
  itemName: string;
  warehouseName: string;
  /** Tồn trên hệ thống (phần nghìn). Chỉ để xem trước chênh lệch; BE chụp lại lúc lưu (BR-KK-01). */
  systemMilli: number;
  counted: string;
  reason: string;
};

export type RowError = { counted?: string; reason?: string };

export type RowsCheck = {
  errors: Record<number, RowError>;
  /** Số dòng đã nhập số. */
  countedRows: number;
  /** Số dòng chưa nhập số. */
  emptyRows: number;
  hasError: boolean;
};

/** Chênh lệch xem trước của một dòng (counted − tồn hệ thống); chưa đếm / sai → null. */
export function previewDiff(row: FormRow): number | null {
  const c = parseCount(row.counted);
  return c.kind === "ok" ? c.milli - row.systemMilli : null;
}

/**
 * Kiểm các dòng trước khi gửi (BR-KK-04, không âm, không trùng lô). `requireAll` (Gửi duyệt): mọi dòng phải có số đếm;
 * Lưu nháp chỉ cần ≥ 1 dòng đã đếm, dòng bỏ trống không gửi. Trả lỗi theo CHỈ SỐ dòng trong `rows`.
 */
export function checkRows(rows: FormRow[], requireAll: boolean): RowsCheck {
  const errors: Record<number, RowError> = {};
  const seen = new Set<number>();
  let countedRows = 0;
  let emptyRows = 0;
  rows.forEach((row, i) => {
    const err: RowError = {};
    if (seen.has(row.batch)) err.counted = "Lô này đã có ở dòng trên, mỗi lô chỉ đếm một lần.";
    seen.add(row.batch);
    const c = parseCount(row.counted);
    if (c.kind === "empty") {
      emptyRows += 1;
      if (requireAll && !err.counted) err.counted = "Nhập số đếm của lô này.";
    } else if (c.kind === "error") {
      countedRows += 1;
      if (!err.counted) err.counted = c.message;
    } else {
      countedRows += 1;
      const diff = c.milli - row.systemMilli;
      if (diff > 0 && !row.reason.trim()) err.reason = `Lô đếm nhiều hơn sổ ${qty(diff)} kg: ghi lý do.`;
    }
    if (row.reason.trim().length > MAX_REASON) err.reason = `Lý do tối đa ${MAX_REASON} ký tự.`;
    if (err.counted || err.reason) errors[i] = err;
  });
  return { errors, countedRows, emptyRows, hasError: Object.keys(errors).length > 0 };
}

/** Các dòng gửi BE: chỉ dòng ĐÃ có số đếm hợp lệ (dòng trống bỏ qua), theo thứ tự trong form. */
export function toLineInputs(rows: FormRow[]) {
  const out: { batch: number; counted_qty: string; reason: string }[] = [];
  for (const row of rows) {
    const c = parseCount(row.counted);
    if (c.kind === "ok") out.push({ batch: row.batch, counted_qty: c.wire, reason: row.reason.trim() });
  }
  return out;
}

/** Tóm tắt xem trước khi nhập: số dòng hụt / dư / khớp và tổng kg (chỉ dòng đã đếm hợp lệ). */
export function summarize(rows: FormRow[]) {
  let short = 0;
  let over = 0;
  let match = 0;
  let shortMilli = 0;
  let overMilli = 0;
  for (const row of rows) {
    const d = previewDiff(row);
    if (d === null) continue;
    if (d < 0) {
      short += 1;
      shortMilli += -d;
    } else if (d > 0) {
      over += 1;
      overMilli += d;
    } else match += 1;
  }
  return { short, over, match, shortMilli, overMilli, netMilli: overMilli - shortMilli };
}

// ---------------------------------------------------------------- lỗi của BE
/** Bỏ mã nghiệp vụ trong ngoặc, vd "… cần ghi lý do (BR-KK-04)." → "… cần ghi lý do." (UI-RULES: không hiện mã BR). */
export function cleanMessage(message: string): string {
  return message.replace(/\s*\((?:BR|SR)-[A-Z]+-\d+\)/g, "").replace(/\s{2,}/g, " ").trim();
}

/** Lỗi của một dòng (BE kèm `line_index`, đếm từ 0, là chỉ số trong danh sách ĐÃ GỬI). */
export function lineErrorOf(err: unknown): { index: number; message: string } | null {
  if (!(err instanceof ApiError)) return null;
  const d = err.details && typeof err.details === "object" ? (err.details as Record<string, unknown>) : null;
  const index = d?.line_index;
  if (typeof index !== "number" || !Number.isInteger(index) || index < 0) return null;
  return { index, message: cleanMessage(err.message) };
}

// ---------------------------------------------------------------- hiển thị
/** Cột Kho: một tên, nhiều kho thì "Tên đầu +N kho" (một ô một giá trị). */
export function warehouseText(names: string[]): string {
  if (names.length === 0) return "—";
  return names.length === 1 ? names[0] : `${names[0]} +${names.length - 1} kho`;
}

export const hasAction = (s: Pick<StocktakeListItem, "available_actions">, a: StocktakeAction) => s.available_actions.includes(a);

export const PATH_STEPS: { key: string; label: string }[] = [
  { key: "DRAFT", label: "Nháp" },
  { key: "SUBMITTED", label: "Chờ duyệt" },
  { key: "APPROVED", label: "Đã duyệt" },
];

/** Số lô sẽ đổi tồn khi duyệt (chênh lệch khác 0). */
export function changedLineCount(s: Pick<StocktakeListItem, "short_count" | "over_count">): number {
  return s.short_count + s.over_count;
}

/** Câu "Tiếp theo" của StatusPath; null khi phiếu đã xong. */
export function nextStepText(s: StocktakeListItem): string | null {
  if (s.status === "APPROVED") return null;
  if (s.status === "DRAFT") {
    if (hasAction(s, "submit")) return "Kiểm lại số đếm rồi gửi duyệt. Sau khi gửi không sửa số đếm được, trừ khi trả về nháp.";
    return "Phiếu còn là nháp, chờ người lập phiếu gửi duyệt.";
  }
  if (hasAction(s, "approve")) {
    const n = changedLineCount(s);
    // BR-KK-09: duyệt áp phần chênh lệch đã ghi lúc đếm (counted − tồn lúc lưu), không đặt tồn bằng số đếm.
    return n > 0
      ? `Xem chênh lệch từng lô rồi duyệt. Duyệt sẽ điều chỉnh tồn của ${n} lô theo chênh lệch đã ghi lúc đếm (${signedQtyText(s.net_difference)} kg).`
      : "Xem chênh lệch từng lô rồi duyệt. Số đếm khớp sổ, tồn không đổi.";
  }
  return "Chờ Chủ hoặc Quản lý duyệt.";
}

/** Các việc đã làm (nhãn ngắn) cho StatusPath. */
export function doneSteps(d: StocktakeDetail): string[] {
  const out = [`Đếm ${d.line_count} lô`];
  if (d.lines.some((l) => (toMilli(l.difference_qty) ?? 0) > 0 && l.reason.trim())) out.push("Ghi lý do lô dư");
  if (d.status === "SUBMITTED" || d.status === "APPROVED") out.push("Đã gửi duyệt");
  if (d.status === "APPROVED") out.push("Đã điều chỉnh tồn");
  return out;
}
