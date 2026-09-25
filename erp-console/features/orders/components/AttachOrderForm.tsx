"use client";

// S12 — Gắn một khoản tiền KHÔNG KHỚP ĐƠN vào đơn (ATTACH_TO_ORDER, S12-AC2). Tìm đơn bằng chính API danh sách đơn (S10,
// BE lọc `q` theo mã / tên khách bỏ dấu / SĐT), mặc định chỉ đơn Giữ chỗ (chỗ tiền thường thuộc về), đổi được sang "Mọi đơn".
// Đơn có tổng bằng đúng số tiền được đánh dấu "Bằng số tiền" để Chủ dễ nhận ra — chỉ là gợi ý hiển thị, BE quyết.
// Chọn đơn → câu hỏi nêu số tiền + mã đơn, hậu quả; gửi một lần; lỗi BE (BR-TT-05 đơn đã tự huỷ, BR-TT-09…) nguyên văn.

import { useEffect, useId, useRef, useState } from "react";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { dateTime, vnd } from "@/shared/lib/format";
import { ORDER_STATUS } from "@/shared/lib/status";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { StatusChip } from "@/shared/ui/StatusChip";
import { listOrders, resolvePayment } from "../api";
import { QUEUE_MSG } from "../messages";
import type { OrderListItem, PaymentQueueItem, QueueOrderRef, ResolveResult } from "../types";
import { Consequences, FormFooter, FormHead, NoteField, useSubmit } from "./QueueFormParts";
import s from "../orders.module.css";

type Props = {
  item: PaymentQueueItem;
  onBusy: (b: boolean) => void;
  onCancel: () => void;
  onDone: (r: ResolveResult, order: QueueOrderRef) => void;
};

type Scope = "booked" | "all";

