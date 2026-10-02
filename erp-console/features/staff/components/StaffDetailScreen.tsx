"use client";

// Hồ sơ một nhân viên (ED-37 / ED-38 / W3g): /staff/detail/?id=<số>. Khung DetailPage: header (tên · chip Đang làm/Đã nghỉ · "Sửa hồ sơ" · "Đổi nhóm" · "…"),
// cột trái: "Thông tin nhân viên" · "Việc đang giao" (chỉ nhân viên giao hàng, chỉ người có quyền xem phiếu giao) · "Quyền theo nhóm" (bấm → trang nhóm)
// · "Hoạt động gần đây" (chỉ người có quyền xem nhật ký). Cột phải: Dòng thời gian của nhân viên.
// Nút CHỈ hiện theo `available_actions` BE trả (FE không tự suy luật); thao tác không làm được nằm mờ trong "…" kèm lý do ngắn. Đặt lại mật khẩu,
// Cho nghỉ / Cho làm lại và Đổi nhóm có hộp hỏi lại; lỗi BE hiện NGUYÊN VĂN trong hộp. Mỗi khối phụ có quyền riêng: lỗi hay 403 của khối nào chỉ ảnh hưởng khối đó.
// Tên, SĐT chỉ ở bộ nhớ trang: URL chỉ mang id số, không storage, không log. Khối việc đang giao KHÔNG có tên/SĐT/địa chỉ khách.

import { useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { groupHref } from "@/features/permissions/permissionsModel";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime } from "@/shared/lib/format";
import { GROUP_HINT, groupLabel } from "@/shared/lib/groups";
import { loadErrorText } from "@/shared/lib/http";
import { PERM, canView, homePath } from "@/shared/lib/nav";
import { ROLE } from "@/shared/lib/roles";
import { Chip } from "@/shared/ui/Chip";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { Timeline } from "@/shared/ui/detail/Timeline";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { useToast } from "@/shared/ui/overlay/Toast";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { STAFF_MSG as M } from "../messages";
import { activityLabel, blockedReason, can, namesOf, whoOf } from "../staffModel";
import type { StaffActivityRow, StaffDelivering, StaffMember } from "../types";
import { useStaffActivity, useStaffDelivering, useStaffDetail, useStaffId, useStaffTimeline } from "../useStaffData";
import type { Loaded } from "../useLoaded";
import { ActiveModal } from "./ActiveModal";
import { EditProfileModal } from "./EditProfileModal";
import { GroupsModal } from "./GroupsModal";
import { ResetPasswordModal } from "./ResetPasswordModal";
import s from "../staff.module.css";

