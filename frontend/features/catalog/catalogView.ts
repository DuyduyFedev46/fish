import type { CatalogItem, ItemImage } from "@/lib/types";
import { foldVietnamese } from "@/lib/text";
import type { SortValue } from "@/components/catalog/SortControl";

export type CatalogFilter = { q: string; group: string; type: string; sort: SortValue };

/** Món hết luôn xuống cuối, giữ thứ tự cũ trong từng nhóm (sắp xếp ổn định). */
export function rankItems<T extends { stock_level: string }>(items: T[]): T[] {
  return [...items.filter((i) => i.stock_level !== "out"), ...items.filter((i) => i.stock_level === "out")];
}

/** Lọc theo từ khoá (bỏ dấu), nhóm, loại combo; sắp xếp theo giá; món hết luôn ở cuối. */
export function filterAndSort(items: CatalogItem[], f: CatalogFilter): CatalogItem[] {
  const q = foldVietnamese(f.q.trim());
  let list = items.filter((i) => {
    if (f.type === "combo" && i.item_type !== "BUNDLE") return false;
    if (f.group && i.group.slug !== f.group) return false;
    if (q && !foldVietnamese(i.name).includes(q)) return false;
    return true;
  });
  if (f.sort === "price_asc") list = [...list].sort((a, b) => Number(a.price) - Number(b.price));
  if (f.sort === "price_desc") list = [...list].sort((a, b) => Number(b.price) - Number(a.price));
  return rankItems(list);
}

/** Câu luật mua dựng từ min_qty/qty_step của catalog (không hard-code). */
export function rulesText(items: CatalogItem[]): string {
  const kg = items.find((i) => i.unit === "kg");
  const fmt = (v: string) => Number(v).toString().replace(".", ",");
  if (!kg) return "Combo tính theo combo.";
  return `Giá tính theo kg. Mua tối thiểu ${fmt(kg.min_qty)} kg, tăng từng ${fmt(kg.qty_step)} kg. Combo tính theo combo.`;
}

/**
 * Lấy ảnh đại diện cho một mục danh mục từ món đầu tiên có ảnh trong mục (ưu tiên món còn hàng nhờ rankItems).
 * - `groupSlug === "combo"`: tìm món BUNDLE (hoặc thuộc nhóm `combo`) có ảnh.
 * - `groupSlug === ""` hoặc `"all"`: tìm món đầu tiên bất kỳ có ảnh.
 * - Các nhóm khác: tìm món đầu tiên có `i.group.slug === groupSlug` và có ảnh.
 */
export function groupRepresentativeImage(items: CatalogItem[], groupSlug: string): ItemImage | null {
  const ranked = rankItems(items);
  const matched = ranked.find((i) => {
    const inGroup =
      groupSlug === "combo"
        ? i.item_type === "BUNDLE" || i.group.slug === "combo"
        : groupSlug === "" || groupSlug === "all"
          ? true
          : i.group.slug === groupSlug;
    if (!inGroup || !i.image) return false;
    const u = i.image.urls;
    return Boolean(u && (u.thumb || u.card || u.detail));
  });
  return matched?.image ?? null;
}

/** Tạo bảng tra cứu ảnh đại diện theo danh sách `groupSlugs`. */
export function groupImageMap(items: CatalogItem[], groupSlugs?: string[]): Record<string, ItemImage | null> {
  const slugs = groupSlugs ?? Array.from(new Set(["", "all", "combo", ...items.map((i) => i.group.slug)]));
  const out: Record<string, ItemImage | null> = {};
  for (const slug of slugs) {
    out[slug] = groupRepresentativeImage(items, slug);
  }
  return out;
}
