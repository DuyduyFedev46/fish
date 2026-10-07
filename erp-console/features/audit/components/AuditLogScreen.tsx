"use client";

// Màn Nhật ký hoạt động (ED-41 / W3f): /audit-logs/. Khung ListPage: nhóm nút Tất cả/Người/AI/Hệ thống · ô tìm mã chứng từ ·
// chọn thao tác · (Chủ) chọn người · khoảng ngày · bảng 8 cột · "Tải thêm". Chỉ xem: không sửa, không xoá (BR-PQ-06).
// Mọi bộ lọc chạy phía BE: loại người / thao tác / người làm (`?actor_kind=&action=&actor=`) và, từ Lô 17a, khoảng ngày + mã chứng từ
// (`?date_from=&date_to=&q=`), nên "Đang hiện n / tổng" đúng cả khi chưa tải hết. Ô tìm chỉ nhận mã (không SĐT, tên): kiểm ở máy theo
// luật của BE, gõ xong chờ 350ms mới gửi. "Người duyệt" suy từ dòng duyệt cùng mã đề xuất (BE chưa có trường).
// Dữ liệu cá nhân: cột "Thay đổi" chỉ in khoá trong danh sách trắng (auditModel.changeSummary), không bao giờ in JSON thô;
// tên đăng nhập chỉ ở bộ nhớ trang (không URL, không storage, không log). Giá vốn: BE đã bỏ khoá giá vốn khỏi `changes` khi thiếu quyền.

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { useStaffList } from "@/features/staff/useStaffData";
import { dateTime } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { canView } from "@/shared/lib/nav";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Icon } from "@/shared/ui/Icon";
import { aiVisible } from "@/shared/lib/features";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar, type FilterSelect } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { getAuditLogs } from "../api";
import { AI_ONLY_ACTIONS, AUDIT_ACTION_LABELS, AUDIT_FILTER_ACTIONS, KIND_OPTIONS, actionLabel, actorInitial, actorName, approverOf, buildApproverMap, changeSummary } from "../auditModel";
import { auditRangeError, checkAuditQuery } from "../auditQuery";
import { AUDIT_MSG as M } from "../messages";
import type { AuditLogParams, AuditLogRow } from "../types";
import s from "../audit.module.css";

function ActorCell({ row }: { row: AuditLogRow }) {
  if (row.actor_kind === "system") {
    return (
      <span className={s.actor}>
        <span className={`${s.avatar} ${s.avatarSystem}`} aria-hidden="true">
          <Icon name="sync_alt" />
        </span>
        <span>{M.system}</span>
      </span>
    );
  }
  const isAi = row.actor_kind === "ai";
  return (
    <span className={s.actor}>
      <span className={`${s.avatar} ${isAi ? s.avatarAi : ""}`} aria-hidden="true">
        {actorInitial(row)}
      </span>
      <span className={s.actorText}>
        <span className={s.actorName}>{actorName(row)}</span>
        {isAi && <span className={`tag ${s.aiTag}`}>{M.aiTag}</span>}
      </span>
    </span>
  );
}

function ChangesCell({ row }: { row: AuditLogRow }) {
  const parts = changeSummary(row.changes, row.model_name);
  if (!parts.length) return <span className="muted">{M.noValue}</span>;
  return (
    <ul className={s.changes}>
      {parts.map((p) => (
        <li key={p}>{p}</li>
      ))}
    </ul>
  );
}