export function AttachOrderForm({ item, onBusy, onCancel, onDone }: Props) {
  const id = useId();
  const [scope, setScope] = useState<Scope>("booked");
  const [q, setQ] = useState("");
  const [qDeb, setQDeb] = useState("");
  const [rows, setRows] = useState<OrderListItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadErr, setLoadErr] = useState<unknown>(null);
  const [picked, setPicked] = useState<OrderListItem | null>(null);
  const [pickErr, setPickErr] = useState(false);
  const [note, setNote] = useState("");
  const seq = useRef(0);
  const searchRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLFieldSetElement>(null);
  const sub = useSubmit(onBusy);

  useEffect(() => {
    searchRef.current?.focus();
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setQDeb(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const load = async () => {
    const n = ++seq.current;
    setLoading(true);
    setLoadErr(null);
    try {
      const r = await listOrders({ status: scope === "booked" ? "BOOKED" : "", q: qDeb, date_from: "", date_to: "" }, 1);
      if (n !== seq.current) return;
      setRows(r.results);
    } catch (err) {
      if (n !== seq.current) return;
      if (!(err instanceof ApiError && err.status === 401)) setLoadErr(err);
    } finally {
      if (n === seq.current) setLoading(false);
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
    if (sub.locked()) return;
    sub.setError(null);
    if (!picked) {
      setPickErr(true);
      const first = listRef.current?.querySelector<HTMLInputElement>("input[type=radio]");
      if (first) first.focus();
      else searchRef.current?.focus();
      return;
    }
    const order: QueueOrderRef = {
      id: picked.id,
      code: picked.code,
      status: picked.status,
      status_label: picked.status_label,
      total_amount: picked.total_amount,
      paid_total: "0",
      customer_name: picked.customer_name,
    };
    void sub.run(
      () => resolvePayment(item.id, { action: "ATTACH_TO_ORDER", order_id: picked.id, note: note.trim() }),
      (r) => onDone(r, order),
    );
  };

  return (
    <form
      className={`${s.pane} attach-order`}
      noValidate
      aria-labelledby={`${id}-q`}
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <FormHead
        id={`${id}-q`}
        icon="link"
        question={picked ? QUEUE_MSG.attachQuestion(item.amount, picked.code) : QUEUE_MSG.attachTitle(item.bank_txn_id)}
        sub={
          <>
            {vnd(item.amount)} · {item.bank_txn_id} · {dateTime(item.received_at)}
            {item.content ? <> · “{item.content}”</> : null}
          </>
        }
      />

      <div className={s.pickTools}>
        <div className="seg" role="group" aria-label={QUEUE_MSG.attachScope}>
          {(["booked", "all"] as const).map((v) => (
            <button key={v} type="button" aria-pressed={scope === v} onClick={() => setScope(v)} disabled={sub.busy}>
              {v === "booked" ? QUEUE_MSG.attachScopeBooked : QUEUE_MSG.attachScopeAll}
            </button>
          ))}
        </div>
        <div className={s.searchField}>
          <label htmlFor={`${id}-s`}>{QUEUE_MSG.attachSearch}</label>
          <div className="search">
            <Icon name="search" />
            <input
              ref={searchRef}
              id={`${id}-s`}
              type="search"
              name="order_q"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={QUEUE_MSG.attachSearchPh}
              autoComplete="off"
              enterKeyHint="search"
              disabled={sub.busy}
              data-autofocus
            />
          </div>
        </div>
      </div>

      <fieldset
        ref={listRef}
        className={`${s.pickList} attach-pick`}
        aria-busy={loading || undefined}
        aria-invalid={pickErr || undefined}
        aria-describedby={pickErr ? `${id}-pick-err` : undefined}
      >
        <legend className="sr-only">{QUEUE_MSG.attachLegend}</legend>
        {rows === null ? (
          loadErr ? (
            <div className="alert-box err" role="alert">
              <Icon name="error" />
              <span>
                {loadErrorText(loadErr)}{" "}
                <button type="button" className="inline-link" onClick={() => void load()}>
                  Thử lại
                </button>
              </span>
            </div>
          ) : (
            <p className={s.nil} role="status">
              <Icon name="progress_activity" className="spin" /> {QUEUE_MSG.attachLoading}
            </p>
          )
        ) : (
          <>
            {loadErr != null && (
              <div className="alert-box err" role="alert">
                <Icon name="error" />
                <span>{loadErrorText(loadErr)}</span>
              </div>
            )}
            {rows.length === 0 ? (
              <p className={s.nil}>{QUEUE_MSG.attachEmpty}</p>
            ) : (
              rows.map((o) => {
                const same = Number(o.total_amount) === Number(item.amount);
                return (
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
                      disabled={sub.busy}
                    />
                    <span className={s.pickBody}>
                      <span className={s.pickTop}>
                        <code className={`${s.mono} ${s.monoStrong}`}>{o.code}</code>
                        <b className="num">
                          <Figure text={vnd(o.total_amount)} />
                        </b>
                      </span>
                      <span className={s.pickSub}>
                        <span>
                          {o.customer_name}
                          {o.customer_phone ? <span className="num"> · …{o.customer_phone.slice(-4)}</span> : null}
                        </span>
                        <StatusChip map={ORDER_STATUS} status={o.status} label={o.status_label} />
                      </span>
                      {same && (
                        <span className={s.sameTag}>
                          <Icon name="check" />
                          {QUEUE_MSG.attachSameAmount}
                        </span>
                      )}
                    </span>
                  </label>
                );
              })
            )}
          </>
        )}
      </fieldset>
      {pickErr && (
        <p className="field-err" id={`${id}-pick-err`}>
          <Icon name="error" />
          {QUEUE_MSG.attachPick}
        </p>
      )}

      <NoteField
        id={`${id}-note`}
        label={QUEUE_MSG.noteLabel}
        value={note}
        onChange={setNote}
        help={QUEUE_MSG.noteHelpAttach}
        disabled={sub.busy}
      />

      <Consequences
        items={[
          { icon: "local_shipping", text: QUEUE_MSG.attachConsequence1 },
          { icon: "timer_off", text: QUEUE_MSG.attachConsequence2 },
          { icon: "block", text: QUEUE_MSG.consequenceFinal },
          { icon: "history", text: QUEUE_MSG.consequenceAudit },
        ]}
      />

      <FormFooter
        error={sub.error}
        errRef={sub.errRef}
        busy={sub.busy}
        onCancel={onCancel}
        submitIcon="link"
        submitLabel={picked ? QUEUE_MSG.attachSubmit(picked.code) : QUEUE_MSG.actAttach}
        busyLabel={QUEUE_MSG.attaching}
      />
    </form>
  );
}
