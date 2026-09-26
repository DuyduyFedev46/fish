// API module catalog (A2, 02-stories.md — hồ sơ 2026-09-26-anh-mat-hang).
// Danh sách mặt hàng + tải/thay ảnh. Endpoint ảnh gửi multipart/form-data — KHÔNG tự đặt
// Content-Type (shared/lib/http.ts lo phần đó khi body là FormData).

import { apiFetch, USE_MOCK, type Paginated } from "@/shared/lib/http";
import { matches } from "@/shared/lib/search";
import { mockListItems, mockUploadImage } from "./mock";
import type { CatalogItem, ImageFilter, UploadImageInput, UploadImageResponse } from "./types";

function queryOf(filter: ImageFilter, page: number): string {
  const qs = new URLSearchParams();
  if (filter === "with_image") qs.set("has_image", "true");
  if (filter === "without_image") qs.set("has_image", "false");
  if (page > 1) qs.set("page", String(page));
  const s = qs.toString();
  return s ? `?${s}` : "";
}

/**
 * `GET /api/catalog/items/` — DANH SÁCH PHÂN TRANG DRF thật ({count,next,previous,results}), KHÔNG
 * PHẢI mảng trần (QA REJECTED lô 1, B1 04-qa-report.md: màn Danh mục sập với mọi vai trò vì hàm này
 * từng khai `Promise<CatalogItem[]>` và đọc thẳng response — `DEFAULT_PAGINATION_CLASS` toàn cục của
 * BE bọc mọi danh sách trong `results`, xem `backend/config/settings.py`). Bộ lọc "Chưa có ảnh" lọc
 * PHÍA SERVER qua `?has_image=` (UC-A5) — không tự lọc lại phía máy trên dữ liệu đã cắt trang.
 */
export function listItems(filter: ImageFilter, page = 1): Promise<Paginated<CatalogItem>> {
  return apiFetch<Paginated<CatalogItem>>(`/api/catalog/items/${queryOf(filter, page)}`, {
    mock: USE_MOCK ? mockListItems : undefined,
  });
}

/** Lọc phía máy trong DANH SÁCH ĐÃ TẢI (tìm tên/mã) — bộ lọc "Chưa có ảnh" gọi lại API (queryOf ở trên). */
export function filterItems(items: CatalogItem[], q: string): CatalogItem[] {
  return items.filter((i) => matches(q, i.code, i.name));
}

/** POST (chưa có ảnh) hoặc thay (đã có ảnh) — cùng một endpoint, BE trả 201/200 tương ứng. */
export function uploadItemImage(itemId: number, input: UploadImageInput): Promise<UploadImageResponse> {
  const fd = new FormData();
  fd.append("file", input.file);
  if (input.altText.trim()) fd.append("alt_text", input.altText.trim());
  fd.append("is_illustration", input.isIllustration ? "true" : "false");
  fd.append("expected_image_id", input.expectedImageId);
  return apiFetch<UploadImageResponse>(`/api/catalog/items/${itemId}/image/`, {
    method: "POST",
    body: fd,
    mock: USE_MOCK ? mockUploadImage : undefined,
  });
}
