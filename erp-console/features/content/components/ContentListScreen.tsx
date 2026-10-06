"use client";

// Danh sách bài viết và trang (ED-35 / W3b): khung ListPage, tab theo trạng thái (kèm số đếm), lọc loại và chuyên mục,
// tìm tại chỗ theo tiêu đề hoặc đường dẫn (BE chưa có tìm kiếm), bảng DataTable bấm dòng để mở bài.
// Từ khoá chỉ nằm trong state. URL chỉ giữ khoá tab và mã chuyên mục (không có dữ liệu cá nhân).

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { aiVisible } from "@/shared/lib/features";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { useResource } from "@/shared/lib/useResource";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { Tabs, useTabParam } from "@/shared/ui/Tabs";
import { fetchCategories, fetchEntries, fetchEntryCounts, fetchGoliveStatus } from "../api";
import {
  CONTENT_PERM,
  STATUS_TAB_KEYS,
  type StatusTab,
  categoryFilterOf,
  entryNote,
  filterEntries,
  hasPerm,
  kindFilterOf,
  statusOfTab,
} from "../contentModel";
import { CONTENT_MSG as M } from "../messages";
import type { ContentEntryListItem } from "../types";

type ListParams = { status: string; kind: string; category: number };

const KIND_OPTIONS = [
  { value: "", label: M.kindAll },
  { value: "post", label: ENUMS.entryKind.post.label },
  { value: "page", label: ENUMS.entryKind.page.label },
];

const TAB_LABELS: Record<StatusTab, string> = {
  all: M.tabAll,
  draft: ENUMS.entryStatus.draft.label,
  pending_review: ENUMS.entryStatus.pending_review.label,
  published: ENUMS.entryStatus.published.label,
  unpublished: ENUMS.entryStatus.unpublished.label,
};

function roleLabel(role: string): string {
  const row = (ENUMS.entryPageRole as Record<string, { label: string }>)[role];
  return row ? row.label : role;
}

