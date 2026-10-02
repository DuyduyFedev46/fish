"use client";

// Hoá đơn bán (W5f, ED-33). CHỈ ĐỌC: hoá đơn do hệ thống phát hành khi đơn đủ tiền (BR-PQ-11), không có nút tạo.
// Quyền xem = sales.view_salesinvoice (Chủ, Quản lý, Nhân viên kho; vai khác vào thẳng URL thì ra "Không có quyền").
// Cột Giá vốn và Lãi gộp (và dòng lãi gộp ở chân) chỉ có khi người xem có quyền xem giá vốn; tên khách chỉ có khi có quyền xem khách hàng
// (không có thì ẩn cả cột, BE trả null). Tìm theo mã hoá đơn hoặc mã đơn, lọc trạng thái và khoảng ngày xuất ở BE.
// Chân bảng: tổng số tiền của toàn bộ kết quả đã lọc (không chỉ trang đang hiện), do BE tính.
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, vnd } from "@/shared/lib/format";
import { PERM, onlyDelivery } from "@/shared/lib/nav";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Chip } from "@/shared/ui/Chip";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { fetchSalesInvoices } from "../api";
import type { SalesInvoiceListParams, SalesInvoiceRow, SalesInvoiceTotals } from "../types";
import s from "../accounting.module.css";

