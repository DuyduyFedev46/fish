import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { CatalogScreen } from "@/features/catalog/components/CatalogScreen";

// ED-30 / ED-31 (W2d): Danh mục & giá, bốn tab Mặt hàng · Bảng giá · Ưu đãi · Nhóm hàng (`?tab=`). Cần catalog.view_item;
// tab và nút ghi tự ẩn theo quyền (CatalogScreen), không khoá cả màn.
export default function Page() {
  return (
    <ViewGuard view="catalog">
      <Suspense fallback={null}>
        <CatalogScreen />
      </Suspense>
    </ViewGuard>
  );
}
