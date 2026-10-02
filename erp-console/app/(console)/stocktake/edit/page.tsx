import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { StocktakeForm } from "@/features/stocktake/components/StocktakeForm";

// Sửa số đếm của phiếu chờ duyệt: /stocktake/edit/?id=<số>. useSearchParams cần Suspense khi xuất tĩnh.
export default function StocktakeFormPage() {
  return (
    <ViewGuard view="stocktake">
      <Suspense fallback={null}>
        <StocktakeForm mode="edit" />
      </Suspense>
    </ViewGuard>
  );
}
