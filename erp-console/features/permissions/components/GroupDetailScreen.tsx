"use client";

// Chi tiết một nhóm quyền (ED-40 / W3i): /permissions/detail/?group=<mã>. Khung DetailPage: header (tên nhóm · số người · "Thêm người vào nhóm"),
// cột trái: "Thông tin nhóm" (khoá: nhóm do hệ thống tạo) · "Thành viên" (bảng, bấm → hồ sơ nhân viên, "Bỏ khỏi nhóm") · "Việc được làm"
// (công tắc theo khu, nhóm Chủ chỉ xem) · "Phạm vi dữ liệu" (8 dòng, ô chọn theo `data_scopes` của BE). Cột phải: "Lịch sử thay đổi".
// PV-11: việc và phạm vi là BẢN NHÁP trong bộ nhớ; thanh "Lưu thay đổi / Huỷ thay đổi" gửi MỘT PUT có `version` (PV-10), sau bước xem trước
// và hộp xác nhận khi mở rộng dữ liệu khách (PV-09). Chủ HOẶC superuser mới sửa được; mọi lỗi hiện nguyên văn BE.
// Việc "Xem khách hàng" đang bật ghi rõ "Tất cả khách" + cảnh báo (quyết định #13, bất biến 9).
// Mã nhóm trong URL là mã hệ thống (không có tên người). Không ghi storage/log.

