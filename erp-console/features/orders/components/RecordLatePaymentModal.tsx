"use client";

// #15 — "Ghi tiền về muộn" (BR-TT-18): Chủ ghi tay khoản tiền đã vào tài khoản mà webhook không báo (E-05). Bốn ô: mã giao dịch,
// số tiền, giờ nhận theo sao kê (giờ Việt Nam), mã đơn (tuỳ chọn). KHÔNG có ô ghi chú (thu tối thiểu, bất biến 9). Chặn tại ô trước khi
// gửi; BE là lớp chặn chính, lỗi 400 hiện dưới đúng ô theo khoá. 409 LATE_PAYMENT_POSSIBLE_DUPLICATE → hộp vàng nêu khoản giống + ô tick
// "Tôi đã kiểm, đây không phải trùng" rồi gửi lại kèm cờ. Không lưu giá trị form vào URL/localStorage, không ghi log.

import { useState } from "react";
import Link from "next/link";
import { dateTime } from "@/shared/lib/format";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { useSubmit } from "@/shared/ui/form/useSubmit";
import { AMOUNT_MSG, TXN_MAX_LENGTH, parseAmount } from "../amount";
import { recordLatePayment } from "../api";
import {
  bookedOrderIdOf,
  buildLateBody,
  checkReceivedAt,
  checkTxnId,
  existingPaymentIdOf,
  nowForInput,
  similarOf,
} from "../latePayment";
import { ORDERS_MSG as M } from "../messages";
import type { RecordLatePaymentResult, SimilarPayment } from "../types";
import s from "../orders.module.css";
import { ActionModal } from "./ActionModal";

type Props = {
  onClose: () => void;
  onDone: (r: RecordLatePaymentResult) => void;
};

type Errs = { txn?: string; amount?: string; receivedAt?: string };

const TXN_MSG = { missing: M.lateTxnMissing, tooLong: M.lateTxnTooLong, badChars: M.lateTxnBadChars } as const;
const AT_MSG = { missing: M.lateReceivedMissing, future: M.lateReceivedFuture } as const;

