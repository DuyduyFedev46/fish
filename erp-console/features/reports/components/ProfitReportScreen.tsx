"use client";

// Báo cáo lãi lỗ (W3a, ED-32). CHỈ CHỦ (reports.view_profitreport): vai khác không có menu, vào thẳng URL thì ViewGuard hoặc API 403
// đều ra "Không có quyền". Tháng chọn nằm trong state (không lên URL). Ba phần: dải số liệu của kỳ so với tháng trước,
// "Cấu thành lãi", và bảng "Lãi lỗ theo lô" (lô phát sinh trong tháng, 20 lô/trang, mở chi tiết trong hộp thoại Modal, chỉ đọc).
// Tiền là chuỗi thập phân, cộng trừ bằng ../decimal.ts. Kỳ không có giao dịch hiện trạng thái trống, không số 0 giả (ED-32-AC2).
import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { ENUMS } from "@/shared/lib/enums";
import { kg, todayInVietnam, vnd } from "@/shared/lib/format";
import { usePagedList } from "@/shared/lib/usePagedList";
import { useResource } from "@/shared/lib/useResource";
import { Chip } from "@/shared/ui/Chip";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { Tabs, type TabItem } from "@/shared/ui/Tabs";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { ListPage } from "@/shared/ui/list/ListPage";
import { Modal } from "@/shared/ui/overlay/Modal";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { fetchBatchReport, fetchPeriodReport } from "../api";
import { absDecimal, signOf, subDecimal } from "../decimal";
import { batchDetail, monthLabel, parseMonthKey, periodIsEmpty, previousMonthKey, profitBreakdown, profitTone, reportMonthOptions, signedVnd } from "../reportView";
import type { BatchReportParams, BatchReportRow, PeriodReport } from "../types";
import s from "../reports.module.css";

const SEGMENTS: TabItem[] = [
  { key: "", label: "Tất cả" },
  { key: "closed", label: "Đã chốt" },
  { key: "provisional", label: "Tạm tính" },
];

const toneClass = (value: string) => (profitTone(value) === "pos" ? s.pos : profitTone(value) === "neg" ? s.neg : "");

