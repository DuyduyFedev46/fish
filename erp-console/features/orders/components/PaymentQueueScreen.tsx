"use client";

// S12 — Hàng chờ thanh toán lệch (menu con của "Đơn & tiền", chỉ Chủ). Danh sách GET /api/sales/payments/ lọc tình trạng
// xử lý (Đang chờ = OPEN · Đã xử lý = RESOLVED) và loại lệch (thiếu / không khớp đơn / về sau khi đơn tự huỷ / chuyển thừa),
// 20 dòng/trang + "Tải thêm". Bấm một khoản → tấm chi tiết (PaymentSheet) với nút theo `available_actions`: gắn vào đơn,
// xác nhận đơn khi khách đã bù (S12), lập phiếu hoàn (S13). Từ tấm khoản tiền mở được chi tiết đơn liên quan (OrderDetailSheet
// — tải mới mỗi lần mở nên luôn thấy trạng thái sau thao tác). Page bọc <ViewGuard view="payments">.

import { useId, useMemo, useRef, useState } from "react";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { dateTime, vnd } from "@/shared/lib/format";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { ErrorBox } from "@/shared/ui/StateBox";
import { StatusChip } from "@/shared/ui/StatusChip";
import { Toast } from "@/shared/ui/Toast";
import { listPaymentQueue } from "../api";
import { QUEUE_TYPE_FILTERS, QUEUE_TYPE_LABEL, QUEUE_TYPE_STATUS, RESOLUTION_LABEL, labelOf } from "../labels";
import { QUEUE_MSG } from "../messages";
import type { OrderListItem, PaymentQueueItem, PaymentQueueParams, QueueOrderRef, ResolutionStatus } from "../types";
import { usePagedList } from "../usePagedList";
import { OrderDetailSheet } from "./OrderDetailSheet";
import { OrdersTabs } from "./OrdersTabs";
import { PaymentSheet } from "./PaymentSheet";
import s from "../orders.module.css";

const RESOLVED_LOOK = { ATTACHED: { tone: "good", icon: "link" }, CONFIRMED: { tone: "good", icon: "check" }, REFUNDED: { tone: "good", icon: "undo" } } as const;

/** Tóm tắt tối thiểu để mở tấm chi tiết đơn từ hàng chờ (tấm tự tải chi tiết đầy đủ). */
function orderSummary(o: QueueOrderRef): OrderListItem {
  return {
    id: o.id,
    code: o.code,
    status: o.status,
    status_label: o.status_label || o.status,
    customer_name: o.customer_name || "",
    customer_phone: "",
    total_amount: o.total_amount,
    created_at: "",
    reserved_until: null,
    delivery_status: null,
    needs_attention: false,
  };
}

function Row({ p, onOpen }: { p: PaymentQueueItem; onOpen: () => void }) {
  const resolved = p.resolution_status === "RESOLVED";
  const pendingRefund = !resolved && (p.refunds || []).some((r) => r.status === "PENDING");
  const typeLabel = labelOf(QUEUE_TYPE_LABEL, p.match_status);
  return (
    <li className={s.row}>
      <button type="button" className={`${s.open} ${s.qOpen} queue-open`} onClick={onOpen} aria-haspopup="dialog" data-id={p.id}>
        <span className={s.qType}>
          {resolved ? (
            <StatusChip
              map={RESOLVED_LOOK}
              status={p.resolution || ""}
              label={p.resolution_label || labelOf(RESOLUTION_LABEL, p.resolution || "")}
            />
          ) : (
            <StatusChip map={QUEUE_TYPE_STATUS} status={p.match_status} label={typeLabel} />
          )}
        </span>
        <span className={`${s.cAmt} num`}>
          <span className="sr-only">, số tiền </span>
          <Figure text={vnd(p.amount)} />
        </span>
        <span className={s.qTxn}>
          <code className={s.qCode}>{p.bank_txn_id}</code>
          <span className={`${s.sub} num`}>
            <span className="sr-only">, nhận lúc </span>
            {dateTime(p.received_at)}
          </span>
        </span>
        <span className={s.qOrder}>
          {p.order ? (
            <>
              <span className="sr-only">, đơn </span>
              <code className={s.qCode}>{p.order.code}</code>
              {p.order.customer_name && <span className={s.qCust}>{p.order.customer_name}</span>}
            </>
          ) : (
            <span className={s.sub}>
              <span className="sr-only">, </span>
              {QUEUE_MSG.noOrder}
            </span>
          )}
          {resolved && typeof p.resolved_by === "string" && p.resolved_by ? (
            <span className={s.sub}>
              <span className="sr-only">, xử lý bởi </span>
              {p.resolved_by}
            </span>
          ) : pendingRefund ? (
            <span className={`${s.sub} ${s.subWarn}`}>
              <span className="sr-only">, </span>
              {QUEUE_MSG.pendingRefund}
            </span>
          ) : null}
        </span>
      </button>
    </li>
  );
}

