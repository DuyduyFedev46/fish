"use client";

// Màn Đơn (S8) — chuyển từ view "Đơn hàng" của bản HTML cũ: 8 đơn gần nhất, có SĐT (4 số cuối)
// và thời gian giữ chỗ còn lại (mốc hết hạn lấy từ backend, BR-BH giữ chỗ TTL). Danh sách đầy đủ + thao tác: S10.
// UI3: bảng phẳng (mã đơn mono xám, số căn phải, trạng thái chấm + chữ), header dính; hẹp thì thành danh sách gọn.

import { useEffect, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { dashboardSummaryKey } from "@/shared/lib/dashboardSummary";
import { remaining, vnd } from "@/shared/lib/format";
import { ORDER_STATUS } from "@/shared/lib/status";
import { useResource } from "@/shared/lib/useResource";
import { EmptyRow } from "@/shared/ui/EmptyRow";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { ResourceView } from "@/shared/ui/ResourceView";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { StatusChip } from "@/shared/ui/StatusChip";
import { Toolbar } from "@/shared/ui/Toolbar";
import { filterOrders, getOrders } from "../api";
import type { OrderRow, OrdersData } from "../types";

/** Đồng hồ phút cho cột "Giữ chỗ còn" — chỉ chạy khi có đơn đang giữ chỗ. */
function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    setNow(Date.now());
    const t = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(t);
  }, [active]);
  return now;
}

function Row({ o, now }: { o: OrderRow; now: number }) {
  const booked = o.status === "BOOKED";
  const left = booked ? remaining(o.expires_at, now) : null;
  return (
    <tr>
      <td className="code m-first" data-label="Mã đơn">{o.code}</td>
      <td className="m-title" data-label="Khách">{o.customer}</td>
      <td className="num muted" data-label="SĐT">
        {o.phone_last4 ? `…${o.phone_last4}` : "—"}
      </td>
      <td className="r num m-fig" data-label="Giá trị">
        <Figure text={vnd(o.amount)} />
      </td>
      <td className={`num${left ? " warn-text" : " muted m-hide"}`} data-m-label="Giữ chỗ còn">
        {left || "—"}
      </td>
      <td className="m-status" data-label="Trạng thái">
        <StatusChip map={ORDER_STATUS} status={o.status} label={o.status_label} />
      </td>
    </tr>
  );
}

function Body({
  data,
  q,
  onClearSearch,
  onReload,
}: {
  data: OrdersData;
  q: string;
  onClearSearch: () => void;
  onReload: () => void;
}) {
  const rows = filterOrders(data.recent_orders, q);
  const now = useNow(data.recent_orders.some((o) => o.status === "BOOKED"));
  return (
    <section className="sect" aria-labelledby="orders-h">
      <div className="sect-h">
        <h2 id="orders-h">Đơn gần nhất</h2>
        <span className="sub num">
          {data.recent_orders.length} đơn mới nhất · {data.kpis.pending_orders} đơn chờ xử lý
        </span>
      </div>
      <div className="dt-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Mã đơn</th>
              <th scope="col">Khách</th>
              <th scope="col">SĐT</th>
              <th scope="col" className="r">
                Giá trị
              </th>
              <th scope="col">Giữ chỗ còn</th>
              <th scope="col">Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((o) => <Row key={o.code} o={o} now={now} />)
            ) : (
              <EmptyRow
                cols={6}
                searching={!!q.trim()}
                onClearSearch={onClearSearch}
                emptyText="Chưa có đơn nào"
                hint="Đơn khách đặt trên Shop sẽ hiện ở đây. Bấm làm mới để kiểm tra đơn vừa vào."
                action={
                  <button type="button" className="btn" onClick={onReload}>
                    <Icon name="refresh" />
                    Làm mới danh sách
                  </button>
                }
              />
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function OrdersScreen() {
  const { me } = useAuth();
  const res = useResource(me ? dashboardSummaryKey(me.id) : null, getOrders);
  const [q, setQ] = useState("");
  return (
    <div className="screen">
      <p className="view-head">Vòng đời: giữ chỗ (có hạn) → thanh toán → xử lý → hoàn tất.</p>
      <Toolbar
        query={q}
        onQuery={setQ}
        placeholder="Tìm mã đơn, khách, 4 số cuối SĐT…"
        onRefresh={() => void res.reload()}
        refreshing={res.loading}
        asOf={res.data?.as_of}
      />
      <ResourceView
        res={res}
        skeleton={
          <SkeletonScreen>
            <SkeletonTable rows={8} cols={6} />
          </SkeletonScreen>
        }
      >
        {(data) => <Body data={data} q={q} onClearSearch={() => setQ("")} onReload={() => void res.reload()} />}
      </ResourceView>
    </div>
  );
}
