"use client";

// Danh sách mặt hàng theo bộ lọc ảnh (A2) — dùng khung phân trang chung `usePagedList` (giống S10/S12/S13
// ở features/orders). Sửa theo QA REJECTED lô 1 (B1, 04-qa-report.md): `GET /api/catalog/items/` là danh
// sách phân trang DRF thật ({count,next,previous,results}), KHÔNG phải mảng trần — không được tự đọc
// thẳng `CatalogItem[]` như trước.

import { listItems } from "./api";
import type { CatalogItem, ImageFilter } from "./types";
import { usePagedList, type PagedState } from "@/shared/lib/usePagedList";

export type CatalogListState = PagedState<CatalogItem>;

export function useCatalogList(filter: ImageFilter, enabled: boolean) {
  return usePagedList<CatalogItem, ImageFilter>(listItems, filter, enabled);
}
