"use client";

// ED-15 — Hàng chờ Gọi xác nhận (CSKH, Chủ, Quản lý). Khung ListPage: tab theo việc (đồng bộ ?tab=), thanh lọc, bảng, "Tải thêm".
// Bấm một dòng → /confirmation/detail/?id=<số> (URL chỉ mang id). Số điện thoại hiện đúng chuỗi BE trả: đủ số khi dòng trong phạm vi,
// `phone_masked` khi ngoài phạm vi (dòng đó không mở được). Tìm kiếm chạy trên các dòng đã tải, không gửi từ khoá đi đâu;
// tra theo số điện thoại hoặc mã đơn trên toàn hệ thống dùng hộp "Tìm khách gọi lại" (POST).
import Link from "next/link";
import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, kg, vnd } from "@/shared/lib/format";
import { loadErrorText, type Paginated } from "@/shared/lib/http";
import { canView } from "@/shared/lib/nav";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { PersonalText } from "@/shared/ui/PersonalText";
import { Tabs, useTabParam } from "@/shared/ui/Tabs";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { fetchConfirmationQueue, fetchConfirmationQueueAll } from "../api";
import { claimActive, detailHref, dueAt, lineNames, loadedOnlyNote, matches, reasonText, telHref } from "../confirmationUi";
import type { ConfirmationQueueRow, QueueTabKey } from "../types";
import { QUEUE_TABS } from "../types";
import { SearchCustomerModal } from "./SearchCustomerModal";
import s from "../confirmation.module.css";

type Params = { tab: QueueTabKey };

const TAB_KEYS = QUEUE_TABS.map((t) => t.key);
const DEFAULT_TAB: QueueTabKey = "DEFAULT";

const EMPTY_HINT: Record<QueueTabKey, string> = {
  DEFAULT: "Đơn đã thanh toán và đơn tới giờ hẹn gọi lại sẽ hiện ở đây.",
  CALLBACK: "Đơn khách hẹn gọi lại sẽ hiện ở đây, kể cả khi chưa tới giờ.",
  ESCALATED: "Đơn gọi không được hoặc khách muốn đổi, huỷ sẽ hiện ở đây để Chủ hoặc Quản lý quyết định.",
  REFUND_CALL: "Đơn đã huỷ cần gọi báo khách sẽ hiện ở đây.",
  PENDING: "Đơn đã thanh toán đang chờ được gọi sẽ hiện ở đây.",
  ALL: "Mọi đơn đang cần gọi, hẹn gọi lại hoặc chờ quyết định sẽ hiện ở đây.",
};

async function loadRows(p: Params, page: number): Promise<Paginated<ConfirmationQueueRow>> {
  const tab = QUEUE_TABS.find((t) => t.key === p.tab);
  const res = p.tab === "ALL" ? await fetchConfirmationQueueAll(page) : await fetchConfirmationQueue({ state: tab?.stateParam, page });
  return { ...res, results: res.results.map((r) => ({ ...r, id: r.note_id })) };
}

