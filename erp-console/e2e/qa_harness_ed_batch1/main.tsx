import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import "@/shared/ui/tokens.css";
import "@/shared/ui/globals.css";
import { ListPage } from "@/shared/ui/list/ListPage";
import { DataTable } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { Tabs, useTabParam } from "@/shared/ui/Tabs";
import { Chip } from "@/shared/ui/Chip";
import { ENUMS } from "@/shared/lib/enums";
import { ToastProvider, useToast } from "@/shared/ui/overlay/Toast";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { OfflineBanner } from "@/shared/ui/states/OfflineBanner";
import { vnd, dateTime } from "@/shared/lib/format";

type Row = { id: number; code: string; status: string; total: string; at: string; cost?: string };
const ROWS: Row[] = [
  { id: 1, code: "SO261002-A1B2C3", status: "BOOKED", total: "540000", at: "2026-10-02T03:30:00Z", cost: "300000" },
  { id: 2, code: "SO261002-D4E5F6", status: "PAID", total: "1250000", at: "2026-10-02T04:10:00Z", cost: "800000" },
  { id: 3, code: "SO261001-0A0B0C", status: "COMPLETED", total: "89500", at: "2026-10-01T09:00:00Z", cost: "50000" },
  { id: 4, code: "SO261001-111213", status: "AUTO_CANCELLED", total: "0", at: "2026-10-01T10:00:00Z", cost: "0" },
];
const params = new URLSearchParams(location.search);
const MODE = params.get("m") || "rows";
const LOCKED = params.get("locked") === "1"; // 1 = có quyền xem giá vốn

function Demo() {
  const toast = useToast();
  const [q, setQ] = useState(params.get("q") || "");
  const [status, setStatus] = useState("");
  const [tab, setTab] = useState("all");
  const base = MODE === "rows" || MODE === "stale" ? ROWS : MODE === "empty" ? [] : MODE === "search" ? [] : null;
  const filtered = base && (MODE === "rows" || MODE === "stale") ? ROWS.filter((r) => (!status || r.status === status) && (!q || r.code.toLowerCase().includes(q.toLowerCase()))) : base;
  const columns: any[] = [
    { key: "code", header: "Mã đơn", mono: true, render: (r: Row) => r.code, width: "180px" },
    { key: "status", header: "Trạng thái", render: (r: Row) => <Chip table={ENUMS.salesOrderStatus} value={r.status} /> },
    { key: "total", header: "Tổng tiền", num: true, render: (r: Row) => vnd(r.total) },
    { key: "at", header: "Tạo lúc", render: (r: Row) => dateTime(r.at) },
  ];
  if (LOCKED) columns.push({ key: "cost", header: "Giá vốn", num: true, locked: true, render: (r: Row) => vnd(r.cost) });
  return (
    <>
      <OfflineBanner />
      <ListPage
        title="Đơn hàng"
        actions={<button className="btn primary">Tạo đơn</button>}
        tabs={<Tabs label="Lọc theo nhóm" tabs={[{ key: "all", label: "Tất cả", count: 4 }, { key: "pay", label: "Hàng chờ thanh toán", count: 2 }, { key: "ref", label: "Phiếu hoàn", count: 0 }]} value={tab} onChange={setTab} />}
        filters={
          <FilterBar query={q} onQuery={setQ} placeholder="Tìm mã đơn" searchLabel="Tìm đơn" summary={`Đang hiện ${filtered?.length ?? 0} / 4 đơn`}
            selects={[{ key: "s", label: "Trạng thái", value: status, onChange: setStatus, options: [{ value: "", label: "Mọi trạng thái" }, { value: "BOOKED", label: "Giữ chỗ" }, { value: "PAID", label: "Đã thanh toán" }] }]} />
        }
        aiBar={null}
        footer={<button className="btn">Tải thêm</button>}
      >
        <DataTable
          columns={columns}
          rows={MODE === "loading" ? null : MODE === "error" ? [] : (filtered as Row[])}
          rowKey={(r: Row) => r.id}
          rowHref={(r: Row) => `/orders/${r.id}/`}
          loading={MODE === "loading"}
          error={MODE === "error" ? "Không tải được danh sách đơn." : null}
          onRetry={() => toast.warn("Đã bấm Thử lại")}
          query={q}
          onClearQuery={() => setQ("")}
          noun="đơn hàng"
          empty={{ icon: "receipt_long", title: "Chưa có đơn hàng nào", hint: "Đơn mới sẽ hiện ở đây khi khách đặt." }}
          canViewCost={LOCKED}
          stale={MODE === "stale" ? true : undefined}
          caption="Danh sách đơn hàng"
        />
      </ListPage>
      <div style={{ display: "flex", gap: 8, padding: 12 }} id="toast-buttons">
        <button className="btn" onClick={() => toast.success("Đã lưu đơn")}>T-success</button>
        <button className="btn" onClick={() => toast.warn("Kho sắp hết lô")}>T-warn</button>
        <button className="btn" onClick={() => toast.error("Không lưu được")}>T-error</button>
        <button className="btn" onClick={() => toast.success("Đã huỷ đơn", { undo: () => (document.title = "undone") })}>T-undo</button>
        <button className="btn" onClick={() => toast.success("Ngắn 1.5 giây", { duration: 1500 })}>T-dur-short</button>
        <button className="btn" onClick={() => toast.error("Lỗi dài 20 giây", { duration: 20000 })}>T-dur-long</button>
        <button className="btn" onClick={() => { for (let i = 0; i < 6; i++) toast.success("Thông báo " + i); }}>T-many</button>
      </div>
    </>
  );
}

