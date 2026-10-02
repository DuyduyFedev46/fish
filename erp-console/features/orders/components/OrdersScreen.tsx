"use client";

// Danh sách đơn hàng (ED-09, tab 1 của "Đơn & tiền"): khung ListPage + bảng DataTable, bấm dòng → /orders/detail/?id=.
// Cột: Mã đơn · Khách hàng · Trạng thái · Giao hàng · Lý do · Tổng tiền · Thời gian. Đơn tự huỷ hiện chip "Đã huỷ" kèm
// lý do "Hết giờ giữ chỗ". Bộ lọc/từ khoá chỉ nằm trong state (không URL, không localStorage). `?order=<id>&open=refund`
// (link cũ từ màn gọi xác nhận) → chuyển sang trang chi tiết, mở sẵn hộp "Lập phiếu hoàn".

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { dateTime, vnd } from "@/shared/lib/format";
import { ENUMS } from "@/shared/lib/enums";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { PersonalText } from "@/shared/ui/PersonalText";
import { DATE_FILTERS, STATUS_FILTERS, type DatePreset } from "../labels";
import { effectiveOrderStatus } from "../orderDetailModel";
import { legacyOrderRedirect, presetRange, reasonText } from "../filters";
import { ORDERS_MSG as M } from "../messages";
import type { OrderListItem, OrderListParams } from "../types";
import { useNow } from "../useNow";
import { useOrderList } from "../useOrderList";
import { OrdersSectionTabs } from "./OrdersSectionTabs";

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function OrdersScreen() {
  const { me } = useAuth();
  const router = useRouter();
  const [redirecting, setRedirecting] = useState(false);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [preset, setPreset] = useState<DatePreset>("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const qDeb = useDebounced(q, 300).trim();
  const badRange = preset === "custom" && !!from && !!to && from > to;
  const params: OrderListParams = useMemo(
    () => ({ status, q: qDeb, ...(badRange ? { date_from: "", date_to: "" } : presetRange(preset, from, to)) }),
    [status, qDeb, preset, from, to, badRange],
  );

  useEffect(() => {
    const target = legacyOrderRedirect(window.location.search);
    if (target) {
      setRedirecting(true);
      router.replace(target);
    }
  }, [router]);

  const list = useOrderList(params, !!me && !redirecting && !badRange);
  const now = useNow(!!list.rows?.some((o) => o.status === "BOOKED"), 5000);

  if (redirecting) return null;
  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission />;

  const columns: Column<OrderListItem>[] = [
    { key: "code", header: M.colCode, mono: true, render: (o) => o.code },
    { key: "customer", header: M.colCustomer, render: (o) => <PersonalText value={o.customer_name} /> },
    { key: "status", header: M.colStatus, render: (o) => <Chip table={ENUMS.salesOrderStatus} value={effectiveOrderStatus(o.status, o.reserved_until, now)} /> },
    { key: "delivery", header: M.colDelivery, render: (o) => <Chip table={ENUMS.deliveryStatus} value={o.delivery_status} /> },
    {
      key: "reason",
      header: M.colReason,
      render: (o) => reasonText(o.reason, effectiveOrderStatus(o.status, o.reserved_until, now)) ?? <span className="muted">—</span>,
    },
    { key: "total", header: M.colTotal, num: true, render: (o) => vnd(o.total_amount) },
    { key: "time", header: M.colTime, tabular: true, render: (o) => dateTime(o.created_at) },
  ];

  const filtered = !!(status || qDeb || params.date_from || params.date_to);
  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;

  return (
    <ListPage
      tabs={<OrdersSectionTabs current="orders" />}
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.searchPlaceholder}
          searchLabel={M.searchLabel}
          selects={[
            { key: "status", label: M.filterStatus, value: status, options: STATUS_FILTERS, onChange: setStatus },
            { key: "date", label: M.filterDate, value: preset, options: DATE_FILTERS, onChange: (v) => setPreset(v as DatePreset) },
          ]}
          dateRange={preset === "custom" ? { from, to, onFrom: setFrom, onTo: setTo } : undefined}
          summary={list.rows ? M.shownOrders(list.rows.length, list.count) : undefined}
        />
      }
      banner={
        <>
          {badRange && (
            <div className="alert-box warn" role="status">
              <Icon name="warning" />
              <span>{M.dateRangeInvalid}</span>
            </div>
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
              {list.moreLoading ? M.loadingMore : M.loadMoreOrders}
            </button>
          )}
        </>
      }
    >
      <DataTable
        caption={M.ordersTitle}
        columns={columns}
        rows={list.rows ?? null}
        rowKey={(o) => o.id}
        rowHref={(o) => `/orders/detail/?id=${o.id}`}
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={qDeb}
        onClearQuery={() => setQ("")}
        noun={M.nounOrders}
        empty={{ icon: filtered ? "search_off" : "inbox", title: M.emptyTitle, hint: M.emptyHint }}
        canViewCost={false}
      />
    </ListPage>
  );
}
