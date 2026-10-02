"use client";

// Hỏi lại trước khi TẮT một việc làm hỏng màn của cả nhóm (xem đơn, giao hàng, nhật ký). Nêu việc, nhóm, số người bị ảnh hưởng.
// Lỗi từ BE (vd 403, 400) hiện ngay trong hộp bằng nguyên văn `detail`; hộp giữ mở, nút chính đổi "Thử lại".

import { errorText } from "@/shared/lib/messages";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { PERM_MSG as M } from "../messages";
import type { PendingOff } from "../useCapabilityToggle";
import s from "../permissions.module.css";

type Props = {
  pending: PendingOff;
  onConfirm: () => Promise<void>;
  onClose: () => void;
  /** Khoá việc → nhãn tiếng Việt. */
  labelOf: (key: string) => string;
};

export function ConfirmOffModal({ pending, onConfirm, onClose, labelOf }: Props) {
  const { group, item, plan, warning } = pending;
  return (
    <ConfirmModal
      title={M.confirmOffTitle(item.label)}
      confirmLabel={M.confirmOffOk}
      busyLabel={M.confirmOffBusy}
      backLabel={M.confirmOffBack}
      danger
      run={onConfirm}
      onDone={onClose}
      onClose={onClose}
      errorText={(err) => errorText(err, M.saveFailed)}
    >
      <p className={s.confirmBody}>{`Nhóm: ${group.label}.`}</p>
      <p className={s.confirmBody}>{warning}</p>
      {plan.alsoChanged.length > 0 && <p className={s.confirmBody}>{`Tắt kèm: ${plan.alsoChanged.map(labelOf).join(", ")}.`}</p>}
    </ConfirmModal>
  );
}
