"use client";

// Màn Phân quyền (ED-40 / W3h): /permissions/. Hai khối: (1) bảng các nhóm (Nhóm · Số người · Xem giá vốn · Đổi lần cuối), bấm → trang nhóm;
// (2) ma trận việc x nhóm có ô tìm "Tìm việc…". Chủ bật/tắt ngay tại ô (công tắc); người khác có manage_staff chỉ xem.
// Cột Chủ luôn đủ quyền và khoá; việc "Chỉ Chủ" ở nhóm khác là ô khoá. Việc "Xem khách hàng" đang bật ghi rõ "Tất cả khách"
// (quyết định #13). Registry (danh sách việc) lấy từ chi tiết nhóm Chủ vì danh sách nhóm không kèm registry.
// Mọi con số lấy từ BE; ô chỉ đổi sau khi BE nhận (không cập nhật lạc quan). Không ghi gì vào storage/URL/log.

import Link from "next/link";
import { useCallback, useMemo, useRef, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { dateTime } from "@/shared/lib/format";
import { loadErrorText } from "@/shared/lib/http";
import { ROLE } from "@/shared/lib/roles";
import { homePath } from "@/shared/lib/nav";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { PERM_MSG as M } from "../messages";
import {
  ALL_CUSTOMERS_LABEL,
  CUSTOMERS_KEY,
  cellMode,
  groupHref,
  isAssignedOnly,
  isToggleable,
  matchesTask,
  sectionsOf,
} from "../permissionsModel";
import { cellKey, useCapabilityToggle, type ToggleGroup } from "../useCapabilityToggle";
import { useGroupDetail, useGroupList } from "../useGroupData";
import type { GroupDetail, GroupSummary, RegistryItem } from "../types";
import { ConfirmOffModal } from "./ConfirmOffModal";
import { PermSwitch } from "./PermSwitch";
import s from "../permissions.module.css";

export function PermissionMatrixScreen() {
  const { me } = useAuth();
  const list = useGroupList(!!me);
  const reg = useGroupDetail(me ? ROLE.owner : null);
  const [q, setQ] = useState("");
  const home = me ? homePath(me) : undefined;
  // Chỉ nhóm Chủ ghi được (BE chặn thật); superuser không thuộc nhóm Chủ thì màn chỉ xem để khỏi hiện nút bấm sẽ bị 403.
  const canEdit = !!me?.groups.includes(ROLE.owner);

  const listRef = useRef<GroupSummary[] | null>(null);
  listRef.current = list.data;
  const replaceList = list.replace;
  const onSaved = useCallback(
    (next: GroupDetail) => {
      const cur = listRef.current;
      if (!cur) return;
      replaceList(
        cur.map((g) =>
          g.code === next.code
            ? { ...g, capabilities: next.capabilities, can_view_cost: next.can_view_cost, last_changed_at: next.last_changed_at, last_changed_by: next.last_changed_by }
            : g,
        ),
      );
    },
    [replaceList],
  );

  const registry = useMemo(() => reg.data?.registry ?? [], [reg.data]);
  const toggler = useCapabilityToggle({ registry, onSaved });
  const sections = useMemo(() => sectionsOf(registry), [registry]);

  const reloadAll = () => {
    void list.reload();
    void reg.reload();
  };

  if (list.status === "forbidden" || reg.status === "forbidden") return <NoPermission homeHref={home} />;

  const failed = list.status === "error" || reg.status === "error" || reg.status === "notfound";
  const loading = !failed && (list.status === "loading" || reg.status === "loading");
  const errText = failed ? loadErrorText(list.status === "error" ? list.error : reg.error) : null;
  const groups = list.data ?? [];

  const groupColumns: Column<GroupSummary>[] = [
    { key: "group", header: M.colGroup, render: (g) => g.label },
    { key: "members", header: M.colMembers, num: true, render: (g) => M.members(g.member_count) },
    {
      key: "cost",
      header: M.colCanSeeCost,
      render: (g) => <span className={`status ${g.can_view_cost ? "good" : "mute"}`}>{g.can_view_cost ? M.yes : M.no}</span>,
    },
    {
      key: "changed",
      header: M.colChanged,
      num: true,
      render: (g) =>
        g.last_changed_at ? M.changedBy(dateTime(g.last_changed_at), g.last_changed_by ?? "") : <span className="muted">{M.neverChanged}</span>,
    },
  ];

  return (
    <ListPage
      onRetry={reloadAll}
      banner={
        toggler.error ? (
          <div className="alert-box err" role="alert">
            <Icon name="error" />
            <span>{toggler.error}</span>
            <button type="button" className="btn" onClick={toggler.clearError}>
              {M.dismiss}
            </button>
          </div>
        ) : undefined
      }
    >
      <p className={s.intro}>{M.matrixIntro}</p>

      <section className={s.section} aria-label={M.groupsCaption}>
        <h3 className={s.sectionH}>{M.groupsCaption}</h3>
        <DataTable
          caption={M.groupsCaption}
          columns={groupColumns}
          rows={failed ? null : list.data}
          rowKey={(g) => g.code}
          rowHref={(g) => groupHref(g.code)}
          loading={list.status === "loading"}
          error={failed ? (errText ?? M.loadFailed) : null}
          onRetry={reloadAll}
          noun={M.noun}
          empty={{ icon: "groups", title: M.groupsEmpty, hint: M.groupsEmptyHint }}
          canViewCost={false}
        />
      </section>

      <section className={s.section} aria-label={M.matrixCaption}>
        <h3 className={s.sectionH}>{M.matrixCaption}</h3>
        {!canEdit && !loading && !failed && (
          <p className={s.note} role="note">
            <Icon name="lock" />
            <span>{M.readOnlyNote}</span>
          </p>
        )}
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.matrixSearchPlaceholder}
          searchLabel={M.matrixSearchLabel}
          summary={registry.length ? M.matrixShown(registry.filter((r) => matchesTask(r, q)).length, registry.length) : undefined}
        />
        <div className={s.matrixCard} aria-busy={loading || undefined}>
          {loading && (
            <div className={s.matrixSkel} role="status">
              <span className="sr-only">Đang tải ma trận phân quyền…</span>
              <div aria-hidden="true">
                <span className="sk sk-l" />
                <span className="sk sk-l" />
                <span className="sk sk-m" />
                <span className="sk sk-l" />
                <span className="sk sk-m" />
              </div>
            </div>
          )}
          {failed && (
            <div className="state state-err" role="alert">
              <span className="state-ic">
                <Icon name="sync_problem" />
              </span>
              <p className="state-title">{errText ?? M.loadFailed}</p>
              <button type="button" className="btn" onClick={reloadAll}>
                <Icon name="refresh" />
                {M.retry}
              </button>
            </div>
          )}
          {!loading && !failed && (
            <Matrix
              groups={groups}
              sections={sections}
              q={q}
              canEdit={canEdit}
              busyCells={toggler.busyCells}
              onToggle={(g, key) => toggler.toggle(asToggleGroup(g), key)}
            />
          )}
        </div>
      </section>

      {toggler.pendingOff && (
        <ConfirmOffModal pending={toggler.pendingOff} onConfirm={toggler.confirmOff} onClose={toggler.cancelOff} labelOf={toggler.labelOf} />
      )}
    </ListPage>
  );
}

