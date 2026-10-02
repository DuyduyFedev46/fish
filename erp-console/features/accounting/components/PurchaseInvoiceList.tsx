"use client";

// Danh sách hoá đơn mua (R11: GET /api/purchasing/invoices/, 20 dòng/trang), dùng ở hai nơi: tab của màn Mua hàng (ED-20)
// và tab "Hoá đơn mua" của màn Hoá đơn mua & chi phí phụ (ED-34).
// Cần purchasing.view_purchaseinvoice (Chủ, Quản lý). Quản lý thấy số tiền hoá đơn (quyết định D-3) nhưng không thêm được hoá đơn;
// nhân viên kho không có màn này (và nếu vào thẳng thì BE trả 403 → màn "Không có quyền").
import { useMemo, useState } from "react";
import Link from "next/link";
import { fetchSuppliers } from "@/features/purchasing/api";
import { referenceHref } from "@/features/ledger/referenceRoutes";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly, dateTime, todayInVietnam, vnd } from "@/shared/lib/format";
import { useResource } from "@/shared/lib/useResource";
import { usePagedList } from "@/shared/lib/usePagedList";
import { matches } from "@/shared/lib/search";
import { Chip } from "@/shared/ui/Chip";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { fetchPurchaseInvoices } from "../api";
import { recentMonthOptions } from "../months";
import type { PurchaseInvoiceListParams, PurchaseInvoiceRow } from "../types";
import { PurchaseInvoiceForm } from "./PurchaseInvoiceForm";
import s from "../accounting.module.css";

const PAID_OPTIONS = [
  { value: "", label: "Mọi tình trạng" },
  { value: "0", label: "Chưa trả tiền" },
  { value: "1", label: "Đã trả tiền" },
];

type Props = {
  tabs: React.ReactNode;
  /** Có quyền thêm hoá đơn (chỉ Chủ). */
  canAdd: boolean;
  /** Có quyền chọn nhà cung cấp để lọc (purchasing.view_supplier). */
  canPickSupplier: boolean;
  /** id vùng nội dung để nối aria-controls của tab. */
  panelId?: string;
  /** Nơi "Về trang chính" khi 403. */
  homeHref?: string;
};

/** "Đang hiện 8 / 8 hoá đơn · 3 chưa trả". Số chưa trả đếm trong các dòng đã tải; còn trang sau thì ghi rõ để không hiểu nhầm là tổng. */
export function summaryText(rows: PurchaseInvoiceRow[], count: number, hasMore: boolean): string {
  const unpaid = rows.filter((r) => !r.is_paid).length;
  return `Đang hiện ${rows.length} / ${count} hoá đơn · ${unpaid} chưa trả${hasMore ? " (trong số đã tải)" : ""}`;
}

