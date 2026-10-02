"use client";

import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { OrderDetailScreen } from "@/features/orders/components/OrderDetailScreen";

// ED-09: chi tiết đơn (/orders/detail/?id=). Khối Trợ lý AI ghép ở đây vì feature màn hình không import features/ai;
// targetId = "<mã đơn>,<pk>" (mã để người đọc, pk để BE tra đúng đơn).
export default function Page() {
  return (
    <ViewGuard view="orders">
      <OrderDetailScreen
        renderAi={(t, onApplied) => <AiDocBlockGate targetModel="sales.salesorder" targetId={`${t.code},${t.id}`} onApplied={onApplied} />}
      />
    </ViewGuard>
  );
}
