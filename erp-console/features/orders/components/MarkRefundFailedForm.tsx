"use client";

// S16 — Báo chuyển khoản hoàn thất bại (sai số tài khoản, khách không nhận…). Lý do KHÔNG bắt buộc ở BE
// (`Refund.failure_reason` cho phép rỗng) nhưng luôn nên ghi để đối chiếu — FE chỉ nhắc, không chặn gửi khi để trống.
// Phiếu chuyển Chờ hoàn → Thất bại; bấm "Thử lại" sau đó để quay lại Chờ hoàn (BR-HT-09).

import { useEffect, useId, useRef, useState } from "react";
import { markRefundFailed } from "../api";
import { REFUND_Q_MSG } from "../messages";
import type { MarkRefundFailedResult, RefundQueueItem } from "../types";
import { Consequences, FormFooter, FormHead, NoteField, useSubmit } from "./QueueFormParts";
import s from "../orders.module.css";

type Props = {
  item: RefundQueueItem;
  onBusy: (b: boolean) => void;
  onCancel: () => void;
  onDone: (r: MarkRefundFailedResult) => void;
};

export function MarkRefundFailedForm({ item, onBusy, onCancel, onDone }: Props) {
  const id = useId();
  const [reason, setReason] = useState("");
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  const sub = useSubmit(onBusy);

  useEffect(() => {
    reasonRef.current?.focus();
  }, []);

  const submit = () => {
    if (sub.locked()) return;
    sub.setError(null);
    void sub.run(() => markRefundFailed(item.id, { reason: reason.trim() }), onDone);
  };

  return (
    <form
      className={`${s.pane} mark-refund-failed`}
      noValidate
      aria-labelledby={`${id}-q`}
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <FormHead
        id={`${id}-q`}
        icon="error"
        tone="warn"
        question={REFUND_Q_MSG.markFailedQuestion}
        sub={
          <>
            {item.customer_name || "—"}
            {item.order_code ? ` · ${item.order_code}` : ` · ${REFUND_Q_MSG.noOrder}`}
          </>
        }
      />

      <NoteField
        id={`${id}-reason`}
        label={REFUND_Q_MSG.markFailedReasonLabel}
        value={reason}
        onChange={setReason}
        help={REFUND_Q_MSG.markFailedReasonHelp}
        disabled={sub.busy}
        inputRef={reasonRef}
      />

      <Consequences items={[{ icon: "replay", text: REFUND_Q_MSG.markFailedConsequence1 }]} />

      <FormFooter
        error={sub.error}
        errRef={sub.errRef}
        busy={sub.busy}
        onCancel={onCancel}
        submitIcon="error"
        submitLabel={REFUND_Q_MSG.markFailedSubmit}
        busyLabel={REFUND_Q_MSG.markingFailed}
      />
    </form>
  );
}
