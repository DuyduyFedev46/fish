"use client";

// S12 — Xác nhận đơn khi khách đã chuyển bù (CONFIRM_ORDER, S12-AC3). Nêu mã đơn, tổng đơn, số đã nhận; nếu theo số liệu
// hiện có đơn còn thiếu thì nhắc trước (chỉ nhắc — BE mới quyết đủ/thiếu, trả BR-TT-09 nguyên văn nếu chưa đủ, S12-AC4;
// đơn đã tự huỷ → BR-TT-05, S12-AC5). Ghi chú không bắt buộc (vd mã GD chuyển bù). Gửi một lần, lỗi BE hiện nguyên văn.

import { useEffect, useId, useRef, useState } from "react";
import { vnd } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { resolvePayment } from "../api";
import { QUEUE_MSG } from "../messages";
import type { PaymentQueueItem, QueueOrderRef, ResolveResult } from "../types";
import { Consequences, FormFooter, FormHead, NoteField, useSubmit } from "./QueueFormParts";
import s from "../orders.module.css";

type Props = {
  item: PaymentQueueItem;
  order: QueueOrderRef;
  onBusy: (b: boolean) => void;
  onCancel: () => void;
  onDone: (r: ResolveResult) => void;
};

export function ConfirmOrderForm({ item, order, onBusy, onCancel, onDone }: Props) {
  const id = useId();
  const [note, setNote] = useState("");
  const noteRef = useRef<HTMLTextAreaElement>(null);
  const sub = useSubmit(onBusy);
  const missing = Number(order.total_amount) - Number(order.paid_total);

  useEffect(() => {
    noteRef.current?.focus();
  }, []);

  return (
    <form
      className={`${s.pane} confirm-order`}
      noValidate
      aria-labelledby={`${id}-q`}
      onSubmit={(e) => {
        e.preventDefault();
        if (sub.locked()) return;
        void sub.run(() => resolvePayment(item.id, { action: "CONFIRM_ORDER", note: note.trim() }), onDone);
      }}
    >
      <FormHead
        id={`${id}-q`}
        icon="check_circle"
        question={QUEUE_MSG.confirmQuestion(order.code)}
        sub={
          <>
            {order.customer_name ? `${order.customer_name} · ` : ""}
            {QUEUE_MSG.orderTotal} {vnd(order.total_amount)} · {QUEUE_MSG.orderPaid} {vnd(order.paid_total)}
          </>
        }
      />

      {missing > 0 && (
        <div className="alert-box warn confirm-short" role="note">
          <Icon name="info" />
          <span>{QUEUE_MSG.confirmShort(String(missing))}</span>
        </div>
      )}

      <NoteField
        id={`${id}-note`}
        label={QUEUE_MSG.noteLabel}
        value={note}
        onChange={setNote}
        help={QUEUE_MSG.noteHelpConfirm}
        disabled={sub.busy}
        inputRef={noteRef}
      />

      <Consequences
        items={[
          { icon: "local_shipping", text: QUEUE_MSG.confirmConsequence1 },
          { icon: "done_all", text: QUEUE_MSG.confirmConsequence2 },
          { icon: "block", text: QUEUE_MSG.consequenceFinal },
          { icon: "history", text: QUEUE_MSG.consequenceAudit },
        ]}
      />

      <FormFooter
        error={sub.error}
        errRef={sub.errRef}
        busy={sub.busy}
        onCancel={onCancel}
        submitIcon="check"
        submitLabel={QUEUE_MSG.confirmSubmit}
        busyLabel={QUEUE_MSG.confirming}
      />
    </form>
  );
}
