/**
 * Danh mục Shop công khai dùng cho hộp "Chèn thẻ mặt hàng" (CMS-06). Hình dạng theo
 * 02b-tech-design Shop §3.1: `GET /api/shop/catalog/` trả `{groups, items}` (không còn là mảng).
 * Chỉ khai các khoá ERP cần; API không có số kg tồn (`sellable_qty` đã bỏ), giá vốn hay mã lô.
 */

export interface ShopCatalogItem {
  item_code: string;
  name: string;
  item_type: "SIMPLE" | "BUNDLE";
  unit: "kg" | "combo";
  /** Tiền là chuỗi số nguyên đồng, vd "278000". */
  price: string;
  stock_level: "in" | "low" | "out";
  group: { slug: string; name: string };
}

export interface ShopCatalogGroup {
  slug: string;
  name: string;
  item_count: number;
}

export interface ShopCatalogResponse {
  groups: ShopCatalogGroup[];
  items: ShopCatalogItem[];
}

/**
 * Lấy danh sách món từ phản hồi danh mục. Phản hồi sai hình dạng (kể cả dạng mảng cũ) thì ném lỗi
 * để hộp chọn hiện "Chưa tải được danh sách mặt hàng" thay vì vỡ màn (review lô 1, H1).
 */
export function itemsFromShopCatalog(data: unknown): ShopCatalogItem[] {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("Danh mục Shop sai hình dạng.");
  }
  const items = (data as { items?: unknown }).items;
  if (!Array.isArray(items)) {
    throw new Error("Danh mục Shop sai hình dạng.");
  }
  return items.filter(
    (it): it is ShopCatalogItem =>
      !!it && typeof it === "object" && typeof (it as ShopCatalogItem).item_code === "string" &&
      typeof (it as ShopCatalogItem).name === "string"
  );
}
