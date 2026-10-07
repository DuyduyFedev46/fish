"use client";

// Cổng MỎNG của khối Trợ lý AI trên trang chứng từ (02b §2.4). Page ghép <AiDocBlockGate/> vào `aiSlot` của DetailPage.
// Chỉ làm một việc: hỏi GET /api/ai/status/ (getAiStatus ghi cờ vào gate-state cho các nơi khác), AI tắt hoặc lỗi → KHÔNG vẽ gì
// (fail-closed, S05-AC5). AI bật mới nạp AiDocBlock. Khối chat nặng (runtime, model) chỉ nạp động bên trong AiDocBlock,
// và chỉ khi đã đồng ý — nên chunk của trang nghiệp vụ không chứa code AI nặng (BR-AI-17).
// Không được để chuỗi runtime nặng xuất hiện trong file này (check-ai-chunks).

import { useEffect, useState } from "react";
import { aiVisible } from "@/shared/lib/features";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { getAiStatus } from "../api";
import { releaseAiEnabled } from "../gate-state";
import type { AiStatus } from "../types";
import { AiDocBlock } from "./AiDocBlock";

type Props = {
  /** Loại chứng từ đích của R1, vd "purchasing.purchasereceipt", "inventory.batch", "sales.salesorder". */
  targetModel: string;
  /** Mã chứng từ đích: phiếu nhập / lô = id số; đơn bán = mã SO… (02b R1). */
  targetId: string | number;
  /** Gọi sau khi một đề xuất được Đồng ý thành công, để trang tải lại chứng từ. */
  onApplied?: () => void;
};

export function AiDocBlockGate({ targetModel, targetId, onApplied }: Props) {
  const { me } = useAuth();
  const visible = aiVisible(me);
  const [status, setStatus] = useState<AiStatus | null>(null);

  useEffect(() => {
    // Cờ AI tắt (SR-HIDE-AI-01): không gọi /api/ai/status/.
    if (!visible) return;
    const ctrl = new AbortController();
    // Chủ riêng của trang này: rời trang thì nhả cờ, không để "AI bật" dính sang trang khác (L2).
    const owner = Symbol("ai-doc-block");
    getAiStatus(ctrl.signal, owner)
      .then((st) => setStatus(st))
      .catch(() => {
        if (!ctrl.signal.aborted) setStatus(null);
      });
    return () => {
      ctrl.abort();
      releaseAiEnabled(owner);
    };
  }, [visible]);

  if (!visible || !status?.ai_enabled) return null;
  return <AiDocBlock status={status} targetModel={targetModel} targetId={String(targetId)} onApplied={onApplied} />;
}