export function ConfirmationQueueView() {
  const { me } = useAuth();
  const [tab, setTab] = useTabParam(TAB_KEYS, DEFAULT_TAB);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);

  const params: Params = useMemo(() => ({ tab: tab as QueueTabKey }), [tab]);
  const list = usePagedList<ConfirmationQueueRow, Params>(loadRows, params, true);
  const rows = list.rows;

  const shown = useMemo(() => (rows ? rows.filter((r) => matches(r, query)) : null), [rows, query]);

  // Thứ tự cột theo board W1c: Mã đơn, Khách hàng, Số điện thoại, Hàng, Tổng số kg, Trạng thái, Lý do, Hạn gọi, Đang gọi, Lần gọi.
  // Không có cột Tổng tiền (board không có; số tiền xem ở trang chi tiết, riêng dòng hoàn tiền ghi "Hoàn <số tiền>" ở cột Lý do).
  const columns: Column<ConfirmationQueueRow>[] = [
    { key: "code", header: "Mã đơn", mono: true, render: (r) => r.order_code, width: "132px" },
    {
      key: "name",
      header: "Khách hàng",
      render: (r) =>
        r.in_scope ? (
          <span title={r.customer_name ?? undefined}>
            <PersonalText value={r.customer_name} whenEmpty="—" />
          </span>
        ) : (
          <span className="muted" title="Ngoài phạm vi gọi">Ngoài phạm vi gọi</span>
        ),
    },
    {
      key: "phone",
      header: "Số điện thoại",
      num: true,
      width: "100px",
      render: (r) => {
        if (!r.in_scope) return <span className={s.maskedPhone}>{r.phone_masked}</span>;
        if (r.phone === null) return <PersonalText value={null} />;
        const tel = telHref(r.phone);
        return tel ? (
          <a className={s.phoneLink} href={tel}>
            {r.phone}
          </a>
        ) : (
          r.phone
        );
      },
    },
    { key: "lines", header: "Hàng", hideBelow: 720, render: (r) => <span className={s.lines} title={lineNames(r.lines_summary) || undefined}>{lineNames(r.lines_summary) || "—"}</span> },
    { key: "kg", header: "Tổng số kg", num: true, hideBelow: 800, render: (r) => kg(r.total_kg), width: "76px" },
    {
      key: "status",
      header: "Trạng thái",
      render: (r) => (r.confirm_state ? <Chip table={ENUMS.confirmTaskState} value={r.confirm_state} /> : <Chip table={ENUMS.deliveryStatus} value={r.note_status} />),
      width: "136px",
    },
    { key: "reason", header: "Lý do", hideBelow: 720, render: (r) => <span title={reasonText(r)}>{reasonText(r)}</span>, width: "108px" },
    { key: "due", header: "Hạn gọi", tabular: true, render: (r) => dateTime(dueAt(r)), width: "132px" },
    {
      key: "holder",
      header: "Đang gọi",
      hideBelow: 980,
      render: (r) => (claimActive(r) ? <span title={r.claimed_by?.display_name}>{r.claimed_by?.display_name}</span> : <span className="muted">—</span>),
      width: "72px",
    },
    { key: "attempts", header: "Lần gọi", num: true, hideBelow: 980, render: (r) => (r.in_scope ? `${r.attempts}/${r.max_attempts}` : "—"), width: "56px" },
  ];

  const tabLabel = QUEUE_TABS.find((t) => t.key === tab)?.label ?? "";
  const filtered = Boolean(query.trim());
  const noMatchWhileMore = filtered && Boolean(shown) && shown!.length === 0;
  const loadedNote = loadedOnlyNote(rows?.length ?? 0);
  const errorText = list.error && !list.rows ? loadErrorText(list.error) : null;

  return (
    <ListPage
      id="confirmation-panel"
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      actions={
        <>
          {me && canView(me, "call-scripts") && (
            <Link href="/confirmation/scripts/" className="btn">
              <Icon name="chat" />
              <span>Kịch bản gọi</span>
            </Link>
          )}
          <button type="button" className="btn" onClick={() => setSearching(true)}>
            <Icon name="search" />
            <span>Tìm khách gọi lại</span>
          </button>
        </>
      }
      tabs={
        <Tabs
          label="Nhóm việc gọi xác nhận"
          panelId="confirmation-panel"
          tabs={QUEUE_TABS.map((t) => ({ key: t.key, label: t.label, count: t.key === tab && !filtered ? list.count : null }))}
          value={tab}
          onChange={setTab}
        />
      }
      filters={
        <FilterBar
          query={query}
          onQuery={setQuery}
          placeholder="Tìm mã đơn, tên khách, mặt hàng"
          searchLabel="Tìm trong hàng chờ gọi"
          summary={shown && rows ? `Đang hiện ${shown.length} / ${list.count} đơn` : undefined}
        />
      }
      banner={
        list.moreError != null ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>Chưa tải thêm được. Bấm Tải thêm để thử lại.</span>
          </div>
        ) : list.error && list.rows ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(list.error)}</span>
          </div>
        ) : tab === "REFUND_CALL" ? (
          <div className="alert-box warn" role="status">
            <Icon name="info" />
            <span>Chỉ báo khách đơn đã huỷ và sẽ được hoàn tiền. Không ghi số tài khoản của khách vào hệ thống.</span>
          </div>
        ) : undefined
      }
      footer={
        list.hasMore ? (
          <>
            {noMatchWhileMore && (
              <p className="muted" role="status">
                {loadedNote}
              </p>
            )}
            <button type="button" className="btn" onClick={() => void list.loadMore()} disabled={list.moreLoading}>
              {list.moreLoading ? <Icon name="progress_activity" className="spin" /> : null}
              <span>{list.moreLoading ? "Đang tải…" : "Tải thêm"}</span>
            </button>
          </>
        ) : undefined
      }
    >
      <DataTable
        columns={columns}
        rows={shown}
        rowKey={(r) => r.id}
        rowHref={(r) => (r.in_scope ? detailHref(r.note_id) : undefined)}
        loading={list.loading && !list.rows}
        error={errorText}
        onRetry={() => void list.reload()}
        query={query}
        onClearQuery={() => setQuery("")}
        noun="đơn"
        empty={{
          icon: "phone_in_talk",
          title: `Chưa có đơn nào ở mục ${tabLabel}`,
          hint: filtered && list.hasMore ? loadedNote : EMPTY_HINT[tab as QueueTabKey],
        }}
        canViewCost={false}
        dense
        caption={`Hàng chờ gọi xác nhận, mục ${tabLabel}`}
      />
      {searching && <SearchCustomerModal onClose={() => setSearching(false)} />}
    </ListPage>
  );
}
