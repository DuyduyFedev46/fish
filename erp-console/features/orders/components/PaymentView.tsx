"use client";

// Nội dung xem một khoản tiền lệch (S12): loại lệch + số tiền lớn, thuộc tính kiểu Notion (mã GD, nội dung CK, giờ, nguồn),
// đơn liên quan (tổng · đã nhận · còn thiếu/thừa, nút mở chi tiết đơn), phiếu hoàn đã lập (S13), phần "Đã xử lý" (ai, lúc,
// ghi chú — BR-TT-09). Thanh nút dính đáy theo `available_actions`. Số "còn thiếu / thừa" chỉ là phép trừ để HIỂN THỊ;
// quyết định đủ/thiếu là của BE (BR-TT-09 trả lỗi nguyên văn).

import type { RefObject } from "react";
import { dateTime, vnd } from "@/shared/lib/format";
import { ORDER_STATUS } from "@/shared/lib/status";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { StatusChip } from "@/shared/ui/StatusChip";
import {
  ORDER_LABEL,
  PAYMENT_SOURCE_LABEL,
  QUEUE_TYPE_LABEL,
  QUEUE_TYPE_STATUS,
  REFUND_LABEL,
  REFUND_STATUS,
  RESOLUTION_LABEL,
  labelOf,
} from "../labels";
import { QUEUE_MSG } from "../messages";
import type { PaymentAction, PaymentQueueItem, QueueOrderRef } from "../types";
import type { ResultNote } from "./OrderDetailSheet";
import s from "../orders.module.css";

/** Thao tác FE đã nối cho khoản lệch. Mã lạ trong `available_actions` → không vẽ nút. */
const ACTION_UI: Partial<Record<PaymentAction, { label: string; icon: string }>> = {
  attach_to_order: { label: QUEUE_MSG.actAttach, icon: "link" },
  confirm_order: { label: QUEUE_MSG.actConfirm, icon: "check_circle" },
  refund: { label: QUEUE_MSG.actRefund, icon: "currency_exchange" },
};

type Props = {
  item: PaymentQueueItem;
  refreshing: boolean;
  /** Không tải lại được khoản sau thao tác → đang hiện bản sửa tại chỗ. */
  stale: boolean;
  note: ResultNote | null;
  noteRef: RefObject<HTMLDivElement>;
  actionRef: RefObject<HTMLButtonElement>;
  onOpenOrder: (o: QueueOrderRef) => void;
  onAction: (a: PaymentAction) => void;
};

function Part({ id, title, count, children }: { id: string; title: string; count?: number; children: React.ReactNode }) {
  return (
    <section className={s.part} aria-labelledby={id}>
      <h3 id={id} className={s.partH}>
        {title}
        {count != null && count > 0 && <span className={`${s.partCount} num`}>{count}</span>}
      </h3>
      {children}
    </section>
  );
}

