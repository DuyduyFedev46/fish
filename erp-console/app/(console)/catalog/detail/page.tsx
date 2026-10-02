"use client";

import { Suspense } from "react";
import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ItemDetailScreen } from "@/features/catalog/components/ItemDetailScreen";

// ED-30 / W2d: chi tiết mặt hàng (/catalog/detail/?id=). Cần catalog.view_item.
// Khối Trợ lý AI ghép ở đây vì màn tính năng không import features/ai (02b §2.3); targetModel = catalog.item, targetId = id số.
export default function Page() {
  return (
    <ViewGuard view="catalog">
      <Suspense fallback={null}>
        <ItemDetailScreen renderAi={(t, onApplied) => <AiDocBlockGate targetModel="catalog.item" targetId={t.id} onApplied={onApplied} />} />
      </Suspense>
    </ViewGuard>
  );
}
