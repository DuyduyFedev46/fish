"use client";

// F2b — "Huỷ đơn" (ED-10-AC2): hai bước. Bước 1 chọn lý do (+ ghi chú, bắt buộc khi chọn "Khác"); bước 2 nêu hậu quả rồi
// mới có nút đỏ "Huỷ đơn". Sau khi huỷ, màn gợi ý "Lập phiếu hoàn" (đơn đã thanh toán).

import { useState } from "react";
import { vnd } from "@/shared/lib/format";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { useSubmit, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { cancelOrder } from "../api";
import { CANCEL_REASONS } from "../labels";
import { ORDERS_MSG as M } from "../messages";
import type { CancelOrderResult, CancelReasonCode } from "../types";
import { ActionModal } from "./ActionModal";

type Props = {
  order: { id: number; code: string; total_amount: string; delivery_status: string | null };
  onClose: () => void;
  onDone: (r: CancelOrderResult) => void;
  onConflict: (c: SubmitConflict) => void;
};

export function CancelOrderModal({ order, onClose, onDone, onConflict }: Props) {
  const [step, setStep] = useState<"form" | "confirm">("form");
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [errs, setErrs] = useState<{ reason?: string; note?: string }>({});
  const sub = useSubmit(() => cancelOrder(order.id, { reason_code: reason as CancelReasonCode, note: note.trim() }), { onSuccess: onDone });
  const reasonLabel = CANCEL_REASONS.find((r) => r.value === reason)?.label ?? "";

  const next = () => {
    const e: { reason?: string; note?: string } = {};
    if (!reason) e.reason = M.cancelReasonMissing;
    else if (reason === "OTHER" && !note.trim()) e.note = M.cancelNoteMissing;
    setErrs(e);
    if (!e.reason && !e.note) setStep("confirm");
  };

  if (step === "form") {
    return (
      <ActionModal
        title={M.cancelTitle}
        onClose={onClose}
        submitting={false}
        failed={false}
        error={null}
        submitLabel={M.cancelNext}
        onSubmit={next}
        backLabel="Đóng"
      >
        <SummaryBlock rows={[{ label: M.rowOrder, value: order.code, mono: true }, { label: M.rowOrderTotal, value: vnd(order.total_amount), num: true }]} />
        <Field
          as="select"
          label={M.cancelReasonLabel}
          required
          name="reason_code"
          value={reason}
          onChange={(v) => {
            setReason(v);
            setErrs({});
          }}
          options={[{ value: "", label: M.cancelReasonPlaceholder }, ...CANCEL_REASONS.map((r) => ({ value: r.value, label: r.label }))]}
          error={errs.reason}
          autoFocus
        />
        <Field
          as="textarea"
          label={M.cancelNoteLabel}
          required={reason === "OTHER"}
          name="note"
          value={note}
          onChange={(v) => {
            setNote(v);
            if (errs.note) setErrs((e) => ({ ...e, note: undefined }));
          }}
          maxLength={500}
          error={errs.note ?? sub.fieldErrors.note}
        />
      </ActionModal>
    );
  }

  return (
    <ActionModal
      title={M.cancelConfirmTitle}
      onClose={onClose}
      onBack={() => {
        sub.reset();
        setStep("form");
      }}
      submitting={sub.submitting}
      failed={sub.failed}
      error={sub.error}
      conflict={sub.conflict}
      onConflict={onConflict}
      submitLabel={M.cancelSubmit}
      busyLabel={M.cancelling}
      danger
      onSubmit={() => void sub.submit()}
    >
      <FormAlert kind="warn">{order.delivery_status === "FAILED" ? M.cancelAlertFailedDelivery : M.cancelAlertRestored}</FormAlert>
      <SummaryBlock
        rows={[
          { label: M.rowOrder, value: order.code, mono: true },
          { label: M.rowOrderTotal, value: vnd(order.total_amount), num: true },
          { label: M.rowReason, value: reasonLabel },
        ]}
      />
    </ActionModal>
  );
}
