"use client";

// Nội dung chi tiết đơn (S10): đầu đơn (mã, trạng thái, tổng tiền, đếm lùi giữ chỗ mm:ss theo `reserved_until` — S10-AC5),
// thuộc tính khách kiểu Notion, rồi các phần Hàng · Phân bổ lô · Thanh toán · Giao hàng · Hoàn tiền · Dòng thời gian,
// ngăn bằng đường mảnh (không khung lồng khung). Giá vốn trong phân bổ lô CHỈ hiện khi JSON có key `unit_cost`
// (BR-PQ-15) và người xem có quyền xem giá vốn. Thanh nút dính đáy tấm (tay cái) theo `available_actions`.

import type { RefObject } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { dateTime, kg, timeHM, vnd } from "@/shared/lib/format";
import { ORDER_STATUS } from "@/shared/lib/status";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { StatusChip } from "@/shared/ui/StatusChip";
import {
  DELIVERY_LABEL,
  DELIVERY_STATUS,
  ORDER_LABEL,
  PAYMENT_LABEL,
  PAYMENT_SOURCE_LABEL,
  PAYMENT_STATUS,
  REFUND_LABEL,
  REFUND_STATUS,
  labelOf,
} from "../labels";
import { ORDERS_MSG } from "../messages";
import type { OrderAction, OrderDetail, OrderListItem, OrderTimelineEntry } from "../types";
import { mmss, useNow } from "../useNow";
import type { ResultNote } from "./OrderDetailSheet";
import s from "../orders.module.css";

/** Thao tác FE đã nối (L7). Mã khác trong `available_actions` (cancel — S14, create_refund — S15) chưa có màn → không vẽ nút. */
const ACTION_UI: Partial<Record<OrderAction, { label: string; icon: string }>> = {
  confirm_payment: { label: ORDERS_MSG.confirmAction, icon: "payments" },
};

type Props = {
  order: OrderDetail;
  fallback: OrderListItem;
  refreshing: boolean;
  refreshError: string | null;
  onRetry: () => void;
  note: ResultNote | null;
  noteRef: RefObject<HTMLDivElement>;
  actionRef: RefObject<HTMLButtonElement>;
  onAction: (a: OrderAction) => void;
};

