"use client";

// Tab "Mặt hàng" (ED-30 / W2d): bảng Mặt hàng · Mã hàng · Nhóm · Giá niêm yết · Áp dụng từ · Hạn dùng · Trạng thái · Ảnh.
// Giá niêm yết và Áp dụng từ CHỈ có khi BE trả `current_price` (người có catalog.view_itemprice): NV kho không thấy cột nào của giá.
// Bộ lọc nhóm / trạng thái / ảnh / loại chạy PHÍA SERVER; ô tìm tên, mã lọc phía máy trong phần đã tải (BE chưa có `q`).
// Nút "Thêm combo" và "Thêm mặt hàng" chỉ khi có catalog.add_item. Từ khoá và bộ lọc chỉ nằm trong state (không URL, không storage).
// Giá niêm yết là giá BÁN; màn này không có giá vốn.

import Link from "next/link";
import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { filterItems } from "../api";
import { asActiveFilter, asTypeFilter, priceCell, shelfLifeText } from "../catalogModel";
import { CATALOG_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import { EMPTY_ITEM_PARAMS, type CatalogItem, type ItemListParams } from "../types";
import { useCatalogList } from "../useCatalogList";
import { useGroupOptions } from "../useCatalogOptions";
import { ItemThumb } from "./ItemThumb";
import s from "../catalog.module.css";

const ACTIVE_OPTIONS = [
  { value: "", label: M.filterActiveAll },
  { value: "1", label: M.optActive },
  { value: "0", label: M.optHidden },
];
const IMAGE_OPTIONS = [
  { value: "", label: M.filterImageAll },
  { value: "1", label: M.optWithImage },
  { value: "0", label: M.optWithoutImage },
];
const TYPE_OPTIONS = [
  { value: "", label: M.filterTypeAll },
  { value: "SIMPLE", label: ENUMS.itemType.SIMPLE.label },
  { value: "BUNDLE", label: ENUMS.itemType.BUNDLE.label },
];

export function ItemListTab({ tabs }: { tabs: React.ReactNode }) {
  const { me } = useAuth();
  const ability = catalogAbility(me?.permissions ?? []);
  const [q, setQ] = useState("");
  const [params, setParams] = useState<ItemListParams>(EMPTY_ITEM_PARAMS);
  const list = useCatalogList(params, !!me);
  const groups = useGroupOptions(!!me && ability.viewGroups);
  const rows = useMemo(() => (list.rows ? filterItems(list.rows, q) : undefined), [list.rows, q]);

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission />;

  // Cột giá chỉ có khi BE trả `current_price` (key có mặt, kể cả null = chưa đặt giá).
  const showPrice = ability.viewPrices || (list.rows ?? []).some((i) => i.current_price !== undefined);

  const columns: Column<CatalogItem>[] = [
    {
      key: "name",
      header: M.colItem,
      width: "240px",
      render: (r) => (
        <span className={s.nameCell}>
          <ItemThumb image={r.image} size={36} />
          <span className={s.nameText}>{r.name}</span>
        </span>
      ),
    },
    { key: "code", header: M.colCode, mono: true, width: "132px", render: (r) => r.code },
    { key: "group", header: M.colGroup, render: (r) => r.group_name || <span className="muted">{M.none}</span> },
    ...(showPrice
      ? ([
          { key: "price", header: M.colPrice, num: true, width: "150px", render: (r) => priceCell(r) ?? <span className="muted">{M.none}</span> },
          { key: "from", header: M.colPriceFrom, num: true, render: (r) => (r.current_price ? dateOnly(r.current_price.valid_from) : <span className="muted">{M.none}</span>) },
        ] satisfies Column<CatalogItem>[])
      : []),
    { key: "shelf", header: M.colShelfLife, num: true, render: (r) => shelfLifeText(r.shelf_life_in_days) ?? <span className="muted">{M.none}</span> },
    { key: "status", header: M.colStatus, width: "144px", render: (r) => <Chip table={ENUMS.itemActive} value={r.is_active} /> },
    { key: "image", header: M.colImage, width: "104px", render: (r) => (r.image ? M.optWithImage : <span className="muted">{M.optWithoutImage}</span>) },
  ];

  const filtered = !!(params.group || params.type || params.active || params.hasImage);
  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;
  const groupSelect = groups.status === "ok" && groups.rows.length > 0
    ? [
        {
          key: "group",
          label: M.filterGroup,
          value: params.group,
          options: [{ value: "", label: M.filterGroupAll }, ...groups.rows.map((g) => ({ value: String(g.id), label: g.name }))],
          onChange: (v: string) => setParams((p) => ({ ...p, group: v })),
        },
      ]
    : [];

  return (
    <ListPage
      id="catalog-panel"
      tabs={tabs}
      actions={
        ability.addItem ? (
          <>
            <Link href="/catalog/new/?type=BUNDLE" className="btn">
              <Icon name="add" />
              <span>{M.addBundle}</span>
            </Link>
            <Link href="/catalog/new/" className="btn primary">
              <Icon name="add" />
              <span>{M.addItem}</span>
            </Link>
          </>
        ) : undefined
      }
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.itemSearchPlaceholder}
          searchLabel={M.itemSearchLabel}
          selects={[
            ...groupSelect,
            { key: "active", label: M.filterActive, value: params.active, options: ACTIVE_OPTIONS, onChange: (v) => setParams((p) => ({ ...p, active: asActiveFilter(v) })) },
            { key: "image", label: M.filterImage, value: params.hasImage, options: IMAGE_OPTIONS, onChange: (v) => setParams((p) => ({ ...p, hasImage: asActiveFilter(v) })) },
            { key: "type", label: M.filterType, value: params.type, options: TYPE_OPTIONS, onChange: (v) => setParams((p) => ({ ...p, type: asTypeFilter(v) })) },
          ]}
          summary={rows ? M.itemShown(rows.length, list.count) : undefined}
        />
      }
      banner={
        refreshFailed ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(list.error)}</span>
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
        caption={M.itemsCaption}
        columns={columns}
        rows={rows ?? null}
        rowKey={(r) => r.id}
        rowHref={(r) => `/catalog/detail/?id=${r.id}`}
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={q.trim()}
        onClearQuery={() => setQ("")}
        noun={M.itemsNoun}
        empty={{
          icon: filtered ? "filter_list_off" : "set_meal",
          title: filtered ? M.emptyFilteredTitle : M.emptyTitle,
          hint: filtered ? M.emptyFilteredHint : ability.addItem ? M.emptyHint : M.emptyReadOnlyHint,
          action:
            ability.addItem && !filtered ? (
              <Link href="/catalog/new/" className="btn primary">
                {M.addItem}
              </Link>
            ) : undefined,
        }}
        canViewCost={false}
        dense
      />
    </ListPage>
  );
}
