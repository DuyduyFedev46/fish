"use client";

// Chi tiết mặt hàng — route tĩnh /shop/item?code=XXX (thay cho route động [itemCode]
// vì static export không dựng được trang cho mã hàng chưa biết lúc build).
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { getCatalogItem } from "../../../lib/api";
import type { CatalogItemDetail } from "../../../lib/types";
import { formatVnd, formatKg } from "../../../lib/format";
import AddToCartControl from "../../../components/AddToCartControl";

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
      <Link href="/shop" className="item-detail-back">← Quay lại bảng giá</Link>
      <div className="item-detail-card">
        <p className="item-detail-group">{item.group}</p>
        <h1 className="item-detail-name">
          {item.name}
          {item.item_type === "BUNDLE" && <span className="badge badge-combo">Combo</span>}
        </h1>
        <div className="item-detail-price">
          {formatVnd(item.price)} <span className="unit">/ kg</span>
        </div>
        <div className={"item-detail-stock " + (item.sellable_qty > 0 ? "in-stock" : "out-stock")}>
          {item.sellable_qty > 0
            ? `Còn ${formatKg(item.sellable_qty)} khả dụng`
            : "Hiện đã hết hàng"}
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
    <Suspense fallback={<p className="empty-state">Đang tải…</p>}>
      <ItemDetail />
    </Suspense>
  );
}
