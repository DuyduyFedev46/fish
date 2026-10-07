"use client";

// Phiếu hoàn tiền (ED-12, tab 3 của "Đơn & tiền"). Chip Chờ hoàn · Đã hoàn · Thất bại; cột "Số tiền hoàn". Mặc định hiện phiếu
// còn phải chuyển (Chờ hoàn + Thất bại); lọc theo tháng (`month=YYYY-MM`) thì có thêm câu tổng tiền của tháng đó theo từng trạng thái (Chờ hoàn, Đã hoàn; không tính Thất bại).
// Quản lý xem được danh sách, không có nút xử lý (BE trả `available_actions` rỗng). Bấm dòng → /orders/refunds/detail/?id=.

import { useEffect, useMemo, useState } from "react";
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
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { listRefunds } from "../api";
import { recentMonths } from "../filters";
import { ORDERS_MSG as M } from "../messages";
import type { RefundListParams, RefundQueueItem } from "../types";
import { OrdersSectionTabs } from "./OrdersSectionTabs";
import s from "../orders.module.css";

const STATUS_OPTIONS = [
  { value: "PENDING,FAILED", label: `Chờ chuyển (${ENUMS.refundStatus.PENDING.label}, ${ENUMS.refundStatus.FAILED.label})` },
  { value: "PENDING", label: ENUMS.refundStatus.PENDING.label },
  { value: "FAILED", label: ENUMS.refundStatus.FAILED.label },
  { value: "REFUNDED", label: ENUMS.refundStatus.REFUNDED.label },
  { value: "", label: "Mọi trạng thái" },
];

export type MonthPart = { status: "PENDING" | "REFUNDED"; count: number; total: string };

/**
 * Cộng tiền phiếu hoàn tiền theo TỪNG trạng thái (Chờ hoàn, Đã hoàn) để câu tổng nói rõ đang cộng những phiếu nào theo bộ lọc.
 * Phiếu Thất bại không tính (tiền chưa rời túi), chỉ đếm riêng để câu chữ nhắc. Số tiền là chuỗi, cộng bằng số nguyên đồng.
 */
export function monthBreakdown(rows: readonly RefundQueueItem[]): { parts: MonthPart[]; failedCount: number } {
  const parts: MonthPart[] = [];
  for (const status of ["PENDING", "REFUNDED"] as const) {
    const hit = rows.filter((r) => r.status === status);
    if (hit.length > 0) parts.push({ status, count: hit.length, total: String(hit.reduce((sum, r) => sum + Math.round(Number(r.amount) || 0), 0)) });
  }
  return { parts, failedCount: rows.filter((r) => r.status === "FAILED").length };
}

export function RefundQueueScreen() {
  const { me } = useAuth();
  const [status, setStatus] = useState("PENDING,FAILED");
  const [month, setMonth] = useState("");
  const [q, setQ] = useState("");
  const params: RefundListParams = useMemo(() => ({ status, month }), [status, month]);
  const list = usePagedList<RefundQueueItem, RefundListParams>(listRefunds, params, !!me);
  const months = useMemo(() => recentMonths(), []);

  // Có lọc tháng → tải hết các trang để dòng tổng đúng cho cả tháng.
  useEffect(() => {
    if (month && list.hasMore && !list.moreLoading && !list.loading && list.moreError == null) void list.loadMore();
  }, [month, list]);

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission />;

  const needle = q.trim().toLowerCase();
  const rows = list.rows
    ? needle
      ? list.rows.filter((r) => (r.order_code ?? "").toLowerCase().includes(needle) || String(r.id).includes(needle))
      : list.rows
    : null;
  const summary = month && list.rows && !list.hasMore ? monthBreakdown(list.rows) : null;
  const monthLabel = months.find((m) => m.value === month)?.label ?? month;

  const columns: Column<RefundQueueItem>[] = [
    { key: "id", header: M.colRefundId, mono: true, render: (r) => `#${r.id}` },
    { key: "order", header: M.colRefundOrder, mono: true, render: (r) => r.order_code ?? <span className="muted">{M.noInvoice}</span> },
    { key: "status", header: M.colStatus, render: (r) => <Chip table={ENUMS.refundStatus} value={r.status} /> },
    { key: "amount", header: M.colRefundAmount, num: true, render: (r) => vnd(r.amount) },
    { key: "at", header: M.colRefundCreatedAt, tabular: true, render: (r) => dateTime(r.created_at) },
  ];
  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;

  return (
    <ListPage
      tabs={<OrdersSectionTabs current="refunds" />}
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder="Tìm mã đơn hoặc số phiếu"
          searchLabel={M.refundsSearchLabel}
          selects={[
            { key: "status", label: M.refundsFilterStatus, value: status, options: STATUS_OPTIONS, onChange: setStatus },
            { key: "month", label: M.refundsFilterMonth, value: month, options: [{ value: "", label: "Mọi tháng" }, ...months], onChange: setMonth },
          ]}
          summary={list.rows ? M.refundsShown(list.rows.length, list.count) : undefined}
        />
      }
      banner={
        <>
          {summary && (
            <p className={`${s.summaryLine} num`} role="status">
              {M.refundsMonthSummary(monthLabel, summary.parts, summary.failedCount)}
            </p>
          )}
          {refreshFailed && (
            <div className="alert-box err" role="alert">
              <Icon name="sync_problem" />
              <span>{loadErrorText(list.error)}</span>
            </div>
          )}
        </>
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
              {list.moreLoading ? M.loadingMore : M.refundsLoadMore}
            </button>
          )}
        </>
      }
    >
      <DataTable
        caption={M.refundsListTitle}
        title={M.refundsListTitle}
        countText={list.rows ? M.refundsHeadCount(list.count) : undefined}
        columns={columns}
        rows={rows}
        rowKey={(r) => r.id}
        rowHref={(r) => `/orders/refunds/detail/?id=${r.id}`}
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={q}
        onClearQuery={() => setQ("")}
        noun={M.refundsNoun}
        empty={
          month
            ? { icon: "inbox", title: M.refundsEmptyMonthTitle, hint: M.refundsEmptyMonthHint }
            : { icon: "task_alt", title: M.refundsEmptyTitle, hint: M.refundsEmptyHint }
        }
        canViewCost={false}
      />
    </ListPage>
  );
}
