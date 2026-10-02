"use client";

// Danh sách hàng hoàn về kho (ED-26 / W5e): khung ListPage + bảng DataTable, bấm dòng → /returns/detail/?id=.
// Cột: Mã phiếu · Phiếu giao · Lô · Mặt hàng · Số kg · Ngoài kho lạnh · Người nhập · Trạng thái · Quyết định · Ghi chú (không có cột Lý do).
// Lọc: trạng thái + tháng (BE) và ô tìm (lọc phía máy, từ khoá không đi đâu khác). Nút "Nhập hàng hoàn" cho người có quyền thêm.
// Người giao chỉ thấy phiếu của phiếu giao gán cho mình (BE lọc); NV kho, Quản lý, Chủ thấy tất cả. Ghi chú là chữ tự do: không lên URL, storage hay log.
import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { kg } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { PersonalText } from "@/shared/ui/PersonalText";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { RETURNS_MSG as M } from "../messages";
import { canCreate, currentMonth, isOutsideLong, matchesQuery, outsideText, pendingCount, recentMonths } from "../returnsModel";
import type { ReturnItem, ReturnListParams } from "../types";
import { useReturnList } from "../useReturnList";
import { CreateReturnModal } from "./CreateReturnModal";
import s from "../returns.module.css";

const STATUS_OPTIONS = [
  { value: "", label: M.allStatuses },
  { value: "DRAFT", label: ENUMS.returnToStockStatus.DRAFT.label },
  { value: "APPROVED", label: ENUMS.returnToStockStatus.APPROVED.label },
];

export function ReturnListScreen() {
  const { me } = useAuth();
  const toast = useToast();
  const [status, setStatus] = useState("");
  const [month, setMonth] = useState(() => currentMonth());
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);
  const params: ReturnListParams = useMemo(() => ({ status, month }), [status, month]);
  const list = useReturnList(params, !!me);
  const months = useMemo(() => recentMonths(), []);

  if (list.error instanceof ApiError && list.error.status === 403) return <NoPermission />;

  const rows = list.rows ? list.rows.filter((r) => matchesQuery(r, q)) : null;
  const pending = list.rows ? pendingCount(list.rows) : 0;

  // Bảng dense (bố cục cố định, chữ dài cắt bằng "…" kèm title): 10 cột phải vừa khung ở 1280 và 1440, không cuộn ngang (QA Lô 9 B2).
  // Cột Người nhập là phụ: ẩn khi khung bảng hẹp hơn 1100px (màn 1280 có khung ~990px; vẫn có ở trang chi tiết). Mặt hàng và Ghi chú nhận phần còn lại.
  const columns: Column<ReturnItem>[] = [
    { key: "code", header: M.colCode, mono: true, width: "84px", render: (r) => r.code },
    { key: "note_code", header: M.colDeliveryNote, mono: true, width: "124px", render: (r) => (r.delivery_note_code ? <span title={r.delivery_note_code}>{r.delivery_note_code}</span> : <span className="muted">—</span>) },
    { key: "batch", header: M.colBatch, mono: true, width: "148px", render: (r) => <span title={r.batch_code}>{r.batch_code}</span> },
    { key: "item", header: M.colItem, render: (r) => <span title={r.item_name}>{r.item_name}</span> },
    { key: "qty", header: M.colQty, num: true, width: "68px", render: (r) => kg(r.qty) },
    {
      key: "outside",
      header: M.colOutside,
      num: true,
      width: "116px",
      render: (r) =>
        isOutsideLong(r.outside_minutes) ? (
          <span className="warn-text">
            {outsideText(r.outside_minutes)}
            <span className="sr-only"> ({M.outsideLong})</span>
          </span>
        ) : (
          outsideText(r.outside_minutes)
        ),
    },
    { key: "by", header: M.colCreatedBy, width: "96px", hideBelow: 1100, render: (r) => r.created_by_name || <span className="muted">—</span> },
    { key: "status", header: M.colStatus, width: "92px", render: (r) => <Chip table={ENUMS.returnToStockStatus} value={r.status} /> },
    { key: "decision", header: M.colDecision, width: "128px", render: (r) => <Chip table={ENUMS.returnToStockDecision} value={r.decision} /> },
    { key: "note", header: M.colNote, render: (r) => <span className={s.noteCell} title={r.note || undefined}><PersonalText value={r.note} mutedWhenEmpty /></span> },
  ];

  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;

  return (
    <ListPage
      actions={
        canCreate(me?.permissions) ? (
          <button type="button" className="btn primary" onClick={() => setCreating(true)}>
            <Icon name="add" />
            <span>{M.createButton}</span>
          </button>
        ) : undefined
      }
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.searchPlaceholder}
          searchLabel={M.searchLabel}
          selects={[
            { key: "status", label: M.statusLabel, value: status, options: STATUS_OPTIONS, onChange: setStatus },
            { key: "month", label: M.monthLabel, value: month, options: [{ value: "", label: M.allMonths }, ...months], onChange: setMonth },
          ]}
          summary={list.rows ? M.shown(rows?.length ?? 0, list.count) : undefined}
        />
      }
      banner={
        <>
          {list.rows && pending > 0 && (
            <p className={`${s.summaryLine} num`} role="status">
              {M.pending(pending)}
            </p>
          )}
          {refreshFailed && (
            <div className="alert-box err" role="alert">
              <Icon name="sync_problem" />
              <span>{loadErrorText(list.error)}</span>
            </div>
          )}
        </>
      }
      footer={
        <>
          {list.moreError != null && (
            <span className="field-err" role="alert">
              {M.loadMoreFailed} {loadErrorText(list.moreError)}
            </span>
          )}
          {list.hasMore && (
            <button type="button" className="btn" onClick={() => void list.loadMore()} disabled={list.moreLoading} aria-busy={list.moreLoading || undefined}>
              {list.moreLoading ? M.loadingMore : M.loadMore}
            </button>
          )}
        </>
      }
    >
      <DataTable
        caption={M.listTitle}
        columns={columns}
        rows={rows}
        rowKey={(r) => r.id}
        rowHref={(r) => `/returns/detail/?id=${r.id}`}
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={q}
        onClearQuery={() => setQ("")}
        noun={M.noun}
        empty={{ icon: "assignment_return", title: M.emptyTitle, hint: M.emptyHint }}
        canViewCost={false}
        dense
      />
      {creating && (
        <CreateReturnModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            toast.success(M.createdToast);
            void list.reload();
          }}
        />
      )}
    </ListPage>
  );
}
