import type { CatalogItem } from "@/lib/types";
import { parseQtyRule } from "@/lib/quantity";
import type { ProductCardItem } from "@/components/catalog/ProductCard";
import { groupIconOf } from "./groupIcon";

/** Dữ liệu catalog -> dữ liệu thẻ trình bày. Số kg tồn không có trong catalog nên không thể lọt vào thẻ. */
export function toCardItem(it: CatalogItem): ProductCardItem {
  const rule = parseQtyRule(it.min_qty, it.qty_step, it.unit);
  return {
    itemCode: it.item_code,
    name: it.name,
    unit: it.unit,
    price: it.price,
    stockLevel: it.stock_level,
    shortNote: it.short_note,
    image: it.image,
    group: groupIconOf(it.group.slug, it.item_type),
    isCombo: it.item_type === "BUNDLE",
    minQty: rule.minQty,
    qtyStep: rule.step,
  };
}

export const itemHref = (code: string) => `/shop/item/?code=${encodeURIComponent(code)}`;
