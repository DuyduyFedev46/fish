// API module catalog — A2 (ảnh mặt hàng) + Lô 13 (ED-30, ED-31) theo contract BE R14.
//   GET   /api/catalog/items/?item_group=&is_active=&item_type=&has_image=&page=
//   GET   /api/catalog/items/{id}/   POST /items/   PATCH /items/{id}/        (PATCH: chỉ Chủ — catalog.change_item)
//   POST  /api/catalog/items/{id}/image/                                     (multipart, A2)
//   POST  /api/catalog/bundle-lines/                                         (công thức combo, mỗi dòng một lần)
//   GET   /api/catalog/item-prices/?item=<id>    POST /item-prices/          (đặt giá mới; BE tự đóng giá cũ)
//   GET   /api/catalog/price-lists/              GET/POST/PATCH /pricing-rules/?is_active=&apply_on=
//   GET   /api/catalog/item-groups/              POST /item-groups/
//   GET   /api/guidance/item/{id}/                                           (chỉ dùng `timeline`)
// Không có DELETE (BE trả 405). Người thiếu quyền xem giá (NV kho) nhận 403 ở item-prices, price-lists, pricing-rules,
// và không có key `current_price` ở mặt hàng — FE chỉ ẩn cho gọn, BE là lớp chặn thật.
// Endpoint ảnh gửi multipart/form-data — KHÔNG tự đặt Content-Type (shared/lib/http.ts lo phần đó khi body là FormData).

import { apiFetch, type Paginated } from "@/shared/lib/http";
import type { GuidanceData } from "@/features/guidance/types";
import { matches } from "@/shared/lib/search";
import { mockCatalogApi, mockUploadImage } from "./mock";
import {
  EMPTY_ITEM_PARAMS,
  type BundleLine,
  type BundleLineInput,
  type CatalogItem,
  type ImageFilter,
  type ItemGroup,
  type ItemGroupInput,
  type ItemGroupPatch,
  type ItemInput,
  type ItemListParams,
  type ItemPatch,
  type ItemPrice,
  type ItemPriceInput,
  type PriceList,
  type PricingRule,
  type PricingRuleInput,
  type PricingRuleListParams,
  type UploadImageInput,
  type UploadImageResponse,
} from "./types";

const ITEMS = "/api/catalog/items/";
const mock = () => (process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockCatalogApi : undefined);

function withPage(qs: URLSearchParams, page: number): string {
  if (page > 1) qs.set("page", String(page));
  const text = qs.toString();
  return text ? `?${text}` : "";
}

/** Chuỗi query theo đúng tên tham số contract; bỏ tham số rỗng. */
export function itemListQuery(params: ItemListParams, page: number): string {
  const qs = new URLSearchParams();
  if (params.group) qs.set("item_group", params.group);
  if (params.type) qs.set("item_type", params.type);
  if (params.active) qs.set("is_active", params.active);
  if (params.hasImage) qs.set("has_image", params.hasImage);
  return withPage(qs, page);
}

function paramsOf(filter: ItemListParams | ImageFilter): ItemListParams {
  if (typeof filter !== "string") return filter;
  if (filter === "with_image") return { ...EMPTY_ITEM_PARAMS, hasImage: "1" };
  if (filter === "without_image") return { ...EMPTY_ITEM_PARAMS, hasImage: "0" };
  return EMPTY_ITEM_PARAMS;
}

/**
 * `GET /api/catalog/items/` — DANH SÁCH PHÂN TRANG DRF thật ({count,next,previous,results}), KHÔNG PHẢI mảng trần.
 * Nhận `ImageFilter` cũ để form Nhập lô (features/purchasing) vẫn gọi `listItems("all")`. Mọi bộ lọc chạy PHÍA SERVER,
 * không tự lọc lại trên dữ liệu đã cắt trang. BE chưa có tham số `q`: tìm tên/mã làm phía máy qua `filterItems`.
 */
export function listItems(filter: ItemListParams | ImageFilter, page = 1, signal?: AbortSignal): Promise<Paginated<CatalogItem>> {
  return apiFetch<Paginated<CatalogItem>>(ITEMS + itemListQuery(paramsOf(filter), page), { signal, mock: mock() });
}

/** Lọc phía máy trong DANH SÁCH ĐÃ TẢI (tìm tên/mã). */
export function filterItems(items: CatalogItem[], q: string): CatalogItem[] {
  return items.filter((i) => matches(q, i.code, i.name));
}

/** GET /api/catalog/items/{id}/ — kèm `bundle_lines`; `current_price` chỉ có với người có quyền xem giá. */
export function getItem(id: number, signal?: AbortSignal): Promise<CatalogItem> {
  return apiFetch<CatalogItem>(`${ITEMS}${id}/`, { signal, mock: mock() });
}

/** POST /api/catalog/items/ → 201. Mã trùng: 400 `{code:[…]}`. Combo: gọi `createBundleLine` cho từng dòng sau đó. */
export function createItem(input: ItemInput): Promise<CatalogItem> {
  return apiFetch<CatalogItem>(ITEMS, { method: "POST", body: input, mock: mock() });
}

/** PATCH /api/catalog/items/{id}/ — chỉ trường đổi; chỉ Chủ. Mã, loại, nhóm không đổi ở đây. */
export function updateItem(id: number, patch: ItemPatch): Promise<CatalogItem> {
  return apiFetch<CatalogItem>(`${ITEMS}${id}/`, { method: "PATCH", body: patch, mock: mock() });
}

