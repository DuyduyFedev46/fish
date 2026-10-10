"use client";

// Hàng chờ thanh toán (ED-11, tab 2 của "Đơn & tiền"): tiền về lệch với đơn. Bảng: Mã giao dịch · Số tiền · Loại khoản
// tiền (Khớp · Thiếu tiền · Về sau khi đơn tự huỷ · Không khớp đơn · Chuyển thừa) · Tình trạng xử lý (Chờ xử lý / Đã xử lý,
// cột riêng) · Đơn · Nhận lúc. Bấm dòng → /orders/payments/detail/?id=. Tìm kiếm chỉ lọc trong các dòng đã tải (BE chưa có
// tham số tìm cho hàng chờ). "Tình trạng xử lý" lưu ở ?state= (chỉ khoá, không dữ liệu cá nhân).

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { dateTime, vnd } from "@/shared/lib/format";
import { ENUMS } from "@/shared/lib/enums";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { PERM } from "@/shared/lib/nav";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { useTabParam } from "@/shared/ui/Tabs";
import { listPaymentQueue } from "../api";
import { hasDuplicateWarning } from "../latePayment";
import { QUEUE_TYPE_FILTERS } from "../labels";
import { ORDERS_MSG as M } from "../messages";
import type { PaymentQueueItem, PaymentQueueParams, ResolutionStatus } from "../types";
import s from "../orders.module.css";
import { OrdersSectionTabs } from "./OrdersSectionTabs";
import { RecordLatePaymentModal } from "./RecordLatePaymentModal";

const STATE_KEYS = ["open", "resolved"] as const;

/** Lọc trong các dòng đã tải theo mã giao dịch / mã đơn. */
export function filterPayments(rows: PaymentQueueItem[], q: string): PaymentQueueItem[] {
  const needle = q.trim().toLowerCase();
  if (!needle) return rows;
  return rows.filter((p) => p.bank_txn_id.toLowerCase().includes(needle) || (p.order?.code ?? "").toLowerCase().includes(needle));
}

export function PaymentQueueScreen() {
  const { me } = useAuth();
  const toast = useToast();
  const router = useRouter();
  const [lateOpen, setLateOpen] = useState(false);
  const [state, setState] = useTabParam(STATE_KEYS, "open", "state");
  const [type, setType] = useState("");
  const [q, setQ] = useState("");
  const status: ResolutionStatus = state === "resolved" ? "RESOLVED" : "OPEN";
  const params: PaymentQueueParams = useMemo(() => ({ resolution_status: status, match_status: type }), [status, type]);
  const list = usePagedList<PaymentQueueItem, PaymentQueueParams>(listPaymentQueue, params, !!me);

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission />;

  const rows = list.rows ? filterPayments(list.rows, q) : null;
  const columns: Column<PaymentQueueItem>[] = [
    { key: "txn", header: M.colTxn, mono: true, render: (p) => p.bank_txn_id },
    { key: "amount", header: M.colAmount, num: true, render: (p) => vnd(p.amount) },
    {
      key: "match",
      header: M.colMatch,
      render: (p) => (
        <>
          <Chip table={ENUMS.paymentMatchStatus} value={p.match_status} />
          {hasDuplicateWarning(p) && (
            <span className={s.dupFlag} title={p.duplicate_warning} data-duplicate-warning>
              <Icon name="warning" />
              <span className="sr-only">{M.dupBadge}: </span>
              <span className="sr-only">{p.duplicate_warning}</span>
            </span>
          )}
        </>
      ),
    },
    { key: "state", header: M.colResolution, render: (p) => <Chip table={ENUMS.paymentResolutionStatus} value={p.resolution_status} /> },
    { key: "order", header: M.colOrder, mono: true, render: (p) => p.order?.code ?? <span className="muted">{M.noOrder}</span> },
    { key: "at", header: M.colReceivedAt, tabular: true, render: (p) => dateTime(p.received_at) },
  ];
  // Chỉ người có "Xác nhận đã nhận tiền" thấy nút; BE vẫn chặn 403 (BR-TT-18).
  const canRecordLate = !!me?.permissions.includes(PERM.confirmPaymentManual);
  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;

  return (
    <ListPage
      tabs={<OrdersSectionTabs current="payments" />}
      actions={
        canRecordLate ? (
          <button type="button" className="btn primary" onClick={() => setLateOpen(true)} data-testid="record-late-open">
            <Icon name="add" />
            <span>{M.lateOpen}</span>
          </button>
        ) : null
      }
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder="Tìm mã giao dịch hoặc mã đơn"
          searchLabel={M.queueSearchLabel}
          selects={[
            {
              key: "state",
              label: M.queueTabsLabel,
              value: state,
              options: [
                { value: "open", label: M.queueOpenTab },
                { value: "resolved", label: M.queueResolvedTab },
              ],
              onChange: setState,
            },
            { key: "type", label: M.queueFilterType, value: type, options: QUEUE_TYPE_FILTERS, onChange: setType },
          ]}
          summary={list.rows ? M.queueShown(list.rows.length, list.count) : undefined}
        />
      }
      banner={
        refreshFailed ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(list.error)}</span>
          </div>
        ) : null
      }
      footer={
        <>
          {list.moreError != null && (
            <span className="field-err" role="alert">
              {M.loadMoreFailed} {loadErrorText(list.moreError)}
            </span>
          )}
          {list.hasMore && (
            <button type="button" className="btn" onClick={() => void list.loadMore()} disabled={list.moreLoading} aria-busy={list.moreLoading || undefined}>
              {list.moreLoading ? M.loadingMore : M.queueLoadMore}
            </button>
          )}
        </>
      }
    >
      <DataTable
        caption={M.queueTitle}
        title={M.queueHeadTitle}
        countText={rows ? M.queueHeadCount(list.count) : undefined}
        columns={columns}
        rows={rows}
        rowKey={(p) => p.id}
        rowHref={(p) => `/orders/payments/detail/?id=${p.id}`}
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={q}
        onClearQuery={() => setQ("")}
        noun={M.queueNoun}
        empty={
          status === "OPEN"
            ? { icon: "task_alt", title: M.queueEmptyOpenTitle, hint: M.queueEmptyOpenHint }
            : { icon: "inbox", title: M.queueEmptyResolvedTitle, hint: M.queueEmptyResolvedHint }
        }
        canViewCost={false}
      />
      {lateOpen && (
        <RecordLatePaymentModal
          onClose={() => setLateOpen(false)}
          onDone={(r) => {
            setLateOpen(false);
            if (r.duplicate) toast.warn(M.lateDoneDup(r.payment.bank_txn_id));
            else toast.success(M.lateDone(r.payment.bank_txn_id));
            router.push(`/orders/payments/detail/?id=${r.payment.id}`);
          }}
        />
      )}
    </ListPage>
  );
}
