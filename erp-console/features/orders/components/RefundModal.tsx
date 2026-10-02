"use client";

// F2c — "Lập phiếu hoàn" (ED-10-AC3), dùng cho HAI nguồn tiền (đúng một trong hai, BR-HT-01): khoản tiền không có hoá đơn
// (gửi `payment_transaction`) hoặc đơn có hoá đơn (gửi `sales_invoice` + `is_partial`). Số hoàn vượt "Còn hoàn được" thì báo
// "Nhập tối đa <số> đ." tại ô và KHOÁ nút chính (BE vẫn là lớp chặn thật, BR-HT-04). `request_id` sinh một lần mỗi lần mở
// hộp: bấm đúp / gửi lại sau lỗi mạng không tạo phiếu thứ hai. Phiếu tạo ra ở trạng thái Chờ hoàn (tiền CHƯA rời túi).

import { useRef, useState } from "react";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock, type SummaryRow } from "@/shared/ui/form/SummaryBlock";
import { useSubmit, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { AMOUNT_MSG, digits, formatAmountInput, parseAmount } from "../amount";
import { createRefund } from "../api";
import { ORDERS_MSG as M } from "../messages";
import { newRequestId, overRefundMax } from "../refund";
import type { CreateRefundInput, CreateRefundResult } from "../types";
import { ActionModal } from "./ActionModal";

/** Nguồn tiền của phiếu hoàn. `invoiceTotal` chỉ dùng để tính `is_partial`. */
export type RefundTarget = { kind: "payment"; id: number } | { kind: "invoice"; id: number; invoiceTotal: string };

type Props = {
  target: RefundTarget;
  /** Số còn hoàn được — điền sẵn ô số tiền; BE vẫn quyết. */
  refundableMax: string;
  reasonDefault: string;
  /** Các dòng tóm tắt ngữ cảnh (đơn / khoản tiền). */
  summary: SummaryRow[];
  onClose: () => void;
  onDone: (r: CreateRefundResult) => void;
  onConflict: (c: SubmitConflict) => void;
};

export function RefundModal({ target, refundableMax, reasonDefault, summary, onClose, onDone, onConflict }: Props) {
  const max = digits(refundableMax);
  const [amountRaw, setAmountRaw] = useState(formatAmountInput(max));
  const [reason, setReason] = useState(reasonDefault);
  const [errs, setErrs] = useState<{ amount?: string; reason?: string }>({});
  const requestId = useRef("");
  if (!requestId.current) requestId.current = newRequestId();
  const check = parseAmount(amountRaw);
  const amount = check.value ?? "";
  const over = overRefundMax(amount, max);

  const sub = useSubmit(
    () => {
      const base = { amount, reason: reason.trim(), request_id: requestId.current };
      const body: CreateRefundInput =
        target.kind === "payment"
          ? { payment_transaction: target.id, ...base }
          : { sales_invoice: target.id, is_partial: Number(amount) < Number(target.invoiceTotal), ...base };
      return createRefund(body);
    },
    { onSuccess: onDone },
  );

  const submit = () => {
    const e: { amount?: string; reason?: string } = {};
    if (check.problem) e.amount = AMOUNT_MSG[check.problem];
    if (!reason.trim()) e.reason = M.refundReasonMissing;
    setErrs(e);
    if (e.amount || e.reason) return;
    void sub.submit();
  };

  return (
    <ActionModal
      title={M.refundTitle}
      onClose={onClose}
      submitting={sub.submitting}
      failed={sub.failed}
      error={sub.error}
      conflict={sub.conflict}
      onConflict={onConflict}
      submitLabel={amount ? M.refundSubmit(amount) : M.refundSubmitNoAmount}
      busyLabel={M.refunding}
      disabled={over}
      onSubmit={submit}
    >
      {/* Dòng "Còn hoàn được" do màn gọi truyền vào `summary` (một dòng duy nhất, UI-RULES §6). */}
      <SummaryBlock rows={summary} />
      <Field
        label={M.refundAmountLabel}
        required
        name="amount"
        type="money"
        unit={M.currencyUnit}
        value={amountRaw}
        onChange={(v) => {
          setAmountRaw(v);
          if (errs.amount) setErrs((e) => ({ ...e, amount: undefined }));
        }}
        error={over ? M.refundAmountMax(max) : (errs.amount ?? sub.fieldErrors.amount)}
        disabled={sub.submitting}
        autoFocus
      />
      <Field
        as="textarea"
        label={M.refundReasonLabel}
        required
        name="reason"
        value={reason}
        onChange={(v) => {
          setReason(v);
          if (errs.reason) setErrs((e) => ({ ...e, reason: undefined }));
        }}
        maxLength={300}
        error={errs.reason ?? sub.fieldErrors.reason}
        disabled={sub.submitting}
      />
      <FormAlert kind="warn">{M.refundAlert}</FormAlert>
    </ActionModal>
  );
}
