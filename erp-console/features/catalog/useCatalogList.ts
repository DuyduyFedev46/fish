"use client";

// Các danh sách phân trang của màn Danh mục & giá — dùng khung chung `usePagedList` (trang 1 khi bộ lọc đổi, "Tải thêm" nối
// trang kế, bỏ kết quả về trễ). `GET /api/catalog/*` là phân trang DRF thật ({count,next,previous,results}), không phải mảng trần.
// Bộ lọc chạy PHÍA SERVER; riêng ô tìm chữ là lọc phía máy trong phần đã tải (BE chưa có tham số `q`).

import { usePagedList } from "@/shared/lib/usePagedList";
import { listItemGroups, listItemPrices, listItems, listPricingRules } from "./api";
import type { CatalogItem, ItemGroup, ItemListParams, ItemPrice, PricingRule, PricingRuleListParams } from "./types";

export function useCatalogList(params: ItemListParams, enabled: boolean) {
  return usePagedList<CatalogItem, ItemListParams>((p, page) => listItems(p, page), params, enabled);
}

/** Mọi mức giá của mọi mặt hàng (tab Bảng giá). Cần catalog.view_itemprice. */
export function usePriceList(enabled: boolean) {
  return usePagedList<ItemPrice, { scope: "all" }>((_p, page) => listItemPrices(null, page), { scope: "all" }, enabled);
}

/** Lịch sử giá của MỘT mặt hàng; `version` đổi (sau khi đặt giá mới) → tải lại từ trang 1. */
export function useItemPriceHistory(itemId: number, enabled: boolean, version: number) {
  return usePagedList<ItemPrice, { item: number; version: number }>((p, page) => listItemPrices(p.item, page), { item: itemId, version }, enabled);
}

export function usePricingRules(params: PricingRuleListParams, enabled: boolean) {
  return usePagedList<PricingRule, PricingRuleListParams>((p, page) => listPricingRules(p, page), params, enabled);
}

export function useItemGroups(enabled: boolean) {
  return usePagedList<ItemGroup, { scope: "all" }>((_p, page) => listItemGroups(page), { scope: "all" }, enabled);
}