export function PaymentView({ item: p, refreshing, stale, note, noteRef, actionRef, onOpenOrder, onAction }: Props) {
  const resolved = p.resolution_status === "RESOLVED";
  const typeLabel = p.match_status_label || labelOf(QUEUE_TYPE_LABEL, p.match_status);
  const actions = p.available_actions.filter((a) => ACTION_UI[a]);
  const refunds = p.refunds || [];
  const pendingRefund = !resolved && refunds.some((r) => r.status === "PENDING");
  const o = p.order;
  // Chuyển thừa (BR-TT-10): `paid_total` BE không tính khoản thừa → phần "Thừa" chính là số tiền của khoản này.
  const diff = !o ? 0 : p.match_status === "OVERPAID" ? Number(p.amount) : Number(o.paid_total) - Number(o.total_amount);

  return (
    <div className={`${s.pane} payment-view`} aria-busy={refreshing || undefined}>
      {note && (
        <div
          ref={noteRef}
          tabIndex={-1}
          className={`alert-box ${note.tone === "ok" ? "ok" : "warn"} ${s.note} queue-result`}
          role="status"
        >
          <Icon name={note.tone === "ok" ? "check_circle" : "info"} />
          <span>{note.text}</span>
        </div>
      )}
      {stale && (
        <div className="alert-box warn" role="status">
          <Icon name="sync_problem" />
          <span>{QUEUE_MSG.stale}</span>
        </div>
      )}

      <header className={s.hd}>
        <div className={s.hdTop}>
          <StatusChip map={QUEUE_TYPE_STATUS} status={p.match_status} label={typeLabel} />
          {resolved && (
            <span className={`status good ${s.resolvedChip}`}>
              <span className="dot" aria-hidden="true" />
              {p.resolution_label || labelOf(RESOLUTION_LABEL, p.resolution || "") || QUEUE_MSG.resolutionPart}
            </span>
          )}
        </div>
        <p className={`${s.hdTotal} num`}>
          <span className="sr-only">Số tiền </span>
          <Figure text={vnd(p.amount)} />
        </p>
        <p className={s.hdSub}>
          <span className="num">Nhận {dateTime(p.received_at)}</span>
        </p>
      </header>

      <dl className={s.props}>
        <div className={s.prop}>
          <dt>{QUEUE_MSG.txn}</dt>
          <dd>
            <code className={`${s.mono} ${s.monoStrong}`}>{p.bank_txn_id}</code>
          </dd>
        </div>
        {p.content !== undefined && (
          <div className={s.prop}>
            <dt>{QUEUE_MSG.content}</dt>
            <dd>{p.content ? <span className={s.contentText}>{p.content}</span> : <span className={s.muted}>{QUEUE_MSG.noContent}</span>}</dd>
          </div>
        )}
        <div className={s.prop}>
          <dt>{QUEUE_MSG.receivedAt}</dt>
          <dd className="num">{dateTime(p.received_at)}</dd>
        </div>
        {p.refundable_amount !== undefined && Number(p.refundable_amount) !== Number(p.amount) && (
          <div className={s.prop}>
            <dt>{QUEUE_MSG.refundableLeft}</dt>
            <dd className="num refundable-left">
              <Figure text={vnd(p.refundable_amount)} />
            </dd>
          </div>
        )}
        {p.source && (
          <div className={s.prop}>
            <dt>{QUEUE_MSG.source}</dt>
            <dd>{labelOf(PAYMENT_SOURCE_LABEL, p.source, p.source_label)}</dd>
          </div>
        )}
      </dl>

      <Part id="pq-order" title={QUEUE_MSG.orderPart}>
        {o ? (
          <div className={s.qOrderBox}>
            <div className={s.item}>
              <code className={`${s.itemName} ${s.mono} ${s.monoStrong}`}>{o.code}</code>
              <span className={s.itemAmt}>
                <StatusChip map={ORDER_STATUS} status={o.status} label={o.status_label || labelOf(ORDER_LABEL, o.status)} />
              </span>
              {o.customer_name && <span className={s.itemSub}>{o.customer_name}</span>}
            </div>
            <dl className={s.sums}>
              <div>
                <dt>{QUEUE_MSG.orderTotal}</dt>
                <dd className="num">
                  <Figure text={vnd(o.total_amount)} />
                </dd>
              </div>
              <div>
                <dt>{QUEUE_MSG.orderPaid}</dt>
                <dd className="num">
                  <Figure text={vnd(o.paid_total)} />
                </dd>
              </div>
              {diff !== 0 && (
                <div className={s.sumWarn}>
                  <dt>{diff < 0 ? QUEUE_MSG.orderMissing : QUEUE_MSG.orderOver}</dt>
                  <dd className="num">
                    <Figure text={vnd(Math.abs(diff))} />
                  </dd>
                </div>
              )}
            </dl>
            <button type="button" className={`btn ${s.openOrderBtn} open-order`} onClick={() => onOpenOrder(o)} aria-haspopup="dialog">
              <Icon name="receipt_long" />
              {QUEUE_MSG.openOrder(o.code)}
            </button>
          </div>
        ) : (
          <p className={s.nil}>{QUEUE_MSG.orderNone}</p>
        )}
      </Part>

      {refunds.length > 0 && (
        <Part id="pq-refunds" title={QUEUE_MSG.refundsPart} count={refunds.length}>
          <ul className={`${s.items} queue-refunds`}>
            {refunds.map((r) => (
              <li key={r.id} className={s.item}>
                <span className={s.itemName}>
                  <StatusChip map={REFUND_STATUS} status={r.status} label={labelOf(REFUND_LABEL, r.status, r.status_label)} />
                </span>
                <span className={`${s.itemAmt} num`}>
                  <Figure text={vnd(r.amount)} />
                </span>
                {r.bank_txn_ref ? (
                  <code className={`${s.itemCode} ${s.mono}`}>{r.bank_txn_ref}</code>
                ) : (
                  <span className={s.itemSub}>{QUEUE_MSG.refundNoRef}</span>
                )}
              </li>
            ))}
          </ul>
          {pendingRefund && <p className={s.caption}>{QUEUE_MSG.pendingRefundHint}</p>}
        </Part>
      )}

      {resolved && (
        <Part id="pq-resolved" title={QUEUE_MSG.resolutionPart}>
          <dl className={s.props}>
            <div className={s.prop}>
              <dt>{QUEUE_MSG.resolutionHow}</dt>
              <dd>{p.resolution_label || labelOf(RESOLUTION_LABEL, p.resolution || "") || "—"}</dd>
            </div>
            <div className={s.prop}>
              <dt>{QUEUE_MSG.resolvedBy}</dt>
              <dd>{typeof p.resolved_by === "string" && p.resolved_by ? p.resolved_by : "—"}</dd>
            </div>
            <div className={s.prop}>
              <dt>{QUEUE_MSG.resolvedAt}</dt>
              <dd className="num">{dateTime(p.resolved_at)}</dd>
            </div>
            <div className={s.prop}>
              <dt>{QUEUE_MSG.note}</dt>
              <dd>{p.resolution_note || <span className={s.muted}>—</span>}</dd>
            </div>
          </dl>
        </Part>
      )}

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
        !resolved && !refreshing && <p className={s.caption}>{QUEUE_MSG.noActions}</p>
      )}
    </div>
  );
}
