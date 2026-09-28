// Màn Nhật ký hoạt động (S03-FE, chốt Duy 27/09: dù admin hay nhân viên đều xem ở ERP).
// Contract: GET /api/audit-logs/?page=&actor_kind=&action= (02b mục 3 S03) — quyền accounts.view_auditlog
// (chu + quan_ly); nv_kho/nv_giao → 403 (S03-AC5) → ViewGuard đã chặn trước khi gọi API.
// S03-AC2: dòng AI hiện actor "ai:<tên user>" rõ ràng kèm lệnh + thời điểm.
// S03-AC4: KHÔNG chép tên/SĐT/địa chỉ khách vào hiển thị — chỉ hiện nguyên văn các trường API trả
// (BE đảm bảo changes/note chỉ chứa mã đơn/mã lệnh/mã đề xuất); màn này không tự nối thêm gì.
// Dữ liệu: dùng getAuditLogs/AuditLogRow của features/ai (endpoint thuộc hồ sơ AI Lô 1); mock Lô 1
// đặt ở features/ai/mock.ts theo phân công — bỏ mock khi BE Lô 1 xong.

"use client";

import { useState } from "react";
import { dateTime } from "@/shared/lib/format";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Icon } from "@/shared/ui/Icon";
import { Empty, ErrorBox, Loading } from "@/shared/ui/StateBox";
import { getAuditLogs } from "@/features/ai/api";
import type { AuditActorKind, AuditLogRow, AuditLogParams } from "@/features/ai/types";
import { AUDIT_MSG } from "@/features/ai/messages";
import s from "./audit.module.css";

const KINDS: { key: "" | AuditActorKind; label: string }[] = [
  { key: "", label: AUDIT_MSG.filterAll },
  { key: "user", label: AUDIT_MSG.filterUser },
  { key: "ai", label: AUDIT_MSG.filterAi },
  { key: "system", label: AUDIT_MSG.filterSystem },
];

function ActorCell({ row }: { row: AuditLogRow }) {
  if (row.actor_kind === "ai") {
    return (
      <span className={s.actor}>
        <span className={`tag ${s.aiTag}`}>{AUDIT_MSG.actorAi}</span>
        <b className={s.aiActor}>{row.actor_display}</b>
      </span>
    );
  }
  if (row.actor_kind === "system") {
    return (
      <span className={s.actor}>
        <span className={s.actorName}>{row.actor_display}</span>
      </span>
    );
  }
  return <span className={`${s.actor} ${s.actorName}`}>{row.actor_display}</span>;
}

function Row({ row }: { row: AuditLogRow }) {
  const changesKeys = row.changes ? Object.keys(row.changes).length : 0;
  return (
    <li className={s.row}>
      <div className={s.main}>
        <div className={s.line1}>
          <ActorCell row={row} />
          <span className={s.action}>{row.action}</span>
        </div>
        <div className={s.line2}>
          {row.object_repr ? <span className={`code ${s.obj}`}>{row.object_repr}</span> : null}
          {row.note ? <span className={s.note}>{row.note}</span> : null}
          {row.proposal_ref ? (
            <span className={s.proposal}>
              {AUDIT_MSG.proposal} <span className="code">{row.proposal_ref}</span>
            </span>
          ) : null}
        </div>
        {changesKeys > 0 ? (
          <details className={s.changes}>
            <summary>
              {AUDIT_MSG.changes}: {changesKeys} trường
            </summary>
            <pre className={`code ${s.changesJson}`}>{JSON.stringify(row.changes, null, 2)}</pre>
          </details>
        ) : null}
      </div>
      <time className={`num ${s.time}`} dateTime={row.created_at}>
        {dateTime(row.created_at)}
      </time>
    </li>
  );
}

export function AuditLogScreen() {
  const [params, setParams] = useState<AuditLogParams>({ actor_kind: "" });
  const { rows, loading, error, hasMore, moreLoading, moreError, loadMore, reload } = usePagedList<
    AuditLogRow,
    AuditLogParams
  >((p, page) => getAuditLogs(p, page), params, true);

  return (
    <div className={s.screen}>
      <div className={s.bar}>
        <div className="seg" role="group" aria-label={AUDIT_MSG.filterAll}>
          {KINDS.map((k) => (
            <button
              key={k.key || "all"}
              type="button"
              className={params.actor_kind === k.key ? "on" : ""}
              aria-pressed={params.actor_kind === k.key}
              onClick={() => setParams({ actor_kind: k.key })}
            >
              {k.label}
            </button>
          ))}
        </div>
        <button type="button" className={`iconbtn ${s.refresh}`} aria-label={AUDIT_MSG.refresh} onClick={() => reload()}>
          <Icon name="refresh" />
        </button>
      </div>

      {loading && rows === undefined ? <Loading label={AUDIT_MSG.title} /> : null}
      {error && rows === undefined ? (
        <ErrorBox message={error instanceof Error ? error.message : AUDIT_MSG.empty} />
      ) : null}
      {rows && rows.length === 0 && !loading ? (
        <Empty icon="history" title={AUDIT_MSG.empty}>
          {AUDIT_MSG.emptyHint}
        </Empty>
      ) : null}

      {rows && rows.length > 0 ? (
        <>
          <ul className={s.rows}>
            {rows.map((r) => (
              <Row key={r.id} row={r} />
            ))}
          </ul>
          <div className={s.more}>
            {moreError ? (
              <button type="button" className="btn" onClick={() => loadMore()}>
                {moreError instanceof Error ? moreError.message : AUDIT_MSG.loadMore}
              </button>
            ) : hasMore ? (
              <button type="button" className="btn" disabled={moreLoading} onClick={() => loadMore()}>
                {moreLoading ? "Đang tải…" : AUDIT_MSG.loadMore}
              </button>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  );
}
