"use client";

// Màn Đơn & tiền (S10) — thay list 8 đơn của dashboard bằng danh sách thật GET /api/sales/orders/: lọc trạng thái, khoảng
// ngày, tìm mã đơn / SĐT (BE lọc, khớp một phần), 20 dòng/trang + "Tải thêm". Bấm một đơn → chi tiết trong tấm bên
// (phải trên máy tính, trượt đáy trên điện thoại). Thao tác trên đơn (S11 xác nhận đã nhận tiền) nằm trong chi tiết,
// chỉ hiện theo `available_actions` BE trả. Page bọc <ViewGuard view="orders"> (sales.view_salesorder, không phải người
// chỉ thuộc nv_giao).

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { dateTime, remaining, vnd } from "@/shared/lib/format";
import { ORDER_STATUS } from "@/shared/lib/status";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { ErrorBox } from "@/shared/ui/StateBox";
import { StatusChip } from "@/shared/ui/StatusChip";
import { Toast } from "@/shared/ui/Toast";
import { Toolbar } from "@/shared/ui/Toolbar";
import { DATE_FILTERS, DELIVERY_LABEL, STATUS_FILTERS, type DatePreset } from "../labels";
import { ORDERS_MSG } from "../messages";
import type { OrderListItem, OrderListParams } from "../types";
import { useNow } from "../useNow";
import { useOrderList } from "../useOrderList";
import { OrderDetailSheet } from "./OrderDetailSheet";
import s from "../orders.module.css";

/** YYYY-MM-DD theo giờ Việt Nam (BE lọc ngày theo Asia/Ho_Chi_Minh). */
function vnDate(ms: number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Ho_Chi_Minh" }).format(new Date(ms));
}

function presetRange(p: DatePreset, from: string, to: string): { date_from: string; date_to: string } {
  const now = Date.now();
  const day = 86_400_000;
  if (p === "today") return { date_from: vnDate(now), date_to: vnDate(now) };
  if (p === "7d") return { date_from: vnDate(now - 6 * day), date_to: vnDate(now) };
  if (p === "30d") return { date_from: vnDate(now - 29 * day), date_to: vnDate(now) };
  if (p === "custom") return { date_from: from, date_to: to };
  return { date_from: "", date_to: "" };
}

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

function Row({ o, now, onOpen }: { o: OrderListItem; now: number; onOpen: () => void }) {
  const booked = o.status === "BOOKED";
  const left = booked ? remaining(o.reserved_until, now) : null;
  // Trạng thái phiếu giao chỉ thêm thông tin khi đơn đang được xử lý (đơn Hoàn tất thì "Hoàn tất" lặp lại).
  const delivery =
    o.delivery_status && o.status !== "COMPLETED" ? DELIVERY_LABEL[o.delivery_status] || o.delivery_status : null;
  const last4 = o.customer_phone ? o.customer_phone.slice(-4) : "";
  return (
    <li className={s.row}>
      <button type="button" className={`${s.open} order-open`} onClick={onOpen} aria-haspopup="dialog" data-id={o.id}>
        <span className={s.cCode}>{o.code}</span>
        <span className={s.cCust}>
          <b>{o.customer_name}</b>
          {last4 && (
            <span className={`${s.phone} num`}>
              <span className="sr-only">, số điện thoại đuôi </span>…{last4}
            </span>
          )}
          {o.needs_attention && (
            <span className={s.attn}>
              <Icon name="error" />
              <span className="sr-only">, {ORDERS_MSG.needsAttention}</span>
            </span>
          )}
        </span>
        <span className={`${s.cWhen} num`}>
          <span className="sr-only">, đặt lúc </span>
          {dateTime(o.created_at)}
        </span>
        <span className={`${s.cAmt} num`}>
          <span className="sr-only">, giá trị </span>
          <Figure text={vnd(o.total_amount)} />
        </span>
        <span className={s.cStatus}>
          <span className="sr-only">, trạng thái </span>
          <StatusChip map={ORDER_STATUS} status={o.status} label={o.status_label} />
          {left ? (
            <span className={`${s.sub} ${s.subWarn} num`}>
              <span className="sr-only">, giữ chỗ </span>còn {left}
            </span>
          ) : delivery ? (
            <span className={s.sub}>
              <span className="sr-only">, giao hàng: </span>
              {delivery}
            </span>
          ) : null}
        </span>
      </button>
    </li>
  );
}

