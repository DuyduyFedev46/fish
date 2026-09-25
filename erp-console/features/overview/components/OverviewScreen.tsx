"use client";

// Màn Tổng quan (S8) — chuyển từ bản HTML cũ: 4 KPI, 8 đơn gần nhất, cảnh báo cận hạn, tồn theo lô (≤20).
// Dữ liệu: GET /api/dashboard/summary/ (dùng chung cache với màn Đơn, Kho & lô và tab Hoạt động).
// Tìm kiếm phía máy lọc bảng đơn + bảng lô (như bản cũ). Cột giá vốn chỉ hiện khi user.can_cost.
// UI3: bố cục phẳng kiểu Linear — dải số liệu, "Cần chú ý", rồi các bảng không đóng khung; bảng thành danh sách gọn khi hẹp.

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { dashboardSummaryKey, nearExpiryDays } from "@/shared/lib/dashboardSummary";
import { dayMonth, kg, vnd } from "@/shared/lib/format";
import { canView } from "@/shared/lib/nav";
import { BATCH_STATUS, ORDER_STATUS } from "@/shared/lib/status";
import { useResource } from "@/shared/lib/useResource";
import { EmptyRow } from "@/shared/ui/EmptyRow";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { ResourceView } from "@/shared/ui/ResourceView";
import { SkeletonKpis, SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { StatusChip } from "@/shared/ui/StatusChip";
import { Toolbar } from "@/shared/ui/Toolbar";
import { filterBatches, filterRecentOrders, getOverview } from "../api";
import type { ExpiryAlert, OverviewData } from "../types";
import { KpiTiles } from "./KpiTiles";

function Alerts({ alerts }: { alerts: ExpiryAlert[] }) {
  if (!alerts.length) {
    return (
      <p className="calm">
        <Icon name="check_circle" />
        Không có lô cận hạn.
      </p>
    );
  }
  return (
    <ul className="alerts">
      {alerts.map((a) => {
        const crit = a.days_left <= 1;
        return (
          <li key={a.batch_id} className={`alert${crit ? " crit" : ""}`}>
            <Icon name={crit ? "error" : "schedule"} />
            <div className="tx">
              <b>
                {a.batch_id} · {a.item}
              </b>
              <span>
                Còn {a.days_left} ngày tới hạn · tồn {kg(a.qty)} — ưu tiên đẩy.
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function Body({ data, q, onClearSearch }: { data: OverviewData; q: string; onClearSearch: () => void }) {
  const { me } = useAuth();
  const canCost = data.user.can_cost;
  const orders = filterRecentOrders(data.recent_orders, q);
  const batches = filterBatches(data.batches, q);
  const batchCols = canCost ? 8 : 7;
  const searching = !!q.trim();
  const canPurchase = canView(me, "purchasing");
  return (
    <>
      <KpiTiles kpis={data.kpis} canCost={canCost} nearDays={nearExpiryDays(data)} />
      <div className="grid-2">
        <section className="sect sect-alerts" aria-labelledby="ov-alerts">
          <div className="sect-h">
            <h2 id="ov-alerts">Cần chú ý</h2>
            <span className="sub">{data.kpis.near_expiry ? `${data.kpis.near_expiry} lô cận hạn` : "Cận hạn"}</span>
          </div>
          <Alerts alerts={data.alerts} />
        </section>
        <section className="sect sect-orders" aria-labelledby="ov-orders">
          <div className="sect-h">
            <h2 id="ov-orders">Đơn hàng gần đây</h2>
            <Link href="/orders/" className="link" aria-label="Xem tất cả đơn hàng">
              Xem tất cả <Icon name="arrow_forward" />
            </Link>
          </div>
          <div className="dt-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">Mã đơn</th>
                  <th scope="col">Khách</th>
                  <th scope="col" className="r">Giá trị</th>
                  <th scope="col">Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {orders.length ? (
                  orders.map((o) => (
                    <tr key={o.code}>
                      <td className="code m-first" data-label="Mã đơn">{o.code}</td>
                      <td className="m-title" data-label="Khách">{o.customer}</td>
                      <td className="r num m-fig" data-label="Giá trị">
                        <Figure text={vnd(o.amount)} />
                      </td>
                      <td className="m-status" data-label="Trạng thái">
                        <StatusChip map={ORDER_STATUS} status={o.status} label={o.status_label} />
                      </td>
                    </tr>
                  ))
                ) : (
                  <EmptyRow
                    cols={4}
                    searching={searching}
                    onClearSearch={onClearSearch}
                    emptyText="Chưa có đơn nào"
                    hint="Đơn khách đặt trên Shop sẽ hiện ở đây."
                  />
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
      <section className="sect" aria-labelledby="ov-batches">
        <div className="sect-h">
          <h2 id="ov-batches">Tồn kho theo lô</h2>
          <span className="sub">Xuất theo hạn dùng sớm nhất (FEFO)</span>
          <Link href="/inventory/" className="link">
            Quản lý kho <Icon name="arrow_forward" />
          </Link>
        </div>
        <div className="dt-wrap">
          <table className="data">
            <thead>
              <tr>
                <th scope="col">Lô</th>
                <th scope="col">Mặt hàng</th>
                <th scope="col">Kho</th>
                <th scope="col" className="r">Tồn</th>
                <th scope="col" className="r">Giữ chỗ</th>
                {canCost && (
                  <th scope="col" className="r">
                    Giá vốn/kg
                  </th>
                )}
                <th scope="col">Hạn dùng</th>
                <th scope="col">Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {batches.length ? (
                batches.map((b) => {
                  const expTone = b.status === "EXPIRED" ? " crit-text" : b.near_expiry ? " warn-text" : "";
                  return (
                    <tr key={b.batch_id}>
                      <td className="code m-first" data-label="Lô">{b.batch_id}</td>
                      <td className="m-title" data-label="Mặt hàng">{b.item}</td>
                      <td data-label="Kho">{b.warehouse}</td>
                      <td className="r num m-fig" data-label="Tồn">
                        <Figure text={kg(b.qty_available)} />
                      </td>
                      <td className={`r num muted${Number(b.qty_reserved || 0) ? "" : " m-hide"}`} data-m-label="Giữ">
                        <Figure text={kg(b.qty_reserved || 0)} />
                      </td>
                      {canCost && (
                        <td className="r num muted" data-m-label="Vốn/kg">
                          <Figure text={vnd(b.unit_cost)} />
                        </td>
                      )}
                      <td className={`num${expTone}`} data-m-label="Hạn">
                        {dayMonth(b.expiry_date)}
                      </td>
                      <td className="m-status" data-label="Trạng thái">
                        <StatusChip map={BATCH_STATUS} status={b.status} label={b.status_label} />
                      </td>
                    </tr>
                  );
                })
              ) : (
                <EmptyRow
                  cols={batchCols}
                  searching={searching}
                  onClearSearch={onClearSearch}
                  emptyText="Chưa có lô nào đang hoạt động"
                  hint="Lô nhập ở Mua hàng sẽ hiện ở đây, xếp theo hạn dùng sớm nhất (FEFO)."
                  action={
                    canPurchase ? (
                      <Link href="/purchasing/" className="btn">
                        Mở Mua hàng
                        <Icon name="arrow_forward" />
                      </Link>
                    ) : undefined
                  }
                />
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

export function OverviewScreen() {
  const { me } = useAuth();
  const res = useResource(me ? dashboardSummaryKey(me.id) : null, getOverview);
  const [q, setQ] = useState("");
  return (
    <div className="screen">
      <Toolbar
        query={q}
        onQuery={setQ}
        placeholder="Tìm đơn, lô, khách, mặt hàng…"
        onRefresh={() => void res.reload()}
        refreshing={res.loading}
        asOf={res.data?.as_of}
      />
      <ResourceView
        res={res}
        skeleton={
          <SkeletonScreen>
            <SkeletonKpis />
            <SkeletonTable rows={5} cols={4} />
            <SkeletonTable rows={6} cols={6} />
          </SkeletonScreen>
        }
      >
        {(data) => <Body data={data} q={q} onClearSearch={() => setQ("")} />}
      </ResourceView>
    </div>
  );
}
