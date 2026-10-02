"use client";

// Danh sách khách hàng (ED-14 / W5a): khung ListPage + bảng DataTable, bấm dòng → /customers/detail/?id=.
// Cột: Khách hàng · Số điện thoại (đủ) · Số đơn · Tổng đã mua · Đơn gần nhất · Ghi chú. Mặc định "Đơn gần nhất mới trước",
// khách chưa mua xếp cuối. Không có thanh AI. Từ khoá và thứ tự chỉ nằm trong state (không URL, không storage — quyết định #11);
// tìm theo số điện thoại không để lại dấu vết nào ngoài request tới BE.

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { dateTime, vnd } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { PersonalText } from "@/shared/ui/PersonalText";
import { DEFAULT_ORDERING, ORDERING_OPTIONS, asOrdering } from "../customersModel";
import { CUSTOMERS_MSG as M } from "../messages";
import type { CustomerListItem, CustomerListParams } from "../types";
import { useCustomerList } from "../useCustomerList";

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function CustomerListScreen() {
  const { me } = useAuth();
  const [q, setQ] = useState("");
  const [ordering, setOrdering] = useState(DEFAULT_ORDERING);
  const qDeb = useDebounced(q, 300).trim();
  const params: CustomerListParams = useMemo(() => ({ q: qDeb, ordering }), [qDeb, ordering]);
  const list = useCustomerList(params, !!me);

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission />;

  const columns: Column<CustomerListItem>[] = [
    { key: "name", header: M.colName, render: (c) => <PersonalText value={c.name} /> },
    { key: "phone", header: M.colPhone, mono: true, render: (c) => <PersonalText value={c.phone} /> },
    { key: "orders", header: M.colOrders, num: true, render: (c) => c.order_count },
    { key: "cancelled", header: M.colCancelled, num: true, render: (c) => c.cancelled_count },
    { key: "spent", header: M.colSpent, num: true, render: (c) => vnd(c.total_spent) },
    { key: "last", header: M.colLast, num: true, render: (c) => (c.last_order_at ? dateTime(c.last_order_at) : <span className="muted">—</span>) },
    { key: "note", header: M.colNote, render: (c) => (c.note ? <PersonalText value={c.note} /> : <span className="muted">—</span>) },
  ];

  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;

  return (
    <ListPage
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.searchPlaceholder}
          searchLabel={M.searchLabel}
          selects={[{ key: "ordering", label: M.sortLabel, value: ordering, options: ORDERING_OPTIONS, onChange: (v) => setOrdering(asOrdering(v)) }]}
          summary={list.rows ? M.shown(list.rows.length, list.count) : undefined}
        />
      }
      banner={
        refreshFailed ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(list.error)}</span>
          </div>
        ) : undefined
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
              {list.moreLoading ? M.loadingMore : M.loadMore}
            </button>
          )}
        </>
      }
    >
      <DataTable
        caption={M.listTitle}
        columns={columns}
        rows={list.rows ?? null}
        rowKey={(c) => c.id}
        rowHref={(c) => `/customers/detail/?id=${c.id}`}
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={qDeb}
        onClearQuery={() => setQ("")}
        noun={M.noun}
        empty={{ icon: qDeb ? "search_off" : "group", title: M.emptyTitle, hint: M.emptyHint }}
        canViewCost={false}
      />
    </ListPage>
  );
}
