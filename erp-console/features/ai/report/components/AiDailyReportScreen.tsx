"use client";

// "Báo cáo AI cuối ngày" của Chủ (ED-41 / W4d): /ai/report/. Chọn ngày (lùi/tiến, không quá hôm nay) · dải 7 số · bảng "Theo nhân viên"
// (có dòng Cộng) · nhật ký việc AI trong ngày. Chỉ đọc. Tên ở đây là tên NHÂN VIÊN nội bộ, không phải khách; không ghi vào storage/URL/log.
// BE (`report/daily`) không trả vai trò, không trả ghi chú từng việc, không trả đường dẫn chứng từ nên các cột đó không có (xem 03-dev-notes).

import { useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, timeHM, todayInVietnam } from "@/shared/lib/format";
import { useResource } from "@/shared/lib/useResource";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { ResourceView } from "@/shared/ui/ResourceView";
import { SkeletonKpis, SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { fetchDailyAiReport } from "../api";
import { REPORT_MSG as M } from "../messages";
import type { AiDailyReport, AiDailyReportItem, AiDailyReportUserStat } from "../../types";
import { canGoNext, clampDay, grandTotal, shiftDay, targetTypeLabel, totalsOf, type ReportTotals } from "../view";
import s from "../report.module.css";

type StaffRow = AiDailyReportUserStat | { user_id: "total"; display_name: string; total: ReportTotals };

const isTotal = (r: StaffRow): r is Extract<StaffRow, { total: ReportTotals }> => r.user_id === "total";

function statCell(pick: (t: ReportTotals | AiDailyReportUserStat) => number, bold = false) {
  return (r: StaffRow) => {
    const n = pick(isTotal(r) ? r.total : r);
    return bold || isTotal(r) ? <b>{n}</b> : <span className={n === 0 ? "muted" : undefined}>{n}</span>;
  };
}

const STAFF_COLUMNS: Column<StaffRow>[] = [
  { key: "name", header: M.staff, render: (r) => (isTotal(r) ? <b>{M.sum}</b> : r.display_name) },
  { key: "A", header: M.readOnly, num: true, render: statCell((r) => r.A) },
  { key: "B", header: M.autoWrite, num: true, render: statCell((r) => r.B) },
  { key: "C", header: M.askApproved, num: true, render: statCell((r) => r.C_confirmed) },
  { key: "CX", header: M.askExpired, num: true, render: statCell((r) => r.C_expired) },
  { key: "U", header: M.undoneShort, num: true, render: statCell((r) => r.undone) },
  { key: "E", header: M.escalated, num: true, render: statCell((r) => r.escalated) },
];

const ITEM_COLUMNS: Column<AiDailyReportItem>[] = [
  { key: "at", header: M.colTime, num: true, width: "150px", render: (r) => dateTime(r.created_at) },
  {
    key: "owner",
    header: M.colOwner,
    render: (r) => (
      <span className={s.owner}>
        <Icon name="auto_awesome" className={s.ownerTag} />
        {M.ownerOf(r.owner_display)}
      </span>
    ),
  },
  { key: "task", header: M.colTask, render: (r) => r.title },
  { key: "level", header: M.colLevel, width: "150px", render: (r) => <Chip table={ENUMS.aiLevel} value={r.level} /> },
  { key: "status", header: M.colStatus, width: "140px", render: (r) => <Chip table={ENUMS.aiActionStatus} value={r.status} /> },
  {
    key: "target",
    header: M.colTarget,
    render: (r) =>
      r.target ? (
        <span className={s.target}>
          {targetTypeLabel(r.target.type)}
          <span className={s.targetCode}>{r.target.code}</span>
        </span>
      ) : (
        <span className="muted">—</span>
      ),
  },
];

function Strip({ report }: { report: AiDailyReport }) {
  const t = totalsOf(report.by_user);
  const cells: [string, number][] = [
    [M.total, grandTotal(t)],
    [M.readOnly, t.A],
    [M.autoWrite, t.B],
    [M.askApproved, t.C_confirmed],
    [M.askExpired, t.C_expired],
    [M.undone, t.undone],
    [M.escalated, t.escalated],
  ];
  return (
    <div className={s.strip} role="group" aria-label={M.total}>
      {cells.map(([label, n]) => (
        <div key={label} className={s.stat}>
          <span className={s.statLabel}>{label}</span>
          <span className={`${s.statValue} ${n === 0 ? s.statZero : ""}`}>{n}</span>
        </div>
      ))}
    </div>
  );
}

function ReportBody({ report }: { report: AiDailyReport }) {
  const rows: StaffRow[] = report.by_user.length > 0 ? [...report.by_user, { user_id: "total", display_name: M.sum, total: totalsOf(report.by_user) }] : [];
  return (
    <>
      <Strip report={report} />

      <section className={s.card} aria-label={M.byStaff}>
        <div className={s.cardHead}>
          <h2>{M.byStaff}</h2>
        </div>
        <DataTable
          caption={M.captionStaff}
          columns={STAFF_COLUMNS}
          rows={rows}
          rowKey={(r) => r.user_id}
          dense
          canViewCost={false}
          noun={M.byStaffNoun}
          empty={{ icon: "insights", title: M.byStaffEmptyTitle, hint: M.byStaffEmptyHint }}
        />
      </section>

      <section className={s.card} aria-label={M.itemsTitle}>
        <div className={s.cardHead}>
          <h2>{M.itemsTitle}</h2>
          <span className={s.cardHint}>{M.itemsCount(report.items.length, grandTotal(totalsOf(report.by_user)))}</span>
        </div>
        <DataTable
          caption={M.caption}
          columns={ITEM_COLUMNS}
          rows={report.items}
          rowKey={(r) => r.id}
          dense
          canViewCost={false}
          noun={M.itemsNoun}
          empty={{ icon: "history", title: M.itemsEmptyTitle, hint: M.itemsEmptyHint }}
        />
      </section>
    </>
  );
}

export function AiDailyReportScreen() {
  const today = todayInVietnam();
  const [date, setDate] = useState(today);
  const res = useResource<AiDailyReport>(`ai-report:${date}`, () => fetchDailyAiReport(date));

  const go = (next: string) => setDate(clampDay(next, today));

  return (
    <div className={s.page}>
      <div className={s.bar}>
        <button type="button" className={`btn ${s.navBtn}`} aria-label={M.prevDay} onClick={() => go(shiftDay(date, -1))}>
          <Icon name="arrow_back" />
        </button>
        <input
          type="date"
          className={s.dateInput}
          aria-label={M.dateLabel}
          value={date}
          max={today}
          onChange={(e) => e.target.value && go(e.target.value)}
        />
        <button type="button" className={`btn ${s.navBtn}`} aria-label={M.nextDay} disabled={!canGoNext(date, today)} onClick={() => go(shiftDay(date, 1))}>
          <Icon name="arrow_forward" />
        </button>
        {res.asOf && <span className={s.updated}>{M.updated(timeHM(res.asOf))}</span>}
      </div>

      <ResourceView
        res={res}
        skeleton={
          <SkeletonScreen label={M.loading}>
            <SkeletonKpis count={7} />
            <SkeletonTable rows={4} cols={6} />
          </SkeletonScreen>
        }
      >
        {(report) => <ReportBody report={report} />}
      </ResourceView>
    </div>
  );
}
