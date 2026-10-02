"use client";

// Chi tiết một nhóm quyền (ED-40 / W3i): /permissions/detail/?group=<mã>. Khung DetailPage: header (tên nhóm · số người · "Thêm người vào nhóm"),
// cột trái: "Thông tin nhóm" (khoá: nhóm do hệ thống tạo) · "Thành viên" (bảng, bấm → hồ sơ nhân viên, "Bỏ khỏi nhóm") · "Việc được làm"
// (công tắc theo khu, nhóm Chủ chỉ xem). Cột phải: "Phạm vi dữ liệu" (chỉ đọc, BE dựng chuỗi) và "Lịch sử thay đổi".
// Việc "Xem khách hàng" đang bật ghi rõ "Tất cả khách" + cảnh báo (quyết định #13, bất biến 9). Chủ mới bật/tắt được; mọi lỗi hiện nguyên văn BE.
// Mã nhóm trong URL là mã hệ thống (không có tên người). Không ghi storage/log.

import { useCallback, useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import { PERM, homePath } from "@/shared/lib/nav";
import { dateTime } from "@/shared/lib/format";
import { groupLabel } from "@/shared/lib/groups";
import { loadErrorText } from "@/shared/lib/http";
import { ENUMS } from "@/shared/lib/enums";
import { ROLE } from "@/shared/lib/roles";
import { Chip } from "@/shared/ui/Chip";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import { Section } from "@/shared/ui/detail/Section";
import { Timeline } from "@/shared/ui/detail/Timeline";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { useToast } from "@/shared/ui/overlay/Toast";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { PERM_MSG as M } from "../messages";
import {
  ALL_CUSTOMERS_LABEL,
  CUSTOMERS_KEY,
  cellMode,
  isAssignedOnly,
  parseGroupCode,
  sectionsOf,
} from "../permissionsModel";
import { cellKey, useCapabilityToggle, type ToggleGroup } from "../useCapabilityToggle";
import { useGroupCode, useGroupDetail, type Loaded } from "../useGroupData";
import type { GroupDetail, GroupMember, RegistryItem } from "../types";
import { AddMemberModal } from "./AddMemberModal";
import { ConfirmOffModal } from "./ConfirmOffModal";
import { PermSwitch } from "./PermSwitch";
import { RemoveMemberModal } from "./RemoveMemberModal";
import s from "../permissions.module.css";

export function DetailSkeleton() {
  return (
    <div className={s.detailSkel} role="status" aria-busy="true">
      <span className="sr-only">{`Đang tải ${M.detailNoun}…`}</span>
      <div aria-hidden="true">
        <span className="sk sk-m" />
        <span className="sk sk-l" />
        <span className="sk sk-m" />
        <span className="sk sk-l" />
        <span className="sk sk-s" />
      </div>
    </div>
  );
}

export function GroupDetailScreen() {
  const { me } = useAuth();
  const code = useGroupCode(parseGroupCode);
  const detail = useGroupDetail(code ?? null);
  const home = me ? homePath(me) : undefined;

  if (code === undefined) return <DetailSkeleton />;
  if (code === null) return <NotFoundScreen homeHref={home} />;
  if (detail.status === "forbidden") return <NoPermission homeHref={home} />;
  if (detail.status === "notfound") return <NotFoundScreen homeHref={home} />;
  if (detail.status === "error") return <ErrorScreen homeHref={home} onRetry={() => void detail.reload()} />;
  if (detail.status === "loading" || !detail.data) return <DetailSkeleton />;
  return <GroupDetailBody key={code} group={detail.data} detail={detail} />;
}

function GroupDetailBody({ group: g, detail }: { group: GroupDetail; detail: Loaded<GroupDetail> }) {
  const { me } = useAuth();
  const toast = useToast();
  const [modal, setModal] = useState<"add" | { remove: GroupMember } | null>(null);
  const isOwnerGroup = g.code === ROLE.owner;
  // Chỉ nhóm Chủ ghi được việc của nhóm (BE chặn thật); thêm/bỏ người cần manage_staff, riêng nhóm Chủ cũng chỉ Chủ.
  const viewerIsOwner = !!me?.groups.includes(ROLE.owner);
  const canEditTasks = viewerIsOwner && !isOwnerGroup;
  const canManageMembers = !!me?.permissions.includes(PERM.manageStaff) && (!isOwnerGroup || viewerIsOwner);

  const replace = detail.replace;
  const onSaved = useCallback((next: GroupDetail) => replace(next), [replace]);
  const toggler = useCapabilityToggle({ registry: g.registry, onSaved });
  const sections = useMemo(() => sectionsOf(g.registry), [g.registry]);
  const label = g.label || groupLabel(g.code);
  const toggleGroup: ToggleGroup = { code: g.code, label, states: g.capabilities, memberCount: g.member_count };

  const afterMembers = (message: string) => {
    toast.success(message);
    setModal(null);
    void detail.reload();
  };

  const memberCols = useMemo<Column<GroupMember>[]>(
    () => [
      {
        key: "name",
        header: M.colName,
        render: (m) => (
          <span>
            <span className={s.memberName}>{m.display_name || m.username}</span>
          </span>
        ),
      },
      { key: "user", header: M.colUsername, mono: true, render: (m) => m.username },
      {
        key: "other",
        header: M.colOtherGroups,
        render: (m) =>
          m.other_groups.length === 0 ? (
            <span className="muted">{M.noOtherGroups}</span>
          ) : (
            <span className={s.tags}>
              {m.other_groups.map((c) => (
                <span key={c} className="tag">
                  {groupLabel(c)}
                </span>
              ))}
            </span>
          ),
      },
      { key: "added", header: M.colAddedAt, num: true, hideBelow: 720, render: (m) => (m.added_at ? dateTime(m.added_at) : <span className="muted">—</span>) },
      { key: "status", header: M.colStatus, render: (m) => <Chip table={ENUMS.staffStatus} value={m.is_active ? "ACTIVE" : "INACTIVE"} /> },
      ...(canManageMembers
        ? [
            {
              key: "act",
              header: M.colAction,
              render: (m: GroupMember) => (
                <button type="button" className="btn" onClick={() => setModal({ remove: m })} aria-label={M.removeMemberFor(m.display_name || m.username)}>
                  {M.removeMember}
                </button>
              ),
            } satisfies Column<GroupMember>,
          ]
        : []),
    ],
    [canManageMembers],
  );

  return (
    <DetailPage
      id="group-detail"
      header={
        <DetailHeader
          back={{ href: "/permissions/", label: M.backToMatrix }}
          title={label}
          status={<span className="tag">{M.members(g.member_count)}</span>}
          primary={
            canManageMembers ? (
              <button type="button" className="btn primary" onClick={() => setModal("add")}>
                <Icon name="person_add" />
                <span>{M.addMember}</span>
              </button>
            ) : null
          }
        />
      }
      banner={
        <>
          {detail.error != null && !detail.reloading && (
            <div className="alert-box err" role="alert">
              <Icon name="sync_problem" />
              <span>{loadErrorText(detail.error)}</span>
              <button type="button" className="btn" onClick={() => void detail.reload()}>
                {M.retry}
              </button>
            </div>
          )}
          {toggler.error && (
            <div className="alert-box err" role="alert">
              <Icon name="error" />
              <span>{toggler.error}</span>
              <button type="button" className="btn" onClick={toggler.clearError}>
                {M.dismiss}
              </button>
            </div>
          )}
          {isOwnerGroup ? (
            <p className={s.note} role="note">
              <Icon name="lock" />
              <span>{M.ownerLockedBanner}</span>
            </p>
          ) : (
            !viewerIsOwner && (
              <p className={s.note} role="note">
                <Icon name="lock" />
                <span>{M.readOnlyBanner}</span>
              </p>
            )
          )}
        </>
      }
      timeline={
        <div className={s.rail}>
          <Section title={M.scopesTitle} aria-label={M.scopesTitle}>
            <p className={s.sectionHint}>{M.scopesIntro}</p>
            <dl className={s.scopes}>
              <ScopeRow term={M.scopeOrders} value={g.scopes.orders} />
              <ScopeRow term={M.scopeDeliveries} value={g.scopes.deliveries} />
              <ScopeRow term={M.scopeCustomers} value={g.scopes.customers} highlight={g.scopes.customers.includes(ALL_CUSTOMERS_LABEL)} />
            </dl>
          </Section>
          <div id="group-timeline" tabIndex={-1}>
            <Timeline entries={toTimelineEntries(g.timeline)} title={M.timelineTitle} />
          </div>
        </div>
      }
    >
      <InfoGrid title={M.sectionInfo}>
        <InfoField kind="locked" label={M.fieldName} value={label} reason={M.lockedReason} />
        <InfoField kind="locked" label={M.fieldCode} value={g.code} mono reason={M.lockedReason} />
        <InfoField kind="locked" label={M.fieldMembers} value={M.members(g.member_count)} num reason={M.lockedReason} />
        <InfoField kind="locked" label={M.fieldCost} value={g.can_view_cost ? M.yes : M.no} reason={M.lockedReason} />
      </InfoGrid>

      <Section title={M.membersTitle} count={M.members(g.members.length)} aria-label={M.membersTitle} flush>
        <DataTable
          caption={M.membersCaption}
          columns={memberCols}
          rows={g.members}
          rowKey={(m) => m.id}
          rowHref={(m) => `/staff/detail/?id=${m.id}`}
          noun={M.memberNoun}
          empty={{ icon: "group_off", title: M.membersEmpty, hint: canManageMembers ? M.membersEmptyHint : undefined }}
          canViewCost={false}
        />
      </Section>

      <Section title={M.tasksTitle} aria-label={M.tasksTitle}>
        <p className={s.sectionHint}>{M.tasksIntro}</p>
        <div className={s.tasks}>
          {sections.map((sec) => (
            <div key={sec.name} className={s.taskGroup}>
              <h4 className={s.taskGroupH}>{sec.name}</h4>
              <ul className={s.taskList}>
                {sec.items.map((item) => (
                  <TaskRow
                    key={item.key}
                    item={item}
                    group={g}
                    labelOf={toggler.labelOf}
                    canEdit={canEditTasks}
                    busy={toggler.busyCells.includes(cellKey(g.code, item.key))}
                    onToggle={() => toggler.toggle(toggleGroup, item.key)}
                  />
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      {toggler.pendingOff && (
        <ConfirmOffModal pending={toggler.pendingOff} onConfirm={toggler.confirmOff} onClose={toggler.cancelOff} labelOf={toggler.labelOf} />
      )}
      {modal === "add" && (
        <AddMemberModal
          groupCode={g.code}
          groupLabelText={label}
          onClose={() => setModal(null)}
          onAdded={(m) => afterMembers(M.added(m.display_name || m.username, label))}
        />
      )}
      {modal && modal !== "add" && (
        <RemoveMemberModal
          member={modal.remove}
          groupCode={g.code}
          groupLabelText={label}
          onClose={() => setModal(null)}
          onDone={() => afterMembers(M.removed(modal.remove.display_name || modal.remove.username, label))}
        />
      )}
    </DetailPage>
  );
}

function ScopeRow({ term, value, highlight = false }: { term: string; value: string; highlight?: boolean }) {
  return (
    <div className={s.scopeRow}>
      <dt>{term}</dt>
      <dd>
        {highlight ? (
          <span className={s.scopeAll}>
            <Icon name="warning" />
            {value}
          </span>
        ) : (
          value
        )}
      </dd>
    </div>
  );
}

function TaskRow({
  item,
  group,
  labelOf,
  canEdit,
  busy,
  onToggle,
}: {
  item: RegistryItem;
  group: GroupDetail;
  labelOf: (key: string) => string;
  canEdit: boolean;
  busy: boolean;
  onToggle: () => void;
}) {
  const mode = cellMode(item, group.code, group.capabilities[item.key]);
  const isCustomers = item.key === CUSTOMERS_KEY;
  const on = mode === "on" || mode === "owner";
  const assigned = (mode === "on" || mode === "partial") && isAssignedOnly(group.code, item.key);

  let control: React.ReactNode;
  if (mode === "owner") {
    control = (
      <span className={`${s.taskState} ${s.stateOn}`} title={M.ownerAlways}>
        <Icon name="check_circle" />
        <span>{M.cellOn}</span>
      </span>
    );
  } else if (mode === "locked") {
    control = (
      <span className={s.taskState} title={M.cellLockedOwner}>
        <Icon name="lock" />
        <span>{M.ownerOnlyBadge}</span>
      </span>
    );
  } else if (canEdit) {
    control = <PermSwitch state={mode === "on" ? "on" : mode === "partial" ? "partial" : "off"} label={`${item.label} — ${group.label}`} busy={busy} onToggle={onToggle} title={mode === "partial" ? M.cellPartial : undefined} />;
  } else {
    control = (
      <span className={`${s.taskState} ${on ? s.stateOn : ""}`}>
        <Icon name={on ? "check_circle" : mode === "partial" ? "indeterminate_check_box" : "remove"} />
        <span>{on ? M.cellOn : mode === "partial" ? "Một phần" : M.cellOff}</span>
      </span>
    );
  }

  return (
    <li className={s.taskRow}>
      <div className={s.taskText}>
        <span className={s.taskLabel}>
          {item.label}
          {item.owner_only && !isOwnerGroupCode(group.code) && (
            <span className="tag" title={M.ownerOnlyHint}>
              {M.ownerOnlyBadge}
            </span>
          )}
          {isCustomers && on && <span className={`tag ${s.tagWarn}`}>{ALL_CUSTOMERS_LABEL}</span>}
          {assigned && (
            <span className="tag" title={M.assignedOnlyHint}>
              {M.assignedOnly}
            </span>
          )}
        </span>
        {item.requires.length > 0 && <span className={s.taskSub}>{M.requiresNote(item.requires.map(labelOf).join(", "))}</span>}
        {isCustomers && !on && <span className={s.taskSub}>{M.allCustomersHint}</span>}
        {isCustomers && on && (
          <span className={s.taskWarn} role="note">
            <Icon name="warning" />
            <span>{M.customersWarning}</span>
          </span>
        )}
      </div>
      {control}
    </li>
  );
}

const isOwnerGroupCode = (code: string) => code === ROLE.owner;
