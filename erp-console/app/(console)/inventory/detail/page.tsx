"use client";

import { Suspense } from "react";
import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { BatchDetailScreen } from "@/features/inventory/components/BatchDetailScreen";

// Chi tiết lô: /inventory/detail/?id=<id>. Cần inventory.view_batch (cùng quyền với danh sách).
// Khối Trợ lý AI ghép ở đây vì màn hình tính năng không import features/ai (02b §2.3). targetId = "<mã lô>,<pk>":
// BE tra lô được cả hai kiểu và đề xuất AI có thể lưu theo mã lô hoặc theo pk, nên gửi cả hai để khối hiện đủ.
export default function Page() {
  return (
    <ViewGuard view="inventory">
      <Suspense fallback={null}>
        <BatchDetailScreen
          renderAi={(t, onApplied) => <AiDocBlockGate targetModel="inventory.batch" targetId={`${t.code},${t.id}`} onApplied={onApplied} />}
        />
      </Suspense>
    </ViewGuard>
  );
}
