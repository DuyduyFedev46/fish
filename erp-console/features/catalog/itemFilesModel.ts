// Hàm thuần cho màn Nhập mặt hàng từ Excel (FISH-66 S5, S6; 02a §3–§5, 02b §10).
// Không chạm DOM, dễ kiểm thử đơn vị trong itemFiles.test.ts.

import { dateOnly, money, vnd } from "@/shared/lib/format";
import { ApiError } from "@/shared/lib/http";
import {
  IMPORT_ALREADY_APPLIED,
  IMPORT_INVALID_ROWS,
  type ImportLimits,
  type ImportPreviewRow,
  type ImportRowError,
  type ImportRowErrorsDetails,
  type ImportSummary,
  type ImportWarning,
  type ShopState,
} from "./itemFilesTypes";
import { ITEM_IMPORT_MSG as M } from "./messages";

export type UpdatedFieldRow = {
  key: string;
  row: number;
  code: string;
  name: string;
  field: string;
  label: string;
  old: string;
  new: string;
};

export type GroupedWarning = {
  column: string;
  rows: number[];
  text: string;
};

export function formatMaxRows(maxRows: number): string {
  return money(maxRows);
}

export function formatMaxMb(maxBytes: number): string {
  const mb = 1024 * 1024;
  if (maxBytes >= mb && maxBytes % mb === 0) {
    return `${money(maxBytes / mb)} MB`;
  }
  if (maxBytes >= mb) {
    return `${(maxBytes / mb).toFixed(1).replace(".", ",")} MB`;
  }
  return `${money(Math.max(1, Math.round(maxBytes / 1024)))} KB`;
}

/** Kiểm nhanh ở máy trước khi gửi (E10, E12). Máy chủ vẫn là lớp chặn thật. */
export function validateImportFile(file: File | null, limits?: ImportLimits): string | null {
  if (!file) return M.errNotXlsx;
  const name = (file.name || "").trim().toLowerCase();
  if (!name.endsWith(".xlsx")) {
    return M.errNotXlsx;
  }
  const maxBytes = limits?.max_bytes ?? 2097152;
  if (file.size > maxBytes) {
    return M.errTooLarge(formatMaxMb(maxBytes));
  }
  return null;
}

/** Tách `rows` của BE thành 4 bảng ở M3 (02a §3.2): Đổi giá, Ẩn/hiện, Món mới, Món sửa. */
export function splitPreviewSections(rows: readonly ImportPreviewRow[]) {
  const priceRows: ImportPreviewRow[] = [];
  const visibilityRows: {
    row: number;
    code: string;
    name: string;
    oldText: string;
    newText: string;
    shopState: ShopState;
  }[] = [];
  const newItemRows: ImportPreviewRow[] = [];
  const updatedFieldRows: UpdatedFieldRow[] = [];

  for (const r of rows) {
    if (r.price !== null) {
      priceRows.push(r);
    }
    if (r.action === "create") {
      newItemRows.push(r);
    } else {
      for (const c of r.changes) {
        if (c.field === "is_active") {
          visibilityRows.push({
            row: r.row,
            code: r.code,
            name: r.name,
            oldText: c.old,
            newText: c.new,
            shopState: r.shop_state,
          });
        } else {
          updatedFieldRows.push({
            key: `${r.row}-${c.field}`,
            row: r.row,
            code: r.code,
            name: r.name,
            field: c.field,
            label: c.label,
            old: c.old,
            new: c.new,
          });
        }
      }
    }
  }

  return { priceRows, visibilityRows, newItemRows, updatedFieldRows };
}

/** Sắp bảng Đổi giá: mặc định theo |Chênh %| giảm dần (dòng rủi ro nhất lên đầu), hoặc theo số dòng Excel. */
export function sortPriceRows(
  priceRows: readonly ImportPreviewRow[],
  sortBy: "percent" | "row",
): ImportPreviewRow[] {
  const copy = [...priceRows];
  if (sortBy === "row") {
    return copy.sort((a, b) => a.row - b.row);
  }
  return copy.sort((a, b) => {
    const pa = a.price?.change_percent != null ? Math.abs(Number(a.price.change_percent)) : -1;
    const pb = b.price?.change_percent != null ? Math.abs(Number(b.price.change_percent)) : -1;
    if (pb !== pa) return pb - pa;
    return a.row - b.row;
  });
}

