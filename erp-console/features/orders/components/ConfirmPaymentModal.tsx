"use client";

// F2a — "Xác nhận đã nhận tiền" (ED-10-AC1). Mã giao dịch + số tiền (điền sẵn tổng đơn); chặn trước tại ô: âm, 0, chữ,
// quá 12 chữ số → báo tại ô, KHÔNG gửi. BE vẫn là lớp chặn chính (BR-TT-08, 403 cho Quản lý). Kết quả PAID / UNDERPAID /
// ORPHAN / duplicate do BE quyết, màn mở hộp chỉ báo lại.

import { useState } from "react";
import { vnd } from "@/shared/lib/format";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { useSubmit, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { AMOUNT_MSG, TXN_MAX_LENGTH, digits, formatAmountInput, parseAmount } from "../amount";
import { confirmPayment } from "../api";
import { ORDERS_MSG as M } from "../messages";
import type { ConfirmPaymentResult } from "../types";
import { ActionModal } from "./ActionModal";

type Props = {
  order: { id: number; code: string; status: string; total_amount: string };
  onClose: () => void;
  onDone: (r: ConfirmPaymentResult) => void;
  onConflict: (c: SubmitConflict) => void;
};

export function ConfirmPaymentModal({ order, onClose, onDone, onConflict }: Props) {
  const total = digits(order.total_amount);
  const [txn, setTxn] = useState("");
  const [amountRaw, setAmountRaw] = useState(formatAmountInput(total));
  const [errs, setErrs] = useState<{ txn?: string; amount?: string }>({});
  const check = parseAmount(amountRaw);
  const amount = check.value ?? "";
  const diff = amount && total ? Number(amount) - Number(total) : 0;
  const lateMoney = order.status === "AUTO_CANCELLED";

  const sub = useSubmit(() => confirmPayment(order.id, { bank_txn_id: txn.trim().slice(0, TXN_MAX_LENGTH), amount }), { onSuccess: onDone });

  const submit = () => {
    const next: { txn?: string; amount?: string } = {};
    if (!txn.trim()) next.txn = M.txnMissing;
    if (check.problem) next.amount = AMOUNT_MSG[check.problem];
    setErrs(next);
    if (next.txn || next.amount) return;
    void sub.submit();
  };

  return (
    <ActionModal
      title={M.confirmTitle}
      onClose={onClose}
      submitting={sub.submitting}
      failed={sub.failed}
      error={sub.error}
      conflict={sub.conflict}
      onConflict={onConflict}
      submitLabel={amount ? M.confirmSubmit(amount) : M.confirmSubmitNoAmount}
      busyLabel={M.confirming}
      onSubmit={submit}
    >
      {lateMoney && <FormAlert kind="warn">{M.alertAutoCancelled}</FormAlert>}
      <SummaryBlock
        rows={[
          { label: M.rowOrder, value: order.code, mono: true },
          { label: M.rowOrderTotal, value: vnd(total), num: true, strong: true },
        ]}
      />
      <Field
        label={M.txnLabel}
        required
        name="bank_txn_id"
        value={txn}
        onChange={(v) => {
          setTxn(v);
          if (errs.txn) setErrs((e) => ({ ...e, txn: undefined }));
        }}
        placeholder={M.txnPlaceholder}
        maxLength={TXN_MAX_LENGTH}
        error={errs.txn ?? sub.fieldErrors.bank_txn_id}
        disabled={sub.submitting}
        autoFocus
      />
      <Field
        label={M.amountLabel}
        required
        name="amount"
        type="money"
        unit={M.currencyUnit}
        value={amountRaw}
        onChange={(v) => {
          setAmountRaw(v);
          if (errs.amount) setErrs((e) => ({ ...e, amount: undefined }));
        }}
        error={errs.amount ?? sub.fieldErrors.amount}
        disabled={sub.submitting}
      />
      {diff < 0 && <FormAlert kind="warn">{M.amountLess(String(-diff))}</FormAlert>}
      {diff > 0 && <FormAlert kind="warn">{M.amountMore(String(diff))}</FormAlert>}
    </ActionModal>
  );
}