export function ProfitReportScreen() {
  const { me } = useAuth();
  const [month, setMonth] = useState(() => todayInVietnam().slice(0, 7));
  const [segment, setSegment] = useState("");
  const [openCode, setOpenCode] = useState<string | null>(null);
  const monthOptions = useMemo(() => reportMonthOptions(todayInVietnam()), []);

  const { year, month: monthNumber } = parseMonthKey(month);
  const prevKey = previousMonthKey(month);
  const prev = parseMonthKey(prevKey);
  const canRead = Boolean(me?.can_view_profit);
  // maxAge 0: số liệu tiền luôn tải lại khi mở màn / đổi tháng (không giữ số cũ).
  const period = useResource(canRead ? `reports:period:${month}` : null, () => fetchPeriodReport(year, monthNumber), 0);
  const previous = useResource(canRead ? `reports:period:${prevKey}` : null, () => fetchPeriodReport(prev.year, prev.month), 0);

  const params: BatchReportParams = useMemo(() => ({ month, state: segment }), [month, segment]);
  const list = usePagedList<BatchReportRow, BatchReportParams>((p, page) => fetchBatchReport(p, page), params, canRead);

  if (!me) return null;
  if (!canRead) return <NoPermission />;
  const forbidden = [period.error, list.error].some((e) => e instanceof ApiError && e.status === 403);
  if (forbidden) return <NoPermission />;

  const selected = openCode ? list.rows?.find((r) => r.batch_id === openCode) ?? null : null;

  const columns: Column<BatchReportRow>[] = [
    {
      key: "batch",
      header: "Lô",
      mono: true,
      render: (r) => (
        <button type="button" className={s.codeButton} onClick={() => setOpenCode(r.batch_id)} aria-label={`Xem chi tiết lô ${r.batch_id}`}>
          {r.batch_id}
        </button>
      ),
    },
    { key: "item", header: "Mặt hàng", render: (r) => r.item_name },
    { key: "status", header: "Trạng thái", render: (r) => <Chip table={ENUMS.batchStatus} value={r.status} /> },
    { key: "received", header: "Nhập", num: true, render: (r) => kg(r.qty_received) },
    { key: "sold", header: "Đã bán", num: true, render: (r) => kg(r.qty_sold) },
    { key: "revenue", header: "Doanh thu", num: true, locked: true, render: (r) => vnd(r.revenue) },
    { key: "cost", header: "Tổng chi phí", num: true, locked: true, render: (r) => vnd(r.total_cost) },
    {
      key: "profit",
      header: "Lãi/lỗ",
      num: true,
      locked: true,
      render: (r) => <span className={toneClass(r.profit)}>{signedVnd(r.profit)}</span>,
    },
    { key: "note", header: "Ghi chú", render: (r) => (r.provisional ? <span className={s.provisional}>Tạm tính</span> : <span className="muted">—</span>) },
  ];

  const segmentItems = SEGMENTS.map((t) => (t.key === segment && list.rows ? { ...t, count: list.count } : t));
  const where = monthLabel(month);

  return (
    <>
      <ListPage
        asOf={period.asOf}
        onRetry={() => {
          void period.reload();
          void previous.reload();
          void list.reload();
        }}
        filters={
          <div className={s.monthBar}>
            <div className={s.monthRow}>
              <label className={s.monthSelect}>
                <span className="sr-only">Tháng báo cáo</span>
                <select
                  value={month}
                  onChange={(e) => {
                    setMonth(e.target.value);
                    setOpenCode(null);
                  }}
                  aria-label="Tháng báo cáo"
                  data-testid="report-month"
                >
                  {monthOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <Icon name="expand_more" />
              </label>
            </div>
            <p className={s.note} data-testid="report-criterion">
              Báo cáo theo tháng. Danh sách lô gồm lô phát sinh trong tháng: nhập, có hoá đơn bán hoặc chốt trong tháng.
            </p>
          </div>
        }
        footer={
          list.hasMore ? (
            <>
              {list.moreError ? <span role="alert">{loadErrorText(list.moreError)}</span> : null}
              <button type="button" className="btn" onClick={() => void list.loadMore()} disabled={list.moreLoading}>
                {list.moreLoading ? "Đang tải…" : list.moreError ? "Thử lại" : "Tải thêm"}
              </button>
            </>
          ) : null
        }
      >
        <PeriodBlock
          where={where}
          period={period.data}
          loading={period.loading && !period.data}
          error={period.error}
          onRetry={() => void period.reload()}
          previous={previous.data}
          previousLabel={`T${prev.month}`}
        />

        <section className={s.section} aria-label="Lãi lỗ theo lô">
          <div className={s.sectionHead}>
            <h3>Lãi lỗ theo lô</h3>
          </div>
          <Tabs tabs={segmentItems} value={segment} onChange={setSegment} label="Lọc lô theo trạng thái chốt" panelId="report-batches" />
          <div id="report-batches">
            <DataTable
              columns={columns}
              rows={list.rows ?? null}
              rowKey={(r) => r.batch_id}
              loading={list.loading && !list.rows}
              error={list.error ? loadErrorText(list.error) : null}
              onRetry={() => void list.reload()}
              noun="lô"
              empty={
                segment
                  ? { icon: "filter_alt_off", title: "Không có lô nào ở mục này", hint: "Chọn “Tất cả” để xem mọi lô phát sinh trong tháng.", action: <button type="button" className="btn" onClick={() => setSegment("")}>Xem tất cả</button> }
                  : { icon: "inventory_2", title: `Không có lô nào phát sinh trong ${where}`, hint: "Lô được tính khi nhập, bán hoặc chốt trong tháng." }
              }
              canViewCost={me.can_view_cost}
              caption={`Lãi lỗ theo lô, ${where}`}
              dense
            />
          </div>
        </section>
      </ListPage>
      {selected && <BatchDetailModal row={selected} onClose={() => setOpenCode(null)} />}
    </>
  );
}

function PeriodBlock({
  where,
  period,
  loading,
  error,
  onRetry,
  previous,
  previousLabel,
}: {
  where: string;
  period: PeriodReport | undefined;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  previous: PeriodReport | undefined;
  previousLabel: string;
}) {
  // Tải lại lỗi thì KHÔNG giữ số cũ (useResource giữ data cũ + gắn error): báo cáo tiền không được hiện số có thể đã lỗi thời.
  if (error) {
    return (
      <div className="state state-err" role="alert">
        <span className="state-ic">
          <Icon name="sync_problem" />
        </span>
        <p className="state-title">{loadErrorText(error)}</p>
        <button type="button" className="btn" onClick={onRetry}>
          <Icon name="refresh" />
          Thử lại
        </button>
      </div>
    );
  }
  if (loading || !period) {
    return (
      <div className={s.stats} aria-busy="true">
        <span className="sr-only" role="status">
          Đang tải số liệu…
        </span>
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className={s.stat} aria-hidden="true">
            <span className="sk sk-s" />
            <span className="sk sk-m" />
          </div>
        ))}
      </div>
    );
  }
  if (periodIsEmpty(period)) {
    return (
      <div className="state" role="status" data-testid="period-empty">
        <span className="state-ic">
          <Icon name="monitoring" />
        </span>
        <b className="state-title">{`${where} chưa có giao dịch`}</b>
        <p>Chưa có hoá đơn hay hoàn tiền nào trong tháng này. Chọn tháng khác để xem số liệu.</p>
      </div>
    );
  }

  const diff = previous && !periodIsEmpty(previous) ? subDecimal(period.profit, previous.profit) : null;
  const diffTone = diff === null ? "none" : profitTone(diff);
  return (
    <>
      <dl className={s.stats} aria-label={`Số liệu ${where}`}>
        <Stat label="Doanh thu ghi nhận" locked value={vnd(period.revenue)} />
        <Stat label="Giá vốn ghi nhận" locked value={vnd(period.cogs)} />
        <Stat
          label={`Lãi/lỗ ${where.toLowerCase()}`}
          locked
          value={signedVnd(period.profit)}
          valueClass={toneClass(period.profit)}
          testId="stat-profit"
          foot={
            diff === null ? (
              previous ? `${previousLabel} chưa có giao dịch để so sánh` : `Chưa so sánh được ${previousLabel}`
            ) : (
              <>
                {/* Chỉ dùng icon đã có trong tập con font (public/fonts/ms): trending_* không có nên hiện thành chữ "T". */}
                {diffTone === "neg" ? <Icon name="south_west" /> : diffTone === "pos" ? <Icon name="north_east" /> : null}
                <span className={diffTone === "neg" ? s.neg : diffTone === "pos" ? s.pos : undefined}>
                  {diffTone === "zero" ? `bằng ${previousLabel}` : `${diffTone === "neg" ? "giảm" : "tăng"} ${vnd(absDecimal(diff ?? "0"))} so với ${previousLabel}`}
                </span>
              </>
            )
          }
        />
        <Stat label="Số hoá đơn" value={String(period.invoice_count)} />
        <Stat label="Hoàn tiền trong kỳ" locked value={vnd(period.refunds)} />
        <Stat label="Phiếu hoàn tiền đã chuyển" value={String(period.refund_count)} />
      </dl>

      <section className={s.card} aria-label="Cấu thành lãi">
        <h3 className={s.cardHead}>Cấu thành lãi</h3>
        <ul className={s.breakdown} data-testid="breakdown">
          {profitBreakdown(period).map((row) => (
            <li key={row.key} className={`${s.bRow} ${row.kind === "total" ? s.bTotal : ""}`} data-row={row.key}>
              <span className={s.bLabel}>
                {row.label} <Icon name="lock" />
              </span>
              <span className={`${s.bAmount} ${row.kind === "total" ? toneClass(row.amount) : ""}`}>{signedVnd(row.amount)}</span>
              {row.kind !== "total" && (
                <span className={s.bTrack} aria-hidden="true">
                  <span className={`${s.bFill} ${signOf(row.amount) === -1 ? s.bFillMinus : s.bFillPlus}`} style={{ width: `${Math.round(row.share * 100)}%` }} />
                </span>
              )}
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

function Stat({
  label,
  value,
  foot,
  locked,
  valueClass,
  testId,
}: {
  label: string;
  value: string;
  /** Chỉ dành cho một số liệu phụ (vd so sánh tháng trước), không dùng cho lời giải thích. */
  foot?: React.ReactNode;
  locked?: boolean;
  valueClass?: string;
  testId?: string;
}) {
  return (
    <div className={s.stat}>
      <dt className={s.statLabel}>
        {label}
        {locked && (
          <>
            <Icon name="lock" />
            <span className="sr-only"> (giới hạn quyền xem)</span>
          </>
        )}
      </dt>
      <dd className={`${s.statValue} ${valueClass ?? ""}`} data-testid={testId}>
        <Figure text={value} />
      </dd>
      {foot ? <dd className={s.statFoot}>{foot}</dd> : null}
    </div>
  );
}

function BatchDetailModal({ row, onClose }: { row: BatchReportRow; onClose: () => void }) {
  const detail = batchDetail(row, kg);
  const line = (l: { key: string; label: string; value: string; kind?: string; locked?: boolean }) => (
    <div key={l.key} className={`${s.line} ${l.kind === "total" ? s.lineTotal : ""}`} data-line={l.key}>
      <dt>
        {l.label}
        {l.locked && <Icon name="lock" />}
      </dt>
      <dd className={l.key === "profit" ? toneClass(row.profit) : undefined}>{l.value}</dd>
    </div>
  );
  return (
    <Modal
      title={`Chi tiết lô ${row.batch_id}`}
      onClose={onClose}
      footer={
        <button type="button" className="btn" onClick={onClose}>
          Đóng
        </button>
      }
    >
      <div className={s.detail} data-testid="batch-detail">
        <div className={s.detailTitle}>
          <strong>{row.item_name}</strong>
          <span>
            <Chip table={ENUMS.batchStatus} value={row.status} />
            {row.provisional && <span className={s.provisional}> Tạm tính, lô chưa chốt</span>}
          </span>
        </div>
        <dl className={s.detailGroup}>{detail.composition.map(line)}</dl>
        <div>
          <p className={s.detailGroupHead}>Số tiền mất đã nằm trong giá mua (chỉ để tham khảo)</p>
          <dl className={s.detailGroup}>{detail.reference.map(line)}</dl>
        </div>
      </div>
    </Modal>
  );
}
