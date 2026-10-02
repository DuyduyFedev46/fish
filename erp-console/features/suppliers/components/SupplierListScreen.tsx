"use client";

// Danh sách nhà cung cấp (ED-22 / W5c): khung ListPage + bảng DataTable, bấm dòng → /suppliers/detail/?id=.
// Cột: Nhà cung cấp · Loại · Số điện thoại (đủ: dữ liệu đối tác) · Số phiếu nhập · Lần nhập gần nhất · Trạng thái · Tổng tiền mua (khoá, CHỈ Chủ:
// cột không có trong DOM với người khác). Số phiếu / lần nhập / tổng tiền chỉ tính phiếu Đã ghi nhận. Nút "Thêm nhà cung cấp" chỉ khi có
// purchasing.add_supplier. Từ khoá và bộ lọc chỉ nằm trong state (không URL, không storage).

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, vnd } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { SUPPLIERS_MSG as M } from "../messages";
import { ACTIVE_OPTIONS, TYPE_OPTIONS, asActiveFilter, asTypeFilter } from "../suppliersModel";
import type { Supplier, SupplierListParams } from "../types";
import { useSupplierList } from "../useSupplierList";
import { SupplierFormModal } from "./SupplierFormModal";

const PERM_ADD_SUPPLIER = "purchasing.add_supplier";

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function SupplierListScreen() {
  const { me } = useAuth();
  const toast = useToast();
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [active, setActive] = useState("");
  const [adding, setAdding] = useState(false);
  const qDeb = useDebounced(q, 300).trim();
  const params: SupplierListParams = useMemo(() => ({ q: qDeb, type, active }), [qDeb, type, active]);
  const list = useSupplierList(params, !!me);
  const canAdd = !!me?.permissions.includes(PERM_ADD_SUPPLIER);
  const canViewCost = !!me?.can_view_cost;

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission />;

  const columns: Column<Supplier>[] = [
    { key: "name", header: M.colName, render: (r) => r.name },
    { key: "type", header: M.colType, render: (r) => r.supplier_type_label || <span className="muted">—</span> },
    { key: "phone", header: M.colPhone, mono: true, render: (r) => r.phone || <span className="muted">—</span> },
    { key: "receipts", header: M.colReceipts, num: true, render: (r) => r.receipt_count },
    { key: "last", header: M.colLast, tabular: true, render: (r) => (r.last_received_at ? dateTime(r.last_received_at) : <span className="muted">—</span>) },
    { key: "status", header: M.colStatus, render: (r) => <Chip table={ENUMS.supplierActive} value={r.is_active} /> },
    { key: "total", header: M.colTotal, num: true, locked: true, render: (r) => (r.purchase_total === undefined ? <span className="muted">—</span> : vnd(r.purchase_total)) },
  ];

  const filtered = !!(type || active);
  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;

  return (
    <ListPage
      actions={
        canAdd ? (
          <button type="button" className="btn primary" onClick={() => setAdding(true)}>
            <Icon name="add" />
            <span>{M.add}</span>
          </button>
        ) : undefined
      }
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.searchPlaceholder}
          searchLabel={M.searchLabel}
          selects={[
            { key: "type", label: M.typeLabel, value: type, options: TYPE_OPTIONS, onChange: (v) => setType(asTypeFilter(v)) },
            { key: "active", label: M.activeLabel, value: active, options: ACTIVE_OPTIONS, onChange: (v) => setActive(asActiveFilter(v)) },
          ]}
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
        title={M.listTitle}
        countText={list.rows ? M.headCount(list.count) : undefined}
        columns={columns}
        rows={list.rows ?? null}
        rowKey={(r) => r.id}
        rowHref={(r) => `/suppliers/detail/?id=${r.id}`}
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={qDeb}
        onClearQuery={() => setQ("")}
        noun={M.noun}
        empty={{
          icon: filtered ? "filter_list_off" : "storefront",
          title: filtered ? M.emptyFilteredTitle : M.emptyTitle,
          hint: filtered ? M.emptyFilteredHint : M.emptyHint,
          action: canAdd && !filtered ? (
            <button type="button" className="btn primary" onClick={() => setAdding(true)}>
              {M.add}
            </button>
          ) : undefined,
        }}
        canViewCost={canViewCost}
      />
      {adding && (
        <SupplierFormModal
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false);
            toast.success(M.created);
            void list.reload();
          }}
        />
      )}
    </ListPage>
  );
}
