"use client";

import Link from "next/link";
import type { CatalogItem } from "../lib/types";
import { formatVnd } from "../lib/format";
import AddToCartControl from "./AddToCartControl";

export default function CatalogGrid({ items }: { items: CatalogItem[] }) {
  if (items.length === 0) {
    return <p className="empty-state">Hiện chưa có mặt hàng nào.</p>;
  }

  const groups = Array.from(new Set(items.map((i) => i.group)));

  return (
    <div className="catalog">
      {groups.map((group) => (
        <section key={group} className="catalog-group">
          <h2 className="catalog-group-title">{group}</h2>
          <div className="catalog-grid">
            {items
              .filter((i) => i.group === group)
              .map((item) => (
                <article key={item.item_code} className="item-card">
                  <Link href={`/shop/item?code=${encodeURIComponent(item.item_code)}`} className="item-card-name">
                    {item.name}
                    {item.item_type === "BUNDLE" && (
                      <span className="badge badge-combo">Combo</span>
                    )}
                  </Link>
                  <div className="item-card-price">
                    {formatVnd(item.price)} <span className="unit">/ kg</span>
                  </div>
                  <div
                    className={
                      "item-card-stock " +
                      (item.sellable_qty > 0 ? "in-stock" : "out-stock")
                    }
                  >
                    {item.sellable_qty > 0
                      ? `Còn ${item.sellable_qty.toLocaleString("vi-VN")} kg`
                      : "Hết hàng"}
                  </div>
                  <AddToCartControl item={item} />
                </article>
              ))}
          </div>
        </section>
      ))}
    </div>
  );
}