export function PurchaseInvoiceList({ tabs, canAdd, canPickSupplier, panelId = "purchasing-panel", homeHref = "/purchasing/" }: Props) {
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [paid, setPaid] = useState("");
  const [supplier, setSupplier] = useState("");
  const [month, setMonth] = useState("");
  const [adding, setAdding] = useState(false);

  const params: PurchaseInvoiceListParams = useMemo(() => ({ is_paid: paid, supplier, month }), [paid, supplier, month]);
  const list = usePagedList<PurchaseInvoiceRow, PurchaseInvoiceListParams>((p, page) => fetchPurchaseInvoices(p, page), params, true);

  const suppliers = useResource(canPickSupplier ? "accounting:invoice-supplier-filter" : null, () => fetchSuppliers(), 60_000);
  const supplierOptions = [{ value: "", label: "Mọi nhà cung cấp" }, ...(suppliers.data ?? []).map((x) => ({ value: String(x.id), label: x.name }))];
  const monthOptions = useMemo(() => recentMonthOptions(todayInVietnam()), []);

  const rows = list.rows ? (query.trim() ? list.rows.filter((r) => matches(query, r.code, r.supplier_name, r.receipt_code)) : list.rows) : null;
  const filtering = !!(query.trim() || paid || supplier || month);
  const clear = () => {
    setQuery("");
    setPaid("");
    setSupplier("");
    setMonth("");
  };

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission homeHref={homeHref} />;

  const columns: Column<PurchaseInvoiceRow>[] = [
    { key: "code", header: "Hoá đơn", mono: true, width: "96px", render: (r) => r.code },
    { key: "supplier", header: "Nhà cung cấp", render: (r) => r.supplier_name },
    {
      key: "receipt",
      header: "Phiếu nhập",
      mono: true,
      render: (r) => {
        if (!r.receipt || !r.receipt_code) return <span className="muted">—</span>;
        const href = referenceHref({ kind: "receipt", id: r.receipt });
        return href ? (
          <Link href={href} className={s.codeLink}>
            {r.receipt_code}
          </Link>
        ) : (
          r.receipt_code
        );
      },
    },
    { key: "date", header: "Ngày hoá đơn", num: true, render: (r) => dateOnly(r.invoice_date) },
    // Số tiền có icon khoá nhưng Quản lý vẫn thấy (quyết định D-3): cột này không phụ thuộc view_costprice, nên màn luôn truyền canViewCost.
    { key: "amount", header: "Số tiền", num: true, locked: true, render: (r) => vnd(r.amount) },
    { key: "paid", header: "Tình trạng", render: (r) => <Chip table={ENUMS.purchaseInvoicePaid} value={String(r.is_paid)} /> },
    { key: "paidAt", header: "Trả lúc", num: true, render: (r) => (r.paid_at ? dateTime(r.paid_at) : <span className="muted">—</span>) },
  ];

  return (
    <>
      <ListPage
        id={panelId}
        tabs={tabs}
        actions={
          canAdd ? (
            <button type="button" className="btn primary" onClick={() => setAdding(true)} data-testid="add-invoice">
              Thêm hoá đơn mua
            </button>
          ) : undefined
        }
        asOf={list.asOf}
        onRetry={() => void list.reload()}
        filters={
          <div className={s.filters}>
            <FilterBar
              query={query}
              onQuery={setQuery}
              placeholder="Tìm mã hoá đơn, nhà cung cấp, phiếu nhập"
              searchLabel="Tìm trong các hoá đơn đã tải"
              selects={[
                { key: "paid", label: "Tình trạng trả tiền", value: paid, options: PAID_OPTIONS, onChange: setPaid },
                ...(canPickSupplier ? [{ key: "supplier", label: "Nhà cung cấp", value: supplier, options: supplierOptions, onChange: setSupplier }] : []),
                { key: "month", label: "Tháng hoá đơn", value: month, options: monthOptions, onChange: setMonth },
              ]}
              summary={rows && list.count >= 0 ? summaryText(rows, list.count, list.hasMore) : undefined}
            >
              {filtering && (
                <button type="button" className="btn" onClick={clear}>
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
          columns={columns}
          rows={rows}
          rowKey={(r) => r.id}
          loading={list.loading && !list.rows}
          error={list.error ? loadErrorText(list.error) : null}
          onRetry={() => void list.reload()}
          query={query}
          onClearQuery={() => setQuery("")}
          noun="hoá đơn"
          empty={
            filtering
              ? { icon: "filter_alt_off", title: "Không có hoá đơn nào khớp bộ lọc", hint: "Bỏ lọc để xem toàn bộ hoá đơn.", action: <button type="button" className="btn" onClick={clear}>Bỏ lọc</button> }
              : { icon: "receipt_long", title: "Chưa có hoá đơn mua", hint: "Hoá đơn xuất hiện khi Chủ thêm hoá đơn của nhà cung cấp." }
          }
          canViewCost
          caption="Danh sách hoá đơn mua"
        />
        {query.trim() && list.hasMore && <p className={s.hint}>Kết quả chỉ tìm trong các hoá đơn đã tải. Bấm Tải thêm để tìm tiếp.</p>}
      </ListPage>
      {adding && (
        <PurchaseInvoiceForm
          onClose={() => setAdding(false)}
          onDone={(row) => {
            setAdding(false);
            toast.success(`Đã thêm hoá đơn ${row.code}.`);
            void list.reload();
          }}
        />
      )}
    </>
  );
}
