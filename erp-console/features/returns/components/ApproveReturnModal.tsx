"use client";

// F2n — Duyệt hàng hoàn (ED-26, BR-HV-02). Tóm tắt phiếu + chọn Quyết định bắt buộc: Tái nhập vào lô | Huỷ bỏ, ghi lỗ.
// 409 (phiếu đã được duyệt ở nơi khác) hiện ConflictBanner kèm "Tải lại" thay vì lỗi đỏ. Lỗi khác: alert đầu hộp, nút chính đổi thành "Thử lại".
import { useId, useState } from "react";
import { kg } from "@/shared/lib/format";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { isConflictError, primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { approveReturn } from "../api";
import { RETURNS_MSG as M } from "../messages";
import { approveErrorText, outsideText } from "../returnsModel";
import type { ApproveDecision, ReturnItem } from "../types";
import s from "../returns.module.css";

type Props = {
  item: ReturnItem;
  /** Quyết định chọn sẵn theo nút đã bấm ở header. */
  initialDecision?: ApproveDecision;
  onClose: () => void;
  onApproved: (item: ReturnItem) => void;
  /** Bấm "Tải lại" ở banner xung đột: màn cha tải lại phiếu và đóng hộp. */
  onReload: () => void;
};

const OPTIONS: { key: ApproveDecision; name: string; hint: string }[] = [
  { key: "RESTOCK", name: M.restock, hint: M.approveRestockHint },
  { key: "WRITE_OFF", name: M.writeOff, hint: M.approveWriteOffHint },
];

export function ApproveReturnModal({ item, initialDecision, onClose, onApproved, onReload }: Props) {
  const [decision, setDecision] = useState<ApproveDecision | "">(initialDecision ?? "");
  const [missing, setMissing] = useState(false);
  const group = useId();

  const sub = useSubmit(
    async () => {
      try {
        return await approveReturn(item.id, decision as ApproveDecision);
      } catch (err) {
        // Giữ nguyên lỗi xung đột để useSubmit bật banner; lỗi khác đổi thành câu tiếng Việt.
        throw isConflictError(err) ? err : new Error(approveErrorText(err));
      }
    },
    { onSuccess: onApproved },
  );

  const trySubmit = () => {
    if (!decision) {
      setMissing(true);
      return;
    }
    setMissing(false);
    void sub.submit();
  };

  return (
    <Modal
      title={M.approveTitle}
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.back}
          </button>
          <button type="button" className="btn primary" onClick={trySubmit} disabled={sub.submitting || sub.conflict !== null} aria-busy={sub.submitting || undefined}>
            {sub.submitting ? M.submitting : primaryLabel(M.approveSubmit, sub.failed && !sub.conflict)}
          </button>
        </>
      }
    >
      <div className={s.form}>
        {sub.conflict && <ConflictBanner noun={M.detailNounShort} updatedByName={sub.conflict.updatedByName} updatedAt={sub.conflict.updatedAt} onReload={onReload} />}
        {sub.error && !sub.conflict && <FormAlert>{sub.error}</FormAlert>}
        <SummaryBlock
          label={M.approveSummary}
          rows={[
            { label: M.fieldBatch, value: item.batch_code, mono: true },
            { label: M.fieldItem, value: item.item_name },
            { label: M.fieldQty, value: kg(item.qty), num: true },
            { label: M.fieldOutside, value: outsideText(item.outside_minutes), num: true },
          ]}
        />
        <fieldset className={s.pickList} aria-invalid={missing || undefined} data-decision-group>
          <legend className={s.pickLegend}>
            {M.approveDecisionLegend} <span aria-hidden="true">*</span>
            <span className="sr-only"> (bắt buộc)</span>
          </legend>
          {OPTIONS.map((o) => (
            <label key={o.key} className={`${s.pick} ${decision === o.key ? s.pickOn : ""} ${missing ? s.pickErr : ""}`}>
              <input
                className={s.pickInput}
                type="radio"
                name={`${group}-decision`}
                value={o.key}
                checked={decision === o.key}
                onChange={() => {
                  setDecision(o.key);
                  setMissing(false);
                }}
                disabled={sub.submitting || sub.conflict !== null}
              />
              <span className={s.pickBody}>
                <span className={s.pickName}>{o.name}</span>
                <span className={s.pickMeta}>{o.hint}</span>
              </span>
            </label>
          ))}
          {missing && (
            <p className={s.pickError} role="alert" data-field-error="decision">
              {M.approveDecisionRequired}
            </p>
          )}
        </fieldset>
      </div>
    </Modal>
  );
}
