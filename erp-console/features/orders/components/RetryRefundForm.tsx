"use client";

// S16 — Thử lại chuyển khoản cho một phiếu Thất bại (BR-HT-09): quay lại Chờ hoàn. Không nhập gì thêm — vẫn qua một
// bước xác nhận (không bấm-là-xong) để tránh bấm nhầm, và để chống bấm đúp giống hai thao tác kia. Số còn hoàn được
// có thể đã bị khoản khác lấp đầy trong lúc chờ → BE trả BR-HT-04 nguyên văn (S16-AC6).

import { retryRefund } from "../api";
import { REFUND_Q_MSG } from "../messages";
import type { RefundQueueItem, RetryRefundResult } from "../types";
import { Consequences, FormFooter, FormHead, useSubmit } from "./QueueFormParts";
import s from "../orders.module.css";

type Props = {
  item: RefundQueueItem;
  onBusy: (b: boolean) => void;
  onCancel: () => void;
  onDone: (r: RetryRefundResult) => void;
};

export function RetryRefundForm({ item, onBusy, onCancel, onDone }: Props) {
  const sub = useSubmit(onBusy);

  const submit = () => {
    if (sub.locked()) return;
    sub.setError(null);
    void sub.run(() => retryRefund(item.id), onDone);
  };

  return (
    <form
      className={`${s.pane} retry-refund`}
      noValidate
      aria-labelledby="retry-q"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <FormHead
        id="retry-q"
        icon="replay"
        question={REFUND_Q_MSG.retryQuestion(item.amount)}
        sub={
          <>
            {item.customer_name || "—"}
            {item.order_code ? ` · ${item.order_code}` : ` · ${REFUND_Q_MSG.noOrder}`}
            {item.failure_reason ? ` · ${item.failure_reason}` : ""}
          </>
        }
      />

      <Consequences items={[{ icon: "schedule", text: REFUND_Q_MSG.retryConsequence1 }]} />

      <FormFooter
        error={sub.error}
        errRef={sub.errRef}
        busy={sub.busy}
        onCancel={onCancel}
        submitIcon="replay"
        submitLabel={REFUND_Q_MSG.retrySubmit}
        busyLabel={REFUND_Q_MSG.retrying}
      />
    </form>
  );
}
