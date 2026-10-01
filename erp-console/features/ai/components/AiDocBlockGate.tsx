"use client";

// Cổng MỎNG của khối Trợ lý AI trên trang chứng từ (02b §2.4). Page ghép <AiDocBlockGate/> vào `aiSlot` của DetailPage.
// Chỉ làm một việc: hỏi GET /api/ai/status/ (getAiStatus ghi cờ vào gate-state cho các nơi khác), AI tắt hoặc lỗi → KHÔNG vẽ gì
// (fail-closed, S05-AC5). AI bật mới nạp AiDocBlock. Khối chat nặng (runtime, model) chỉ nạp động bên trong AiDocBlock,
// và chỉ khi đã đồng ý — nên chunk của trang nghiệp vụ không chứa code AI nặng (BR-AI-17).
// Không được để chuỗi runtime nặng xuất hiện trong file này (check-ai-chunks).

import { useEffect, useState } from "react";
import { getAiStatus } from "../api";
import type { AiStatus } from "../types";
import { AiDocBlock } from "./AiDocBlock";

type Props = {
  /** Loại chứng từ đích của R1, vd "purchasing.purchasereceipt", "inventory.batch", "sales.order". */
  targetModel: string;
  /** Mã chứng từ đích: phiếu nhập / lô = id số; đơn bán = mã SO… (02b R1). */
  targetId: string | number;
  /** Gọi sau khi một đề xuất được Đồng ý thành công, để trang tải lại chứng từ. */
  onApplied?: () => void;
};

export function AiDocBlockGate({ targetModel, targetId, onApplied }: Props) {
  const [status, setStatus] = useState<AiStatus | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    getAiStatus(ctrl.signal)
      .then((st) => setStatus(st))
      .catch(() => {
        if (!ctrl.signal.aborted) setStatus(null);
      });
    return () => ctrl.abort();
  }, []);

  if (!status?.ai_enabled) return null;
  return <AiDocBlock status={status} targetModel={targetModel} targetId={String(targetId)} onApplied={onApplied} />;
}
