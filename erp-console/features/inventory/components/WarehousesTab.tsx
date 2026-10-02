"use client";

// Tab "Kho" (W5l, ED-25): danh sách kho từ R7 + nút "Thêm kho" (F3m) chỉ cho Chủ (inventory.add_warehouse).
import { useState } from "react";
import type { Me } from "@/features/auth/types";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { kg } from "@/shared/lib/format";
import { ENUMS } from "@/shared/lib/enums";
import { PERM } from "@/shared/lib/nav";
import { matches } from "@/shared/lib/search";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { fetchWarehouses } from "../api";
import type { Warehouse } from "../types";
import { AddWarehouseModal } from "./AddWarehouseModal";
import s from "../inventory.module.css";

const NO_PARAMS = {};

export function WarehousesTab({ tabs, me }: { tabs: React.ReactNode; me: Me }) {
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const list = usePagedList<Warehouse, Record<string, never>>(fetchWarehouses_, NO_PARAMS, true);
  const canAdd = me.permissions.includes(PERM.addWarehouse);

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission homeHref="/overview/" />;

  const rows = list.rows ? (query.trim() ? list.rows.filter((w) => matches(query, w.name, w.is_group_label)) : list.rows) : null;
  const columns: Column<Warehouse>[] = [
    { key: "name", header: "Tên kho", render: (w) => w.name },
    { key: "kind", header: "Loại", render: (w) => <Chip table={ENUMS.warehouseKind} value={String(w.is_group)} /> },
    { key: "batches", header: "Số lô đang có", num: true, render: (w) => String(w.active_batch_count) },
    { key: "qty", header: "Tổng tồn (kg)", num: true, render: (w) => kg(w.total_qty) },
  ];

  return (
    <ListPage
      id="inventory-panel"
      tabs={tabs}
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      actions={
        canAdd ? (
          <button type="button" className="btn primary" onClick={() => setAdding(true)}>
            <Icon name="add" />
            Thêm kho
          </button>
        ) : undefined
      }
      filters={
        <div className={s.filters}>
          <FilterBar
            query={query}
            onQuery={setQuery}
            placeholder="Tìm tên kho"
            searchLabel="Tìm kho"
            summary={rows ? `Đang hiện ${rows.length} / ${list.count} kho` : undefined}
          />
        </div>
      }
    >
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(w) => w.id}
        loading={list.loading && !list.rows}
        error={list.error ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={query}
        onClearQuery={() => setQuery("")}
        noun="kho hàng"
        empty={{ icon: "warehouse", title: "Chưa có kho nào", hint: canAdd ? "Bấm Thêm kho để tạo kho đầu tiên." : "Chủ vựa tạo kho khi cần." }}
        canViewCost={false}
        caption="Danh sách kho"
      />
      {adding && (
        <AddWarehouseModal
          onClose={() => setAdding(false)}
          onDone={(name) => {
            setAdding(false);
            toast.success(`Đã thêm kho ${name}.`);
            void list.reload();
          }}
        />
      )}
    </ListPage>
  );
}

function fetchWarehouses_(_params: Record<string, never>, page: number) {
  return fetchWarehouses(page);
}
