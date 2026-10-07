"use client";

// In lại tem: hỏi lý do (hỏng/mất tem, hay đổi thông tin nhận) trước khi in. Tem cũ vẫn phải xé và xác nhận huỷ (CS-14).
import { useId, useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { Modal } from "@/shared/ui/overlay/Modal";
import type { LabelPrintReason } from "../types";
import s from "../deliveries.module.css";

type Props = { code: string; onClose: () => void; onConfirm: (reason: LabelPrintReason) => void };

// Lô 17b (UI-RULES §6.2): không dòng gợi ý xám; tên lý do (enums.ts) đã tự nói rõ.
const OPTIONS: Array<{ value: LabelPrintReason }> = [{ value: "REPRINT" }, { value: "ADDRESS_CHANGED" }];

export function ReprintLabelModal({ code, onClose, onConfirm }: Props) {
  const [reason, setReason] = useState<LabelPrintReason>("REPRINT");
  const name = useId();
  return (
    <Modal
      title="In lại tem"
      size="sm"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            Quay lại
          </button>
          <button type="button" className="btn primary" onClick={() => onConfirm(reason)}>
            In lại tem
          </button>
        </>
      }
    >
      <SummaryBlock label="Phiếu in lại tem" rows={[{ label: "Phiếu giao", value: code, mono: true }]} />
      <fieldset className={s.pickList}>
        <legend className={s.pickLegend}>Vì sao in lại?</legend>
        {OPTIONS.map((o) => (
          <label key={o.value} className={`${s.pick} ${reason === o.value ? s.pickOn : ""}`}>
            <input className={s.pickInput} type="radio" name={`${name}-reason`} checked={reason === o.value} onChange={() => setReason(o.value)} />
            <span className={s.pickBody}>
              <span className={s.pickName}>{ENUMS.deliveryLabelReason[o.value].label}</span>
            </span>
          </label>
        ))}
      </fieldset>
    </Modal>
  );
}
