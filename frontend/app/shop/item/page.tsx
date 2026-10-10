"use client";

// Chi tiết mặt hàng — route tĩnh /shop/item?code=XXX (thay cho route động [itemCode]
// vì static export không dựng được trang cho mã hàng chưa biết lúc build). Lô 2 viết lại thành ItemDetailScreen.
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { getCatalogItem } from "../../../lib/api";
import type { CatalogItemDetail } from "../../../lib/types";
import { formatKg } from "../../../lib/format";
import { groupIconOf } from "../../../features/catalog/groupIcon";
import AddToCartControl from "../../../components/AddToCartControl";
import ImageFrame from "../../../components/catalog/ImageFrame";
import PriceTag from "../../../components/catalog/PriceTag";
import StockBadge from "../../../components/catalog/StockBadge";
import ShopFrame from "../../../components/ShopFrame";

function ItemDetail() {
  const code = useSearchParams().get("code") || "";
  const [item, setItem] = useState<CatalogItemDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    if (!code) {
      setLoading(false);
      return;
    }
    getCatalogItem(code)
      .then((data) => active && setItem(data))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [code]);

  if (loading) return <p className="empty-state">Đang tải…</p>;
  if (!item) {
    return (
      <div className="item-detail">
        <Link href="/shop" className="item-detail-back">← Quay lại bảng giá</Link>
        <p className="empty-state">Không tìm thấy mặt hàng.</p>
      </div>
    );
  }

  return (
    <div className="item-detail">
      <div className="item-detail-card">
        <div className="item-image-detail">
          <ImageFrame
            image={item.image}
            alt={item.name}
            group={groupIconOf(item.group.slug, item.item_type)}
            ratio="1/1"
            loadingPriority="eager"
            dimmed={item.stock_level === "out"}
          />
        </div>
        <p className="item-detail-group">{item.group.name}</p>
        <h1 className="item-detail-name">
          {item.name}
          {item.item_type === "BUNDLE" && <span className="badge badge-combo">Combo</span>}
        </h1>
        <PriceTag amount={item.price} unit={item.unit} size="detail" tone={item.stock_level === "out" ? "muted" : "accent"} />
        <div className="item-detail-stock">
          <StockBadge level={item.stock_level} placement="inline" size="md" />
        </div>

        <AddToCartControl item={item} />

        {item.item_type === "BUNDLE" && item.bundle_components && item.bundle_components.length > 0 && (
          <div className="bundle-box">
            <h3>Combo gồm các thành phần</h3>
            <ul className="bundle-list">
              {item.bundle_components.map((c) => (
                <li key={c.item_code}>
                  <span>{c.name}</span>
                  <span>{formatKg(c.qty_per_bundle)} / combo</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ItemDetailPage() {
  return (
    <ShopFrame header="sub" title="Chi tiết sản phẩm" footer="full" bottomNav={false}>
      <div className="shop-main">
        <Suspense fallback={<p className="empty-state">Đang tải…</p>}>
          <ItemDetail />
        </Suspense>
      </div>
    </ShopFrame>
  );
}
