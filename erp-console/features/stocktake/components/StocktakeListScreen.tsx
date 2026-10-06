"use client";

// ED-28 W2c — Danh sách phiếu kiểm kê (Chủ, Quản lý, NV kho). Khung ListPage: nút "Lập phiếu kiểm kê", thanh lọc (kho, trạng thái),
// bảng một ô một giá trị, "Tải thêm". Bấm một dòng → /stocktake/detail/?id=<số>. Không có số tiền: chỉ kg (bất biến 1).
// Tìm kiếm chạy trên các dòng đã tải (mã phiếu, người nhập, người duyệt, ghi chú); từ khoá không đi đâu (không URL, không localStorage).
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly } from "@/shared/lib/format";
import { loadErrorText } from "@/shared/lib/http";
import { PERM } from "@/shared/lib/nav";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { fetchStocktakes, fetchWarehouses } from "../api";
import { NEW_HREF, detailHref, qtyText, warehouseText } from "../stocktakeUi";
import type { StocktakeListItem, WarehouseOption } from "../types";
import s from "../stocktake.module.css";

type Params = { status: string; warehouse: string };

const ALL = "";

function matches(row: StocktakeListItem, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return [row.code, row.created_by?.display_name, row.approved_by?.display_name, row.note].some((v) => (v || "").toLowerCase().includes(needle));
}

export function StocktakeListScreen() {
  const { me } = useAuth();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState(ALL);
  const [warehouse, setWarehouse] = useState(ALL);
  const [warehouses, setWarehouses] = useState<WarehouseOption[]>([]);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchWarehouses(ctrl.signal)
      .then(setWarehouses)
      .catch(() => {
        // Không tải được danh sách kho: bộ lọc kho chỉ còn "Mọi kho", bảng vẫn dùng được.
      });
    return () => ctrl.abort();
  }, []);

  const params: Params = useMemo(() => ({ status, warehouse }), [status, warehouse]);
  const list = usePagedList<StocktakeListItem, Params>((p, page) => fetchStocktakes({ ...p, page }), params, true);

  const rows = list.rows;
  const shown = useMemo(() => (rows ? rows.filter((r) => matches(r, query)) : null), [rows, query]);
  const filtered = Boolean(query.trim() || status || warehouse);
  const pending = rows ? rows.filter((r) => r.status === "SUBMITTED").length : 0;
  const mayCreate = Boolean(me?.permissions.includes(PERM.addStockReconciliation));
  const errorText = list.error && !list.rows ? loadErrorText(list.error) : null;

  const columns: Column<StocktakeListItem>[] = [
    { key: "code", header: "Mã phiếu", mono: true, render: (r) => r.code, width: "104px" },
    { key: "date", header: "Ngày", tabular: true, render: (r) => dateOnly(r.count_date), width: "112px" },
    { key: "wh", header: "Kho", render: (r) => warehouseText(r.warehouse_names) },
    { key: "lines", header: "Số lô", num: true, render: (r) => r.line_count, width: "72px" },
    {
      key: "short",
      header: "Hụt (kg)",
      num: true,
      render: (r) => (r.short_count > 0 ? <span className={s.short}>−{qtyText(r.short_qty)}</span> : <span className="muted">—</span>),
      width: "96px",
    },
    {
      key: "over",
      header: "Dư (kg)",
      num: true,
      render: (r) => (r.over_count > 0 ? <span className={s.over}>+{qtyText(r.over_qty)}</span> : <span className="muted">—</span>),
      width: "96px",
    },
    { key: "by", header: "Người nhập số", hideBelow: 800, render: (r) => r.created_by?.display_name || "—", width: "130px" },
    { key: "approver", header: "Người duyệt", hideBelow: 980, render: (r) => r.approved_by?.display_name || "—", width: "130px" },
    { key: "status", header: "Trạng thái", render: (r) => <Chip table={ENUMS.stockReconciliationStatus} value={r.status} />, width: "120px" },
    { key: "note", header: "Ghi chú", hideBelow: 980, render: (r) => r.note || "—" },
  ];

  return (
    <ListPage
      id="stocktake-panel"
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      actions={
        mayCreate ? (
          <Link href={NEW_HREF} className="btn primary">
            <Icon name="add" />
            <span>Lập phiếu kiểm kê</span>
          </Link>
        ) : undefined
      }
      filters={
        <FilterBar
          query={query}
          onQuery={setQuery}
          placeholder="Tìm mã phiếu, người nhập, ghi chú"
          searchLabel="Tìm phiếu kiểm kê"
          selects={[
            {
              key: "warehouse",
              label: "Lọc theo kho",
              value: warehouse,
              onChange: setWarehouse,
              options: [{ value: ALL, label: "Mọi kho" }, ...warehouses.map((w) => ({ value: String(w.id), label: w.name }))],
            },
            {
              key: "status",
              label: "Lọc theo trạng thái",
              value: status,
              onChange: setStatus,
              options: [
                { value: ALL, label: "Mọi trạng thái" },
                { value: "DRAFT", label: ENUMS.stockReconciliationStatus.DRAFT.label },
                { value: "SUBMITTED", label: ENUMS.stockReconciliationStatus.SUBMITTED.label },
                { value: "APPROVED", label: ENUMS.stockReconciliationStatus.APPROVED.label },
              ],
            },
          ]}
          summary={shown && rows ? `Đang hiện ${shown.length} / ${list.count} phiếu${pending > 0 && !status ? ` · ${pending} chờ duyệt` : ""}` : undefined}
        />
      }
      footer={
        list.hasMore ? (
          <button type="button" className="btn" onClick={() => void list.loadMore()} disabled={list.moreLoading}>
            {list.moreLoading ? <Icon name="progress_activity" className="spin" /> : null}
            <span>{list.moreLoading ? "Đang tải…" : "Tải thêm"}</span>
          </button>
        ) : undefined
      }
      banner={
        list.moreError != null ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>Chưa tải thêm được. Bấm Tải thêm để thử lại.</span>
          </div>
        ) : list.error && list.rows ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(list.error)}</span>
          </div>
        ) : undefined
      }
    >
      <DataTable
        title="Phiếu kiểm kê"
        countText={rows ? (pending > 0 ? `${pending} chờ duyệt` : `${list.count} phiếu`) : undefined}
        columns={columns}
        rows={shown}
        rowKey={(r) => r.id}
        rowHref={(r) => detailHref(r.id)}
        loading={list.loading && !list.rows}
        error={errorText}
        onRetry={() => void list.reload()}
        query={query}
        onClearQuery={() => setQuery("")}
        noun="phiếu kiểm kê"
        dense
        empty={{
          icon: "fact_check",
          title: filtered ? "Không có phiếu nào khớp bộ lọc" : "Chưa có phiếu kiểm kê nào",
          hint: filtered ? "Bỏ bớt bộ lọc để xem lại các phiếu đã tải." : "Phiếu mới sẽ hiện ở đây sau khi có người nhập số đếm.",
          action:
            !filtered && mayCreate ? (
              <Link href={NEW_HREF} className="btn primary">
                Lập phiếu kiểm kê
              </Link>
            ) : undefined,
        }}
        canViewCost={false}
        caption="Danh sách phiếu kiểm kê"
      />
    </ListPage>
  );
}