export function countPriceFlags(priceRows: readonly ImportPreviewRow[]) {
  let checkZeros = 0;
  let largeChange = 0;
  let backdated = 0;
  const flaggedRows: ImportPreviewRow[] = [];

  for (const r of priceRows) {
    const flags = r.price?.flags || [];
    const hasZero = flags.includes("check_zeros");
    const hasLarge = flags.includes("large_change");
    const hasBack = flags.includes("backdated");
    if (hasZero) checkZeros += 1;
    if (hasLarge) largeChange += 1;
    if (hasBack) backdated += 1;
    if (hasZero || hasLarge) {
      flaggedRows.push(r);
    }
  }

  const sortedFlagged = sortPriceRows(flaggedRows, "percent");
  return {
    total: priceRows.length,
    checkZeros,
    largeChange,
    backdated,
    flaggedRows: sortedFlagged,
  };
}

/** Dòng đếm đầu phần Đổi giá: "20 giá mới · 2 cần kiểm lại số 0 · 3 chênh lớn · 1 lùi ngày" (02a §3.2). */
export function formatPriceHeaderSummary(priceRows: readonly ImportPreviewRow[]): string {
  const counts = countPriceFlags(priceRows);
  const parts = [`${counts.total} giá mới`];
  if (counts.checkZeros > 0) parts.push(`${counts.checkZeros} cần kiểm lại số 0`);
  if (counts.largeChange > 0) parts.push(`${counts.largeChange} chênh lớn`);
  if (counts.backdated > 0) parts.push(`${counts.backdated} lùi ngày`);
  return parts.join(" · ");
}

/** Định dạng cột Chênh lệch: "▲ +80.000 đ" hoặc "▼ −166.500 đ" hoặc "—" (02a §3.2). */
export function formatPriceDiffAmount(changeAmount: string | null | undefined): string {
  if (changeAmount == null || changeAmount === "") return M.none;
  const n = Number(changeAmount);
  if (!Number.isFinite(n) || n === 0) return vnd(0);
  const absFormatted = vnd(Math.abs(n));
  return n > 0 ? `▲ +${absFormatted}` : `▼ −${absFormatted}`;
}

/** Định dạng cột Chênh %: "▲ +33,3%" hoặc "▼ −90,0%" hoặc "—" (02a §3.2). */
export function formatPriceDiffPercent(changePercent: string | null | undefined): string {
  if (changePercent == null || changePercent === "") return M.none;
  const n = Number(changePercent);
  if (!Number.isFinite(n) || n === 0) return "0,0%";
  const absText = Math.abs(n).toFixed(1).replace(".", ",");
  return n > 0 ? `▲ +${absText}%` : `▼ −${absText}%`;
}

export function shopStateLabel(state: ShopState): string {
  switch (state) {
    case "selling":
      return M.shopSelling;
    case "hidden":
      return M.shopHidden;
    case "will_show":
      return M.shopWillShow;
    case "will_hide":
      return M.shopWillHide;
  }
}

/** Gộp ngày áp dụng giá cho hộp xác nhận M5: "14/11/2026 (2 món), 15/11/2026 (18 món)" (02a §3.4). */
export function groupValidFromSummary(priceRows: readonly ImportPreviewRow[]): string {
  if (priceRows.length === 0) return M.none;
  const counts = new Map<string, number>();
  for (const r of priceRows) {
    const vf = r.price?.valid_from;
    if (!vf) continue;
    counts.set(vf, (counts.get(vf) || 0) + 1);
  }
  const dates = [...counts.keys()].sort();
  if (dates.length === 0) return M.none;
  return dates.map((iso) => `${dateOnly(iso)} (${counts.get(iso)} món)`).join(", ");
}

/** Dòng tóm tắt bên trái thanh nút đáy M3: "20 giá mới · 1 món mới · 1 món sửa" (02a §3.2). */
export function formatActionBarSummary(summary: ImportSummary): string {
  const parts: string[] = [];
  if (summary.price_changed > 0) parts.push(`${summary.price_changed} giá mới`);
  if (summary.created > 0) parts.push(`${summary.created} món mới`);
  if (summary.updated > 0) parts.push(`${summary.updated} món sửa`);
  if (summary.visibility_changed > 0) parts.push(`${summary.visibility_changed} đổi ẩn/hiện`);
  return parts.join(" · ");
}

