import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { StocktakeForm } from "@/features/stocktake/components/StocktakeForm";

// Lập phiếu kiểm kê: /stocktake/new/.
export default function StocktakeFormPage() {
  return (
    <ViewGuard view="stocktake">
      <Suspense fallback={null}>
        <StocktakeForm mode="new" />
      </Suspense>
    </ViewGuard>
  );
}
