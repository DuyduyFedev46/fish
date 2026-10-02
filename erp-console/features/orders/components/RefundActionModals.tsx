"use client";

// F2f / F2g / chuyển lại — ba thao tác của Chủ trên phiếu hoàn (cần sales.confirm_refund; Quản lý không có nút, gọi BE → 403).
// Phiếu hoàn không có bản "hoàn tác": mọi thao tác ở đây là một chiều, nên hộp nói rõ hậu quả trước khi gửi.

import { useState } from "react";
import { vnd } from "@/shared/lib/format";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { useSubmit, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { confirmRefund, markRefundFailed, retryRefund } from "../api";
import { TXN_MAX_LENGTH } from "../amount";
import { ORDERS_MSG as M } from "../messages";
import type { RefundQueueItem } from "../types";
import { ActionModal } from "./ActionModal";

type CommonProps = {
  refund: Pick<RefundQueueItem, "id" | "amount" | "order_code" | "source_bank_txn_id">;
  onClose: () => void;
  onDone: () => void;
  onConflict: (c: SubmitConflict) => void;
};

function Summary({ refund }: Pick<CommonProps, "refund">) {
  const rows = [
    ...(refund.order_code ? [{ label: M.rowRefundOrder, value: refund.order_code, mono: true }] : []),
    ...(refund.source_bank_txn_id ? [{ label: M.rowSourceTxn, value: refund.source_bank_txn_id, mono: true }] : []),
    { label: M.rowRefundAmount, value: vnd(refund.amount), num: true, strong: true },
  ];
  return <SummaryBlock rows={rows} />;
}

/** F2f — "Xác nhận đã hoàn tiền": Chủ đã chuyển khoản trả khách, nhập mã giao dịch hoàn để đối chiếu sao kê. */
export function ConfirmRefundModal({ refund, onClose, onDone, onConflict }: CommonProps) {
  const [ref, setRef] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const sub = useSubmit(() => confirmRefund(refund.id, { bank_txn_ref: ref.trim().slice(0, TXN_MAX_LENGTH) }), { onSuccess: onDone });
  return (
    <ActionModal
      title={M.refundConfirmTitle}
      onClose={onClose}
      submitting={sub.submitting}
      failed={sub.failed}
      error={sub.error}
      conflict={sub.conflict}
      onConflict={onConflict}
      submitLabel={M.refundConfirmSubmit(refund.amount)}
      busyLabel={M.confirming}
      onSubmit={() => {
        if (!ref.trim()) {
          setErr(M.refundConfirmTxnMissing);
          return;
        }
        void sub.submit();
      }}
    >
      <Summary refund={refund} />
      <Field
        label={M.refundConfirmTxnLabel}
        required
        name="bank_txn_ref"
        value={ref}
        onChange={(v) => {
          setRef(v);
          setErr(null);
        }}
        placeholder={M.refundConfirmTxnPlaceholder}
        maxLength={TXN_MAX_LENGTH}
        error={err ?? sub.fieldErrors.bank_txn_ref}
        disabled={sub.submitting}
        autoFocus
      />
      <FormAlert kind="warn">{M.refundConfirmAlert}</FormAlert>
    </ActionModal>
  );
}

/** F2g — "Báo chuyển thất bại": chuyển khoản không thành; lý do ghi vào phiếu (không bắt buộc). */
export function MarkRefundFailedModal({ refund, onClose, onDone, onConflict }: CommonProps) {
  const [reason, setReason] = useState("");
  const sub = useSubmit(() => markRefundFailed(refund.id, { reason: reason.trim() }), { onSuccess: onDone });
  return (
    <ActionModal
      title={M.markFailedTitle}
      onClose={onClose}
      submitting={sub.submitting}
      failed={sub.failed}
      error={sub.error}
      conflict={sub.conflict}
      onConflict={onConflict}
      submitLabel={M.markFailedSubmit}
      busyLabel="Đang ghi nhận…"
      danger
      onSubmit={() => void sub.submit()}
    >
      <Summary refund={refund} />
      <Field as="textarea" label={M.markFailedReasonLabel} name="reason" value={reason} onChange={setReason} maxLength={300} disabled={sub.submitting} autoFocus />
      <FormAlert kind="warn">{M.markFailedAlert}</FormAlert>
    </ActionModal>
  );
}

/** "Chuyển lại": phiếu Thất bại quay về Chờ hoàn. */
export function RetryRefundModal({ refund, onClose, onDone, onConflict }: CommonProps) {
  const sub = useSubmit(() => retryRefund(refund.id), { onSuccess: onDone });
  return (
    <ActionModal
      title={M.retryTitle}
      onClose={onClose}
      submitting={sub.submitting}
      failed={sub.failed}
      error={sub.error}
      conflict={sub.conflict}
      onConflict={onConflict}
      submitLabel={M.retrySubmit(refund.amount)}
      busyLabel="Đang chuyển lại…"
      size="sm"
      onSubmit={() => void sub.submit()}
    >
      <Summary refund={refund} />
      <FormAlert kind="warn">{M.retryAlert}</FormAlert>
    </ActionModal>
  );
}
