"use client";

// Xác nhận "Đã giao xong": phiếu hoàn tất không quay lại được, nên hỏi lại một lần để khỏi bấm nhầm trên điện thoại.
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { PersonalText } from "@/shared/ui/PersonalText";
import { Modal } from "@/shared/ui/overlay/Modal";
import { completeDelivery, type DeliveryStatusResponse } from "../api";
import type { DeliveryNoteItem } from "../types";

type Props = {
  note: Pick<DeliveryNoteItem, "id" | "code" | "order" | "customer_name">;
  onClose: () => void;
  onDone: (res: DeliveryStatusResponse) => void;
  /** 409 (phiếu đã đổi trạng thái): màn cha báo và tải lại. */
  onConflict: () => void;
};

export function ConfirmCompleteModal({ note, onClose, onDone, onConflict }: Props) {
  const sub = useSubmit(() => completeDelivery(note.id), { onSuccess: onDone });
  const conflict = sub.conflict;
  return (
    <Modal
      title="Xác nhận đã giao xong"
      size="sm"
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          {conflict ? (
            <button type="button" className="btn primary" onClick={onConflict}>
              Tải lại
            </button>
          ) : (
            <button type="button" className="btn primary" onClick={() => void sub.submit()} disabled={sub.submitting}>
              {sub.submitting ? "Đang gửi…" : primaryLabel("Đã giao xong", sub.failed)}
            </button>
          )}
        </>
      }
    >
      {conflict && <FormAlert kind="warn">Phiếu vừa đổi trạng thái. Tải lại để xem bản mới.</FormAlert>}
      {sub.error && <FormAlert>{sub.error}</FormAlert>}
      <SummaryBlock
        label="Phiếu giao cần xác nhận"
        rows={[
          { label: "Phiếu giao", value: note.code, mono: true },
          { label: "Đơn", value: note.order?.code || "—", mono: true },
          { label: "Khách hàng", value: <PersonalText value={note.customer_name} whenEmpty="—" /> },
        ]}
      />
      <p>Đã giao tận tay khách? Phiếu hoàn tất rồi thì không sửa lại được.</p>
    </Modal>
  );
}