function asToggleGroup(g: GroupSummary): ToggleGroup {
  return { code: g.code, label: g.label, states: g.capabilities, memberCount: g.member_count };
}

type MatrixProps = {
  groups: GroupSummary[];
  sections: ReturnType<typeof sectionsOf>;
  q: string;
  canEdit: boolean;
  busyCells: string[];
  onToggle: (group: GroupSummary, key: string) => void;
};

function Matrix({ groups, sections, q, canEdit, busyCells, onToggle }: MatrixProps) {
  const visible = sections
    .map((sec) => ({ name: sec.name, items: sec.items.filter((i) => matchesTask(i, q)) }))
    .filter((sec) => sec.items.length > 0);
  const total = visible.reduce((n, sec) => n + sec.items.length, 0);
  const cols = groups.length + 2;

  if (groups.length === 0 || sections.length === 0) {
    return <p className={s.matrixEmpty}>{M.groupsEmpty}</p>;
  }

  return (
    <div className={s.matrixScroll} tabIndex={0} role="region" aria-label={M.matrixCaption}>
      <table className={s.matrix}>
        <caption className="sr-only">{M.matrixCaption}</caption>
        <thead>
          <tr>
            <th scope="col" className={s.taskCol}>
              {M.colTask}
            </th>
            {groups.map((g) => (
              <th key={g.code} scope="col" className={g.code === ROLE.owner ? s.ownerCol : undefined}>
                <span className={s.groupHead}>
                  <Link className={s.groupLink} href={groupHref(g.code)} aria-label={M.openGroup(g.label)}>
                    {g.label}
                  </Link>
                </span>
              </th>
            ))}
            <th scope="col" title={M.ownerOnlyHint}>
              {M.ownerOnlyHeader}
            </th>
          </tr>
        </thead>
        <tbody>
          {total === 0 && (
            <tr>
              <td colSpan={cols} className={s.matrixEmpty}>
                {M.matrixEmptyQuery(q.trim())}
              </td>
            </tr>
          )}
          {visible.map((sec) => (
            <SectionRows key={sec.name} name={sec.name} items={sec.items} groups={groups} cols={cols} canEdit={canEdit} busyCells={busyCells} onToggle={onToggle} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SectionRows({
  name,
  items,
  groups,
  cols,
  canEdit,
  busyCells,
  onToggle,
}: {
  name: string;
  items: RegistryItem[];
  groups: GroupSummary[];
  cols: number;
  canEdit: boolean;
  busyCells: string[];
  onToggle: (group: GroupSummary, key: string) => void;
}) {
  return (
    <>
      <tr className={s.sectionRow}>
        <th scope="colgroup" colSpan={cols}>
          {name}
        </th>
      </tr>
      {items.map((item) => (
        <tr key={item.key}>
          <th scope="row" className={s.task}>
            <span className={s.taskName}>{item.label}</span>
          </th>
          {groups.map((g) => (
            <td key={g.code} className={g.code === ROLE.owner ? s.ownerCol : undefined}>
              <MatrixCell group={g} item={item} canEdit={canEdit} busy={busyCells.includes(cellKey(g.code, item.key))} onToggle={() => onToggle(g, item.key)} />
            </td>
          ))}
          <td>
            {item.owner_only ? (
              <span className="tag" title={M.ownerOnlyHint}>
                {M.ownerOnlyBadge}
              </span>
            ) : (
              <span className="muted" aria-label={M.no}>
                —
              </span>
            )}
          </td>
        </tr>
      ))}
    </>
  );
}

function MatrixCell({ group, item, canEdit, busy, onToggle }: { group: GroupSummary; item: RegistryItem; canEdit: boolean; busy: boolean; onToggle: () => void }) {
  const mode = cellMode(item, group.code, group.capabilities[item.key]);
  const name = `${item.label} — ${group.label}`;
  const allCustomers = item.key === CUSTOMERS_KEY && (mode === "on" || mode === "owner");
  const assigned = (mode === "on" || mode === "partial") && isAssignedOnly(group.code, item.key);

  let control: React.ReactNode;
  if (mode === "owner") {
    control = (
      <span className={`${s.cellFixed} ${s.cellOn}`} title={M.ownerAlways}>
        <Icon name="check_circle" />
        <span className="sr-only">{`${name}: ${M.cellOn}. ${M.ownerAlways}`}</span>
      </span>
    );
  } else if (mode === "locked") {
    control = (
      <span className={`${s.cellFixed} ${s.cellLocked}`} title={M.cellLockedOwner}>
        <Icon name="lock" />
        <span className="sr-only">{`${name}: ${M.cellOff}. ${M.cellLockedOwner}`}</span>
      </span>
    );
  } else if (canEdit && isToggleable(mode)) {
    control = (
      <PermSwitch
        state={mode === "on" ? "on" : mode === "partial" ? "partial" : "off"}
        label={name}
        busy={busy}
        onToggle={onToggle}
        title={mode === "partial" ? M.cellPartial : undefined}
      />
    );
  } else {
    const on = mode === "on";
    control = (
      <span className={`${s.cellFixed} ${on ? s.cellOn : s.cellOff}`}>
        <Icon name={on ? "check_circle" : mode === "partial" ? "indeterminate_check_box" : "remove"} />
        <span className="sr-only">{`${name}: ${on ? M.cellOn : mode === "partial" ? M.cellPartial : M.cellOff}`}</span>
      </span>
    );
  }

  return (
    <span className={s.cell}>
      {control}
      {allCustomers && (
        <span className={`tag ${s.cellTag} ${s.tagWarn}`} title={M.allCustomersHint}>
          {ALL_CUSTOMERS_LABEL}
        </span>
      )}
      {assigned && (
        <span className={`tag ${s.cellTag}`} title={M.assignedOnlyHint}>
          {M.assignedOnly}
        </span>
      )}
    </span>
  );
}
