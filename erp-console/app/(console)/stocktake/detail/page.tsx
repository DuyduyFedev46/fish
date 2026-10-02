import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { StocktakeDetailScreen } from "@/features/stocktake/components/StocktakeDetailScreen";

// Chi tiết phiếu kiểm kê: /stocktake/detail/?id=<số>. useSearchParams cần Suspense khi xuất tĩnh.
export default function StocktakeDetailPage() {
  return (
    <ViewGuard view="stocktake">
      <Suspense fallback={null}>
        <StocktakeDetailScreen />
      </Suspense>
    </ViewGuard>
  );
}