const STATUS_OPTIONS = [
  { value: "", label: "Mọi trạng thái" },
  ...Object.entries(ENUMS.salesInvoiceStatus).map(([value, entry]) => ({ value, label: entry.label })),
];

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function SalesInvoiceListScreen() {
  const { me } = useAuth();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [totalsBox, setTotalsBox] = useState<{ key: string; totals: SalesInvoiceTotals } | null>(null);

  const debounced = useDebounced(query, 300).trim();
  const badRange = !!from && !!to && from > to;
  const params: SalesInvoiceListParams = useMemo(
    () => ({ q: debounced, status, date_from: badRange ? "" : from, date_to: badRange ? "" : to }),
    [debounced, status, from, to, badRange],
  );
  // `usePagedList` chỉ giữ dòng; tổng của cả kết quả lấy từ trang 1 và gắn với đúng bộ lọc đã gọi.
  const list = usePagedList<SalesInvoiceRow, SalesInvoiceListParams>(
    async (p, page) => {
      const r = await fetchSalesInvoices(p, page);
      if (page === 1) setTotalsBox({ key: JSON.stringify(p), totals: r.totals });
      return r;
    },
    params,
    !!me,
  );

  if (!me) return null;
  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission />;

  const showCost = me.can_view_cost;
  const showCustomer = me.permissions.includes(PERM.viewCustomerList);
  const canOpenOrder = me.permissions.includes(PERM.viewSalesOrder) && !onlyDelivery(me);
  const totals = totalsBox && totalsBox.key === JSON.stringify(params) && list.rows ? totalsBox.totals : null;
  const filtering = !!(query.trim() || status || from || to);
  const clear = () => {
    setQuery("");
    setStatus("");
    setFrom("");
    setTo("");
  };

  const columns: Column<SalesInvoiceRow>[] = [
    { key: "code", header: "Mã hoá đơn", mono: true, width: "112px", render: (r) => r.code },
    {
      key: "order",
      header: "Đơn",
      mono: true,
      width: "96px",
      render: (r) =>
        canOpenOrder ? (
          <Link href={`/orders/detail/?id=${r.sales_order}`} className={s.codeLink}>
            {r.order_code}
          </Link>
        ) : (
          r.order_code
        ),
    },
    ...(showCustomer ? [{ key: "customer", header: "Khách hàng", hideBelow: 800 as const, render: (r: SalesInvoiceRow) => r.customer_name || <span className="muted">—</span> }] : []),
    { key: "issued", header: "Ngày xuất", tabular: true, width: "140px", render: (r) => dateTime(r.issued_at) },
    { key: "amount", header: "Số tiền", num: true, render: (r) => vnd(r.amount) },
    { key: "cogs", header: "Giá vốn", num: true, locked: true, hideBelow: 800, render: (r) => (r.cogs === undefined ? "—" : vnd(r.cogs)) },
    { key: "profit", header: "Lãi gộp", num: true, locked: true, hideBelow: 720, render: (r) => (r.gross_profit === undefined ? "—" : vnd(r.gross_profit)) },
    { key: "status", header: "Trạng thái", render: (r) => <Chip table={ENUMS.salesInvoiceStatus} value={r.status} /> },
  ];

  return (
    <ListPage
      id="sales-invoices-panel"
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      filters={
        <div className={s.filters}>
          <FilterBar
            query={query}
            onQuery={setQuery}
            placeholder="Tìm mã hoá đơn hoặc mã đơn"
            searchLabel="Tìm hoá đơn bán"
            selects={[{ key: "status", label: "Trạng thái hoá đơn", value: status, options: STATUS_OPTIONS, onChange: setStatus }]}
            dateRange={{ from, to, onFrom: setFrom, onTo: setTo }}
            summary={list.rows ? `Đang hiện ${list.rows.length} / ${list.count} hoá đơn` : undefined}
          >
            {filtering && (
              <button type="button" className="btn" onClick={clear}>
                Bỏ lọc
              </button>
            )}
          </FilterBar>
          {badRange && (
            <p className={s.fieldNote} role="alert">
              Ngày bắt đầu đang sau ngày kết thúc. Chọn lại khoảng ngày.
            </p>
          )}
        </div>
      }
      footer={
        <>
          {totals && (
            <div className={s.totals} data-testid="invoice-totals">
              <span className={s.totalsItem}>
                <span className="muted">Tổng số tiền</span>
                <strong data-testid="total-amount">
                  <Figure text={vnd(totals.amount)} />
                </strong>
              </span>
              {showCost && totals.gross_profit !== undefined && (
                <span className={s.totalsItem}>
                  <span className="muted">
                    <Icon name="lock" /> Lãi gộp
                  </span>
                  <strong data-testid="total-profit">
                    <Figure text={vnd(totals.gross_profit)} />
                  </strong>
                </span>
              )}
              <span className={s.hint} data-testid="invoice-note">Không tính hoá đơn Đã huỷ.</span>
            </div>
          )}
          {list.hasMore && (
            <>
              {list.moreError ? <span role="alert">{loadErrorText(list.moreError)}</span> : null}
              <button type="button" className="btn" onClick={() => void list.loadMore()} disabled={list.moreLoading}>
                {list.moreLoading ? "Đang tải…" : list.moreError ? "Thử lại" : "Tải thêm"}
              </button>
            </>
          )}
        </>
      }
    >
      <DataTable
        title="Hoá đơn bán"
        countText={list.rows ? `${list.count} hoá đơn` : undefined}
        columns={columns}
        rows={list.rows ?? null}
        rowKey={(r) => r.id}
        rowHref={canOpenOrder ? (r) => `/orders/detail/?id=${r.sales_order}` : undefined}
        loading={list.loading && !list.rows}
        error={list.error ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={debounced}
        onClearQuery={() => setQuery("")}
        noun="hoá đơn"
        empty={
          filtering
            ? { icon: "filter_alt_off", title: "Không có hoá đơn nào khớp bộ lọc", hint: "Bỏ lọc để xem toàn bộ hoá đơn.", action: <button type="button" className="btn" onClick={clear}>Bỏ lọc</button> }
            : { icon: "receipt_long", title: "Chưa có hoá đơn bán", hint: "Hoá đơn tự xuất hiện khi một đơn được xác nhận đủ tiền." }
        }
        canViewCost={showCost}
        caption="Danh sách hoá đơn bán"
        dense
      />
    </ListPage>
  );
}
