"use client";

// Bảng giá — client component fetch lúc chạy (static export không SSR).
import { useEffect, useState } from "react";
import { getCatalog } from "../../lib/api";
import type { CatalogItem } from "../../lib/types";
import CatalogGrid from "../../components/CatalogGrid";

export default function ShopCatalogPage() {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getCatalog()
      .then((data) => active && setItems(data))
      .catch(() => active && setLoadError("Không tải được bảng giá lúc này. Vui lòng thử lại sau."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <h1 className="page-title">Bảng giá hải sản</h1>
      <p className="page-subtitle">
        Bán theo kg, giá niêm yết — tồn kho hiển thị là số lượng còn khả dụng.
      </p>
      {loading ? (
        <p className="empty-state">Đang tải bảng giá…</p>
      ) : loadError ? (
        <p className="form-banner-error">{loadError}</p>
      ) : (
        <CatalogGrid items={items} />
      )}
    </>
  );
}
