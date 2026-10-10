"use client";

// Lưới danh mục tạm của lô 1 (đọc catalog mới: stock_level, group.{slug,name}). Lô 2 thay bằng CatalogScreen + ProductCard.
import Link from "next/link";
import type { CatalogItem } from "../lib/types";
import { groupIconOf } from "../features/catalog/groupIcon";
import AddToCartControl from "./AddToCartControl";
import ImageFrame from "./catalog/ImageFrame";
import PriceTag from "./catalog/PriceTag";
import StockBadge from "./catalog/StockBadge";

export default function CatalogGrid({ items }: { items: CatalogItem[] }) {
  if (items.length === 0) {
    return <p className="empty-state">Hiện chưa có mặt hàng nào.</p>;
  }

  const groups = Array.from(new Set(items.map((i) => i.group.name)));

  return (
    <div className="catalog">
      {groups.map((group) => (
        <section key={group} className="catalog-group">
          <h2 className="catalog-group-title">{group}</h2>
          <div className="catalog-grid">
            {items
              .filter((i) => i.group.name === group)
              .map((item) => (
                <article key={item.item_code} className="item-card">
                  <Link
                    href={`/shop/item?code=${encodeURIComponent(item.item_code)}`}
                    className="item-card-media"
                    aria-hidden="true"
                    tabIndex={-1}
                  >
                    <ImageFrame
                      image={item.image}
                      alt=""
                      group={groupIconOf(item.group.slug, item.item_type)}
                      ratio="1/1"
                      dimmed={item.stock_level === "out"}
                    />
                  </Link>
                  <Link href={`/shop/item?code=${encodeURIComponent(item.item_code)}`} className="item-card-name">
                    {item.name}
                    {item.item_type === "BUNDLE" && (
                      <span className="badge badge-combo">Combo</span>
                    )}
                  </Link>
                  <PriceTag amount={item.price} unit={item.unit} size="card" tone={item.stock_level === "out" ? "muted" : "default"} />
                  <StockBadge level={item.stock_level} placement="inline" />
                  <AddToCartControl item={item} />
                </article>
              ))}
          </div>
        </section>
      ))}
    </div>
  );
}
