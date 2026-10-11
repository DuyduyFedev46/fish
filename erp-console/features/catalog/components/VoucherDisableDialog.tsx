"use client";

// Hộp "Tắt mã giảm giá" (SHOP-3b-02, 02b §3.9): bắt buộc chọn lý do; lý do "Lý do khác" bắt buộc ghi chú ngắn (≤ 200 ký tự, không dãy 9 chữ số).
// Khách không nhập được mã nữa; đơn đang giữ lượt vẫn giữ giá đã giảm (BR-DM-19). Lỗi gửi → alert đầu hộp, nút chính "Thử lại", giữ nguyên chữ đã nhập.

import { useId, useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { RadioGroup } from "@/shared/ui/form/Choice";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { disableVoucher } from "../api";
import { VOUCHER_MSG as M } from "../messages";
import type { Voucher } from "../types";
import { serverFieldMessages, validateDisable, type DisableDraft, type DisableErrors } from "../voucherModel";
import s from "../catalog.module.css";

const REASON_OPTIONS = (["BUDGET", "INCIDENT", "OTHER"] as const).map((value) => ({ value, label: ENUMS.voucherDisableReason[value].label }));

export function VoucherDisableDialog({ voucher, onClose, onDone }: { voucher: Voucher; onClose: () => void; onDone: (v: Voucher) => void }) {
  const formId = useId();
  const [draft, setDraft] = useState<DisableDraft>({ reason: "", note: "" });
  const [errs, setErrs] = useState<DisableErrors>({});

  const [fe, setFe] = useState<Record<string, string>>({});

  const sub = useSubmit(
    async () => {
      setFe({});
      try {
        return await disableVoucher(voucher.id, { reason: draft.reason as "BUDGET" | "INCIDENT" | "OTHER", note: draft.note.trim() });
      } catch (err) {
        setFe(serverFieldMessages(err));
        throw err;
      }
    },
    { onSuccess: onDone },
  );

  const submit = () => {
    const found = validateDisable(draft);
    setErrs(found);
    if (Object.keys(found).length) return;
    void sub.submit();
  };

  const hasFieldErrors = Object.keys(fe).length > 0;
  return (
    <Modal
      title={M.disableTitle(voucher.code)}
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.cancel}
          </button>
          <button type="submit" form={formId} className="btn primary" disabled={sub.submitting} aria-busy={sub.submitting || undefined}>
            {sub.submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>Đang gửi…</span>
              </>
            ) : (
              primaryLabel(M.disableConfirm, sub.failed)
            )}
          </button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        className={s.form}
        onSubmit={(e) => {
          e.preventDefault();
          // Hộp này có thể mở từ trong một form khác (trang sửa mã): không để sự kiện nổi lên làm form ngoài gửi theo.
          e.stopPropagation();
          if (!sub.submitting) submit();
        }}
      >
        {sub.error && !hasFieldErrors && <FormAlert>{sub.error}</FormAlert>}
        <p className={s.railNote}>{M.disableIntro}</p>
        <RadioGroup
          label={M.disableReasonLabel}
          required
          name="reason"
          value={draft.reason}
          onChange={(v) => {
            setDraft((d) => ({ ...d, reason: v === "BUDGET" || v === "INCIDENT" || v === "OTHER" ? v : "" }));
            setErrs((e) => ({ ...e, reason: undefined }));
          }}
          options={REASON_OPTIONS}
          error={errs.reason ?? fe.reason}
        />
        <Field
          as="textarea"
          label={M.disableNoteLabel}
          required={draft.reason === "OTHER"}
          name="note"
          value={draft.note}
          onChange={(v) => {
            setDraft((d) => ({ ...d, note: v }));
            setErrs((e) => ({ ...e, note: undefined }));
          }}
          rows={3}
          maxLength={200}
          counter
          error={errs.note ?? fe.note}
        />
      </form>
    </Modal>
  );
}
