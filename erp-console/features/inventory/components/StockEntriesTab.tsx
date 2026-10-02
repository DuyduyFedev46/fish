"use client";

// Tab "Điều chỉnh tồn" (W5a, ED-24 / quyết định D-1): CHỈ ĐỌC. Danh sách phiếu từ R7b (GET /api/inventory/stock-entries/).
// Không có nút tạo, không có form (F1j bỏ). Lọc: mục đích, khoảng ngày. Ô tìm lọc trên các phiếu đã tải.
import { useMemo, useState } from "react";
import Link from "next/link";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { dateTime, kg } from "@/shared/lib/format";
import { ENUMS } from "@/shared/lib/enums";
import { matches } from "@/shared/lib/search";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Chip } from "@/shared/ui/Chip";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { signedKg } from "@/features/ledger/ledgerView";
import { badDateRange } from "@/features/ledger/ledgerView";
import { fetchStockEntries } from "../api";
import type { StockEntry, StockEntryParams } from "../types";
import s from "../inventory.module.css";

const PURPOSE_OPTIONS = [
  { value: "", label: "Mọi mục đích" },
  ...Object.entries(ENUMS.stockEntryPurpose).map(([value, entry]) => ({ value, label: entry.label })),
];

export function StockEntriesTab({ tabs }: { tabs: React.ReactNode }) {
  const [query, setQuery] = useState("");
  const [purpose, setPurpose] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const badRange = badDateRange(from, to);
  const params: StockEntryParams = useMemo(() => ({ purpose, date_from: badRange ? "" : from, date_to: badRange ? "" : to }), [purpose, from, to, badRange]);
  const list = usePagedList<StockEntry, StockEntryParams>(fetchStockEntries, params, !badRange);

  const rows = list.rows ? (query.trim() ? list.rows.filter((r) => matches(query, r.code, r.batch_code, r.item_name, r.reason, r.created_by_name)) : list.rows) : null;
  const filtering = !!(purpose || from || to);
  const clearFilters = () => {
    setPurpose("");
    setFrom("");
    setTo("");
  };

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission homeHref="/overview/" />;

  const columns: Column<StockEntry>[] = [
    { key: "code", header: "Mã phiếu", mono: true, width: "112px", render: (r) => <span className={s.codeCell}>{r.code}</span> },
    { key: "at", header: "Thời gian", tabular: true, width: "148px", render: (r) => dateTime(r.created_at) },
    { key: "purpose", header: "Mục đích", render: (r) => <Chip table={ENUMS.stockEntryPurpose} value={r.purpose} /> },
    {
      key: "batch",
      header: "Lô",
      mono: true,
      render: (r) => (
        <Link href={`/inventory/detail/?id=${r.batch}`} className={s.codeLink}>
          {r.batch_code}
        </Link>
      ),
    },
    { key: "item", header: "Mặt hàng", render: (r) => r.item_name },
    { key: "change", header: "Thay đổi (kg)", num: true, render: (r) => signedKg(r.qty_change) },
    { key: "reason", header: "Lý do", render: (r) => r.reason || <span className="muted">—</span> },
    { key: "actor", header: "Người làm", render: (r) => r.created_by_name || "Hệ thống" },
  ];

  return (
    <ListPage
      id="inventory-panel"
      tabs={tabs}
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      filters={
        <div className={s.filters}>
          <FilterBar
            query={query}
            onQuery={setQuery}
            placeholder="Tìm mã phiếu, lô, mặt hàng"
            searchLabel="Tìm trong các phiếu đã tải"
            selects={[{ key: "purpose", label: "Mục đích", value: purpose, options: PURPOSE_OPTIONS, onChange: setPurpose }]}
            dateRange={{ from, to, onFrom: setFrom, onTo: setTo }}
            summary={rows ? `Đang hiện ${rows.length} / ${list.count} phiếu` : undefined}
          >
            {filtering && (
              <button type="button" className={`btn ${s.clearBtn}`} onClick={clearFilters}>
                Bỏ lọc
              </button>
            )}
          </FilterBar>
          {badRange && (
            <p className={s.dateError} role="alert">
              Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.
            </p>
          )}
        </div>
      }
      footer={
        list.hasMore ? (
          <button type="button" className="btn" onClick={() => void list.loadMore()} disabled={list.moreLoading}>
            {list.moreLoading ? "Đang tải…" : list.moreError ? "Thử lại" : "Tải thêm"}
          </button>
        ) : null
      }
    >
      <DataTable
        title="Phiếu điều chỉnh tồn"
        countText={rows ? `${list.count} phiếu` : undefined}
        columns={columns}
        rows={rows}
        rowKey={(r) => r.id}
        loading={list.loading && !list.rows}
        error={list.error ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={query}
        onClearQuery={() => setQuery("")}
        noun="phiếu điều chỉnh tồn"
        empty={
          filtering
            ? { icon: "filter_alt_off", title: "Không có phiếu nào khớp bộ lọc", action: <button type="button" className="btn" onClick={clearFilters}>Bỏ lọc</button> }
            : { icon: "tune", title: "Chưa có phiếu điều chỉnh tồn", hint: "Phiếu xuất hiện khi kiểm kê hoặc nhập vật tư làm đổi tồn." }
        }
        canViewCost={false}
        caption="Phiếu điều chỉnh tồn (chỉ đọc)"
      />
    </ListPage>
  );
}