export function RecordLatePaymentModal({ onClose, onDone }: Props) {
  const [txn, setTxn] = useState("");
  const [amountRaw, setAmountRaw] = useState("");
  const [receivedAt, setReceivedAt] = useState(nowForInput);
  const [orderCode, setOrderCode] = useState("");
  const [errs, setErrs] = useState<Errs>({});
  // Phản hồi riêng của BE cần hiện ngoài lỗi ô: khoản giống (409), đơn Giữ chỗ (link sang đơn), khoản trùng mã (link mở).
  const [similar, setSimilar] = useState<SimilarPayment | null>(null);
  const [ack, setAck] = useState(false);
  const [bookedOrderId, setBookedOrderId] = useState<number | null>(null);
  const [existingId, setExistingId] = useState<number | null>(null);
  const check = parseAmount(amountRaw);
  const amount = check.value ?? "";

  const sub = useSubmit(
    async () => {
      try {
        return await recordLatePayment(buildLateBody({ txn, amount, receivedAt, orderCode, ack }));
      } catch (err) {
        setSimilar(similarOf(err));
        setBookedOrderId(bookedOrderIdOf(err));
        setExistingId(existingPaymentIdOf(err));
        throw err;
      }
    },
    { onSuccess: onDone },
  );

  /** Đổi số tiền / giờ / đơn thì khoản "giống" không còn đúng nữa: bỏ hộp cảnh báo và ô tick, gửi lại sẽ hỏi lại BE. */
  const resetSimilar = () => {
    setSimilar(null);
    setAck(false);
  };

  const submit = () => {
    const next: Errs = {};
    const tp = checkTxnId(txn);
    if (tp) next.txn = TXN_MSG[tp];
    if (check.problem) next.amount = AMOUNT_MSG[check.problem];
    const ap = checkReceivedAt(receivedAt);
    if (ap) next.receivedAt = AT_MSG[ap];
    setErrs(next);
    if (next.txn || next.amount || next.receivedAt) return;
    void sub.submit();
  };

  // 409 nghi trùng: hộp vàng thay cho alert đỏ; nút chính vẫn nói rõ việc, không đổi thành "Thử lại".
  const needAck = similar != null;
  // Lỗi 400 có khoá ô đã hiện dưới đúng ô: không lặp lại thành alert đỏ ở đầu form.
  const hasFieldError = Object.keys(sub.fieldErrors).length > 0;
  return (
    <ActionModal
      title={M.lateTitle}
      onClose={onClose}
      submitting={sub.submitting}
      failed={sub.failed && !needAck}
      error={needAck || hasFieldError ? null : sub.error}
      submitLabel={amount ? M.lateSubmit(amount) : M.lateSubmitNoAmount}
      busyLabel={M.lateSubmitting}
      disabled={needAck && !ack}
      onSubmit={submit}
    >
      <p className="muted" style={{ margin: 0 }}>
        {M.lateIntro}
      </p>
      <Field
        label={M.lateTxnLabel}
        required
        name="bank_txn_id"
        value={txn}
        onChange={(v) => {
          setTxn(v);
          setExistingId(null);
          if (errs.txn) setErrs((e) => ({ ...e, txn: undefined }));
        }}
        placeholder={M.lateTxnPlaceholder}
        maxLength={TXN_MAX_LENGTH * 2}
        error={errs.txn ?? sub.fieldErrors.bank_txn_id}
        disabled={sub.submitting}
        autoFocus
      />
      {existingId != null && !errs.txn && (
        <Link href={`/orders/payments/detail/?id=${existingId}`} className="inline-link">
          {M.lateOpenExisting}
        </Link>
      )}
      <Field
        label={M.lateAmountLabel}
        required
        name="amount"
        type="money"
        unit={M.currencyUnit}
        value={amountRaw}
        onChange={(v) => {
          setAmountRaw(v);
          resetSimilar();
          if (errs.amount) setErrs((e) => ({ ...e, amount: undefined }));
        }}
        error={errs.amount ?? sub.fieldErrors.amount}
        disabled={sub.submitting}
      />
      <Field
        label={M.lateReceivedLabel}
        required
        name="received_at"
        type="datetime-local"
        value={receivedAt}
        onChange={(v) => {
          setReceivedAt(v);
          resetSimilar();
          if (errs.receivedAt) setErrs((e) => ({ ...e, receivedAt: undefined }));
        }}
        error={errs.receivedAt ?? sub.fieldErrors.received_at}
        disabled={sub.submitting}
      />
      <Field
        label={M.lateOrderLabel}
        name="order_code"
        value={orderCode}
        onChange={(v) => {
          setOrderCode(v);
          setBookedOrderId(null);
          resetSimilar();
        }}
        placeholder={M.lateOrderPlaceholder}
        maxLength={40}
        error={sub.fieldErrors.order_code}
        disabled={sub.submitting}
      />
      {bookedOrderId != null && (
        <Link href={`/orders/detail/?id=${bookedOrderId}`} className="inline-link">
          {M.lateOpenOrder}
        </Link>
      )}
      {similar && (
        <div className={s.dupBox} data-similar-box>
          <FormAlert kind="warn">
            <strong>{M.lateSimilarTitle}.</strong> {M.lateSimilar(similar.bank_txn_id, similar.received_at ? dateTime(similar.received_at) : "")}
          </FormAlert>
          <Link href={`/orders/payments/detail/?id=${similar.id}`} className="inline-link">
            {M.lateSimilarOpen}
          </Link>
          <label className="check-row">
            <input type="checkbox" name="acknowledge_possible_duplicate" checked={ack} disabled={sub.submitting} onChange={(e) => setAck(e.target.checked)} />
            <span>{M.lateAckLabel}</span>
          </label>
        </div>
      )}
    </ActionModal>
  );
}