export function ContentListScreen() {
  const { me } = useAuth();
  const aiOn = aiVisible(me); // W39: AI tắt thì bỏ cột "AI" và ghi chú "AI soạn nháp"
  const [tab, selectTab] = useTabParam(STATUS_TAB_KEYS, "all");
  const [kind, setKind] = useState("");
  const [category, setCategory] = useState(0);
  const [q, setQ] = useState("");
  const canView = hasPerm(me, CONTENT_PERM.view);
  const canAdd = hasPerm(me, CONTENT_PERM.add);
  const canManageCategories = canView;

  // Mã chuyên mục từ link "Xem N bài" ở màn Chuyên mục: chỉ nhận số.
  useEffect(() => {
    const v = new URLSearchParams(window.location.search).get("category");
    if (v) setCategory(categoryFilterOf(v));
  }, []);

  const params: ListParams = useMemo(() => ({ status: statusOfTab(tab as StatusTab), kind, category }), [tab, kind, category]);
  const list = usePagedList<ContentEntryListItem, ListParams>(
    (p, page) => fetchEntries({ status: p.status || undefined, kind: p.kind || undefined, category: p.category || undefined, page }),
    params,
    !!me && canView,
  );
  const counts = useResource(me && canView ? `content-counts:${kind}` : null, () => fetchEntryCounts(kind ? { kind } : undefined), 0);
  const cats = useResource(me && canView ? "content-categories" : null, () => fetchCategories(), 0);
  const golive = useResource(me && canView ? "content-golive" : null, () => fetchGoliveStatus(), 0);

  const catNames = useMemo(() => new Map((cats.data ?? []).map((c) => [c.id, c.name])), [cats.data]);
  const catOptions = useMemo(
    () => [{ value: "", label: M.categoryAll }, ...(cats.data ?? []).map((c) => ({ value: String(c.id), label: c.name }))],
    [cats.data],
  );
  const shownRows = useMemo(() => (list.rows ? filterEntries(list.rows, q) : undefined), [list.rows, q]);

  if (me && !canView) return <NoPermission />;
  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission />;

  const tabs = STATUS_TAB_KEYS.map((k) => {
    const n = k === "all" ? undefined : counts.data?.[k];
    return { key: k, label: TAB_LABELS[k], count: n ?? null };
  });
  const filtered = tab !== "all" || kind !== "" || category !== 0;
  const missingRoles = golive.data?.missing_roles ?? [];
  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;

  const columns: Column<ContentEntryListItem>[] = [
    { key: "title", header: M.colTitle, render: (r) => <b>{r.title || "Chưa đặt tiêu đề"}</b> },
    { key: "path", header: M.colPath, mono: true, hideBelow: 980, render: (r) => r.slug || <span className="muted">—</span> },
    { key: "kind", header: M.colKind, hideBelow: 720, render: (r) => ENUMS.entryKind[r.kind].label },
    {
      key: "category",
      header: M.colCategory,
      hideBelow: 800,
      render: (r) => {
        const name = r.category === null ? "" : catNames.get(r.category) ?? "";
        return name || <span className="muted">—</span>;
      },
    },
    { key: "status", header: M.colStatus, render: (r) => <Chip table={ENUMS.entryStatus} value={r.status} /> },
    ...(aiOn ? [{ key: "ai", header: M.colAi, hideBelow: 1100 as const, render: (r: ContentEntryListItem) => (r.source === "ai" ? <Chip table={ENUMS.entrySource} value="ai" /> : <span className="muted">—</span>) }] : []),
    {
      key: "note",
      header: M.colNote,
      hideBelow: 1100,
      render: (r) => {
        const note = entryNote(r, aiOn);
        return note || <span className="muted">—</span>;
      },
    },
    { key: "updated", header: M.colUpdated, tabular: true, hideBelow: 720, render: (r) => dateTime(r.updated_at) },
  ];

  return (
    <ListPage
      actions={
        <>
          {canManageCategories && (
            <Link href="/content/categories/" className="btn">
              <Icon name="category" />
              <span>{M.manageCategories}</span>
            </Link>
          )}
          {canAdd && (
            <Link href="/content/edit/?new=page" className="btn">
              <Icon name="description" />
              <span>{M.newPage}</span>
            </Link>
          )}
          {canAdd && (
            <Link href="/content/edit/?new=post" className="btn primary">
              <Icon name="add" />
              <span>{M.newPost}</span>
            </Link>
          )}
        </>
      }
      tabs={<Tabs tabs={tabs} value={tab} onChange={selectTab} label={M.tabsLabel} />}
      banner={
        <>
          {missingRoles.length > 0 && (
            <div className="alert-box warn" role="status">
              <Icon name="warning" />
              <span>{M.goliveMissing(missingRoles.map(roleLabel))}</span>
              {canAdd && (
                <Link href="/content/edit/?new=page" className="inline-link">
                  {M.newPage}
                </Link>
              )}
            </div>
          )}
          {refreshFailed && (
            <div className="alert-box err" role="alert">
              <Icon name="sync_problem" />
              <span>{loadErrorText(list.error)}</span>
            </div>
          )}
        </>
      }
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.searchPlaceholder}
          searchLabel={M.searchLabel}
          selects={[
            { key: "kind", label: M.kindLabel, value: kind, options: KIND_OPTIONS, onChange: (v) => setKind(kindFilterOf(v)) },
            { key: "category", label: M.categoryLabel, value: category ? String(category) : "", options: catOptions, onChange: (v) => setCategory(categoryFilterOf(v)) },
          ]}
          summary={list.rows ? M.shown(list.rows.length, list.count) : undefined}
        />
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
      asOf={list.asOf}
      onRetry={() => void list.reload()}
    >
      <DataTable
        canViewCost={false}
        caption={M.listTitle}
        columns={columns}
        rows={shownRows ?? null}
        rowKey={(r) => r.id}
        rowHref={(r) => `/content/edit/?id=${r.id}`}
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={q.trim()}
        onClearQuery={() => setQ("")}
        noun={M.noun}
        dense
        empty={{
          icon: filtered ? "filter_alt_off" : "article",
          title: filtered ? M.emptyFilteredTitle : M.emptyTitle,
          hint: filtered ? M.emptyFilteredHint : M.emptyHint,
          action:
            canAdd && !filtered ? (
              <Link href="/content/edit/?new=post" className="btn primary">
                {M.newPost}
              </Link>
            ) : undefined,
        }}
      />
    </ListPage>
  );
}