// Chế độ ?m=tabparam: kiểm useTabParam (pushState + popstate) trên trình duyệt thật (ED-01-AC4).
function TabParamDemo() {
  const keys = ["all", "pay", "ref"];
  const [tab, setTab] = useTabParam(keys, "all");
  return (
    <>
      <Tabs label="Lọc theo nhóm" tabs={[{ key: "all", label: "Tất cả" }, { key: "pay", label: "Hàng chờ thanh toán" }, { key: "ref", label: "Phiếu hoàn" }]} value={tab} onChange={setTab} />
      <output id="tab-now">{tab}</output>
    </>
  );
}

// QA vòng 2: chế độ ?m=enums (H1: giá trị enum lạ / rỗng trong chip)
function EnumsDemo() {
  const vals: (string | null | undefined)[] = ["BOOKED", "NEW_FANCY_STATE", "", null, undefined, "paid", "  "];
  return (
    <ul id="enum-list">
      {vals.map((v, i) => (
        <li key={i} data-v={String(v)}><Chip table={ENUMS.salesOrderStatus} value={v} /></li>
      ))}
    </ul>
  );
}

function App() {
  if (MODE === "enums") return <div className="app"><aside className="rail-left" aria-hidden="true" /><div className="center"><main className="content" id="main"><EnumsDemo /></main></div></div>;
  if (MODE === "tabparam") return <div className="app"><aside className="rail-left" aria-hidden="true" /><div className="center"><main className="content" id="main"><TabParamDemo /></main></div></div>;
  if (MODE === "error-screen") return <div className="app"><aside className="rail-left" aria-hidden="true" /><div className="center"><main className="content" id="main"><ErrorScreen onRetry={() => (document.title = "retried")} /></main></div></div>;
  if (MODE === "notfound-screen") return <div className="app"><aside className="rail-left" aria-hidden="true" /><div className="center"><main className="content" id="main"><NotFoundScreen /></main></div></div>;
  return (
    <ToastProvider>
      <div className="app">
        <aside className="rail-left" aria-hidden="true" />
        <div className="center">
          <main className="content" id="main"><Demo /></main>
        </div>
      </div>
    </ToastProvider>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
