"use client";

// Lập phiếu hoàn — dùng chung cho HAI nguồn tiền (đúng một trong hai, BR-HT-01):
//  - S13: khoản tiền KHÔNG có hoá đơn (về sau khi đơn tự huỷ, chuyển thiếu mà khách không bù, không khớp đơn, chuyển
//    thừa — P5) → gửi `payment_transaction`.
//  - S15: đơn CÓ hoá đơn (huỷ đơn đã thanh toán, hoàn toàn phần/một phần) → gửi `sales_invoice` + `is_partial`.
// Số tiền mặc định = số còn được hoàn (`max` do nơi gọi tính — BE mới là lớp chặn thật, BR-HT-04), đọc bằng parseAmount
// dùng chung với S11 — sai thì báo tại ô, không gửi. Vượt số còn hoàn thì nhắc tại ô nhưng vẫn cho gửi: BE trả lỗi nguyên
// văn (S13-AC3). Lý do bắt buộc (ghi vào phiếu + nhật ký), điền sẵn theo nơi gọi. `request_id` sinh một lần mỗi lần mở
// form: bấm đúp / gửi lại sau lỗi mạng không tạo phiếu thứ hai. Phiếu tạo ra ở trạng thái Chờ hoàn — tiền CHƯA rời túi
// (xác nhận ở S16).

import { useEffect, useId, useRef, useState } from "react";
import { vnd } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { AMOUNT_MSG, digits, parseAmount, type AmountProblem } from "../amount";
import { createRefund } from "../api";
import { QUEUE_MSG } from "../messages";
import type { CreateRefundInput, CreateRefundResult } from "../types";
import { Consequences, FormFooter, FormHead, NoteField, useSubmit } from "./QueueFormParts";
import s from "../orders.module.css";

/** Nguồn tiền của phiếu hoàn (đúng một trong hai — BR-HT-01). `invoiceTotal` chỉ dùng để tính `is_partial`. */
export type RefundTarget = { kind: "payment"; id: number } | { kind: "invoice"; id: number; invoiceTotal: string };

type Props = {
  target: RefundTarget;
  /** Số tiền tối đa còn được hoàn — mặc định điền sẵn ô số tiền; BE vẫn quyết (BR-HT-04). */
  refundableMax: string;
  reasonDefault: string;
  /** Dòng phụ dưới câu hỏi (mã GD/khoản hoặc mã đơn/khách). */
  subLabel: React.ReactNode;
  onBusy: (b: boolean) => void;
  onCancel: () => void;
  onDone: (r: CreateRefundResult) => void;
};

/**
 * Mã chống tạo trùng — BE đòi UUID ("request_id phải là UUID."). crypto.randomUUID chỉ có ở ngữ cảnh an toàn (https,
 * localhost); không có thì dựng UUID v4 từ crypto.getRandomValues (hoặc Math.random ở máy rất cũ).
 */
