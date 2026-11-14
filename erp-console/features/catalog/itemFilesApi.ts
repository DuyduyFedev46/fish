// API tải và nhập file Excel mặt hàng (FISH-66 S3–S6), theo 02b §3.2–3.6:
//   GET  /api/catalog/items/export/?item_group=&is_active=&item_type=&has_image=   -> .xlsx, header Content-Disposition + X-Row-Count
//   GET  /api/catalog/items/export-template/                                       -> mau-hang-ban.xlsx
//   GET  /api/catalog/items/import/limits/                                         -> { max_rows, max_bytes, preview_ttl_minutes }
//   POST /api/catalog/items/import/preview/      (multipart/form-data: file)       -> ImportPreviewResponse
//   POST /api/catalog/items/import/commit/       (multipart/form-data: file, preview_token) -> ImportCommitResponse
// Số cột theo quyền do BE quyết (17 cột; NV kho 14 cột, không có giá bán). FE không đọc hay ghi xlsx.

import { apiDownload, apiFetch } from "@/shared/lib/http";
import { saveBlob } from "@/shared/lib/download";
import { itemListQuery } from "./api";
import { mockItemFilesApi } from "./itemFilesMock";
import type {
  ImportCommitResponse,
  ImportLimits,
  ImportPreviewResponse,
  ItemExportParams,
  ItemFileSaved,
} from "./itemFilesTypes";

const EXPORT = "/api/catalog/items/export/";
const TEMPLATE = "/api/catalog/items/export-template/";
const IMPORT_LIMITS = "/api/catalog/items/import/limits/";
const IMPORT_PREVIEW = "/api/catalog/items/import/preview/";
const IMPORT_COMMIT = "/api/catalog/items/import/commit/";

const mock = () => (process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockItemFilesApi : undefined);

/** Đường dẫn tải danh sách, dùng lại cách tạo query của danh sách và bỏ `page`. */
export function exportItemsPath(params: ItemExportParams): string {
  return EXPORT + itemListQuery(params, 1);
}

/** Tải danh sách mặt hàng theo bộ lọc rồi lưu xuống máy. Lỗi ném `ApiError`, không lưu file hỏng. */
export async function exportItems(params: ItemExportParams): Promise<ItemFileSaved> {
  const file = await apiDownload(exportItemsPath(params), { mock: mock(), fallbackName: "hang-ban.xlsx" });
  saveBlob(file.blob, file.filename);
  return { filename: file.filename, rowCount: file.rowCount };
}

/** Tải file mẫu trống (mau-hang-ban.xlsx) rồi lưu xuống máy. */
export async function exportTemplate(): Promise<ItemFileSaved> {
  const file = await apiDownload(TEMPLATE, { mock: mock(), fallbackName: "mau-hang-ban.xlsx" });
  saveBlob(file.blob, file.filename);
  return { filename: file.filename, rowCount: file.rowCount };
}

/** Đọc giới hạn file nhập (số dòng tối đa, dung lượng tối đa, thời hạn xem trước). */
export async function getImportLimits(signal?: AbortSignal): Promise<ImportLimits> {
  return apiFetch<ImportLimits>(IMPORT_LIMITS, { method: "GET", signal, mock: mock() });
}

/** Gửi file .xlsx lên BE để đọc và xem trước thay đổi (chưa ghi DB). Dùng `apiFetch` với `FormData` để giữ `details` của 400. */
export async function previewImport(file: File, signal?: AbortSignal): Promise<ImportPreviewResponse> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<ImportPreviewResponse>(IMPORT_PREVIEW, {
    method: "POST",
    body: form,
    signal,
    mock: mock(),
  });
}

/** Xác nhận ghi thay đổi đã xem trước (gửi lại chính `File` đã xem trước kèm `preview_token`). */
export async function commitImport(
  file: File,
  previewToken: string,
  signal?: AbortSignal,
): Promise<ImportCommitResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("preview_token", previewToken);
  return apiFetch<ImportCommitResponse>(IMPORT_COMMIT, {
    method: "POST",
    body: form,
    signal,
    mock: mock(),
  });
}
