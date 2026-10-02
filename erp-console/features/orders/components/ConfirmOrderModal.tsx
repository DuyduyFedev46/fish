"use client";

// F2e — "Xác nhận đơn đã đủ tiền" (ED-11): khách đã bù phần thiếu ngoài hệ thống, Chủ chốt đơn. BE từ chối nếu tổng tiền
// đã nhận chưa đủ (câu lỗi nguyên văn). 409 → ConflictBanner ở màn mở hộp.

import { useState } from "react";
import { vnd } from "@/shared/lib/format";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { useSubmit, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { resolvePayment } from "../api";
import { ORDERS_MSG as M } from "../messages";
import type { PaymentQueueItem, ResolveResult } from "../types";
import { ActionModal } from "./ActionModal";

type Props = {
  payment: PaymentQueueItem;
  onClose: () => void;
  onDone: (r: ResolveResult) => void;
  onConflict: (c: SubmitConflict) => void;
};

export function ConfirmOrderModal({ payment, onClose, onDone, onConflict }: Props) {
  const [note, setNote] = useState("");
  const order = payment.order;
  const missing = order ? Math.max(0, Number(order.total_amount) - Number(order.paid_total)) : 0;
  const sub = useSubmit(() => resolvePayment(payment.id, { action: "CONFIRM_ORDER", note: note.trim() }), { onSuccess: onDone });
  return (
    <ActionModal
      title={M.confirmOrderTitle}
      onClose={onClose}
      submitting={sub.submitting}
      failed={sub.failed}
      error={sub.error}
      conflict={sub.conflict}
      onConflict={onConflict}
      submitLabel={M.confirmOrderSubmit(order?.total_amount ?? payment.amount)}
      busyLabel={M.confirming}
      onSubmit={() => void sub.submit()}
    >
      {order && (
        <SummaryBlock
          rows={[
            { label: M.rowOrder, value: order.code, mono: true },
            { label: M.fieldOrderTotal, value: vnd(order.total_amount), num: true },
            { label: M.fieldOrderPaid, value: vnd(order.paid_total), num: true },
            { label: M.fieldOrderMissing, value: vnd(missing), num: true, strong: true },
          ]}
        />
      )}
      {missing > 0 && <FormAlert kind="warn">{M.confirmOrderShort(String(missing))}</FormAlert>}
      <Field as="textarea" label={M.attachNoteLabel} name="note" value={note} onChange={setNote} maxLength={300} disabled={sub.submitting} autoFocus />
      <FormAlert kind="warn">{M.confirmOrderAlert}</FormAlert>
    </ActionModal>
  );
}
