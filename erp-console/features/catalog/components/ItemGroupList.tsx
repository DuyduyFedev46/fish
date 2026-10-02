"use client";

// Tab "Nhóm hàng" (ED-31 / F1o): bảng Nhóm hàng · Nhóm cha · Số mặt hàng. Chủ có nút "Thêm nhóm hàng" (catalog.add_itemgroup)
// mở hộp nhập tên và nhóm cha. Ô tìm và bộ lọc nhóm cha chạy phía máy trên danh sách đã tải (danh sách nhóm ngắn).

import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { loadErrorText, ApiError } from "@/shared/lib/http";
import { matches } from "@/shared/lib/search";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { CATALOG_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import type { ItemGroup } from "../types";
import { useItemGroups } from "../useCatalogList";
import { ItemGroupModal } from "./ItemGroupModal";

export function ItemGroupList({ tabs }: { tabs: React.ReactNode }) {
  const { me } = useAuth();
  const toast = useToast();
  const ability = catalogAbility(me?.permissions ?? []);
  const [q, setQ] = useState("");
  const [parent, setParent] = useState("");
  const [adding, setAdding] = useState(false);
  const list = useItemGroups(!!me && ability.viewGroups);
  const all = list.rows;
  const rows = useMemo(
    () => (all ? all.filter((g) => matches(q, g.name, g.parent_name ?? "") && (!parent || String(g.parent ?? "") === parent)) : undefined),
    [all, q, parent],
  );
  const parents = useMemo(() => (all ?? []).filter((g) => (all ?? []).some((c) => c.parent === g.id)), [all]);

  if (!ability.viewGroups || (list.error instanceof ApiError && list.error.status === 403)) return <NoPermission />;

  const columns: Column<ItemGroup>[] = [
    { key: "name", header: M.colGroupName, render: (g) => g.name },
    { key: "parent", header: M.colGroupParent, render: (g) => g.parent_name ?? <span className="muted">{M.none}</span> },
    { key: "count", header: M.colGroupCount, num: true, render: (g) => g.item_count },
  ];

  const refreshFailed = all !== undefined && list.error != null && !list.loading;
  const filtered = !!parent;

  return (
    <ListPage
      id="catalog-panel"
      tabs={tabs}
      actions={
        ability.addGroup ? (
          <button type="button" className="btn primary" onClick={() => setAdding(true)} disabled={all === undefined}>
            <Icon name="add" />
            <span>{M.addGroup}</span>
          </button>
        ) : undefined
      }
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.groupSearchPlaceholder}
          searchLabel={M.groupSearchLabel}
          selects={
            parents.length > 0
              ? [
                  {
                    key: "parent",
                    label: M.filterParent,
                    value: parent,
                    options: [{ value: "", label: M.filterParentAll }, ...parents.map((g) => ({ value: String(g.id), label: g.name }))],
                    onChange: setParent,
                  },
                ]
              : []
          }
          summary={rows ? M.groupShown(rows.length, list.count) : undefined}
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
        caption={M.groupsCaption}
        columns={columns}
        rows={rows ?? null}
        rowKey={(g) => g.id}
        loading={list.loading && all === undefined}
        error={all === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={q.trim()}
        onClearQuery={() => setQ("")}
        noun={M.groupsNoun}
        empty={{
          icon: filtered ? "filter_list_off" : "category",
          title: filtered ? M.emptyFilteredTitle : M.groupsEmptyTitle,
          hint: filtered ? M.emptyFilteredHint : ability.addGroup ? M.groupsEmptyHint : M.groupsEmptyReadOnlyHint,
        }}
        canViewCost={false}
        dense
      />
      {adding && all && (
        <ItemGroupModal
          groups={all}
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false);
            toast.success(M.groupCreated);
            void list.reload();
          }}
        />
      )}
    </ListPage>
  );
}
