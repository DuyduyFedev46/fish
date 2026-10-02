"use client";

import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ReturnDetailScreen } from "@/features/returns/components/ReturnDetailScreen";

// ED-26 / W5f: chi tiết hàng hoàn (/returns/detail/?id=). Khối Trợ lý AI ghép ở đây vì feature màn hình không import features/ai
// (02b §2.3); targetModel = inventory.returntostock, targetId = pk phiếu.
export default function Page() {
  return (
    <ViewGuard view="returns">
      <ReturnDetailScreen renderAi={(id, onApplied) => <AiDocBlockGate targetModel="inventory.returntostock" targetId={id} onApplied={onApplied} />} />
    </ViewGuard>
  );
}
