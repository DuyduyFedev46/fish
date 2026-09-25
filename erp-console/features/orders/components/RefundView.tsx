"use client";

// S16 — Nội dung xem một phiếu hoàn đang chờ chuyển: số tiền lớn + trạng thái, thuộc tính kiểu Notion (đơn liên quan,
// SĐT khách dạng link tel: — Q13 không lưu STK, mã GD tiền vào, người lập, lúc lập, lý do thất bại lần trước nếu có).
// Thanh nút CHỈ theo `available_actions` của phiếu (BE tính cả luật lẫn quyền — chỉ Chủ có sales.confirm_refund).

import type { RefObject } from "react";
import { dateTime, vnd } from "@/shared/lib/format";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { StatusChip } from "@/shared/ui/StatusChip";
import { REFUND_LABEL, REFUND_STATUS, labelOf } from "../labels";
import { REFUND_Q_MSG } from "../messages";
import type { RefundQueueAction, RefundQueueItem } from "../types";
import type { ResultNote } from "./OrderDetailSheet";
import s from "../orders.module.css";

const ACTION_UI: Partial<Record<RefundQueueAction, { label: string; icon: string }>> = {
  confirm: { label: REFUND_Q_MSG.actConfirm, icon: "task_alt" },
  mark_failed: { label: REFUND_Q_MSG.actMarkFailed, icon: "error" },
  retry: { label: REFUND_Q_MSG.actRetry, icon: "replay" },
};

type Props = {
  item: RefundQueueItem;
  refreshing: boolean;
  note: ResultNote | null;
  noteRef: RefObject<HTMLDivElement>;
  actionRef: RefObject<HTMLButtonElement>;
  onAction: (a: RefundQueueAction) => void;
};

export function RefundView({ item: r, refreshing, note, noteRef, actionRef, onAction }: Props) {
  const statusLabel = r.status_label || labelOf(REFUND_LABEL, r.status);
  const actions = r.available_actions.filter((a) => ACTION_UI[a]);

  return (
    <div className={`${s.pane} refund-view`} aria-busy={refreshing || undefined}>
      {note && (
        <div ref={noteRef} tabIndex={-1} className={`alert-box ${note.tone === "ok" ? "ok" : "warn"} ${s.note} refund-result`} role="status">
          <Icon name={note.tone === "ok" ? "check_circle" : "info"} />
          <span>{note.text}</span>
        </div>
      )}

      <header className={s.hd}>
        <div className={s.hdTop}>
          <StatusChip map={REFUND_STATUS} status={r.status} label={statusLabel} />
        </div>
        <p className={`${s.hdTotal} num`}>
          <span className="sr-only">Số tiền hoàn </span>
          <Figure text={vnd(r.amount)} />
        </p>
        {r.created_at && (
          <p className={s.hdSub}>
            <span className="num">Lập {dateTime(r.created_at)}</span>
          </p>
        )}
      </header>

      <dl className={s.props}>
        <div className={s.prop}>
          <dt>{REFUND_Q_MSG.order}</dt>
          <dd>{r.order_code ? <code className={`${s.mono} ${s.monoStrong}`}>{r.order_code}</code> : <span className={s.muted}>{REFUND_Q_MSG.noOrder}</span>}</dd>
        </div>
        {r.customer_name && (
          <div className={s.prop}>
            <dt>Khách</dt>
            <dd>{r.customer_name}</dd>
          </div>
        )}
        {r.customer_phone && (
          <div className={s.prop}>
            <dt>Số điện thoại</dt>
            <dd>
              <a className={`${s.tel} num`} href={`tel:${r.customer_phone}`}>
                <Icon name="call" />
                {r.customer_phone}
              </a>
            </dd>
          </div>
        )}
        {r.source_bank_txn_id && (
          <div className={s.prop}>
            <dt>{REFUND_Q_MSG.sourceTxn}</dt>
            <dd>
              <code className={`${s.mono} ${s.monoStrong}`}>{r.source_bank_txn_id}</code>
            </dd>
          </div>
        )}
        <div className={s.prop}>
          <dt>{REFUND_Q_MSG.reason}</dt>
          <dd>{r.reason || <span className={s.muted}>—</span>}</dd>
        </div>
        {r.created_by && (
          <div className={s.prop}>
            <dt>{REFUND_Q_MSG.createdByLabel}</dt>
            <dd>{r.created_by}</dd>
          </div>
        )}
        {r.bank_txn_ref && (
          <div className={s.prop}>
            <dt>Mã GD hoàn</dt>
            <dd>
              <code className={`${s.mono} ${s.monoStrong}`}>{r.bank_txn_ref}</code>
            </dd>
          </div>
        )}
        {r.confirmed_at && (
          <div className={s.prop}>
            <dt>{REFUND_Q_MSG.confirmedAt}</dt>
            <dd className="num">{dateTime(r.confirmed_at)}</dd>
          </div>
        )}
        {r.status === "FAILED" && r.failure_reason && (
          <div className={s.prop}>
            <dt>{REFUND_Q_MSG.failureReason}</dt>
            <dd className={s.warnText}>{r.failure_reason}</dd>
          </div>
        )}
      </dl>

      {actions.length > 0 ? (
        <div className={`form-actions ${s.footer} ${s.stack}`}>
          {actions.map((a, i) => {
            const ui = ACTION_UI[a]!;
            return (
              <button
                key={a}
                ref={i === 0 ? actionRef : undefined}
                type="button"
                className={`btn ${i === 0 ? "primary" : ""}`}
                onClick={() => onAction(a)}
                disabled={refreshing}
                data-action={a}
              >
                <Icon name={ui.icon} />
                {ui.label}
              </button>
            );
          })}
        </div>
      ) : (
        !refreshing && <p className={s.caption}>{REFUND_Q_MSG.noActions}</p>
      )}
    </div>
  );
}
