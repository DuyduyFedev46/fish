"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { PurchaseCostForm } from "@/features/accounting/components/PurchaseCostForm";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { receiptFromSearch } from "@/features/purchasing/receiptView";

// F1d Nhập chi phí mua: /purchasing/costs/new/?receipt=<id>. Chỉ Chủ (form tự kiểm quyền); không có ?receipt thì cho chọn phiếu.
function CostFormFromQuery() {
  const params = useSearchParams();
  return <PurchaseCostForm receiptId={receiptFromSearch(params.get("receipt"))} />;
}

export default function Page() {
  return (
    <ViewGuard view="purchasing">
      <Suspense fallback={null}>
        <CostFormFromQuery />
      </Suspense>
    </ViewGuard>
  );
}
