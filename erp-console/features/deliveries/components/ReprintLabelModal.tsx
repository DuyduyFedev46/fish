"use client";

// In lại tem: hỏi lý do (hỏng/mất tem, hay đổi thông tin nhận) trước khi in. Tem cũ vẫn phải xé và xác nhận huỷ (CS-14).
import { useId, useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { Modal } from "@/shared/ui/overlay/Modal";
import type { LabelPrintReason } from "../types";
import s from "../deliveries.module.css";

type Props = { code: string; onClose: () => void; onConfirm: (reason: LabelPrintReason) => void };

const OPTIONS: Array<{ value: LabelPrintReason; hint: string }> = [
  { value: "REPRINT", hint: "Tem cũ bị hỏng, mất hoặc in mờ." },
  { value: "ADDRESS_CHANGED", hint: "Khách đổi người nhận hoặc địa chỉ, tem cũ hết hiệu lực." },
];

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
      <p className="muted">
        Phiếu <span className="num">{code}</span>
      </p>
      <fieldset className={s.pickList}>
        <legend className={s.pickLegend}>Vì sao in lại?</legend>
        {OPTIONS.map((o) => (
          <label key={o.value} className={`${s.pick} ${reason === o.value ? s.pickOn : ""}`}>
            <input className={s.pickInput} type="radio" name={`${name}-reason`} checked={reason === o.value} onChange={() => setReason(o.value)} />
            <span className={s.pickBody}>
              <span className={s.pickName}>{ENUMS.deliveryLabelReason[o.value].label}</span>
              <span className={s.pickMeta}>{o.hint}</span>
            </span>
          </label>
        ))}
      </fieldset>
    </Modal>
  );
}
