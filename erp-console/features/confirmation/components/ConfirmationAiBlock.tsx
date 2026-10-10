"use client";

// Khối Trợ lý AI của trang Gọi xác nhận. Giống AiDocBlockGate nhưng truyền câu hỏi nhanh theo NGỮ CẢNH chứng từ
// (cuộc gọi, hẹn gọi lại, quyết định). Câu hỏi nhanh KHÔNG chứa tên, số điện thoại, địa chỉ: chỉ gửi mã chứng từ đích.
// AI tắt hoặc lỗi → không vẽ gì (fail-closed). Không có chuỗi runtime nặng ở file này (check-ai-chunks).
import { useEffect, useState } from "react";
import { aiVisible } from "@/shared/lib/features";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { getAiStatus } from "@/features/ai/api";
import { AiDocBlock } from "@/features/ai/components/AiDocBlock";
import type { AiStatus } from "@/features/ai/types";

export const CONFIRMATION_AI_CHIPS = ["Tóm tắt các cuộc gọi của đơn này", "Nên hẹn gọi lại lúc nào?", "Gợi ý lời nhắn khi khách không nghe máy"];

type Props = { noteId: number; onApplied?: () => void };

export function ConfirmationAiBlock({ noteId, onApplied }: Props) {
  const { me } = useAuth();
  const visible = aiVisible(me);
  const [status, setStatus] = useState<AiStatus | null>(null);

  useEffect(() => {
    // Cờ AI tắt (SR-HIDE-AI-01): không gọi /api/ai/status/.
    if (!visible) return;
    const ctrl = new AbortController();
    getAiStatus(ctrl.signal)
      .then((st) => setStatus(st))
      .catch(() => {
        if (!ctrl.signal.aborted) setStatus(null);
      });
    return () => ctrl.abort();
  }, [visible]);

  if (!visible || !status?.ai_enabled) return null;
  return <AiDocBlock status={status} targetModel="delivery.deliverynote" targetId={String(noteId)} onApplied={onApplied} chips={CONFIRMATION_AI_CHIPS} />;
}