export function DetailSkeleton() {
  return (
    <div className={s.detailSkel} role="status" aria-busy="true">
      <span className="sr-only">Đang tải hồ sơ nhân viên…</span>
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

export function StaffDetailScreen() {
  const { me } = useAuth();
  const id = useStaffId();
  const detail = useStaffDetail(id);
  const home = me ? homePath(me) : undefined;

  if (id === undefined) return <DetailSkeleton />;
  if (id === null) return <NotFoundScreen homeHref={home} />;
  if (detail.status === "forbidden") return <NoPermission homeHref={home} />;
  if (detail.status === "notfound") return <NotFoundScreen homeHref={home} />;
  if (detail.status === "error") return <ErrorScreen homeHref={home} onRetry={() => void detail.reload()} />;
  if (detail.status === "loading" || !detail.data) return <DetailSkeleton />;
  return <StaffDetailBody key={id} member={detail.data} detail={detail} />;
}

type Modal = "edit" | "groups" | "reset" | "active" | null;

function StaffDetailBody({ member: m, detail }: { member: StaffMember; detail: Loaded<StaffMember> }) {
  const { me } = useAuth();
  const toast = useToast();
  const [modal, setModal] = useState<Modal>(null);
  const [version, setVersion] = useState(0);
  const who = whoOf(m);
  const self = !!me && me.id === m.id;

  const canSeeLog = !!me?.permissions.includes(PERM.viewAuditLog);
  const isDeliveryStaff = m.groups.includes(ROLE.deliveryStaff);
  const canSeeDelivering = isDeliveryStaff && !!me?.permissions.includes(PERM.viewDeliveryNote);
  const canOpenNote = canView(me, "deliveries");
  const canOpenGroup = canView(me, "permissions");

  const timeline = useStaffTimeline(m.id, version);
  const activity = useStaffActivity(m.id, canSeeLog, version);
  const delivering = useStaffDelivering(m.id, canSeeDelivering, version);

  const afterChange = (message: string) => {
    toast.success(message);
    setVersion((n) => n + 1);
    void detail.reload();
  };

  const more: MoreMenuItem[] = [
    can(m, "reset_password")
      ? { key: "reset", label: M.resetPassword, onSelect: () => setModal("reset") }
      : { key: "reset", label: M.resetPassword, blockedReason: blockedReason("reset_password", m, me?.id ?? null) },
    m.is_active
      ? can(m, "deactivate")
        ? { key: "deactivate", label: M.deactivate, danger: true, onSelect: () => setModal("active") }
        : { key: "deactivate", label: M.deactivate, blockedReason: blockedReason("deactivate", m, me?.id ?? null) }
      : can(m, "reactivate")
        ? { key: "reactivate", label: M.reactivate, onSelect: () => setModal("active") }
        : { key: "reactivate", label: M.reactivate, blockedReason: blockedReason("reactivate", m, me?.id ?? null) },
    {
      key: "log",
      label: M.viewLog,
      onSelect: () => {
        const el = document.getElementById("staff-timeline");
        el?.scrollIntoView({ block: "start" });
        el?.focus();
      },
    },
  ];

  const noteCols: Column<StaffDelivering>[] = useMemo(
    () => [
      { key: "code", header: M.colNote, mono: true, render: (n) => n.code },
      { key: "status", header: M.colStatusShort, render: (n) => n.status_label },
      { key: "at", header: M.colStarted, num: true, render: (n) => (n.started_at ? dateTime(n.started_at) : <span className="muted">—</span>) },
    ],
    [],
  );
  const activityCols: Column<StaffActivityRow>[] = useMemo(
    () => [
      { key: "what", header: M.colWhat, render: (r) => activityLabel(r) },
      { key: "obj", header: M.colObject, hideBelow: 720, render: (r) => r.object_repr || <span className="muted">—</span> },
      { key: "at", header: M.colAt, num: true, render: (r) => dateTime(r.created_at) },
    ],
    [],
  );

  const hasAnyAction = m.available_actions.length > 0;

  return (
    <DetailPage
      id="staff-detail"
      header={
        <DetailHeader
          back={{ href: "/staff/", label: M.backToList }}
          title={m.display_name || m.username}
          status={<Chip table={ENUMS.staffStatus} value={m.is_active ? "ACTIVE" : "INACTIVE"} />}
          primary={
            can(m, "edit") || can(m, "set_groups") ? (
              <>
                {can(m, "edit") && (
                  <button type="button" className="btn" onClick={() => setModal("edit")}>
                    {M.edit}
                  </button>
                )}
                {can(m, "set_groups") && (
                  <button type="button" className="btn primary" onClick={() => setModal("groups")}>
                    {M.editGroups}
                  </button>
                )}
              </>
            ) : null
          }
          more={more}
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
          {self && (
            <p className={s.selfNote} role="note">
              {M.selfNote}
            </p>
          )}
          {!hasAnyAction && !self && (
            <p className={s.selfNote} role="note">
              {M.noActions}
            </p>
          )}
        </>
      }
      timeline={
        <div id="staff-timeline" tabIndex={-1}>
          {timeline.status === "error" ? (
            <p className={s.railNote} role="alert">
              <span>{M.timelineFailed}</span>
              <button type="button" className="btn" onClick={timeline.retry}>
                {M.retry}
              </button>
            </p>
          ) : (
            timeline.status !== "forbidden" && <Timeline entries={timeline.entries} truncated={timeline.truncated} title={M.timelineTitle} />
          )}
        </div>
      }
    >
      <InfoGrid title={M.sectionInfo}>
        <InfoField label={M.fieldDisplayName} value={m.display_name} />
        <InfoField kind="locked" label={M.fieldUsername} value={m.username} mono reason={M.fixedReason} />
        <InfoField label={M.fieldPhone} value={m.phone} mono />
        <InfoField label={M.fieldStatus} value={<Chip table={ENUMS.staffStatus} value={m.is_active ? "ACTIVE" : "INACTIVE"} />} />
        <InfoField kind="locked" label={M.fieldLastLogin} value={m.last_login ? dateTime(m.last_login) : M.neverLoggedIn} num reason={M.fixedReason} />
      </InfoGrid>

      {canSeeDelivering && delivering.status !== "forbidden" && (
        <section className={s.section} aria-label={M.sectionDelivering}>
          <h3 className={s.sectionH}>
            {M.sectionDelivering}
            {delivering.data && <span className={s.sectionCount}>{M.deliveringCount(delivering.data.length)}</span>}
          </h3>
          <DataTable
            caption={M.sectionDelivering}
            columns={noteCols}
            rows={delivering.data}
            rowKey={(n) => n.id}
            rowHref={canOpenNote ? (n) => `/deliveries/detail/?id=${n.id}` : undefined}
            loading={delivering.status === "loading"}
            error={delivering.status === "error" ? M.deliveringFailed : null}
            onRetry={delivering.retry}
            noun="phiếu"
            empty={{ icon: "local_shipping", title: M.deliveringEmpty }}
            canViewCost={false}
            dense
          />
        </section>
      )}

      <section className={s.section} aria-label={M.sectionGroups}>
        <h3 className={s.sectionH}>{M.sectionGroups}</h3>
        {m.groups.length === 0 ? (
          <p className={s.sectionNote}>{M.groupsEmpty}</p>
        ) : (
          <ul className={s.groupRows}>
            {m.groups.map((g) => (
              <li key={g} className={s.groupRow}>
                <span className={s.groupText}>
                  <b>{groupLabel(g)}</b>
                  <small>{GROUP_HINT[g]}</small>
                </span>
                {canOpenGroup && (
                  <Link className={s.groupLink} href={groupHref(g)} aria-label={M.groupsOpen(groupLabel(g))}>
                    {M.groupsOpen(groupLabel(g))}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {canSeeLog && activity.status !== "forbidden" && (
        <section className={s.section} aria-label={M.sectionActivity}>
          <h3 className={s.sectionH}>{M.sectionActivity}</h3>
          <DataTable
            caption={M.sectionActivity}
            columns={activityCols}
            rows={activity.data?.rows ?? null}
            rowKey={(r) => r.id}
            loading={activity.status === "loading"}
            error={activity.status === "error" ? M.activityFailed : null}
            onRetry={activity.retry}
            noun="hoạt động"
            empty={{ icon: "history", title: M.activityEmpty }}
            canViewCost={false}
            dense
          />
          {activity.data && activity.data.total > activity.data.rows.length && (
            <p className={s.sectionNote}>{M.activityMore(activity.data.rows.length, activity.data.total)}</p>
          )}
        </section>
      )}

      {modal === "edit" && (
        <EditProfileModal
          member={m}
          onClose={() => setModal(null)}
          onSaved={() => {
            setModal(null);
            afterChange(M.profileSaved(m.username));
          }}
        />
      )}
      {modal === "groups" && (
        <GroupsModal
          member={m}
          onClose={() => setModal(null)}
          onSaved={(r) => {
            setModal(null);
            afterChange(M.groupsChanged(who, namesOf(r.added), namesOf(r.removed)));
          }}
        />
      )}
      {modal === "reset" && <ResetPasswordModal member={m} onClose={() => setModal(null)} onDone={() => afterChange(M.passwordReset(who))} />}
      {modal === "active" && (
        <ActiveModal
          member={m}
          deactivating={m.is_active}
          onClose={() => setModal(null)}
          onDone={() => {
            setModal(null);
            afterChange(m.is_active ? M.deactivated(who) : M.reactivated(who));
          }}
        />
      )}
    </DetailPage>
  );
}
