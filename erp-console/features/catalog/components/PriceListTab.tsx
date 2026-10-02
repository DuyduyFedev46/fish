"use client";

// Tab "Bảng giá" (ED-30 / W2h): mọi mức giá BÁN của mọi mặt hàng, mới nhất trước: Mặt hàng · Giá bán (đ) · Áp dụng từ · Áp dụng đến.
// Chỉ có khi người xem có catalog.view_itemprice (Chủ, Quản lý); NV kho không thấy tab, và nếu vào thẳng thì BE trả 403 → màn "Không có quyền".
// Nút "Đặt giá mới" chỉ Chủ (catalog.add_itemprice) và mở hộp Đặt giá mới có ô chọn mặt hàng. Không có sửa hay xoá một mức giá:
// giá đã áp vào đơn không đổi (quyết định #10), muốn đổi thì đặt giá mới từ ngày mai.

import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { dateOnly, money } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { matches } from "@/shared/lib/search";
import { CATALOG_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import type { ItemPrice } from "../types";
import { usePriceList } from "../useCatalogList";
import { useItemOptions, usePriceListOptions } from "../useCatalogOptions";
import { SetPriceModal } from "./SetPriceModal";

export function PriceListTab({ tabs }: { tabs: React.ReactNode }) {
  const { me } = useAuth();
  const toast = useToast();
  const ability = catalogAbility(me?.permissions ?? []);
  const [q, setQ] = useState("");
  const [adding, setAdding] = useState(false);
  const list = usePriceList(!!me && ability.viewPrices);
  const items = useItemOptions(ability.setPrice);
  const lists = usePriceListOptions(ability.setPrice);
  const rows = useMemo(() => (list.rows ? list.rows.filter((r) => matches(q, r.item_name, r.item_code)) : undefined), [list.rows, q]);

  if (!ability.viewPrices || (list.error instanceof ApiError && list.error.status === 403)) return <NoPermission />;

  const columns: Column<ItemPrice>[] = [
    { key: "item", header: M.colPriceItem, render: (r) => r.item_name },
    { key: "rate", header: M.colPriceRate, num: true, render: (r) => money(r.rate) },
    { key: "from", header: M.colPriceFrom, num: true, render: (r) => dateOnly(r.valid_from) },
    { key: "upto", header: M.colPriceUpto, num: true, render: (r) => (r.valid_upto ? dateOnly(r.valid_upto) : <span className="muted">{M.none}</span>) },
  ];

  const optionsReady = items.status === "ok" && lists.status === "ok";
  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;

  return (
    <ListPage
      id="catalog-panel"
      tabs={tabs}
      actions={
        ability.setPrice ? (
          <button type="button" className="btn primary" onClick={() => setAdding(true)} disabled={!optionsReady} aria-busy={!optionsReady || undefined}>
            <Icon name="add" />
            <span>{M.setPrice}</span>
          </button>
        ) : undefined
      }
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.priceSearchPlaceholder}
          searchLabel={M.priceSearchLabel}
          summary={rows ? M.priceShown(rows.length, list.count) : undefined}
        />
      }
      banner={
        refreshFailed ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(list.error)}</span>
          </div>
        ) : ability.setPrice && (items.status === "error" || lists.status === "error") ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{M.optionsFailed}</span>
            <button
              type="button"
              className="btn"
              onClick={() => {
                items.reload();
                lists.reload();
              }}
            >
              {M.retry}
            </button>
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
        caption={M.pricesCaption}
        columns={columns}
        rows={rows ?? null}
        rowKey={(r) => r.id}
        rowHref={(r) => `/catalog/detail/?id=${r.item}`}
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={q.trim()}
        onClearQuery={() => setQ("")}
        noun={M.pricesNoun}
        empty={{ icon: "sell", title: M.pricesEmptyTitle, hint: ability.setPrice ? M.pricesEmptyHint : M.pricesEmptyReadOnlyHint }}
        canViewCost={false}
      />
      {adding && optionsReady && (
        <SetPriceModal
          items={items.rows.filter((i) => i.is_active)}
          priceLists={lists.rows}
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false);
            toast.success(M.priceSaved);
            void list.reload();
          }}
        />
      )}
    </ListPage>
  );
}
