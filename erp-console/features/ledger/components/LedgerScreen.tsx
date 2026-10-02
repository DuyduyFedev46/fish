"use client";

// Sổ nhập xuất (W5i, ED-29): MỌI lần tồn kho đổi (nhập lô, bán, hoàn kho, điều chỉnh, huỷ, trả nhà cung cấp), mới nhất trước.
// CHỈ ĐỌC: không sửa, không xoá. Lọc: khoảng ngày, lô, loại, kho (BE lọc, 20 dòng/trang + "Tải thêm"); ô tìm lọc trên các dòng đã tải.
// `?batch=<id>` (link từ trang chi tiết lô) chọn sẵn lô. Cột Tồn sau = tồn của lô ngay sau dòng đó (balance_after của BE).
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { fetchAllWarehouses } from "@/features/inventory/api";
import { fetchBatchOptions } from "@/features/inventory/api";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { ENUMS } from "@/shared/lib/enums";
import { PERM } from "@/shared/lib/nav";
import { useResource } from "@/shared/lib/useResource";
import { usePagedList } from "@/shared/lib/usePagedList";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { fetchLedger } from "../api";
import { badDateRange, batchFromSearch, filterLedgerRows } from "../ledgerView";
import type { LedgerEntry, LedgerParams } from "../types";
import { LedgerTable } from "./LedgerTable";
import s from "../ledger.module.css";

const TYPE_OPTIONS = [
  { value: "", label: "Mọi loại" },
  ...Object.entries(ENUMS.stockMovementType).map(([value, entry]) => ({ value, label: entry.label })),
];

export function LedgerScreen() {
  const { me } = useAuth();
  const [query, setQuery] = useState("");
  const [batch, setBatch] = useState("");
  const [type, setType] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  // `?batch=` đọc sau khi mount (trang tĩnh: lần vẽ đầu phải khớp HTML); tải lần đầu chờ đọc xong để khỏi gọi hai lần.
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setBatch(batchFromSearch(window.location.search));
    setReady(true);
  }, []);

  const badRange = badDateRange(from, to);
  const params: LedgerParams = useMemo(
    () => ({ batch, movement_type: type, warehouse, date_from: badRange ? "" : from, date_to: badRange ? "" : to }),
    [batch, type, warehouse, from, to, badRange],
  );
  const list = usePagedList<LedgerEntry, LedgerParams>(fetchLedger, params, ready && !badRange);

  const canPickWarehouse = !!me?.permissions.includes(PERM.viewWarehouse);
  const canPickBatch = !!me?.permissions.includes(PERM.viewBatch);
  const batches = useResource(canPickBatch ? "ledger:batch-options" : null, () => fetchBatchOptions(), 60_000);
  const warehouses = useResource(canPickWarehouse ? "ledger:warehouse-options" : null, fetchAllWarehouses, 60_000);

  const batchOptions = useMemo(() => {
    const opts = (batches.data ?? []).map((b) => ({ value: String(b.id), label: `${b.batch_id} · ${b.item_name}` }));
    if (batch && !opts.some((o) => o.value === batch)) opts.unshift({ value: batch, label: "Lô đã chọn" });
    return [{ value: "", label: "Mọi lô" }, ...opts];
  }, [batches.data, batch]);
  const warehouseOptions = [{ value: "", label: "Mọi kho" }, ...(warehouses.data ?? []).map((w) => ({ value: String(w.id), label: w.name }))];

  if (!me) return null;
  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission homeHref="/overview/" />;

  const rows = list.rows ? filterLedgerRows(list.rows, query) : null;
  const filtering = !!(batch || type || warehouse || from || to);
  const clearFilters = () => {
    setBatch("");
    setType("");
    setWarehouse("");
    setFrom("");
    setTo("");
    const url = new URL(window.location.href);
    if (url.searchParams.has("batch")) {
      url.searchParams.delete("batch");
      window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
    }
  };

  return (
    <ListPage
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      filters={
        <div className={s.filters}>
          <FilterBar
            query={query}
            onQuery={setQuery}
            placeholder="Tìm lô, mặt hàng, chứng từ, người làm"
            searchLabel="Tìm trong các dòng đã tải"
            selects={[
              ...(canPickBatch ? [{ key: "batch", label: "Lô", value: batch, options: batchOptions, onChange: setBatch }] : []),
              { key: "type", label: "Loại", value: type, options: TYPE_OPTIONS, onChange: setType },
              ...(canPickWarehouse ? [{ key: "warehouse", label: "Kho", value: warehouse, options: warehouseOptions, onChange: setWarehouse }] : []),
            ]}
            dateRange={{ from, to, onFrom: setFrom, onTo: setTo }}
            summary={rows ? `Đang hiện ${rows.length} / ${list.count} dòng` : undefined}
          >
            {filtering && (
              <button type="button" className="btn" onClick={clearFilters}>
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
          <>
            {list.moreError ? <span role="alert">{loadErrorText(list.moreError)}</span> : null}
            <button type="button" className="btn" onClick={() => void list.loadMore()} disabled={list.moreLoading}>
              {list.moreLoading ? "Đang tải…" : list.moreError ? "Thử lại" : "Tải thêm"}
            </button>
          </>
        ) : null
      }
    >
      <LedgerTable
        title="Biến động kho"
        countText={rows && list.count >= 0 ? `${list.count} dòng` : undefined}
        rows={rows}
        loading={list.loading && !list.rows}
        error={list.error ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={query}
        onClearQuery={() => setQuery("")}
        caption="Sổ nhập xuất kho"
        empty={
          filtering
            ? { icon: "filter_alt_off", title: "Không có dòng nào khớp bộ lọc", hint: "Bỏ lọc hoặc chọn khoảng ngày rộng hơn.", action: <button type="button" className="btn" onClick={clearFilters}>Bỏ lọc</button> }
            : { icon: "receipt_long", title: "Chưa có dòng nhập xuất", hint: "Dòng xuất hiện khi nhập lô, bán hàng hay điều chỉnh tồn." }
        }
      />
      {list.hasMore && query.trim() ? <p className={s.hint}>Kết quả chỉ tìm trong các dòng đã tải. Bấm Tải thêm để tìm tiếp.</p> : null}
    </ListPage>
  );
}
