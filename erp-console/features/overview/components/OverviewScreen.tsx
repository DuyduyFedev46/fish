"use client";

// Tổng quan (ED-08 / D1): dải 5 số liệu · "Cần chú ý" · "Đơn hàng gần đây" · "Tồn kho theo lô".
// Dữ liệu: GET /api/dashboard/summary/ (cache dùng chung với Đơn, Kho & lô và tab Hoạt động) + /api/dashboard/attention/ (khối riêng).
// Giá vốn: ô "Giá trị tồn kho" và cột "Giá vốn/kg" chỉ có trong DOM khi `user.can_cost` (bất biến 1, ED-08-AC4).
// Bảng đơn không có tên khách/SĐT (SR-17, bất biến 9). Tìm kiếm dùng ô tìm chung của khung app (⌘K), màn này không có ô tìm riêng.
// Đếm ngược giữ chỗ ở CỘT RIÊNG, không gộp vào Lý do (ED-08-AC2). Đơn Giữ chỗ quá mốc đổi sang "Đã huỷ" ngay tại máy (ED-09-AC5).

import Link from "next/link";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { holdInfo } from "@/features/orders/orderDetailModel";
import { useNow } from "@/features/orders/useNow";
import { dashboardSummaryKey, fefoOrder, nearExpiryDays } from "@/shared/lib/dashboardSummary";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly, kg, timeHM, vnd } from "@/shared/lib/format";
import { canView } from "@/shared/lib/nav";
import { useResource } from "@/shared/lib/useResource";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { ResourceView } from "@/shared/ui/ResourceView";
import { SkeletonKpis, SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { useOfflineRegistration } from "@/shared/ui/states/offlineSource";
import { getOverview } from "../api";
import type { DashboardBatch, OverviewData, RecentOrder } from "../types";
import { orderLine } from "../view";
import { AttentionBlock } from "./AttentionBlock";
import { KpiTiles } from "./KpiTiles";
import s from "../overview.module.css";

function orderColumns(now: number): Column<RecentOrder>[] {
  return [
    { key: "code", header: "Mã đơn", mono: true, render: (o) => o.code },
    { key: "amount", header: "Giá trị", num: true, render: (o) => vnd(o.amount) },
    {
      key: "status",
      header: "Trạng thái",
      width: "128px",
      render: (o) => <Chip table={ENUMS.salesOrderStatus} value={orderLine(o.status, o.expires_at, now).status} />,
    },
    {
      key: "reason",
      header: "Lý do",
      hideBelow: 720,
      render: (o) => orderLine(o.status, o.expires_at, now).reason ?? <span className="muted">—</span>,
    },
    {
      key: "hold",
      header: "Còn giữ chỗ",
      num: true,
      width: "96px",
      render: (o) => {
        const until = orderLine(o.status, o.expires_at, now).holdUntil;
        const h = until ? holdInfo("BOOKED", until, now) : null;
        return h ? <span className={s.hold}>{h.left}</span> : <span className="muted">—</span>;
      },
    },
  ];
}

function batchColumns(): Column<DashboardBatch>[] {
  return [
    { key: "batch", header: "Lô", mono: true, render: (b) => b.batch_id },
    { key: "item", header: "Mặt hàng", render: (b) => b.item },
    { key: "warehouse", header: "Kho", hideBelow: 800, render: (b) => b.warehouse },
    { key: "qty", header: "Tồn", num: true, render: (b) => kg(b.qty_available) },
    {
      key: "reserved",
      header: "Giữ chỗ",
      num: true,
      hideBelow: 720,
      render: (b) => (Number(b.qty_reserved || 0) > 0 ? kg(b.qty_reserved) : <span className="muted">—</span>),
    },
    { key: "unit_cost", header: "Giá vốn/kg", num: true, locked: true, hideBelow: 980, render: (b) => vnd(b.unit_cost) },
    {
      key: "expiry",
      header: "Hạn dùng",
      num: true,
      render: (b) => {
        const tone = b.status === "EXPIRED" ? "crit-text" : b.near_expiry ? "warn-text" : undefined;
        return <span className={tone}>{dateOnly(b.expiry_date)}</span>;
      },
    },
    { key: "status", header: "Trạng thái", width: "130px", render: (b) => <Chip table={ENUMS.batchStatus} value={b.status} /> },
  ];
}

function Body({ data }: { data: OverviewData }) {
  const { me } = useAuth();
  const canCost = data.user.can_cost;
  const canPurchase = canView(me, "purchasing");
  const hasBooked = data.recent_orders.some((o) => o.status === "BOOKED" && !!o.expires_at);
  const now = useNow(hasBooked, 1000);
  const batches = fefoOrder(data.batches);

  return (
    <>
      <KpiTiles kpis={data.kpis} canCost={canCost} nearDays={nearExpiryDays(data)} asOf={data.as_of} />

      <div className={s.cols}>
        <section className={s.card} aria-labelledby="ov-alerts">
          <div className={s.cardHead}>
            <h2 id="ov-alerts">Cần chú ý</h2>
            <span className={s.cardHint}>{data.kpis.near_expiry ? `${data.kpis.near_expiry} lô cận hạn` : "Cận hạn"}</span>
          </div>
          <AttentionBlock alerts={data.alerts} />
        </section>

        <section className={s.card} aria-labelledby="ov-orders">
          <div className={s.cardHead}>
            <h2 id="ov-orders">Đơn hàng gần đây</h2>
            <Link href="/orders/" className={s.cardLink}>
              Xem tất cả <Icon name="arrow_forward" />
            </Link>
          </div>
          <DataTable
            caption="Đơn hàng gần đây"
            columns={orderColumns(now)}
            rows={data.recent_orders}
            rowKey={(o) => o.code}
            dense
            canViewCost={false}
            noun="đơn hàng"
            empty={{ icon: "receipt_long", title: "Chưa có đơn nào", hint: "Đơn khách đặt trên Shop sẽ hiện ở đây." }}
          />
        </section>
      </div>

      <section className={s.card} aria-labelledby="ov-batches">
        <div className={s.cardHead}>
          <h2 id="ov-batches">Tồn kho theo lô</h2>
          <span className={s.cardHint}>Xuất theo hạn dùng sớm nhất (FEFO)</span>
          <Link href="/inventory/" className={s.cardLink}>
            Quản lý kho <Icon name="arrow_forward" />
          </Link>
        </div>
        <DataTable
          caption="Tồn kho theo lô"
          columns={batchColumns()}
          rows={batches}
          rowKey={(b) => b.batch_id}
          dense
          canViewCost={canCost}
          noun="lô hàng"
          empty={{
            icon: "inventory_2",
            title: "Chưa có lô nào đang hoạt động",
            hint: "Lô nhập ở Mua hàng sẽ hiện ở đây, xếp theo hạn dùng sớm nhất (FEFO).",
            action: canPurchase ? (
              <Link href="/purchasing/" className="btn">
                Mở Mua hàng
                <Icon name="arrow_forward" />
              </Link>
            ) : undefined,
          }}
        />
      </section>
    </>
  );
}

export function OverviewScreen() {
  const { me } = useAuth();
  const res = useResource(me ? dashboardSummaryKey(me.id) : null, getOverview);
  useOfflineRegistration(res.data?.as_of || res.asOf ? { asOf: res.data?.as_of ?? res.asOf, onRetry: () => void res.reload() } : null);
  return (
    <div className={s.page}>
      {res.data?.as_of && <span className={s.asof}>Cập nhật {timeHM(res.data.as_of)}</span>}
      <ResourceView
        res={res}
        skeleton={
          <SkeletonScreen>
            <SkeletonKpis count={5} />
            <SkeletonTable rows={5} cols={3} />
            <SkeletonTable rows={6} cols={6} />
          </SkeletonScreen>
        }
      >
        {(data) => <Body data={data} />}
      </ResourceView>
    </div>
  );
}