/** POST /api/catalog/bundle-lines/ — một thành phần của combo (định mức kg cho MỘT combo). */
export function createBundleLine(input: BundleLineInput): Promise<BundleLine> {
  return apiFetch<BundleLine>("/api/catalog/bundle-lines/", { method: "POST", body: input, mock: mock() });
}

/** GET /api/guidance/item/{id}/ — dòng thời gian của mặt hàng (cùng quyền xem mặt hàng). Chỉ dùng `timeline`. */
export function getItemTimeline(id: number, signal?: AbortSignal): Promise<GuidanceData> {
  return apiFetch<GuidanceData>(`/api/guidance/item/${id}/`, { signal, mock: mock() });
}

/** POST (chưa có ảnh) hoặc thay (đã có ảnh) — cùng một endpoint, BE trả 201/200 tương ứng. */
export function uploadItemImage(itemId: number, input: UploadImageInput): Promise<UploadImageResponse> {
  const fd = new FormData();
  fd.append("file", input.file);
  if (input.altText.trim()) fd.append("alt_text", input.altText.trim());
  fd.append("is_illustration", input.isIllustration ? "true" : "false");
  fd.append("expected_image_id", input.expectedImageId);
  return apiFetch<UploadImageResponse>(`${ITEMS}${itemId}/image/`, {
    method: "POST",
    body: fd,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockUploadImage : undefined,
  });
}

/** GET /api/catalog/item-groups/ — nhóm hàng kèm `parent_name` và `item_count`. */
export function listItemGroups(page = 1, signal?: AbortSignal): Promise<Paginated<ItemGroup>> {
  return apiFetch<Paginated<ItemGroup>>(`/api/catalog/item-groups/${withPage(new URLSearchParams(), page)}`, { signal, mock: mock() });
}

/** POST /api/catalog/item-groups/ → 201. Tên trùng: 400 `{name:[…]}`. */
export function createItemGroup(input: ItemGroupInput): Promise<ItemGroup> {
  return apiFetch<ItemGroup>("/api/catalog/item-groups/", { method: "POST", body: input, mock: mock() });
}

/** PATCH /api/catalog/item-groups/{id}/ — đổi đường dẫn nhóm; chỉ Chủ. Lỗi 400 `{slug:[…]}`. */
export function updateItemGroup(id: number, patch: ItemGroupPatch): Promise<ItemGroup> {
  return apiFetch<ItemGroup>(`/api/catalog/item-groups/${id}/`, { method: "PATCH", body: patch, mock: mock() });
}

/** GET /api/catalog/price-lists/ — thường chỉ có một bảng giá mặc định. Cần catalog.view_pricelist. */
export function listPriceLists(signal?: AbortSignal): Promise<Paginated<PriceList>> {
  return apiFetch<Paginated<PriceList>>("/api/catalog/price-lists/", { signal, mock: mock() });
}

/** GET /api/catalog/item-prices/?item=<id>&page= — lịch sử giá bán, mới nhất trước. Cần catalog.view_itemprice. */
export function listItemPrices(itemId: number | null, page = 1, signal?: AbortSignal): Promise<Paginated<ItemPrice>> {
  const qs = new URLSearchParams();
  if (itemId !== null) qs.set("item", String(itemId));
  return apiFetch<Paginated<ItemPrice>>(`/api/catalog/item-prices/${withPage(qs, page)}`, { signal, mock: mock() });
}

/**
 * POST /api/catalog/item-prices/ → 201. BE tự đóng giá cũ ở ngày liền trước `valid_from` (BR-DM-03).
 * Giá đã có đơn dùng: 400/409 `PRICE_USED_BY_ORDERS` với `detail` tiếng Việt — màn hiện nguyên văn.
 */
export function setItemPrice(input: ItemPriceInput): Promise<ItemPrice> {
  return apiFetch<ItemPrice>("/api/catalog/item-prices/", { method: "POST", body: input, mock: mock() });
}

export function pricingRuleQuery(params: PricingRuleListParams, page: number): string {
  const qs = new URLSearchParams();
  if (params.active) qs.set("is_active", params.active);
  if (params.applyOn) qs.set("apply_on", params.applyOn);
  return withPage(qs, page);
}

/** GET /api/catalog/pricing-rules/?is_active=&apply_on=&page= — cần catalog.view_pricingrule. */
export function listPricingRules(params: PricingRuleListParams, page = 1, signal?: AbortSignal): Promise<Paginated<PricingRule>> {
  return apiFetch<Paginated<PricingRule>>(`/api/catalog/pricing-rules/${pricingRuleQuery(params, page)}`, { signal, mock: mock() });
}

/** POST /api/catalog/pricing-rules/ → 201. */
export function createPricingRule(input: PricingRuleInput): Promise<PricingRule> {
  return apiFetch<PricingRule>("/api/catalog/pricing-rules/", { method: "POST", body: input, mock: mock() });
}

/** PATCH /api/catalog/pricing-rules/{id}/ — bật/tắt ưu đãi (không xoá). */
export function setPricingRuleActive(id: number, active: boolean): Promise<PricingRule> {
  return apiFetch<PricingRule>(`/api/catalog/pricing-rules/${id}/`, { method: "PATCH", body: { is_active: active }, mock: mock() });
}
