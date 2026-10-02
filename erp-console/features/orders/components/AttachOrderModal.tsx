"use client";

// F2d — "Gắn khoản tiền vào đơn" (ED-11). Tìm đơn bằng API danh sách đơn (BE lọc `q` theo mã / tên / số điện thoại), mặc
// định chỉ đơn Giữ chỗ. Đơn có tổng bằng đúng số tiền được đánh dấu "Bằng số tiền" (chỉ gợi ý hiển thị, BE quyết).
// 409 (người khác vừa xử lý) → màn bật ConflictBanner, không xử lý lần hai. Từ khoá tìm đơn KHÔNG vào URL/localStorage.

import { useEffect, useRef, useState } from "react";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { vnd } from "@/shared/lib/format";
import { ENUMS } from "@/shared/lib/enums";
import { Chip } from "@/shared/ui/Chip";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { useSubmit, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { PersonalText } from "@/shared/ui/PersonalText";
import { listOrders, resolvePayment } from "../api";
import { ORDERS_MSG as M } from "../messages";
import type { OrderListItem, ResolveResult } from "../types";
import { ActionModal } from "./ActionModal";
import s from "../orders.module.css";

type Props = {
  payment: { id: number; bank_txn_id: string; amount: string };
  onClose: () => void;
  onDone: (r: ResolveResult, order: OrderListItem) => void;
  onConflict: (c: SubmitConflict) => void;
};

export function AttachOrderModal({ payment, onClose, onDone, onConflict }: Props) {
  const [scope, setScope] = useState<"booked" | "all">("booked");
  const [q, setQ] = useState("");
  const [qDeb, setQDeb] = useState("");
  const [rows, setRows] = useState<OrderListItem[] | null>(null);
  const [loadErr, setLoadErr] = useState<unknown>(null);
  const [picked, setPicked] = useState<OrderListItem | null>(null);
  const [pickErr, setPickErr] = useState(false);
  const [note, setNote] = useState("");
  const seq = useRef(0);

  const sub = useSubmit(
    () => resolvePayment(payment.id, { action: "ATTACH_TO_ORDER", order_id: picked?.id ?? 0, note: note.trim() }),
    { onSuccess: (r) => picked && onDone(r, picked) },
  );

  useEffect(() => {
    const t = setTimeout(() => setQDeb(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const load = async () => {
    const n = ++seq.current;
    setLoadErr(null);
    try {
      const r = await listOrders({ status: scope === "booked" ? "BOOKED" : "", q: qDeb, date_from: "", date_to: "" }, 1);
      if (n === seq.current) setRows(r.results);
    } catch (err) {
      if (n === seq.current && !(err instanceof ApiError && err.status === 401)) setLoadErr(err);
    }
  };

  useEffect(() => {
    void load();
    return () => {
      seq.current += 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, qDeb]);

  const submit = () => {
    if (!picked) {
      setPickErr(true);
      return;
    }
    void sub.submit();
  };

  return (
    <ActionModal
      title={M.attachTitle}
      onClose={onClose}
      submitting={sub.submitting}
      failed={sub.failed}
      error={sub.error}
      conflict={sub.conflict}
      onConflict={onConflict}
      submitLabel={picked ? M.attachSubmit(picked.code) : M.attachSubmitNoPick}
      busyLabel={M.attaching}
      onSubmit={submit}
    >
      <SummaryBlock
        rows={[
          { label: M.rowPayment, value: payment.bank_txn_id, mono: true },
          { label: M.amountLabel, value: vnd(payment.amount), num: true, strong: true },
        ]}
      />
      <Field
        as="select"
        label={M.attachScopeLabel}
        name="scope"
        value={scope}
        onChange={(v) => setScope(v === "all" ? "all" : "booked")}
        options={[
          { value: "booked", label: M.attachScopeBooked },
          { value: "all", label: M.attachScopeAll },
        ]}
        disabled={sub.submitting}
      />
      <Field label={M.attachSearchLabel} name="order_q" value={q} onChange={setQ} placeholder={M.attachSearchPlaceholder} disabled={sub.submitting} autoFocus />

      <fieldset className={s.pickList} aria-busy={rows === null || undefined} aria-invalid={pickErr || undefined}>
        <legend className="sr-only">{M.attachLegend}</legend>
        {loadErr != null ? (
          <FormAlert>
            {loadErrorText(loadErr)}{" "}
            <button type="button" className="inline-link" onClick={() => void load()}>
              Thử lại
            </button>
          </FormAlert>
        ) : rows === null ? (
          <p className={s.nil} role="status">
            {M.attachLoading}
          </p>
        ) : rows.length === 0 ? (
          <p className={s.nil}>{M.attachEmpty}</p>
        ) : (
          rows.map((o) => (
            <label key={o.id} className={`check-row ${s.pickRow}`} data-id={o.id}>
              <input
                type="radio"
                name="order_id"
                value={o.id}
                checked={picked?.id === o.id}
                onChange={() => {
                  setPicked(o);
                  setPickErr(false);
                }}
                disabled={sub.submitting}
              />
              <span className={s.pickBody}>
                <span className={s.pickTop}>
                  <code className="mono">{o.code}</code>
                  <b className="num">{vnd(o.total_amount)}</b>
                </span>
                <span className={s.pickSub}>
                  <span>
                    <PersonalText value={o.customer_name} whenEmpty="" />
                    {o.customer_phone ? <span className="num"> · {o.customer_phone}</span> : null}
                  </span>
                  <Chip table={ENUMS.salesOrderStatus} value={o.status} />
                </span>
                {Number(o.total_amount) === Number(payment.amount) && <span className={s.sameTag}>{M.attachSameAmount}</span>}
              </span>
            </label>
          ))
        )}
      </fieldset>
      {pickErr && <FormAlert>{M.attachPickMissing}</FormAlert>}
      <Field as="textarea" label={M.attachNoteLabel} name="note" value={note} onChange={setNote} maxLength={300} disabled={sub.submitting} />
      <FormAlert kind="warn">{M.attachAlert}</FormAlert>
    </ActionModal>
  );
}
