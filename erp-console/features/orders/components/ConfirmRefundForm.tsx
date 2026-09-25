"use client";

// S16 — Chủ xác nhận đã chuyển khoản hoàn cho một phiếu Chờ hoàn (BR-HT-03, BR-PQ-05). Bắt buộc mã giao dịch chuyển
// khoản hoàn (khác mã GD tiền vào ban đầu); thiếu → 400 BR-HT-03 nguyên văn từ BE (FE cũng chặn trước tại ô).
// Phiếu REFUNDED là chốt — không đổi lại bằng nút này (đổi thì phải nhờ BE sửa tay).

import { useEffect, useId, useRef, useState } from "react";
import { Icon } from "@/shared/ui/Icon";
import { TXN_MAX_LENGTH } from "../amount";
import { confirmRefund } from "../api";
import { REFUND_Q_MSG } from "../messages";
import type { ConfirmRefundResult, RefundQueueItem } from "../types";
import { Consequences, FormFooter, FormHead, useSubmit } from "./QueueFormParts";
import s from "../orders.module.css";

type Props = {
  item: RefundQueueItem;
  onBusy: (b: boolean) => void;
  onCancel: () => void;
  onDone: (r: ConfirmRefundResult) => void;
};

export function ConfirmRefundForm({ item, onBusy, onCancel, onDone }: Props) {
  const id = useId();
  const [txn, setTxn] = useState("");
  const [missing, setMissing] = useState(false);
  const txnRef = useRef<HTMLInputElement>(null);
  const sub = useSubmit(onBusy);

  useEffect(() => {
    txnRef.current?.focus();
  }, []);

  const submit = () => {
    if (sub.locked()) return;
    sub.setError(null);
    const t = txn.trim();
    if (t !== txn) setTxn(t);
    if (!t) {
      setMissing(true);
      txnRef.current?.focus();
      return;
    }
    void sub.run(() => confirmRefund(item.id, { bank_txn_ref: t.slice(0, TXN_MAX_LENGTH) }), onDone);
  };

  return (
    <form
      className={`${s.pane} confirm-refund`}
      noValidate
      aria-labelledby={`${id}-q`}
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <FormHead
        id={`${id}-q`}
        icon="task_alt"
        question={REFUND_Q_MSG.confirmTitle(item.amount)}
        sub={
          <>
            {item.customer_name || "—"}
            {item.order_code ? ` · ${item.order_code}` : ` · ${REFUND_Q_MSG.noOrder}`}
          </>
        }
      />

      <div className="field">
        <label htmlFor={`${id}-txn`}>
          {REFUND_Q_MSG.confirmTxnLabel}
          <span className={s.req} aria-hidden="true">
            *
          </span>
        </label>
        <input
          ref={txnRef}
          id={`${id}-txn`}
          name="bank_txn_ref"
          className="mono-input"
          value={txn}
          onChange={(e) => {
            setTxn(e.target.value);
            if (missing) setMissing(false);
          }}
          onBlur={() => setTxn((v) => v.trim())}
          maxLength={TXN_MAX_LENGTH}
          placeholder={REFUND_Q_MSG.confirmTxnPlaceholder}
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          required
          disabled={sub.busy}
          data-autofocus
          aria-invalid={missing || undefined}
          aria-describedby={`${missing ? `${id}-txn-err ` : ""}${id}-txn-help`}
        />
        {missing && (
          <p className="field-err" id={`${id}-txn-err`}>
            <Icon name="error" />
            {REFUND_Q_MSG.confirmTxnMissing}
          </p>
        )}
        <p className="help" id={`${id}-txn-help`}>
          {REFUND_Q_MSG.confirmTxnHelp}
        </p>
      </div>

      <Consequences
        items={[
          { icon: "block", text: REFUND_Q_MSG.confirmConsequence1 },
          { icon: "link", text: REFUND_Q_MSG.confirmConsequence2 },
          { icon: "history", text: "Nhật ký ghi tên bạn là người xác nhận, kèm giờ." },
        ]}
      />

      <FormFooter
        error={sub.error}
        errRef={sub.errRef}
        busy={sub.busy}
        onCancel={onCancel}
        submitIcon="task_alt"
        submitLabel={REFUND_Q_MSG.confirmSubmit}
        busyLabel={REFUND_Q_MSG.confirming}
      />
    </form>
  );
}