export function OrdersScreen() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [preset, setPreset] = useState<DatePreset>("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const qDeb = useDebounced(q, 300);
  const range = presetRange(preset, from, to);
  const badRange = preset === "custom" && !!from && !!to && from > to;
  const params: OrderListParams = useMemo(
    () => ({ status, q: qDeb.trim(), ...(badRange ? { date_from: "", date_to: "" } : range) }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [status, qDeb, preset, from, to, badRange],
  );
  const list = useOrderList(params, !badRange);
  const filtered = !!(status || params.q || params.date_from || params.date_to);
  const now = useNow(!!list.rows?.some((o) => o.status === "BOOKED"), 30_000);

  const [openRow, setOpenRow] = useState<OrderListItem | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const pendingToast = useRef<string | null>(null);
  const statusId = useId();
  const dateId = useId();

  const clearFilters = () => {
    setQ("");
    setStatus("");
    setPreset("all");
    setFrom("");
    setTo("");
  };

  const forbidden = list.error instanceof ApiError && list.error.status === 403;

  return (
    <div className="screen">
      <p className="view-head">Vòng đời: giữ chỗ (có hạn) → thanh toán → xử lý → hoàn tất. Bấm một đơn để xem tiền, giao hàng và hoàn tiền.</p>

      <div className={s.bar}>
        <Toolbar
          query={q}
          onQuery={setQ}
          placeholder={ORDERS_MSG.searchPlaceholder}
          onRefresh={() => void list.reload()}
          refreshing={list.loading}
        />
        <div className={s.filters} role="group" aria-label="Lọc đơn">
          <div className={s.select}>
            <label htmlFor={statusId} className="sr-only">
              Trạng thái
            </label>
            <select id={statusId} name="status" value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUS_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
            <Icon name="expand_more" />
          </div>
          <div className={s.select}>
            <label htmlFor={dateId} className="sr-only">
              Ngày đặt
            </label>
            <select id={dateId} name="date" value={preset} onChange={(e) => setPreset(e.target.value as DatePreset)}>
              {DATE_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
            <Icon name="expand_more" />
          </div>
        </div>
        {preset === "custom" && (
          <div className={s.range}>
            <div className="field">
              <label htmlFor={`${dateId}-from`}>Từ ngày</label>
              <input
                id={`${dateId}-from`}
                type="date"
                value={from}
                max={to || undefined}
                onChange={(e) => setFrom(e.target.value)}
                aria-invalid={badRange || undefined}
                aria-describedby={badRange ? `${dateId}-err` : undefined}
              />
            </div>
            <div className="field">
              <label htmlFor={`${dateId}-to`}>Đến ngày</label>
              <input
                id={`${dateId}-to`}
                type="date"
                value={to}
                min={from || undefined}
                onChange={(e) => setTo(e.target.value)}
                aria-invalid={badRange || undefined}
                aria-describedby={badRange ? `${dateId}-err` : undefined}
              />
            </div>
            {badRange && (
              <p className="field-err" id={`${dateId}-err`} role="alert">
                <Icon name="error" />
                {ORDERS_MSG.dateRangeInvalid}
              </p>
            )}
          </div>
        )}
      </div>

      {list.rows === undefined ? (
        list.error && !list.loading ? (
          <ErrorBox icon={forbidden ? "lock" : undefined} message={loadErrorText(list.error)} onRetry={() => void list.reload()} />
        ) : (
          <SkeletonScreen label="Đang tải danh sách đơn…">
            <SkeletonTable rows={8} cols={5} />
          </SkeletonScreen>
        )
      ) : (
        <section className={`sect ${s.list}`} aria-labelledby="orders-h" aria-busy={list.loading}>
          <div className="sect-h">
            <h2 id="orders-h">Đơn hàng</h2>
            <span className="sub num" aria-live="polite">
              {list.loading ? "Đang tải…" : ORDERS_MSG.shown(list.rows.length, list.count)}
            </span>
          </div>
          {list.error != null && !list.loading && (
            <div className="alert-box err" role="alert">
              <Icon name="sync_problem" />
              <span>
                {ORDERS_MSG.refreshFailed} {loadErrorText(list.error)}
              </span>
            </div>
          )}
          {list.rows.length ? (
            <>
              <div className={s.head} aria-hidden="true">
                <span>Mã đơn</span>
                <span>Khách</span>
                <span>Đặt lúc</span>
                <span className={s.hAmt}>Giá trị</span>
                <span>Trạng thái</span>
              </div>
              <ul className={`${s.rows} order-list`}>
                {list.rows.map((o) => (
                  <Row
                    key={o.id}
                    o={o}
                    now={now}
                    onOpen={() => {
                      setToast(null);
                      pendingToast.current = null;
                      setOpenRow(o);
                    }}
                  />
                ))}
              </ul>
              {list.moreError != null && (
                <div className="alert-box err" role="alert">
                  <Icon name="error" />
                  <span>
                    {ORDERS_MSG.loadMoreFailed} {loadErrorText(list.moreError)}
                  </span>
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
                    {list.moreLoading ? ORDERS_MSG.loadingMore : ORDERS_MSG.loadMore}
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className={`state ${s.emptyState}`}>
              <span className="state-ic">
                <Icon name={filtered ? "search_off" : "inbox"} />
              </span>
              <h3 className="state-title">{filtered ? ORDERS_MSG.noMatchTitle : ORDERS_MSG.emptyTitle}</h3>
              <p>{filtered ? ORDERS_MSG.noMatchHint : ORDERS_MSG.emptyHint}</p>
              {filtered ? (
                <button type="button" className="btn" onClick={clearFilters}>
                  <Icon name="filter_alt_off" />
                  Bỏ lọc
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

      {openRow && (
        <OrderDetailSheet
          key={openRow.id}
          summary={openRow}
          onChanged={(change, message) => {
            list.patch(openRow.id, change);
            if (message) pendingToast.current = message;
          }}
          onClose={() => {
            setOpenRow(null);
            if (pendingToast.current) {
              setToast(pendingToast.current);
              pendingToast.current = null;
            }
          }}
        />
      )}

      {toast && !openRow && <Toast key={toast} message={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
