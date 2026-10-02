"use client";

// Hộp xác nhận "Nhờ người xử lý" (menu "…" của trang chi tiết). Gọi POST /api/ai/actions/escalate/ qua `escalateStep`
// (thuần http, không kéo runtime AI). Lỗi của BE (đã có quyền tự làm, bước không còn, 403/404…) hiện nguyên văn ở alert đầu hộp.

import { escalateStep } from "@/features/ai/actions/api";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { ESCALATE_MSG as M, whoText } from "../escalation";
import type { GuidanceNextStep } from "../types";

type Props = {
  docType: string;
  docId: string | number;
  step: GuidanceNextStep;
  onClose: () => void;
  /** Đã chuyển xong; `who` là chuỗi người nhận để màn báo "Đã nhờ …". */
  onDone: (who: string) => void;
  /** Tải lại chứng từ khi hộp báo xung đột phiên bản (nút "Tải lại" của ConfirmModal). Lỗi 400 của BE (STEP_NOT_FOUND, BR-AI-25 …) chỉ hiện trong hộp. */
  onReload?: () => void;
};

export function EscalateModal({ docType, docId, step, onClose, onDone, onReload }: Props) {
  const who = whoText(step);
  return (
    <ConfirmModal
      title={M.title}
      confirmLabel={M.confirm}
      busyLabel={M.busy}
      noun="chứng từ"
      run={() => escalateStep({ doc_type: docType, doc_id: docId, step_key: step.key })}
      onDone={() => onDone(who)}
      onClose={onClose}
      onReload={onReload}
    >
      <p>{M.body(step.label, who)}</p>
    </ConfirmModal>
  );
}
