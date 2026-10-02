"use client";

// Tab "Tồn theo lô" (W5a, ED-23): danh sách lô từ R5 (GET /api/inventory/batches/, 50 dòng/trang), bấm dòng → trang chi tiết lô.
// R5 chưa có tham số tìm, nên ô tìm lọc trên các lô ĐÃ TẢI và nói rõ khi còn lô chưa tải.
// Giá mua/kg và giá vốn/kg là cột khoá: chỉ Chủ (me.can_view_cost) thấy, người khác không có cột trong DOM.
// Dưới bảng: "Nhập xuất gần đây" (R6) cho ai có quyền xem sổ nhập xuất.
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { Me } from "@/features/auth/types";
import { fetchLedger } from "@/features/ledger/api";
import { LedgerTable } from "@/features/ledger/components/LedgerTable";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { dateOnly, kg, vnd } from "@/shared/lib/format";
import { ENUMS } from "@/shared/lib/enums";
import { PERM } from "@/shared/lib/nav";
import { useResource } from "@/shared/lib/useResource";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Chip } from "@/shared/ui/Chip";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { batchAbility, filterBatchRows, qtyAvailable, qtyReserved, statusFromSearch } from "../lotView";
import { fetchAllWarehouses, fetchBatches } from "../api";
import type { BatchApiRow, BatchListParams } from "../types";
import s from "../inventory.module.css";

const STATUS_OPTIONS = [
  { value: "", label: "Mọi trạng thái" },
  ...Object.entries(ENUMS.batchStatus).map(([value, entry]) => ({ value, label: entry.label })),
];
const STOCK_OPTIONS = [
  { value: "", label: "Mọi mức tồn" },
  { value: "1", label: "Còn hàng" },
];
const RECENT_LEDGER_ROWS = 8;

