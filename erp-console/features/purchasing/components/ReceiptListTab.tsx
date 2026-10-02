"use client";

// Tab "Phiếu nhập" của Mua hàng (W2a, ED-20): danh sách từ R10 (GET /api/purchasing/receipts/, 20 dòng/trang), bấm dòng → chi tiết phiếu.
// R10 chưa có tham số tìm nên ô tìm lọc trên các phiếu ĐÃ TẢI và nói rõ khi còn phiếu chưa tải.
// Tiền mua là cột khoá: chỉ Chủ có trong DOM. Cột Hoá đơn chỉ hiện cho người xem được hoá đơn mua (Chủ, Quản lý).
// Nhân viên kho thấy mọi phiếu (quyết định #9).
import { useMemo, useState } from "react";
import Link from "next/link";
import type { Me } from "@/features/auth/types";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly, kg, vnd } from "@/shared/lib/format";
import { usePagedList } from "@/shared/lib/usePagedList";
import { useResource } from "@/shared/lib/useResource";
import { PERM } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { fetchReceipts, fetchSuppliers } from "../api";
import { filterReceiptRows, receiptAbility, receiptTotals } from "../receiptView";
import type { ReceiptListParams, ReceiptRow } from "../types";
import s from "../purchasing.module.css";

const STATUS_OPTIONS = [
  { value: "", label: "Mọi trạng thái" },
  ...Object.entries(ENUMS.purchaseReceiptStatus).map(([value, entry]) => ({ value, label: entry.label })),
];
const INVOICE_OPTIONS = [
  { value: "", label: "Mọi phiếu" },
  { value: "1", label: "Đã có hoá đơn" },
  { value: "0", label: "Chưa có hoá đơn" },
];

export function ReceiptListTab({ tabs, me }: { tabs: React.ReactNode; me: Me }) {
  const ability = receiptAbility(me);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [supplier, setSupplier] = useState("");
  const [hasInvoice, setHasInvoice] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const params: ReceiptListParams = useMemo(() => ({ status, supplier, date_from: from, date_to: to, has_invoice: hasInvoice }), [status, supplier, from, to, hasInvoice]);
  const list = usePagedList<ReceiptRow, ReceiptListParams>((p, page) => fetchReceipts(p, page), params, true);

  const canPickSupplier = me.permissions.includes(PERM.viewSupplier);
  const suppliers = useResource(canPickSupplier ? "purchasing:supplier-filter" : null, () => fetchSuppliers(), 60_000);
  const supplierOptions = [{ value: "", label: "Mọi nhà cung cấp" }, ...(suppliers.data ?? []).map((x) => ({ value: String(x.id), label: x.name }))];

  const rows = list.rows ? filterReceiptRows(list.rows, query) : null;
  const totals = receiptTotals(rows ?? []);
  const filtering = !!(query.trim() || status || supplier || hasInvoice || from || to);
  const clear = () => {
    setQuery("");
    setStatus("");
    setSupplier("");
    setHasInvoice("");
    setFrom("");
    setTo("");
  };

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission homeHref="/overview/" />;

  const columns: Column<ReceiptRow>[] = [
    { key: "code", header: "Mã phiếu", mono: true, width: "104px", render: (r) => <span className={s.codeCell}>{r.code}</span> },
    { key: "date", header: "Ngày nhập", tabular: true, render: (r) => dateOnly(r.received_date) },
    { key: "supplier", header: "Nhà cung cấp", render: (r) => r.supplier_name },
    { key: "items", header: "Mặt hàng", render: (r) => r.items_summary || <span className="muted">—</span> },
    { key: "qty", header: "Số kg", num: true, render: (r) => kg(r.total_qty) },
    { key: "amount", header: "Tiền mua", num: true, locked: true, render: (r) => (r.purchase_amount === undefined ? "—" : vnd(r.purchase_amount)) },
    ...(ability.viewInvoices
      ? [{ key: "invoice", header: "Hoá đơn mua", render: (r: ReceiptRow) => (r.invoice ? <span className="stat-chip good">Đã có</span> : <span className="stat-chip mute">Chưa có</span>) }]
      : []),
    { key: "status", header: "Trạng thái", render: (r) => <Chip table={ENUMS.purchaseReceiptStatus} value={r.status} /> },
  ];

  const unloaded = list.hasMore && query.trim() ? list.count - (list.rows?.length ?? 0) : 0;

  return (
    <ListPage
      id="purchasing-panel"
      tabs={tabs}
      actions={
        ability.create ? (
          <Link href="/purchasing/new/" className="btn primary" data-testid="new-receipt">
            <Icon name="add" />
            <span>Nhập lô tại cảng</span>
          </Link>
        ) : undefined
      }
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      filters={
        <div className={s.filters}>
          <FilterBar
            query={query}
            onQuery={setQuery}
            placeholder="Tìm mã phiếu, nhà cung cấp, mặt hàng, mã lô"
            searchLabel="Tìm trong các phiếu đã tải"
            selects={[
              { key: "status", label: "Trạng thái phiếu", value: status, options: STATUS_OPTIONS, onChange: setStatus },
              ...(canPickSupplier ? [{ key: "supplier", label: "Nhà cung cấp", value: supplier, options: supplierOptions, onChange: setSupplier }] : []),
              ...(ability.viewInvoices ? [{ key: "invoice", label: "Hoá đơn", value: hasInvoice, options: INVOICE_OPTIONS, onChange: setHasInvoice }] : []),
            ]}
            dateRange={{ from, to, onFrom: setFrom, onTo: setTo }}
            summary={rows && list.count >= 0 ? `Đang hiện ${rows.length} / ${list.count} phiếu` : undefined}
          >
            {filtering && (
              <button type="button" className="btn" onClick={clear} data-testid="clear-filters">
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
        title="Phiếu nhập"
        countText={rows && rows.length > 0 ? `${totals.count} phiếu · ${kg(totals.qty)}${list.hasMore ? " (đã tải)" : ""}` : undefined}
        columns={columns}
        rows={rows}
        rowKey={(r) => r.id}
        rowHref={(r) => `/purchasing/detail/?id=${r.id}`}
        loading={list.loading && !list.rows}
        error={list.error ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={query}
        onClearQuery={() => setQuery("")}
        noun="phiếu nhập"
        empty={
          filtering
            ? { icon: "filter_alt_off", title: "Không có phiếu nào khớp bộ lọc", hint: "Bỏ lọc để xem toàn bộ phiếu.", action: <button type="button" className="btn" onClick={clear}>Bỏ lọc</button> }
            : { icon: "shopping_cart", title: "Chưa có phiếu nhập", hint: "Phiếu xuất hiện khi nhập lô tại cảng." }
        }
        canViewCost={me.can_view_cost}
        caption="Danh sách phiếu nhập"
      />
      {unloaded > 0 && <p className={s.hint}>Kết quả chỉ tìm trong các phiếu đã tải. Còn {unloaded} phiếu chưa tải, bấm Tải thêm để tìm tiếp.</p>}
    </ListPage>
  );
}
