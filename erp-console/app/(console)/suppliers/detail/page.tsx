"use client";

import { Suspense } from "react";
import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { SupplierDetailScreen } from "@/features/suppliers/components/SupplierDetailScreen";

// ED-22 / W5d: chi tiết nhà cung cấp (/suppliers/detail/?id=). Cần purchasing.view_supplier.
// Khối Trợ lý AI ghép ở đây vì màn tính năng không import features/ai (02b §2.3); targetModel = purchasing.supplier, targetId = id số.
export default function Page() {
  return (
    <ViewGuard view="suppliers">
      <Suspense fallback={null}>
        <SupplierDetailScreen renderAi={(t, onApplied) => <AiDocBlockGate targetModel="purchasing.supplier" targetId={t.id} onApplied={onApplied} />} />
      </Suspense>
    </ViewGuard>
  );
}
