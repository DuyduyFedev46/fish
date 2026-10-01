"use client";

// ED-17 — Danh sách phiếu giao (Chủ, Quản lý, NV kho). Khung ListPage: tab theo trạng thái (đồng bộ ?tab=), thanh lọc, bảng, "Tải thêm".
// Bấm một dòng → /deliveries/detail/?id=<số> (URL chỉ mang id). Tìm kiếm chạy trên các dòng đã tải, không gửi từ khoá đi đâu.
// Cột người nhận dùng PersonalText (null = đã ẩn theo thời hạn). Không có giá vốn trong màn này.
import { useMemo, useState } from "react";
import { ENUMS, deliveryLabelText } from "@/shared/lib/enums";
import { kg, todayInVietnam } from "@/shared/lib/format";
import { loadErrorText } from "@/shared/lib/http";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { PersonalText } from "@/shared/ui/PersonalText";
import { Tabs, useTabParam } from "@/shared/ui/Tabs";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { fetchDeliveryNotes } from "../api";
import { detailHref, lineNames, loadedOnlyNote } from "../deliveryUi";
import { STATUS_GROUP_TABS, type DeliveryNoteItem, type DeliveryStatusGroup } from "../types";
import s from "../deliveries.module.css";

type Params = { status: string; completed_from?: string };

const TAB_KEYS = STATUS_GROUP_TABS.map((t) => t.key);
const DEFAULT_TAB: DeliveryStatusGroup = "PREPARING";
const LABEL_ALL = "";
const COURIER_ALL = "";
const COURIER_NONE = "none";

function matches(row: DeliveryNoteItem, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return [row.code, row.order?.code, row.invoice_code, row.lines_summary].some((v) => (v || "").toLowerCase().includes(needle));
}

export function DeliveriesView() {
  const [tab, setTab] = useTabParam(TAB_KEYS, DEFAULT_TAB);
  const [query, setQuery] = useState("");
  const [label, setLabel] = useState(LABEL_ALL);
  const [courier, setCourier] = useState(COURIER_ALL);

  const params: Params = useMemo(
    () => (tab === "COMPLETED" ? { status: "COMPLETED", completed_from: todayInVietnam() } : { status: tab }),
    [tab],
  );
  const list = usePagedList<DeliveryNoteItem, Params>((p, page) => fetchDeliveryNotes({ ...p, page }), params, true);

  const rows = list.rows;
  const courierOptions = useMemo(() => {
    const names = new Map<number, string>();
    for (const r of rows ?? []) if (r.assigned_to && r.assigned_to_name) names.set(r.assigned_to, r.assigned_to_name);
    return [
      { value: COURIER_ALL, label: "Mọi người giao" },
      { value: COURIER_NONE, label: "Chưa giao cho ai" },
      ...Array.from(names, ([id, name]) => ({ value: String(id), label: name })),
    ];
  }, [rows]);

  const shown = useMemo(() => {
    if (!rows) return null;
    return rows.filter((r) => {
      if (!matches(r, query)) return false;
      if (label === "printed" && !r.label.printed) return false;
      if (label === "unprinted" && r.label.printed) return false;
      if (courier === COURIER_NONE && r.assigned_to) return false;
      if (courier && courier !== COURIER_NONE && String(r.assigned_to ?? "") !== courier) return false;
      return true;
    });
  }, [rows, query, label, courier]);

  const columns: Column<DeliveryNoteItem>[] = [
    { key: "code", header: "Mã phiếu", mono: true, render: (r) => r.code, width: "180px" },
    { key: "order", header: "Đơn hàng", mono: true, render: (r) => r.order?.code || "—", width: "150px" },
    { key: "name", header: "Người nhận", render: (r) => <PersonalText value={r.customer_name} whenEmpty="—" /> },
    { key: "lines", header: "Hàng", render: (r) => <span className={s.lines}>{lineNames(r.lines_summary) || "—"}</span> },
    { key: "kg", header: "Tổng kg", num: true, render: (r) => kg(r.total_kg), width: "100px" },
    { key: "courier", header: "Người giao", render: (r) => r.assigned_to_name || <span className="muted">Chưa giao</span>, width: "140px" },
    { key: "label", header: "Tem", render: (r) => <Chip entry={deliveryLabelText(r.label.printed ? r.label.valid_print_no ?? 1 : null)} />, width: "130px" },
    { key: "status", header: "Trạng thái", render: (r) => <Chip table={ENUMS.deliveryStatus} value={r.status} />, width: "140px" },
  ];

  const tabLabel = STATUS_GROUP_TABS.find((t) => t.key === tab)?.label ?? "";
  const filtered = !!(query.trim() || label || courier);
  // Bộ lọc/tìm kiếm chạy trên các dòng đã tải: còn trang chưa tải thì nói rõ để khỏi hiểu nhầm là không có.
  const noMatchWhileMore = filtered && Boolean(shown) && shown!.length === 0;
  const loadedNote = loadedOnlyNote(rows?.length ?? 0);
  const errorText = list.error && !list.rows ? loadErrorText(list.error) : null;

  return (
    <ListPage
      id="deliveries-panel"
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      tabs={
        <Tabs
          label="Nhóm phiếu giao theo trạng thái"
          panelId="deliveries-panel"
          tabs={STATUS_GROUP_TABS.map((t) => ({ key: t.key, label: t.label, count: t.key === tab && !filtered ? list.count : null }))}
          value={tab}
          onChange={setTab}
        />
      }
      filters={
        <FilterBar
          query={query}
          onQuery={setQuery}
          placeholder="Tìm mã phiếu, mã đơn, mặt hàng"
          searchLabel="Tìm phiếu giao"
          selects={[
            {
              key: "label",
              label: "Lọc theo tem",
              value: label,
              onChange: setLabel,
              options: [
                { value: LABEL_ALL, label: "Mọi tem" },
                { value: "unprinted", label: "Chưa in tem" },
                { value: "printed", label: "Đã in tem" },
              ],
            },
            { key: "courier", label: "Lọc theo người giao", value: courier, onChange: setCourier, options: courierOptions },
          ]}
          summary={shown && rows ? `Đang hiện ${shown.length} / ${list.count} phiếu` : undefined}
        />
      }
      footer={
        list.hasMore ? (
          <>
            {noMatchWhileMore && query.trim() && (
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
        ) : undefined
      }
    >
      <DataTable
        columns={columns}
        rows={shown}
        rowKey={(r) => r.id}
        rowHref={(r) => detailHref(r.id)}
        loading={list.loading && !list.rows}
        error={errorText}
        onRetry={() => void list.reload()}
        query={query}
        onClearQuery={() => setQuery("")}
        noun="phiếu giao"
        empty={{
          icon: "local_shipping",
          title: filtered ? "Không có phiếu nào khớp bộ lọc" : `Chưa có phiếu giao nào ở mục ${tabLabel}`,
          hint: filtered
            ? list.hasMore
              ? loadedNote
              : "Bỏ bớt bộ lọc để xem lại các phiếu đã tải."
            : "Phiếu mới sẽ hiện ở đây khi đơn đã thanh toán chuyển sang giao hàng.",
        }}
        canViewCost={false}
        caption={`Danh sách phiếu giao, mục ${tabLabel}`}
      />
    </ListPage>
  );
}