export function LotsTab({ tabs, me }: { tabs: React.ReactNode; me: Me }) {
  const ability = batchAbility(me);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [hasStock, setHasStock] = useState(false);
  // `?status=` đọc SAU khi mount (trang tĩnh: lần vẽ đầu phải khớp HTML). `ready` chặn tải lần đầu với bộ lọc rỗng.
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const fromUrl = statusFromSearch(window.location.search);
    if (fromUrl) {
      setStatus(fromUrl);
      setHasStock(fromUrl === "EXPIRED");
    }
    setReady(true);
  }, []);

  const params: BatchListParams = useMemo(() => ({ status, warehouse, has_stock: hasStock }), [status, warehouse, hasStock]);
  const list = usePagedList<BatchApiRow, BatchListParams>(fetchBatches, params, ready);

  const canPickWarehouse = me.permissions.includes(PERM.viewWarehouse);
  const warehouses = useResource(canPickWarehouse ? "inventory:warehouse-options" : null, fetchAllWarehouses, 60_000);
  const warehouseOptions = [{ value: "", label: "Mọi kho" }, ...(warehouses.data ?? []).map((w) => ({ value: String(w.id), label: w.name }))];

  const rows = list.rows ? filterBatchRows(list.rows, query) : null;
  const filtering = !!(status || warehouse || hasStock);
  const clearFilters = () => {
    setStatus("");
    setWarehouse("");
    setHasStock(false);
    const url = new URL(window.location.href);
    if (url.searchParams.has("status")) {
      url.searchParams.delete("status");
      window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
    }
  };

  const forbidden = list.error instanceof ApiError && list.error.status === 403;
  if (forbidden) return <NoPermission homeHref="/overview/" />;

  const columns: Column<BatchApiRow>[] = [
    { key: "code", header: "Lô", mono: true, width: "168px", render: (r) => <span className={s.codeCell}>{r.batch_id}</span> },
    { key: "item", header: "Mặt hàng", render: (r) => r.item_name },
    { key: "warehouse", header: "Kho", render: (r) => r.warehouse_name },
    { key: "available", header: "Tồn (kg)", num: true, render: (r) => kg(qtyAvailable(r)) },
    { key: "reserved", header: "Giữ chỗ (kg)", num: true, render: (r) => kg(qtyReserved(r)) },
    {
      key: "expiry",
      header: "Hạn dùng",
      num: true,
      render: (r) => (
        <span className={r.status === "EXPIRED" ? s.critText : r.status === "NEAR_EXPIRY" ? s.warnText : undefined}>{dateOnly(r.expiry_date)}</span>
      ),
    },
    { key: "purchase", header: "Giá mua/kg", num: true, locked: true, render: (r) => (r.purchase_rate === undefined ? "—" : vnd(r.purchase_rate)) },
    { key: "landed", header: "Giá vốn/kg", num: true, locked: true, render: (r) => (r.landed_unit_cost === undefined ? "—" : vnd(r.landed_unit_cost)) },
    { key: "status", header: "Trạng thái", render: (r) => <Chip table={ENUMS.batchStatus} value={r.status} /> },
  ];

  const unloaded = list.hasMore && query.trim() ? list.count - (list.rows?.length ?? 0) : 0;

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
            placeholder="Tìm mã lô, mặt hàng, nhà cung cấp"
            searchLabel="Tìm trong các lô đã tải"
            selects={[
              { key: "status", label: "Trạng thái lô", value: status, options: STATUS_OPTIONS, onChange: setStatus },
              ...(canPickWarehouse ? [{ key: "warehouse", label: "Kho", value: warehouse, options: warehouseOptions, onChange: setWarehouse }] : []),
              { key: "stock", label: "Mức tồn", value: hasStock ? "1" : "", options: STOCK_OPTIONS, onChange: (v: string) => setHasStock(v === "1") },
            ]}
            summary={rows && list.count >= 0 ? `Đang hiện ${rows.length} / ${list.count} lô` : undefined}
          >
            {filtering && (
              <button type="button" className={`btn ${s.clearBtn}`} onClick={clearFilters} data-testid="clear-status-filter">
                Bỏ lọc
              </button>
            )}
          </FilterBar>
        </div>
      }
      footer={
        list.hasMore ? (
          <>
            {list.moreError ? <span role="alert">{loadErrorText(list.moreError)}</span> : null}
            <button type="button" className="btn" onClick={() => void list.loadMore()} disabled={list.moreLoading}>
              {list.moreLoading ? "Đang tải…" : list.moreError ? "Thử lại" : "Tải thêm"}
            </button>
          </>
        ) : null
      }
    >
      <DataTable
        title="Tồn theo lô"
        countText={rows && list.count >= 0 ? `${list.count} lô` : undefined}
        columns={columns}
        rows={rows}
        rowKey={(r) => r.id}
        rowHref={(r) => `/inventory/detail/?id=${r.id}`}
        loading={list.loading && !list.rows}
        error={list.error ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={query}
        onClearQuery={() => setQuery("")}
        noun="lô"
        empty={
          filtering
            ? { icon: "filter_alt_off", title: "Không có lô nào khớp bộ lọc", hint: "Bỏ lọc để xem toàn bộ lô.", action: <button type="button" className="btn" onClick={clearFilters}>Bỏ lọc</button> }
            : { icon: "inventory_2", title: "Chưa có lô nào", hint: "Lô xuất hiện khi nhập hàng vào kho." }
        }
        canViewCost={me.can_view_cost}
        caption="Danh sách lô trong kho"
      />
      {unloaded > 0 && <p className={s.hint}>Kết quả chỉ tìm trong các lô đã tải. Còn {unloaded} lô chưa tải, bấm Tải thêm để tìm tiếp.</p>}
      {ability.viewLedger && <RecentLedger />}
    </ListPage>
  );
}

function RecentLedger() {
  // maxAge 0: luôn tải lại khi vào màn (vừa trả hàng, huỷ tồn ở trang chi tiết xong quay lại phải thấy dòng mới).
  const res = useResource("inventory:recent-ledger", () => fetchLedger({}, 1), 0);
  const rows = res.data ? res.data.results.slice(0, RECENT_LEDGER_ROWS) : null;
  return (
    <section aria-label="Nhập xuất gần đây">
      <LedgerTable
        title="Nhập xuất gần đây"
        countText={rows ? `${rows.length} lần` : undefined}
        headAction={
          <Link href="/ledger/" className={s.panelLink}>
            Xem sổ nhập xuất
          </Link>
        }
        rows={rows}
        loading={res.loading && !res.data}
        error={res.error && !res.data ? loadErrorText(res.error) : null}
        onRetry={() => void res.reload()}
        caption="Nhập xuất gần đây"
        empty={{ icon: "receipt_long", title: "Chưa có dòng nhập xuất", hint: "Dòng xuất hiện khi nhập lô, bán hàng hay điều chỉnh tồn." }}
        skeletonRows={4}
      />
    </section>
  );
}
