// API tải file Excel mặt hàng (FISH-66 S3, S4), theo 02b §3.2–3.3:
//   GET /api/catalog/items/export/?item_group=&is_active=&item_type=&has_image=   -> .xlsx, header Content-Disposition + X-Row-Count
//   GET /api/catalog/items/export-template/                                       -> mau-hang-ban.xlsx
// Số cột theo quyền do BE quyết (17 cột; NV kho 14 cột, không có giá bán). FE không đọc hay ghi xlsx.
// Lô 3 thêm getImportLimits, previewImport, commitImport vào file này.

import { apiDownload } from "@/shared/lib/http";
import { saveBlob } from "@/shared/lib/download";
import { itemListQuery } from "./api";
import { mockItemFilesApi } from "./itemFilesMock";
import type { ItemExportParams, ItemFileSaved } from "./itemFilesTypes";

const EXPORT = "/api/catalog/items/export/";
const TEMPLATE = "/api/catalog/items/export-template/";
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
