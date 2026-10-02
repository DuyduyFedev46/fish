"use client";

// Danh sách chi phí phụ (R12: GET /api/purchasing/costs/, 20 dòng/trang), dùng ở tab "Chi phí mua" của màn Mua hàng (ED-20)
// và tab "Chi phí phụ" của màn Hoá đơn mua & chi phí phụ (ED-34). CHỈ CHỦ: cả chứng từ là giá vốn,
// nên vai khác không có tab, và nếu vào thẳng thì BE trả 403 (màn "Không có quyền"). Số tiền là cột khoá.
// Chưa có màn sửa chi phí: chi phí đã chia vào lô thì khoá (COST_ALLOCATED_LOCKED), nên danh sách này không có nút sửa/xoá.
// Thêm chi phí: sang trang riêng /purchasing/costs/new/ (form nhiều dòng chia lô).
import { useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly, todayInVietnam, vnd } from "@/shared/lib/format";
import { usePagedList } from "@/shared/lib/usePagedList";
import { matches } from "@/shared/lib/search";
import { Chip } from "@/shared/ui/Chip";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { fetchPurchaseCosts } from "../api";
import { recentMonthOptions } from "../months";
import type { PurchaseCostListParams, PurchaseCostRow } from "../types";
import s from "../accounting.module.css";

const TYPE_OPTIONS = [
  { value: "", label: "Mọi loại chi phí" },
  ...Object.entries(ENUMS.purchaseCostType).map(([value, entry]) => ({ value, label: entry.label })),
];

export function PurchaseCostList({ tabs, canAdd, panelId = "purchasing-panel", homeHref = "/purchasing/" }: { tabs: React.ReactNode; canAdd: boolean; panelId?: string; homeHref?: string }) {
  const { me } = useAuth();
  const canViewCost = Boolean(me?.can_view_cost);
  const [query, setQuery] = useState("");
  const [costType, setCostType] = useState("");
  const [month, setMonth] = useState("");

  const params: PurchaseCostListParams = useMemo(() => ({ cost_type: costType, month }), [costType, month]);
  const list = usePagedList<PurchaseCostRow, PurchaseCostListParams>((p, page) => fetchPurchaseCosts(p, page), params, true);
  const monthOptions = useMemo(() => recentMonthOptions(todayInVietnam()), []);

  const rows = list.rows ? (query.trim() ? list.rows.filter((r) => matches(query, r.cost_type_label, r.note, r.allocation_method_label)) : list.rows) : null;
  const filtering = !!(query.trim() || costType || month);
  const clear = () => {
    setQuery("");
    setCostType("");
    setMonth("");
  };

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission homeHref={homeHref} />;

  const columns: Column<PurchaseCostRow>[] = [
    { key: "type", header: "Loại chi phí", render: (r) => <Chip table={ENUMS.purchaseCostType} value={r.cost_type} /> },
    { key: "amount", header: "Số tiền", num: true, locked: true, render: (r) => vnd(r.amount) },
    { key: "method", header: "Cách chia", render: (r) => <Chip table={ENUMS.purchaseCostAllocation} value={r.allocation_method} /> },
    { key: "date", header: "Ngày phát sinh", num: true, width: "132px", render: (r) => dateOnly(r.incurred_date) },
    { key: "lots", header: "Số lô được chia", num: true, render: (r) => r.batch_count },
    { key: "note", header: "Ghi chú", render: (r) => r.note || <span className="muted">—</span> },
  ];

  return (
    <ListPage
      id={panelId}
      tabs={tabs}
      actions={
        canAdd ? (
          <Link href="/purchasing/costs/new/" className="btn primary" data-testid="add-cost">
            Thêm chi phí phụ
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
            placeholder="Tìm loại chi phí, ghi chú"
            searchLabel="Tìm trong các chi phí đã tải"
            selects={[
              { key: "type", label: "Loại chi phí", value: costType, options: TYPE_OPTIONS, onChange: setCostType },
              { key: "month", label: "Tháng phát sinh", value: month, options: monthOptions, onChange: setMonth },
            ]}
            summary={rows && list.count >= 0 ? `Đang hiện ${rows.length} / ${list.count} khoản chi phí` : undefined}
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
        noun="khoản chi phí"
        empty={
          filtering
            ? { icon: "filter_alt_off", title: "Không có chi phí nào khớp bộ lọc", hint: "Bỏ lọc để xem toàn bộ chi phí.", action: <button type="button" className="btn" onClick={clear}>Bỏ lọc</button> }
            : { icon: "payments", title: "Chưa có chi phí mua", hint: "Đá, vận chuyển, bốc vác chia vào giá vốn của lô." }
        }
        canViewCost={canViewCost}
        caption="Danh sách chi phí phụ"
      />
      {query.trim() && list.hasMore && <p className={s.hint}>Kết quả chỉ tìm trong các khoản đã tải. Bấm Tải thêm để tìm tiếp.</p>}
    </ListPage>
  );
}
