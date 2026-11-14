// Kiểu cho tải/nhập file Excel mặt hàng (FISH-66 S3, S4; contract 02b §3.2–3.3).
// Lô 2 chỉ có phần tải; phần nhập (limits, preview, commit) thêm ở lô 3.

import type { ItemListParams } from "./types";

/** Bộ lọc gửi kèm khi tải file: đúng bộ lọc phía máy chủ của danh sách (ô tìm chữ không đi vào file). */
export type ItemExportParams = ItemListParams;

/** Mã lỗi BE trả ở 400 khi tham số lọc sai (S3-AC8). */
export const INVALID_FILTER = "INVALID_FILTER";

/** Kết quả tải file đã xử lý: tên file lấy từ Content-Disposition, số món từ X-Row-Count. */
export type ItemFileSaved = { filename: string; rowCount: number | null };
