"use client";

// Bảng giá tạm của lô 1 (khung mới bọc ngoài). Lô 2 thay bằng CatalogScreen (lọc, sắp xếp, tìm).
import { useEffect, useState } from "react";
import { getCatalog } from "../../lib/api";
import type { CatalogItem } from "../../lib/types";
import CatalogGrid from "../../components/CatalogGrid";
import ShopFrame from "../../components/ShopFrame";

export default function ShopCatalogPage() {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getCatalog()
      .then((data) => active && setItems(data.items))
      .catch(() => active && setLoadError("Không tải được bảng giá lúc này. Vui lòng thử lại sau."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  return (
    <ShopFrame header="sticky" footer="full" bottomNav>
      <div className="shop-main">
        <h1 className="page-title">Bảng giá hải sản</h1>
        {loading ? (
          <p className="empty-state">Đang tải bảng giá…</p>
        ) : loadError ? (
          <p className="form-banner-error">{loadError}</p>
        ) : (
          <CatalogGrid items={items} />
        )}
      </div>
    </ShopFrame>
  );
}