/** Tiêu đề hộp xác nhận M5: "Nhập 20 giá mới, 1 món mới, 1 món sửa?" (02a §3.4). */
export function formatConfirmTitle(summary: ImportSummary): string {
  const parts: string[] = [];
  if (summary.price_changed > 0) parts.push(`${summary.price_changed} giá mới`);
  if (summary.created > 0) parts.push(`${summary.created} món mới`);
  if (summary.updated > 0) parts.push(`${summary.updated} món sửa`);
  if (summary.visibility_changed > 0 && parts.length === 0) {
    parts.push(`${summary.visibility_changed} đổi ẩn/hiện`);
  }
  return `Nhập ${parts.join(", ")}?`;
}

/** Nhãn nút chính hộp M5: "Xác nhận nhập 20 giá mới" hoặc "Xác nhận nhập 2 thay đổi" (02a §3.4, L8). */
export function formatConfirmSubmitLabel(summary: ImportSummary): string {
  if (summary.price_changed > 0) {
    return `Xác nhận nhập ${summary.price_changed} giá mới`;
  }
  const totalChanges = summary.created + summary.updated + summary.visibility_changed;
  return `Xác nhận nhập ${ Math.max(1, totalChanges) } thay đổi`;
}

/** Câu toast T4 sau khi ghi thành công: "Đã nhập: 1 món mới, 1 món sửa, 2 giá mới." (bỏ vế có số 0, 02a §5). */
export function formatImportSuccessToast(counts: {
  created: number;
  updated: number;
  price_changed: number;
  visibility_changed?: number;
}): string {
  const parts: string[] = [];
  if (counts.created > 0) parts.push(`${counts.created} món mới`);
  if (counts.updated > 0) parts.push(`${counts.updated} món sửa`);
  if (counts.price_changed > 0) parts.push(`${counts.price_changed} giá mới`);
  if (parts.length === 0 && (counts.visibility_changed ?? 0) > 0) {
    parts.push(`${counts.visibility_changed} đổi ẩn/hiện`);
  }
  return `Đã nhập: ${parts.join(", ")}.`;
}

/** Gộp cảnh báo sửa cột chỉ đọc theo tên cột (W1, 02a §3.2, §5). */
export function groupReadonlyWarnings(warnings: readonly ImportWarning[]): GroupedWarning[] {
  const byCol = new Map<string, number[]>();
  for (const w of warnings) {
    const list = byCol.get(w.column) || [];
    if (!list.includes(w.row)) list.push(w.row);
    byCol.set(w.column, list);
  }
  const result: GroupedWarning[] = [];
  for (const [column, rows] of byCol.entries()) {
    const sorted = [...rows].sort((a, b) => a - b);
    result.push({
      column,
      rows: sorted,
      text: M.readonlyWarning(sorted.length, column, sorted.join(", ")),
    });
  }
  return result;
}

/** Trích xuất bảng lỗi dòng từ `ApiError` (400 `IMPORT_INVALID_ROWS`). */
export function extractRowErrors(err: unknown): ImportRowErrorsDetails | null {
  if (!(err instanceof ApiError) || err.code !== IMPORT_INVALID_ROWS) return null;
  const d = (err.details || {}) as Partial<ImportRowErrorsDetails>;
  const rawErrors = Array.isArray(d.errors) ? (d.errors as ImportRowError[]) : [];
  const sorted = [...rawErrors].sort((a, b) => a.row - b.row);
  const rowSet = new Set(sorted.map((e) => e.row));
  return {
    error_count: typeof d.error_count === "number" ? d.error_count : sorted.length,
    error_row_count: typeof d.error_row_count === "number" ? d.error_row_count : rowSet.size,
    errors_truncated: Boolean(d.errors_truncated),
    errors: sorted,
    limits: d.limits,
  };
}

/** 409 `IMPORT_ALREADY_APPLIED` (T5, S6-AC7): file đã được ghi rồi, coi như thành công. Chỉ xét `code`; toast dùng câu cố định (02a §5). */
export function isImportAlreadyApplied(err: unknown): boolean {
  return err instanceof ApiError && err.code === IMPORT_ALREADY_APPLIED;
}
