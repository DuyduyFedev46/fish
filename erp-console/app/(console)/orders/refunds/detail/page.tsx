"use client";

import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { RefundDetailScreen } from "@/features/orders/components/RefundDetailScreen";

// ED-12: chi tiết phiếu hoàn (/orders/refunds/detail/?id=). Nút theo `available_actions` (chỉ Chủ có confirm_refund).
// Khối Trợ lý AI ghép ở đây (feature màn hình không import features/ai); targetId = pk phiếu hoàn.
export default function Page() {
  return (
    <ViewGuard view="refunds">
      <RefundDetailScreen
        renderAi={(t, onApplied) => <AiDocBlockGate targetModel="sales.refund" targetId={t.id} onApplied={onApplied} />}
      />
    </ViewGuard>
  );
}