export function AuditLogScreen() {
  const { me } = useAuth();
  const aiOn = aiVisible(me);
  const canPickActor = canView(me, "staff");
  const staff = useStaffList(!!me && canPickActor);

  const [kind, setKind] = useState<AuditLogParams["actor_kind"]>("");
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [q, setQ] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  // Từ khoá gõ dở không gửi ngay: chờ 350ms. Từ khoá sai luật (SĐT, chữ có dấu…) không bao giờ rời máy.
  const [qSent, setQSent] = useState("");
  const qCheck = checkAuditQuery(q);
  const qWanted = qCheck.ok ? qCheck.q : "";
  useEffect(() => {
    const t = setTimeout(() => setQSent(qWanted), 350);
    return () => clearTimeout(t);
  }, [qWanted]);
  const rangeError = auditRangeError(from, to);

  const params = useMemo<AuditLogParams>(
    () => ({
      actor_kind: kind,
      action,
      actor: actor ? Number(actor) : undefined,
      date_from: rangeError ? undefined : from || undefined,
      date_to: rangeError ? undefined : to || undefined,
      q: qSent || undefined,
    }),
    [kind, action, actor, from, to, rangeError, qSent],
  );
  const list = usePagedList<AuditLogRow, AuditLogParams>((p, page) => getAuditLogs(p, page), params, !!me);

  const approvers = useMemo(() => buildApproverMap(list.rows ?? []), [list.rows]);
  // W39: AI tắt thì không hiện dòng do AI làm hay đề xuất của AI, kể cả khi BE chưa lọc (BE bật nhưng giao diện tắt).
  const shown = useMemo(
    () => (list.rows ? list.rows.filter((r) => aiOn || (r.actor_kind !== "ai" && !r.proposal_ref)) : null),
    [list.rows, aiOn],
  );

  if (list.error instanceof ApiError && list.error.status === 403 && !list.rows) return <NoPermission />;

  // 400 của BE về bộ lọc (vd INVALID_FILTER): câu của BE hiện dưới ô tìm, không lặp lại từ khoá; bảng không hiện "lỗi tải".
  const filterRejected = list.error instanceof ApiError && list.error.status === 400;
  const filterMessage = (qCheck.ok ? null : qCheck.message) ?? rangeError ?? (filterRejected ? (list.error instanceof Error && list.error.message ? list.error.message : M.filterError) : null);
  const filterActive = !!(kind || action || actor || qSent || from || to);

  const selects: FilterSelect[] = [
    {
      key: "action",
      label: M.actionLabel,
      value: action,
      onChange: setAction,
      options: [{ value: "", label: M.allActions }, ...AUDIT_FILTER_ACTIONS.filter((a) => aiOn || !AI_ONLY_ACTIONS.includes(a)).map((a) => ({ value: a, label: AUDIT_ACTION_LABELS[a] }))],
    },
  ];
  if (canPickActor && staff.data) {
    selects.push({
      key: "actor",
      label: M.actorSelectLabel,
      value: actor,
      onChange: setActor,
      options: [{ value: "", label: M.allActors }, ...staff.data.map((u) => ({ value: String(u.id), label: u.display_name || u.username }))],
    });
  }

  const columns: Column<AuditLogRow>[] = [
    {
      key: "time",
      header: M.colTime,
      num: true,
      width: "152px",
      render: (r) => <time dateTime={r.created_at}>{dateTime(r.created_at)}</time>,
    },
    { key: "actor", header: M.colActor, width: "176px", render: (r) => <ActorCell row={r} /> },
    {
      key: "approver",
      header: M.colApprover,
      hideBelow: 980,
      width: "120px",
      render: (r) => approverOf(r, approvers) ?? <span className="muted">{M.noValue}</span>,
    },
    { key: "action", header: M.colAction, width: "200px", render: (r) => actionLabel(r.action) },
    { key: "object", header: M.colObject, mono: true, hideBelow: 720, width: "148px", render: (r) => r.object_repr || <span className="muted">{M.noValue}</span> },
    { key: "note", header: M.colNote, hideBelow: 1100, render: (r) => r.note || <span className="muted">{M.noValue}</span> },
    { key: "changes", header: M.colChanges, hideBelow: 800, render: (r) => <ChangesCell row={r} /> },
    ...(aiOn ? [{ key: "proposal", header: M.colProposal, mono: true, hideBelow: 1100 as const, width: "88px", render: (r: AuditLogRow) => r.proposal_ref || <span className="muted">{M.noValue}</span> }] : []),
  ];

  const summary = shown && list.rows ? M.shown(shown.length, list.count) : undefined;

  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;
  const clearAll = () => {
    setQ("");
    setFrom("");
    setTo("");
    setKind("");
    setAction("");
    setActor("");
  };

  return (
    <ListPage
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
      filters={
        <>
          <div className={s.kinds}>
            <div className="seg" role="group" aria-label={M.kindLabel}>
              {KIND_OPTIONS.filter((k) => aiOn || k.key !== "ai").map((k) => (
                <button key={k.key || "all"} type="button" aria-pressed={kind === k.key} onClick={() => setKind(k.key)}>
                  {k.label}
                </button>
              ))}
            </div>
          </div>
          <FilterBar
            query={q}
            onQuery={setQ}
            placeholder={M.searchPlaceholder}
            searchLabel={M.searchLabel}
            selects={selects}
            dateRange={{ from, to, onFrom: setFrom, onTo: setTo }}
            summary={summary}
          />
          {filterMessage && (
            <p className="field-err" role="alert" data-testid="audit-filter-error">
              {filterMessage}
            </p>
          )}
        </>
      }
      footer={
        <div className={s.foot}>
          {list.moreError ? (
            <button type="button" className="btn" onClick={() => void list.loadMore()}>
              {M.loadMoreFailed}
            </button>
          ) : list.hasMore ? (
            <button type="button" className="btn" disabled={list.moreLoading} onClick={() => void list.loadMore()}>
              {list.moreLoading ? M.loadingMore : M.loadMore}
            </button>
          ) : null}
          <p className={s.note}>{M.readOnly}</p>
        </div>
      }
      onRetry={() => void list.reload()}
    >
      <DataTable
        caption={M.caption}
        columns={columns}
        rows={filterRejected && !shown ? [] : shown}
        rowKey={(r) => r.id}
        dense
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null && !filterRejected ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={qSent}
        onClearQuery={() => setQ("")}
        noun={M.noun}
        empty={
          filterActive
            ? {
                icon: "filter_alt_off",
                title: M.emptyFiltered,
                hint: M.emptyFilteredHint,
                action: (
                  <button type="button" className="btn" onClick={clearAll}>
                    Bỏ lọc
                  </button>
                ),
              }
            : { icon: "history", title: M.emptyTitle, hint: M.emptyHint }
        }
        canViewCost={false}
      />
    </ListPage>
  );
}
