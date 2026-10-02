"use client";

import { Suspense } from "react";
import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ReceiptDetailScreen } from "@/features/purchasing/components/ReceiptDetailScreen";

// Chi tiết phiếu nhập: /purchasing/detail/?id=<id>. Khối Trợ lý AI ghép ở đây vì màn hình tính năng không import features/ai.
export default function Page() {
  return (
    <ViewGuard view="purchasing">
      <Suspense fallback={null}>
        <ReceiptDetailScreen renderAi={(t, onApplied) => <AiDocBlockGate targetModel="purchasing.purchasereceipt" targetId={String(t.id)} onApplied={onApplied} />} />
      </Suspense>
    </ViewGuard>
  );
}
