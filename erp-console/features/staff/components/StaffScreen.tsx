"use client";

// Màn Nhân sự (ED-37 / W3f): /staff/. Khung ListPage: nút "Thêm nhân viên" · ba tab Đang làm / Đã nghỉ / Tất cả (có số đếm) · ô tìm
// "Tìm tên, số điện thoại, nhóm…" · bảng nhân viên (bấm dòng → trang hồ sơ /staff/detail/?id=) · bảng "Nhóm quyền" (bấm → trang nhóm).
// Danh sách tải MỘT lần (mọi tài khoản), tab và tìm kiếm tính phía máy nên số đếm luôn khớp. Thao tác (đổi nhóm, đặt lại mật khẩu, cho nghỉ…)
// nằm ở trang hồ sơ. SĐT/tên nhân viên chỉ ở bộ nhớ trang: không URL (chỉ `?tab=`), không storage, không log.

import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { groupHref } from "@/features/permissions/permissionsModel";
import { useGroupList } from "@/features/permissions/useGroupData";
import type { GroupSummary } from "@/features/permissions/types";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { canView } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { Tabs, useTabParam, type TabItem } from "@/shared/ui/Tabs";
import { filterStaff } from "../api";
import { STAFF_MSG as M } from "../messages";
import { STAFF_TABS, asTab, countByTab, rowsOfTab } from "../staffModel";
import type { StaffMember } from "../types";
import { useStaffList } from "../useStaffData";
import { StaffFormModal } from "./StaffFormModal";
import { GroupTags } from "./parts";
import s from "../staff.module.css";

const TAB_KEYS = STAFF_TABS.map((t) => t.key);

export function StaffScreen() {
  const { me } = useAuth();
  const toast = useToast();
  const [tabKey, selectTab] = useTabParam(TAB_KEYS, "active");
  const tab = asTab(tabKey);
  const [q, setQ] = useState("");
  const [adding, setAdding] = useState(false);
  const list = useStaffList(!!me);
  const showGroups = canView(me, "permissions");
  const groups = useGroupList(!!me && showGroups);

  const rows = list.data;
  const counts = useMemo(() => (rows ? countByTab(rows) : null), [rows]);
  const shown = useMemo(() => (rows ? filterStaff(rowsOfTab(rows, tab), q.trim()) : null), [rows, tab, q]);

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission />;

  const tabs: TabItem[] = STAFF_TABS.map((t) => ({ key: t.key, label: t.label, count: counts ? counts[t.key] : null }));

  const columns: Column<StaffMember>[] = [
    { key: "name", header: M.colName, render: (r) => r.display_name || r.username },
    { key: "user", header: M.colUsername, mono: true, hideBelow: 720, render: (r) => r.username },
    { key: "phone", header: M.colPhone, mono: true, hideBelow: 800, render: (r) => r.phone || <span className="muted">—</span> },
    { key: "groups", header: M.colGroups, render: (r) => <GroupTags groups={r.groups} /> },
    { key: "status", header: M.colStatus, render: (r) => <Chip table={ENUMS.staffStatus} value={r.is_active ? "ACTIVE" : "INACTIVE"} /> },
    { key: "last", header: M.colLastLogin, num: true, hideBelow: 980, render: (r) => (r.last_login ? dateTime(r.last_login) : <span className="muted">{M.neverLoggedIn}</span>) },
  ];

  const groupCols: Column<GroupSummary>[] = [
    { key: "name", header: M.colGroupName, render: (g) => g.label },
    { key: "members", header: M.colMembers, num: true, render: (g) => M.groupMembers(g.member_count) },
    {
      key: "tasks",
      header: M.colTasks,
      num: true,
      render: (g) => {
        const all = Object.values(g.capabilities);
        return M.groupTasks(all.filter((v) => v === "on").length, all.length);
      },
    },
  ];

  const emptyTitle = tab === "active" ? M.emptyActiveTitle : tab === "inactive" ? M.emptyInactiveTitle : M.emptyAllTitle;
  const emptyHint = tab === "inactive" ? M.emptyInactiveHint : tab === "active" ? M.emptyActiveHint : M.emptyAllHint;
  const refreshFailed = rows !== null && list.error != null && !list.reloading;

  return (
    <ListPage
      id="staff-panel"
      actions={
        <button type="button" className="btn primary" onClick={() => setAdding(true)}>
          <Icon name="add" />
          <span>{M.add}</span>
        </button>
      }
      tabs={<Tabs tabs={tabs} value={tab} onChange={selectTab} label={M.tabsLabel} panelId="staff-panel" />}
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.searchPlaceholder}
          searchLabel={M.searchLabel}
          summary={shown && rows ? M.shown(shown.length, rowsOfTab(rows, tab).length) : undefined}
        />
      }
      banner={
        refreshFailed ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(list.error)}</span>
            <button type="button" className="btn" onClick={() => void list.reload()}>
              {M.retry}
            </button>
          </div>
        ) : undefined
      }
      onRetry={() => void list.reload()}
    >
      <div className={s.pageStack}>
        <DataTable
          caption={M.listTitle}
          columns={columns}
          rows={shown}
          rowKey={(r) => r.id}
          rowHref={(r) => `/staff/detail/?id=${r.id}`}
          loading={list.status === "loading"}
          error={rows === null && list.error != null ? loadErrorText(list.error) : null}
          onRetry={() => void list.reload()}
          query={q.trim()}
          onClearQuery={() => setQ("")}
          noun={M.noun}
          empty={{
            icon: "group_off",
            title: emptyTitle,
            hint: emptyHint,
            action:
              tab !== "inactive" ? (
                <button type="button" className="btn primary" onClick={() => setAdding(true)}>
                  {M.add}
                </button>
              ) : undefined,
          }}
          canViewCost={false}
        />

        {showGroups && groups.status !== "forbidden" && (
          <section className={s.section} aria-label={M.groupsTitle}>
            <h3 className={s.sectionH}>
              {M.groupsTitle}
              {groups.data && <span className={s.sectionCount}>{groups.data.length}</span>}
            </h3>
            <DataTable
              caption={M.groupsCaption}
              columns={groupCols}
              rows={groups.data}
              rowKey={(g) => g.code}
              rowHref={(g) => groupHref(g.code)}
              loading={groups.status === "loading"}
              error={groups.status === "error" || groups.status === "notfound" ? M.groupsFailed : null}
              onRetry={() => void groups.reload()}
              noun="nhóm"
              empty={{ icon: "shield_person", title: M.groupsFailed }}
              canViewCost={false}
              dense
            />
          </section>
        )}
      </div>

      {adding && (
        <StaffFormModal
          onClose={() => setAdding(false)}
          onCreated={(m) => {
            toast.success(M.created(m.username));
            void list.reload();
            if (showGroups) void groups.reload();
          }}
        />
      )}
    </ListPage>
  );
}