export function PaymentQueueScreen() {
  const [status, setStatus] = useState<ResolutionStatus>("OPEN");
  const [type, setType] = useState("");
  const params: PaymentQueueParams = useMemo(() => ({ resolution_status: status, match_status: type }), [status, type]);
  const list = usePagedList<PaymentQueueItem, PaymentQueueParams>(listPaymentQueue, params, true);
  const typeId = useId();

  const [openItem, setOpenItem] = useState<PaymentQueueItem | null>(null);
  const [openOrder, setOpenOrder] = useState<QueueOrderRef | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const pendingToast = useRef<string | null>(null);
  const changed = useRef(false);

  const forbidden = list.error instanceof ApiError && list.error.status === 403;
  const filtered = !!type;

  const afterClose = () => {
    if (changed.current) {
      changed.current = false;
      void list.reload();
    }
    if (pendingToast.current) {
      setToast(pendingToast.current);
      pendingToast.current = null;
    }
  };

  return (
    <div className="screen">
      <OrdersTabs current="payments" />
      <p className="view-head">{QUEUE_MSG.intro}</p>

      <div className={s.bar}>
        <div className="seg" role="group" aria-label={QUEUE_MSG.filterStatus}>
          {(["OPEN", "RESOLVED"] as const).map((v) => (
            <button key={v} type="button" aria-pressed={status === v} onClick={() => setStatus(v)}>
              {v === "OPEN" ? QUEUE_MSG.openTab : QUEUE_MSG.resolvedTab}
            </button>
          ))}
        </div>
        <div className={s.qFilters}>
          <div className={s.select}>
            <label htmlFor={typeId} className="sr-only">
              {QUEUE_MSG.filterType}
            </label>
            <select id={typeId} name="match_status" value={type} onChange={(e) => setType(e.target.value)}>
              {QUEUE_TYPE_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
            <Icon name="expand_more" />
          </div>
          <div className="toolbar">
            <button
              type="button"
              className="iconbtn"
              onClick={() => void list.reload()}
              disabled={list.loading}
              aria-label="Làm mới"
              title="Làm mới"
            >
              <Icon name="refresh" className={list.loading ? "spin" : undefined} />
            </button>
          </div>
        </div>
      </div>

      {list.rows === undefined ? (
        list.error && !list.loading ? (
          <ErrorBox icon={forbidden ? "lock" : undefined} message={loadErrorText(list.error)} onRetry={() => void list.reload()} />
        ) : (
          <SkeletonScreen label={QUEUE_MSG.loading}>
            <SkeletonTable rows={5} cols={4} />
          </SkeletonScreen>
        )
      ) : (
        <section className={`sect ${s.list}`} aria-labelledby="queue-h" aria-busy={list.loading}>
          <div className="sect-h">
            <h2 id="queue-h">{QUEUE_MSG.listTitle}</h2>
            <span className="sub num" aria-live="polite">
              {list.loading ? "Đang tải…" : QUEUE_MSG.shown(list.rows.length, list.count)}
            </span>
          </div>
          {list.error != null && !list.loading && (
            <div className="alert-box err" role="alert">
              <Icon name="sync_problem" />
              <span>{loadErrorText(list.error)}</span>
            </div>
          )}
          {list.rows.length ? (
            <>
              <div className={`${s.head} ${s.qHead}`} aria-hidden="true">
                <span>{status === "OPEN" ? "Loại lệch" : "Cách xử lý"}</span>
                <span>Mã giao dịch</span>
                <span>Đơn liên quan</span>
                <span className={s.hAmt}>Số tiền</span>
              </div>
              <ul className={`${s.rows} queue-list`}>
                {list.rows.map((p) => (
                  <Row
                    key={p.id}
                    p={p}
                    onOpen={() => {
                      setToast(null);
                      pendingToast.current = null;
                      setOpenItem(p);
                    }}
                  />
                ))}
              </ul>
              {list.moreError != null && (
                <div className="alert-box err" role="alert">
                  <Icon name="error" />
                  <span>{loadErrorText(list.moreError)}</span>
                </div>
              )}
              {list.hasMore && (
                <div className={s.more}>
                  <button
                    type="button"
                    className="btn"
                    onClick={() => void list.loadMore()}
                    disabled={list.moreLoading}
                    aria-busy={list.moreLoading || undefined}
                  >
                    {list.moreLoading ? <Icon name="progress_activity" className="spin" /> : <Icon name="expand_more" />}
                    {list.moreLoading ? QUEUE_MSG.loadingMore : QUEUE_MSG.loadMore}
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className={`state ${s.emptyState}`}>
              <span className="state-ic">
                <Icon name={filtered ? "filter_alt_off" : status === "OPEN" ? "task_alt" : "inbox"} />
              </span>
              <h3 className="state-title">
                {filtered ? QUEUE_MSG.noMatchTitle : status === "OPEN" ? QUEUE_MSG.emptyOpenTitle : QUEUE_MSG.emptyResolvedTitle}
              </h3>
              <p>{filtered ? QUEUE_MSG.noMatchHint : status === "OPEN" ? QUEUE_MSG.emptyOpenHint : QUEUE_MSG.emptyResolvedHint}</p>
              {filtered ? (
                <button type="button" className="btn" onClick={() => setType("")}>
                  <Icon name="filter_alt_off" />
                  {QUEUE_MSG.showAllTypes}
                </button>
              ) : (
                <button type="button" className="btn" onClick={() => void list.reload()}>
                  <Icon name="refresh" />
                  Làm mới danh sách
                </button>
              )}
            </div>
          )}
        </section>
      )}

      {openItem && (
        <PaymentSheet
          key={openItem.id}
          item={openItem}
          onChanged={(message) => {
            changed.current = true;
            pendingToast.current = message;
          }}
          onOpenOrder={(o) => {
            setOpenItem(null);
            setOpenOrder(o);
          }}
          onClose={() => {
            setOpenItem(null);
            afterClose();
          }}
        />
      )}

      {openOrder && (
        <OrderDetailSheet
          key={`order-${openOrder.id}`}
          summary={orderSummary(openOrder)}
          onChanged={() => {
            changed.current = true; // vd xác nhận tiền trong chi tiết đơn → hàng chờ có thể đổi
          }}
          onClose={() => {
            setOpenOrder(null);
            afterClose();
          }}
        />
      )}

      {toast && !openItem && !openOrder && <Toast key={toast} message={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