function newRequestId(): string {
  const c = typeof crypto !== "undefined" ? (crypto as Crypto & { randomUUID?: () => string }) : undefined;
  if (c?.randomUUID) return c.randomUUID();
  const b = new Uint8Array(16);
  if (c?.getRandomValues) c.getRandomValues(b);
  else for (let i = 0; i < 16; i++) b[i] = Math.floor(Math.random() * 256);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

export function RefundForm({ target, refundableMax, reasonDefault, subLabel, onBusy, onCancel, onDone }: Props) {
  const id = useId();
  const max = digits(refundableMax);
  const [amountRaw, setAmountRaw] = useState(max);
  const [reason, setReason] = useState(reasonDefault);
  const [amountErr, setAmountErr] = useState<AmountProblem | null>(null);
  const [reasonErr, setReasonErr] = useState(false);
  const requestId = useRef<string>("");
  if (!requestId.current) requestId.current = newRequestId();
  const amountRef = useRef<HTMLInputElement>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  const sub = useSubmit(onBusy);
  const check = parseAmount(amountRaw);
  const amount = check.value ?? "";
  const over = !!amount && !!max && Number(amount) > Number(max);

  useEffect(() => {
    amountRef.current?.focus();
    amountRef.current?.select();
  }, []);

  const submit = () => {
    if (sub.locked()) return;
    sub.setError(null);
    if (check.problem) {
      setAmountErr(check.problem);
      amountRef.current?.focus();
      return;
    }
    const r = reason.trim();
    if (!r) {
      setReasonErr(true);
      reasonRef.current?.focus();
      return;
    }
    const body: CreateRefundInput =
      target.kind === "payment"
        ? { payment_transaction: target.id, amount: check.value, reason: r, request_id: requestId.current }
        : {
            sales_invoice: target.id,
            amount: check.value,
            is_partial: Number(check.value) < Number(target.invoiceTotal),
            reason: r,
            request_id: requestId.current,
          };
    void sub.run(() => createRefund(body), onDone);
  };

  return (
    <form
      className={`${s.pane} refund-form`}
      noValidate
      aria-labelledby={`${id}-q`}
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <FormHead
        id={`${id}-q`}
        icon="currency_exchange"
        tone="warn"
        question={amount ? QUEUE_MSG.refundQuestion(amount) : QUEUE_MSG.refundQuestionNoAmount}
        sub={subLabel}
      />

      <div className="field">
        <label htmlFor={`${id}-amt`}>
          {QUEUE_MSG.refundAmount}
          <span className={s.req} aria-hidden="true">
            *
          </span>
        </label>
        <div className={s.money}>
          <input
            ref={amountRef}
            id={`${id}-amt`}
            name="amount"
            className="num"
            inputMode="numeric"
            value={check.value ?? amountRaw}
            onChange={(e) => {
              setAmountRaw(e.target.value);
              if (amountErr) setAmountErr(null);
            }}
            autoComplete="off"
            required
            disabled={sub.busy}
            aria-invalid={amountErr ? true : undefined}
            aria-describedby={`${amountErr ? `${id}-amt-err ` : ""}${id}-amt-help`}
          />
          <span className={s.moneyUnit} aria-hidden="true">
            ₫
          </span>
        </div>
        {amountErr && (
          <p className="field-err" id={`${id}-amt-err`}>
            <Icon name="error" />
            {AMOUNT_MSG[amountErr]}
          </p>
        )}
        <p className="help num" id={`${id}-amt-help`} aria-live="polite">
          {amount ? <b className={s.moneyRead}>{vnd(amount)}</b> : null}
          {amount ? " · " : ""}
          {over ? <span className={s.warnText}>{QUEUE_MSG.refundOverMax(max)}</span> : QUEUE_MSG.refundAmountHelp(max)}
        </p>
      </div>

      <NoteField
        id={`${id}-reason`}
        label={QUEUE_MSG.refundReason}
        value={reason}
        onChange={(v) => {
          setReason(v);
          if (reasonErr) setReasonErr(false);
        }}
        help={QUEUE_MSG.refundReasonHelp}
        required
        error={reasonErr ? QUEUE_MSG.refundReasonMissing : null}
        disabled={sub.busy}
        inputRef={reasonRef}
      />

      <Consequences
        items={[
          { icon: "schedule", text: QUEUE_MSG.refundConsequence1 },
          { icon: "pending", text: QUEUE_MSG.refundConsequence2 },
          {
            icon: "monitoring",
            text: target.kind === "invoice" ? QUEUE_MSG.refundConsequence3Invoice : QUEUE_MSG.refundConsequence3,
          },
          { icon: "history", text: QUEUE_MSG.consequenceAudit },
        ]}
      />

      <FormFooter
        error={sub.error}
        errRef={sub.errRef}
        busy={sub.busy}
        onCancel={onCancel}
        submitIcon="currency_exchange"
        submitLabel={amount ? QUEUE_MSG.refundSubmit(amount) : QUEUE_MSG.refundSubmitNoAmount}
        busyLabel={QUEUE_MSG.refunding}
      />
    </form>
  );
}