import { objectLabelOf } from "../objectLabel";
import { useCallback, useId, useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import { PERM, homePath } from "@/shared/lib/nav";
import { aiVisible } from "@/shared/lib/features";
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
  applyChanges,
  cellMode,
  effectiveValues,
  isAssignedOnly,
  isGroupWriter,
  isScopeInactive,
  parseGroupCode,
  scopeValueLabel,
  sectionsOf,
  showsAllCustomers,
  visibleRegistry,
} from "../permissionsModel";
import { useGroupDraft } from "../useGroupDraft";
import { useGroupCode, useGroupDetail, type Loaded } from "../useGroupData";
import type { CapabilityState, DataScopeRow, GroupDetail, GroupMember, RegistryItem } from "../types";
import { AddMemberModal } from "./AddMemberModal";
import { ConfirmSaveModal } from "./ConfirmSaveModal";
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
  // Chủ HOẶC superuser ghi được (BE chặn thật, Duy chốt 06/10); thêm/bỏ người cần manage_staff, riêng nhóm Chủ cũng chỉ người ghi được.
  const viewerIsWriter = isGroupWriter(me);
  const canEdit = viewerIsWriter && !isOwnerGroup;
  const canManageMembers = !!me?.permissions.includes(PERM.manageStaff) && (!isOwnerGroup || viewerIsWriter);

  const replace = detail.replace;
  const reload = detail.reload;
  const onSaved = useCallback((next: GroupDetail) => replace(next), [replace]);
  const aiOn = aiVisible(me);
  const registry = useMemo(() => visibleRegistry(g.registry, aiOn), [g.registry, aiOn]);
  const drafting = useGroupDraft({ group: g, onSaved, reload });
  const { draft } = drafting;
  const states = useMemo(() => applyChanges(g.capabilities, draft.capabilities), [g.capabilities, draft.capabilities]);
  const values = useMemo(() => effectiveValues(g.data_scope_values, draft), [g.data_scope_values, draft]);
  const sections = useMemo(() => sectionsOf(registry), [registry]);
  const label = g.label || groupLabel(g.code);
  // `labelOf` đọc registry GỐC `g.registry` (không phải bản đã lọc AI ở `registry`) có chủ đích: nhãn trong chip `requires` của một việc vẫn phải tra
  // được dù việc đó đang bị ẩn. Đừng "đồng bộ" thành bản đã lọc (review techlead F1 gộp main, L2).
  const labelOf = useCallback((key: string) => g.registry.find((r) => r.key === key)?.label ?? key, [g.registry]);
  // Khoá `widened` có thể là đối tượng phạm vi hoặc việc V2 (`view_order_customer_info`), nên tra thêm nhãn việc ở registry gốc.
  const objectLabel = useCallback((key: string) => objectLabelOf(key, g.data_scopes, g.registry), [g.data_scopes, g.registry]);

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
          {drafting.conflict && (
            <div className="alert-box warn" role="alert" data-testid="group-conflict">
              <Icon name="sync_problem" />
              <span>{M.conflictText}</span>
              <button type="button" className="btn" onClick={() => void drafting.reloadAfterConflict()} disabled={drafting.reloading}>
                {drafting.reloading ? <Icon name="progress_activity" className="spin" /> : <Icon name="refresh" />}
                <span>{drafting.reloading ? M.conflictReloading : M.conflictReload}</span>
              </button>
            </div>
          )}
          {isOwnerGroup ? (
            <p className={s.note} role="note">
              <Icon name="lock" />
              <span>{M.ownerLockedBanner}</span>
            </p>
          ) : (
            !viewerIsWriter && (
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
        <div className={canManageMembers ? s.memberTable : undefined}>
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
        </div>
      </Section>

      <Section title={M.tasksTitle} aria-label={M.tasksTitle}>
        <p className={s.sectionHint}>{canEdit ? M.tasksIntroDraft : M.tasksIntro}</p>
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
                    state={states[item.key]}
                    scopeValues={values}
                    unsaved={item.key in draft.capabilities}
                    labelOf={labelOf}
                    canEdit={canEdit}
                    disabled={drafting.saving}
                    onToggle={() => drafting.toggleCap(item.key)}
                  />
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      <Section title={M.scopesTitle} aria-label={M.scopesTitle}>
        <p className={s.sectionHint}>{canEdit ? M.scopesIntro : M.scopesIntroReadOnly}</p>
        <ul className={s.scopeList} data-testid="scope-list">
          {g.data_scopes.map((row) => (
            <ScopeRowEditor
              key={row.key}
              row={row}
              value={values[row.key] ?? row.value}
              inactive={isScopeInactive(row, states, draft)}
              unsaved={row.key in draft.scopes}
              canEdit={canEdit}
              disabled={drafting.saving}
              onChange={(v) => drafting.setScope(row.key, v)}
            />
          ))}
        </ul>
      </Section>

      {canEdit && drafting.size > 0 && (
        <div className={s.saveBar} role="region" aria-label={M.draftBarLabel} data-testid="draft-bar">
          <div className={s.saveBarText}>
            <span className={s.saveBarCount}>{M.draftCount(drafting.size)}</span>
            {(drafting.problem || drafting.saveError) && (
              <span className={s.saveBarError} role="alert">
                <Icon name="error" />
                <span>{drafting.problem ?? drafting.saveError}</span>
              </span>
            )}
          </div>
          <div className={s.saveBarActions}>
            <button type="button" className="btn" onClick={drafting.discard} disabled={drafting.saving}>
              {M.draftDiscard}
            </button>
            <button
              type="button"
              className="btn primary"
              onClick={() => void drafting.save()}
              disabled={drafting.saving || drafting.conflict || !!drafting.problem}
              aria-busy={drafting.saving || undefined}
            >
              {drafting.saving ? (
                <>
                  <Icon name="progress_activity" className="spin" />
                  <span>{M.draftSaving}</span>
                </>
              ) : drafting.failed ? (
                M.draftRetry
              ) : (
                M.draftSave
              )}
            </button>
          </div>
        </div>
      )}

      {drafting.confirm && (
        <ConfirmSaveModal
          groupLabelText={label}
          preview={drafting.confirm.preview}
          breaking={drafting.confirm.breaking}
          objectLabel={objectLabel}
          run={drafting.confirmSave}
          onClose={drafting.cancelConfirm}
        />
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

/** Một dòng phạm vi: ô chọn (Chủ sửa được), hoặc chữ chỉ đọc. Ô mờ khi `inactive`: giá trị cũ vẫn hiện kèm lý do (PV-11-AC2). */
function ScopeRowEditor({
  row,
  value,
  inactive,
  unsaved,
  canEdit,
  disabled,
  onChange,
}: {
  row: DataScopeRow;
  value: string;
  inactive: boolean;
  unsaved: boolean;
  canEdit: boolean;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const uid = useId();
  const selectId = `${uid}-scope`;
  const noteId = `${uid}-note`;
  const editable = canEdit && row.editable && row.options.length > 0;
  const valueText = scopeValueLabel(row, value);
  // Dòng chỉ đọc có ghi chú trùng giá trị (vd "Theo Đơn hàng") thì chỉ hiện một lần.
  const note = inactive ? row.inactive_reason : !editable && row.note === valueText ? null : row.note;
  const wide = row.customer_data && row.options.length > 0 && row.options[row.options.length - 1].value === value;
  return (
    <li className={s.scopeItem} data-scope={row.key} data-inactive={inactive || undefined}>
      <div className={s.scopeHead}>
        <label className={s.scopeLabel} htmlFor={editable ? selectId : undefined}>
          {row.label}
        </label>
        {row.customer_data && (
          <span className={`tag ${s.scopeTag}`} title={M.scopeCustomerData}>
            {M.scopeCustomerData}
          </span>
        )}
        {unsaved && <span className={`tag ${s.tagWarn}`}>{M.unsaved}</span>}
      </div>
      {editable ? (
        <select
          id={selectId}
          className={s.scopeSelect}
          value={value}
          disabled={inactive || disabled}
          aria-describedby={note ? noteId : undefined}
          aria-label={M.scopeSelectLabel(row.label)}
          onChange={(e) => onChange(e.target.value)}
        >
          {row.options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      ) : (
        <p className={`${s.scopeValue} ${inactive ? s.scopeMuted : ""}`}>
          {wide && !inactive && <Icon name="warning" />}
          <span>{valueText}</span>
        </p>
      )}
      {note && (
        <p id={noteId} className={`${s.scopeNote} ${inactive ? s.scopeNoteInactive : ""}`}>
          {inactive && <Icon name="info" />}
          <span>{note}</span>
        </p>
      )}
    </li>
  );
}

function TaskRow({
  item,
  group,
  state,
  scopeValues,
  unsaved,
  labelOf,
  canEdit,
  disabled,
  onToggle,
}: {
  item: RegistryItem;
  group: GroupDetail;
  /** Trạng thái đã cộng bản nháp. */
  state: CapabilityState | undefined;
  /** Phạm vi đã cộng bản nháp (chip "Được gán" lấy từ BE, không còn hằng số FE). */
  scopeValues: Record<string, string>;
  unsaved: boolean;
  labelOf: (key: string) => string;
  canEdit: boolean;
  disabled: boolean;
  onToggle: () => void;
}) {
  const mode = cellMode(item, group.code, state);
  const isCustomers = item.key === CUSTOMERS_KEY;
  const on = mode === "on" || mode === "owner";
  const allCustomers = isCustomers && showsAllCustomers(scopeValues, on);
  const assigned = (mode === "on" || mode === "partial") && isAssignedOnly(scopeValues, item.key);

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
    control = <PermSwitch state={mode === "on" ? "on" : mode === "partial" ? "partial" : "off"} label={`${item.label} — ${group.label}`} disabled={disabled} onToggle={onToggle} title={mode === "partial" ? M.cellPartial : undefined} />;
  } else {
    control = (
      <span className={`${s.taskState} ${on ? s.stateOn : ""}`}>
        <Icon name={on ? "check_circle" : mode === "partial" ? "indeterminate_check_box" : "remove"} />
        <span>{on ? M.cellOn : mode === "partial" ? M.cellPartialShort : M.cellOff}</span>
      </span>
    );
  }

  return (
    <li className={s.taskRow} data-unsaved={unsaved || undefined}>
      <div className={s.taskText}>
        <span className={s.taskLabel}>
          {item.label}
          {item.owner_only && !isOwnerGroupCode(group.code) && (
            <span className="tag" title={M.ownerOnlyHint}>
              {M.ownerOnlyBadge}
            </span>
          )}
          {allCustomers && <span className={`tag ${s.tagWarn}`}>{ALL_CUSTOMERS_LABEL}</span>}
          {assigned && (
            <span className="tag" title={M.assignedOnlyHint}>
              {M.assignedOnly}
            </span>
          )}
          {unsaved && <span className={`tag ${s.tagWarn}`}>{M.unsaved}</span>}
        </span>
        {item.requires.length > 0 && <span className={s.taskSub}>{M.requiresNote(item.requires.map(labelOf).join(", "))}</span>}
        {isCustomers && !on && <span className={s.taskSub}>{M.allCustomersHint}</span>}
        {allCustomers && (
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