function Part({ title, count, children }: { title: string; count?: number; children: React.ReactNode }) {
  const id = `od-${title.replace(/\s+/g, "-")}`;
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

function Nil({ children }: { children: React.ReactNode }) {
  return <p className={s.nil}>{children}</p>;
}

/** Icon + tông theo `kind` của BE. Chỉ tô màu khi có nghĩa: giao thất bại / huỷ = hổ phách, giao xong / đã hoàn = xanh lá. */
const TIMELINE_LOOK: Record<string, { icon: string; tone?: "warn" | "good" }> = {
  order_placed: { icon: "shopping_bag" },
  payment_received: { icon: "payments" },
  invoice_issued: { icon: "receipt_long" },
  delivery_created: { icon: "inventory" },
  delivery_status: { icon: "local_shipping" },
  delivered: { icon: "task_alt", tone: "good" },
  delivery_failed: { icon: "report", tone: "warn" },
  return_to_warehouse: { icon: "undo" },
  return_approved: { icon: "fact_check" },
  auto_cancelled: { icon: "timer_off", tone: "warn" },
  cancelled: { icon: "cancel", tone: "warn" },
  refund_created: { icon: "currency_exchange" },
  refund_confirmed: { icon: "price_check", tone: "good" },
};
const TIMELINE_DEFAULT = { icon: "radio_button_checked" } as const;

/**
 * Dòng thời gian: BE trả `timeline` (L7 bổ sung, `at` tăng dần) thì dùng NGUYÊN — không sắp lại, không ghép thêm.
 * BE cũ chưa có key → ghép tạm từ các mốc giờ có sẵn (chỉ hiển thị, không suy luật) và ghi chú rõ là ghép tạm.
 */
function timelineOf(o: OrderDetail): { entries: OrderTimelineEntry[]; derived: boolean } {
  if (o.timeline) return { entries: o.timeline, derived: false };
  const out: OrderTimelineEntry[] = [];
  if (o.created_at) out.push({ at: o.created_at, kind: "order_placed", label: ORDERS_MSG.tlCreated });
  o.payments.forEach((p) => {
    if (!p.received_at) return;
    const src = p.source_label || (p.source ? PAYMENT_SOURCE_LABEL[p.source] : "");
    out.push({ at: p.received_at, kind: "payment_received", label: `${ORDERS_MSG.tlPayment(p.amount)}${src ? ` · ${src}` : ""}` });
  });
  if (o.invoice?.issued_at) out.push({ at: o.invoice.issued_at, kind: "invoice_issued", label: ORDERS_MSG.tlInvoice(o.invoice.code) });
  out.sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
  return { entries: out, derived: true };
}

export function OrderDetailView({ order: o, fallback, refreshing, refreshError, onRetry, note, noteRef, actionRef, onAction }: Props) {
  const { me } = useAuth();
  const booked = o.status === "BOOKED";
  const reservedUntil = o.reserved_until ?? (booked ? fallback.reserved_until : null);
  const now = useNow(booked && !!reservedUntil, 1000);
  const hold = booked ? mmss(reservedUntil, now) : null;
  const statusLabel = o.status_label || labelOf(ORDER_LABEL, o.status);
  const total = o.total_amount ?? fallback.total_amount;
  const created = o.created_at ?? fallback.created_at;
  const lineName = (no: number) => o.lines.find((l) => l.no === no)?.item_name || `Dòng ${no}`;
  // Hai lớp: key phải có trong JSON (BE chặn thật) VÀ người xem có quyền (FE ẩn cho chắc).
  const showCost = !!me?.can_view_cost && o.allocations.some((a) => "unit_cost" in a);
  const actions = o.available_actions.filter((a) => ACTION_UI[a]);
  const tl = timelineOf(o);

  return (
    <div className={s.pane} aria-busy={refreshing || undefined}>
      {note && (
        <div
          ref={noteRef}
          tabIndex={-1}
          className={`alert-box ${note.tone === "ok" ? "ok" : "warn"} ${s.note} confirm-result`}
          role="status"
        >
          <Icon name={note.tone === "ok" ? "check_circle" : "info"} />
          <span>
            {note.duplicate && <b className={s.noteLead}>{ORDERS_MSG.duplicate} </b>}
            {note.text}
          </span>
        </div>
      )}
      {refreshError && (
        <div className="alert-box err" role="alert">
          <Icon name="sync_problem" />
          <span>
            {refreshError}{" "}
            <button type="button" className="inline-link" onClick={onRetry}>
              Thử lại
            </button>
          </span>
        </div>
      )}

      <header className={s.hd}>
        <div className={s.hdTop}>
          <code className={s.hdCode}>{o.code}</code>
          <StatusChip map={ORDER_STATUS} status={o.status} label={statusLabel} />
        </div>
        <p className={`${s.hdTotal} num`}>
          <span className="sr-only">Tổng đơn </span>
          <Figure text={vnd(total)} />
        </p>
        <p className={s.hdSub}>
          <span className="num">Đặt {dateTime(created)}</span>
          <span aria-hidden="true"> · </span>
          <span className="num">{o.lines.length} mặt hàng</span>
        </p>
      </header>

      {hold && (
        <div className={`${s.hold}${hold.over ? ` ${s.holdOver}` : ""} hold-countdown`}>
          <Icon name={hold.over ? "timer_off" : "timer"} />
          <div className={s.holdText}>
            {hold.over ? (
              <b>{ORDERS_MSG.reservedOver}</b>
            ) : (
              <b>
                {ORDERS_MSG.reservedLeft}{" "}
                <span className={`${s.holdClock} num`} role="timer" aria-live="off" data-until={reservedUntil || ""}>
                  {hold.text}
                </span>
              </b>
            )}
            <span>
              Tới {timeHM(reservedUntil)}. {ORDERS_MSG.reservedHint}
            </span>
          </div>
        </div>
      )}

      <dl className={s.props}>
        <div className={s.prop}>
          <dt>Khách</dt>
          <dd>{o.customer.name || "—"}</dd>
        </div>
        <div className={s.prop}>
          <dt>Số điện thoại</dt>
          <dd>
            {o.customer.phone ? (
              <a className={`${s.tel} num`} href={`tel:${o.customer.phone}`}>
                <Icon name="call" />
                {o.customer.phone}
              </a>
            ) : (
              "—"
            )}
          </dd>
        </div>
        <div className={s.prop}>
          <dt>Địa chỉ</dt>
          <dd>{o.customer.address || <span className={s.muted}>{ORDERS_MSG.noAddress}</span>}</dd>
        </div>
        <div className={s.prop}>
          <dt>Hoá đơn</dt>
          <dd>
            {o.invoice ? (
              <span className={s.inline}>
                <code className={s.mono}>{o.invoice.code}</code>
                {o.invoice.issued_at && <span className={`${s.muted} num`}>{dateTime(o.invoice.issued_at)}</span>}
              </span>
            ) : (
              <span className={s.muted}>{ORDERS_MSG.noInvoice}</span>
            )}
          </dd>
        </div>
      </dl>

      <Part title="Hàng" count={o.lines.length}>
        <ul className={s.items}>
          {o.lines.map((l) => (
            <li key={l.no} className={s.item}>
              <span className={s.itemName}>{l.item_name}</span>
              <span className={`${s.itemAmt} num`}>
                <Figure text={vnd(l.line_total)} />
              </span>
              <span className={`${s.itemSub} num`}>
                {kg(l.qty_kg)} × {vnd(l.unit_price)}
                {Number(l.discount) > 0 && <> · giảm {vnd(l.discount)}</>}
              </span>
              <code className={`${s.itemCode} ${s.mono}`}>{l.item_code}</code>
            </li>
          ))}
          <li className={`${s.item} ${s.itemTotal}`}>
            <span className={s.itemName}>Tổng đơn</span>
            <span className={`${s.itemAmt} num`}>
              <Figure text={vnd(total)} />
            </span>
          </li>
        </ul>
      </Part>

      <Part title="Phân bổ lô" count={o.allocations.length}>
        {o.allocations.length ? (
          <ul className={`${s.items} alloc-list`}>
            {o.allocations.map((a, i) => (
              <li key={`${a.line_no}-${a.batch_id}-${i}`} className={s.item}>
                <code className={`${s.itemName} ${s.mono} ${s.monoStrong}`}>{a.batch_id}</code>
                <span className={`${s.itemAmt} num`}>
                  <Figure text={kg(a.qty_kg)} />
                </span>
                <span className={s.itemSub}>{lineName(a.line_no)}</span>
                {showCost && a.unit_cost !== undefined && (
                  <span className={`${s.itemCode} num alloc-cost`}>
                    Vốn <Figure text={vnd(a.unit_cost)} />
                    /kg
                  </span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <Nil>{ORDERS_MSG.noAllocations}</Nil>
        )}
      </Part>

      <Part title="Thanh toán" count={o.payments.length}>
        {o.payments.length ? (
          <ul className={s.items}>
            {o.payments.map((p) => (
              <li key={p.id} className={s.item}>
                <span className={s.itemName}>
                  <StatusChip map={PAYMENT_STATUS} status={p.match_status} label={labelOf(PAYMENT_LABEL, p.match_status, p.match_status_label)} />
                </span>
                <span className={`${s.itemAmt} num`}>
                  <Figure text={vnd(p.amount)} />
                </span>
                <span className={`${s.itemSub} num`}>
                  {dateTime(p.received_at)}
                  {p.source ? ` · ${labelOf(PAYMENT_SOURCE_LABEL, p.source, p.source_label)}` : ""}
                </span>
                <code className={`${s.itemCode} ${s.mono}`}>{p.bank_txn_id || "—"}</code>
              </li>
            ))}
          </ul>
        ) : (
          <Nil>{ORDERS_MSG.noPayments}</Nil>
        )}
      </Part>

      <Part title="Giao hàng">
        {o.delivery ? (
          <div className={s.delivery}>
            <div className={s.item}>
              <code className={`${s.itemName} ${s.mono} ${s.monoStrong}`}>{o.delivery.code}</code>
              <span className={s.itemAmt}>
                <StatusChip
                  map={DELIVERY_STATUS}
                  status={o.delivery.status}
                  label={labelOf(DELIVERY_LABEL, o.delivery.status, o.delivery.status_label)}
                />
              </span>
              <span className={s.itemSub}>
                {o.delivery.assigned_to ? o.delivery.assigned_to.display_name : ORDERS_MSG.unassigned}
                {o.delivery.failed_attempts > 0 && (
                  <span className={s.warnText}> · {ORDERS_MSG.failedAttempts(o.delivery.failed_attempts)}</span>
                )}
              </span>
            </div>
            {o.delivery.assigned_to?.phone && (
              <a
                className={`btn ${s.callBtn}`}
                href={`tel:${o.delivery.assigned_to.phone}`}
                aria-label={`Gọi ${o.delivery.assigned_to.display_name}: ${o.delivery.assigned_to.phone}`}
              >
                <Icon name="call" />
                <span className="num">{o.delivery.assigned_to.phone}</span>
              </a>
            )}
          </div>
        ) : (
          <Nil>{ORDERS_MSG.noDelivery}</Nil>
        )}
      </Part>

      <Part title="Hoàn tiền" count={o.refunds.length}>
        {o.refunds.length ? (
          <ul className={s.items}>
            {o.refunds.map((r) => (
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
                  <span className={s.itemSub}>Chưa có mã chuyển khoản</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <Nil>{ORDERS_MSG.noRefunds}</Nil>
        )}
      </Part>

      <Part title="Dòng thời gian">
        <ol className={`${s.tl} order-timeline`}>
          {tl.entries.map((e, i) => {
            const look = TIMELINE_LOOK[e.kind] || TIMELINE_DEFAULT;
            const tone = "tone" in look ? look.tone : undefined;
            return (
              <li
                key={`${e.at}-${i}`}
                className={`${s.tlItem}${tone === "warn" ? ` ${s.tlWarn}` : tone === "good" ? ` ${s.tlGood}` : ""}`}
                data-kind={e.kind}
              >
                <span className={s.tlIcon} aria-hidden="true">
                  <Icon name={look.icon} />
                </span>
                <span className={s.tlBody}>
                  <span className={s.tlLabel}>{e.label}</span>
                  <span className={s.tlMeta}>
                    <time className="num" dateTime={e.at}>
                      {dateTime(e.at)}
                    </time>
                    {e.actor_display ? <span className="tl-actor"> · {e.actor_display}</span> : null}
                  </span>
                </span>
              </li>
            );
          })}
          <li className={`${s.tlItem} ${s.tlNow}`}>
            <span className={s.tlIcon} aria-hidden="true">
              <Icon name="radio_button_checked" />
            </span>
            <span className={s.tlBody}>
              <span className={s.tlLabel}>
                Hiện tại: <b>{statusLabel}</b>
              </span>
            </span>
          </li>
        </ol>
        {tl.derived && <p className={s.caption}>{ORDERS_MSG.timelineDerived}</p>}
      </Part>

      {actions.length > 0 && (
        <div className={`form-actions ${s.footer}`}>
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
      )}
    </div>
  );
}
