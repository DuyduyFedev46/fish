// Kiểu cho tải/nhập file Excel mặt hàng (FISH-66 S3–S6; contract 02b §3.2–3.7).

import type { ItemListParams } from "./types";

/** Bộ lọc gửi kèm khi tải file: đúng bộ lọc phía máy chủ của danh sách (ô tìm chữ không đi vào file). */
export type ItemExportParams = ItemListParams;

/** Mã lỗi BE trả ở 400 khi tham số lọc sai (S3-AC8). */
export const INVALID_FILTER = "INVALID_FILTER";

/** Mã lỗi BE trả cho luồng nhập file Excel (02b §3.7). */
export const IMPORT_INVALID_FILE = "IMPORT_INVALID_FILE";
export const IMPORT_INVALID_ROWS = "IMPORT_INVALID_ROWS";
export const IMPORT_PREVIEW_INVALID = "IMPORT_PREVIEW_INVALID";
export const IMPORT_DATA_CHANGED = "IMPORT_DATA_CHANGED";
export const IMPORT_ALREADY_APPLIED = "IMPORT_ALREADY_APPLIED";
export const IMPORT_PREVIEW_EXPIRED = "IMPORT_PREVIEW_EXPIRED";

export type ImportInvalidFileReason =
  | "not_xlsx"
  | "unreadable"
  | "too_large"
  | "too_many_rows"
  | "missing_columns"
  | "unknown_columns"
  | "duplicate_columns"
  | "empty"
  | "no_price_list";

/** Kết quả tải file đã xử lý: tên file lấy từ Content-Disposition, số món từ X-Row-Count. */
export type ItemFileSaved = { filename: string; rowCount: number | null };

/** GET /api/catalog/items/import/limits/ (02b §3.4). */
export type ImportLimits = {
  max_rows: number;
  max_bytes: number;
  preview_ttl_minutes?: number;
};

export type PriceFlag = "check_zeros" | "large_change" | "backdated";

export type ShopState = "selling" | "hidden" | "will_show" | "will_hide";

export type ImportFieldChange = {
  field: string;
  label: string;
  old: string;
  new: string;
};

export type ImportPriceDiff = {
  old: string | null;
  new: string;
  valid_from: string;
  change_amount: string | null;
  change_percent: string | null;
  flags: PriceFlag[];
};

export type ImportPreviewRow = {
  row: number;
  code: string;
  action: "create" | "update";
  name: string;
  item_group?: string;
  changes: ImportFieldChange[];
  price: ImportPriceDiff | null;
  is_active_after: boolean;
  shop_state: ShopState;
};

export type ImportWarning = {
  row: number;
  code: string;
  column: string;
  message: string;
};

export type ImportSummary = {
  total_rows: number;
  created: number;
  updated: number;
  price_changed: number;
  visibility_changed: number;
  unchanged: number;
  will_show_on_shop: number;
  will_hide_from_shop: number;
};

/** POST /api/catalog/items/import/preview/ -> 200 (02b §3.5). */
export type ImportPreviewResponse = {
  preview_token: string | null;
  expires_at: string | null;
  has_changes: boolean;
  summary: ImportSummary;
  rows: ImportPreviewRow[];
  warnings: ImportWarning[];
  limits: ImportLimits;
};

export type ImportRowError = {
  row: number;
  code: string;
  column: string;
  message: string;
};

/** POST /api/catalog/items/import/preview/ -> 400 IMPORT_INVALID_ROWS (02b §3.5). */
export type ImportRowErrorsDetails = {
  error_count: number;
  error_row_count: number;
  errors_truncated: boolean;
  errors: ImportRowError[];
  limits?: ImportLimits;
};

/** POST /api/catalog/items/import/commit/ -> 200 (02b §3.6). */
export type ImportCommitResponse = {
  created: number;
  updated: number;
  price_changed: number;
  visibility_changed: number;
  codes: string[];
};
