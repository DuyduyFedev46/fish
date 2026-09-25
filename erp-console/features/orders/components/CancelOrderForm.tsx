"use client";

// S14 — Huỷ đơn đã thanh toán theo trạng thái phiếu giao (BR-HT-05, BR-GH-07). Chọn lý do (4 mã cố định; "Khác" bắt
// buộc ghi chú — S14-AC6); nêu rõ hậu quả: hàng về kho lô gốc (trừ khi phiếu giao đã Giao thất bại — Q8b, không hoàn
// kho), cần hoàn tiền lại cho khách, phiếu giao đóng theo. BE quyết theo trạng thái phiếu giao thật (BR-GH-07 đang
// giao, BR-GH-05 đã xong, BR-LO-05 lô đã chốt) — lỗi hiện NGUYÊN VĂN. Gửi một lần, chống bấm đúp.

import { useEffect, useId, useRef, useState } from "react";
import { Icon } from "@/shared/ui/Icon";
import { CANCEL_REASONS } from "../labels";
import { ORDERS_MSG } from "../messages";
import { cancelOrder } from "../api";
import type { CancelOrderResult, CancelReasonCode, OrderDetail } from "../types";
import { Consequences, FormFooter, FormHead, NoteField, useSubmit } from "./QueueFormParts";
import s from "../orders.module.css";

type Props = {
  order: OrderDetail;
  onBusy: (b: boolean) => void;
  onCancel: () => void;
  onDone: (r: CancelOrderResult) => void;
};

export function CancelOrderForm({ order, onBusy, onCancel, onDone }: Props) {
  const id = useId();
  const [reasonCode, setReasonCode] = useState<CancelReasonCode | "">("");
  const [reasonErr, setReasonErr] = useState(false);
  const [note, setNote] = useState("");
  const [noteErr, setNoteErr] = useState(false);
  const listRef = useRef<HTMLFieldSetElement>(null);
  const noteRef = useRef<HTMLTextAreaElement>(null);
  const sub = useSubmit(onBusy);
  const isOther = reasonCode === "OTHER";

  useEffect(() => {
    listRef.current?.querySelector<HTMLInputElement>("input[type=radio]")?.focus();
  }, []);

  const submit = () => {
    if (sub.locked()) return;
    sub.setError(null);
    if (!reasonCode) {
      setReasonErr(true);
      listRef.current?.querySelector<HTMLInputElement>("input[type=radio]")?.focus();
      return;
    }
    const n = note.trim();
    if (isOther && !n) {
      setNoteErr(true);
      noteRef.current?.focus();
      return;
    }
    void sub.run(() => cancelOrder(order.id, { reason_code: reasonCode, note: n }), onDone);
  };

  return (
    <form
      className={`${s.pane} cancel-order`}
      noValidate
      aria-labelledby={`${id}-q`}
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <FormHead
        id={`${id}-q`}
        icon="cancel"
        tone="warn"
        question={ORDERS_MSG.cancelQuestion(order.code)}
        sub={<>{order.customer.name} · Tổng đơn {order.total_amount}</>}
      />

      <fieldset
        ref={listRef}
        className={`${s.pickList} cancel-reasons`}
        aria-invalid={reasonErr || undefined}
        aria-describedby={reasonErr ? `${id}-reason-err` : undefined}
      >
        <legend>
          {ORDERS_MSG.cancelReasonLabel}
          <span className={s.req} aria-hidden="true">
            *
          </span>
        </legend>
        {CANCEL_REASONS.map((r) => (
          <label key={r.value} className={`check-row ${s.pickRow}`}>
            <input
              type="radio"
              name="reason_code"
              value={r.value}
              checked={reasonCode === r.value}
              onChange={() => {
                setReasonCode(r.value as CancelReasonCode);
                setReasonErr(false);
              }}
              disabled={sub.busy}
            />
            <span>
              <b>{r.label}</b>
              <small>{r.hint}</small>
            </span>
          </label>
        ))}
      </fieldset>
      {reasonErr && (
        <p className="field-err" id={`${id}-reason-err`}>
          <Icon name="error" />
          {ORDERS_MSG.cancelReasonMissing}
        </p>
      )}

      <NoteField
        id={`${id}-note`}
        label={ORDERS_MSG.cancelNoteLabel}
        value={note}
        onChange={(v) => {
          setNote(v);
          if (noteErr) setNoteErr(false);
        }}
        help={ORDERS_MSG.cancelNoteHelp}
        required={isOther}
        error={noteErr ? ORDERS_MSG.cancelNoteMissing : null}
        disabled={sub.busy}
        inputRef={noteRef}
      />

      <Consequences
        items={[
          { icon: "undo", text: ORDERS_MSG.cancelConsequence1 },
          { icon: "currency_exchange", text: ORDERS_MSG.cancelConsequence2 },
          { icon: "local_shipping", text: ORDERS_MSG.cancelConsequence3 },
          { icon: "history", text: ORDERS_MSG.consequenceAudit },
        ]}
      />

      <FormFooter
        error={sub.error}
        errRef={sub.errRef}
        busy={sub.busy}
        onCancel={onCancel}
        submitIcon="cancel"
        submitLabel={ORDERS_MSG.cancelSubmit}
        busyLabel={ORDERS_MSG.cancelling}
      />
    </form>
  );
}
