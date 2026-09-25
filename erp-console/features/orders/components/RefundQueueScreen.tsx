"use client";

// S16 — Phiếu hoàn chờ chuyển (menu con "Phiếu hoàn chờ chuyển" của "Đơn & tiền", ưu tiên điện thoại). Danh sách
// GET /api/sales/refunds/?status=PENDING,FAILED (Chờ hoàn + Thất bại gộp chung — cả hai đều "đang chờ Lộc xử lý"),
// 20 dòng/trang + "Tải thêm". Bấm một phiếu → tấm chi tiết (RefundSheet) với nút theo `available_actions`: xác nhận đã
// chuyển, báo thất bại, thử lại (S16-AC7: Quản lý thấy danh sách nhưng không có nút vì thiếu sales.confirm_refund).
// Page bọc <ViewGuard view="refunds">.

import { useRef, useState } from "react";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { dateTime, vnd } from "@/shared/lib/format";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { ErrorBox } from "@/shared/ui/StateBox";
import { StatusChip } from "@/shared/ui/StatusChip";
import { Toast } from "@/shared/ui/Toast";
import { listRefundQueue } from "../api";
import { REFUND_LABEL, REFUND_STATUS, labelOf } from "../labels";
import { REFUND_Q_MSG } from "../messages";
import type { RefundQueueItem } from "../types";
import { usePagedList } from "../usePagedList";
import { OrdersTabs } from "./OrdersTabs";
import { RefundSheet } from "./RefundSheet";
import s from "../orders.module.css";

const NO_PARAMS: Record<string, never> = {};

function Row({ r, onOpen }: { r: RefundQueueItem; onOpen: () => void }) {
  const statusLabel = r.status_label || labelOf(REFUND_LABEL, r.status);
  return (
    <li className={s.row}>
      <button type="button" className={`${s.open} ${s.rOpen} refund-open`} onClick={onOpen} aria-haspopup="dialog" data-id={r.id}>
        <span className={s.rType}>
          <StatusChip map={REFUND_STATUS} status={r.status} label={statusLabel} />
        </span>
        <span className={`${s.cAmt} num`}>
          <span className="sr-only">, số tiền </span>
          <Figure text={vnd(r.amount)} />
        </span>
        <span className={s.rOrder}>
          {r.order_code ? (
            <>
              <span className="sr-only">, đơn </span>
              <code className={s.qCode}>{r.order_code}</code>
            </>
          ) : (
            <span className={s.sub}>{REFUND_Q_MSG.noOrder}</span>
          )}
          {r.customer_name && <span className={s.qCust}>{r.customer_name}</span>}
        </span>
        <span className={s.rCreated}>
          {r.created_by && (
            <span className={s.sub}>
              <span className="sr-only">, lập bởi </span>
              {r.created_by}
            </span>
          )}
          {r.created_at && (
            <span className={`${s.sub} num`}>
              <span className="sr-only">, lúc </span>
              {dateTime(r.created_at)}
            </span>
          )}
        </span>
      </button>
    </li>
  );
}

export function RefundQueueScreen() {
  const list = usePagedList<RefundQueueItem, Record<string, never>>(listRefundQueue, NO_PARAMS, true);
  const [openItem, setOpenItem] = useState<RefundQueueItem | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const pendingToast = useRef<string | null>(null);
  const changed = useRef(false);

  const forbidden = list.error instanceof ApiError && list.error.status === 403;

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
      <OrdersTabs current="refunds" />
      <p className="view-head">{REFUND_Q_MSG.intro}</p>

      {list.rows === undefined ? (
        list.error && !list.loading ? (
          <ErrorBox icon={forbidden ? "lock" : undefined} message={loadErrorText(list.error)} onRetry={() => void list.reload()} />
        ) : (
          <SkeletonScreen label={REFUND_Q_MSG.loading}>
            <SkeletonTable rows={5} cols={4} />
          </SkeletonScreen>
        )
      ) : (
        <section className="sect" aria-labelledby="refund-h" aria-busy={list.loading}>
          <div className="sect-h">
            <h2 id="refund-h">{REFUND_Q_MSG.listTitle}</h2>
            <span className="sub num" aria-live="polite">
              {list.loading ? "Đang tải…" : REFUND_Q_MSG.shown(list.rows.length, list.count)}
            </span>
            <button type="button" className="link" onClick={() => void list.reload()} disabled={list.loading}>
              <Icon name="refresh" className={list.loading ? "spin" : undefined} />
              {REFUND_Q_MSG.refresh}
            </button>
          </div>
          {list.error != null && !list.loading && (
            <div className="alert-box err" role="alert">
              <Icon name="sync_problem" />
              <span>{loadErrorText(list.error)}</span>
            </div>
          )}
          {list.rows.length ? (
            <>
              <div className={`${s.head} ${s.rHead}`} aria-hidden="true">
                <span>Trạng thái</span>
                <span>Đơn liên quan</span>
                <span>Lập lúc</span>
                <span className={s.hAmt}>Số tiền</span>
              </div>
              <ul className={`${s.rows} refund-list`}>
                {list.rows.map((r) => (
                  <Row
                    key={r.id}
                    r={r}
                    onOpen={() => {
                      setToast(null);
                      pendingToast.current = null;
                      setOpenItem(r);
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
                    {list.moreLoading ? REFUND_Q_MSG.loadingMore : REFUND_Q_MSG.loadMore}
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className={`state ${s.emptyState}`}>
              <span className="state-ic">
                <Icon name="task_alt" />
              </span>
              <h3 className="state-title">{REFUND_Q_MSG.emptyTitle}</h3>
              <p>{REFUND_Q_MSG.emptyHint}</p>
              <button type="button" className="btn" onClick={() => void list.reload()}>
                <Icon name="refresh" />
                Làm mới danh sách
              </button>
            </div>
          )}
        </section>
      )}

      {openItem && (
        <RefundSheet
          key={openItem.id}
          item={openItem}
          onChanged={(message) => {
            changed.current = true;
            pendingToast.current = message;
          }}
          onClose={() => {
            setOpenItem(null);
            afterClose();
          }}
        />
      )}

      {toast && !openItem && <Toast key={toast} message={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
