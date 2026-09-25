"use client";

// Màn Kho & lô (S8) — chuyển từ view "Kho & Lô" của bản HTML cũ: lô đang hoạt động (≤20), xếp theo thứ tự xuất FEFO (hạn dùng sớm nhất trước).
// Cột "Giá vốn/kg" chỉ hiện khi user.can_cost (inventory.view_costprice) — bất biến #1, S8-AC2/AC3.
// Backend mới là lớp chặn thật: thiếu quyền thì response không có key unit_cost.
// UI3: bảng phẳng, header dính, số căn phải; hẹp thì thành danh sách gọn (mặt hàng + tồn, dòng phụ lô · kho · hạn).

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { dashboardSummaryKey } from "@/shared/lib/dashboardSummary";
import { dayMonth, kg, vnd } from "@/shared/lib/format";
import { BATCH_STATUS } from "@/shared/lib/status";
import { canView } from "@/shared/lib/nav";
import { useResource } from "@/shared/lib/useResource";
import { EmptyRow } from "@/shared/ui/EmptyRow";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { ResourceView } from "@/shared/ui/ResourceView";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { StatusChip } from "@/shared/ui/StatusChip";
import { Toolbar } from "@/shared/ui/Toolbar";
import { filterBatches, getInventory } from "../api";
import type { InventoryData } from "../types";

function Body({ data, q, onClearSearch }: { data: InventoryData; q: string; onClearSearch: () => void }) {
  const { me } = useAuth();
  const canCost = data.user.can_cost;
  const rows = filterBatches(data.batches, q);
  const canPurchase = canView(me, "purchasing");
  return (
    <section className="sect" aria-labelledby="inv-h">
      <div className="sect-h">
        <h2 id="inv-h">Tồn theo lô</h2>
        <span className="sub num">{data.batches.length} lô đang hoạt động · Xuất theo hạn dùng sớm nhất (FEFO)</span>
      </div>
      <div className="dt-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Lô</th>
              <th scope="col">Mặt hàng</th>
              <th scope="col">NCC</th>
              <th scope="col">Kho</th>
              <th scope="col" className="r">
                Tồn
              </th>
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
            {rows.length ? (
              rows.map((b) => {
                const expTone = b.status === "EXPIRED" ? " crit-text" : b.near_expiry ? " warn-text" : "";
                return (
                  <tr key={b.batch_id}>
                    <td className="code m-first" data-label="Lô">{b.batch_id}</td>
                    <td className="m-title" data-label="Mặt hàng">{b.item}</td>
                    <td className="muted" data-m-label="NCC">
                      {b.supplier}
                    </td>
                    <td data-label="Kho">{b.warehouse}</td>
                    <td className="r num m-fig" data-label="Tồn">
                      <Figure text={kg(b.qty_available)} />
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
                cols={canCost ? 8 : 7}
                searching={!!q.trim()}
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
  );
}

export function InventoryScreen() {
  const { me } = useAuth();
  const res = useResource(me ? dashboardSummaryKey(me.id) : null, getInventory);
  const [q, setQ] = useState("");
  const canCost = res.data?.user.can_cost;
  return (
    <div className="screen">
      <p className="view-head">
        Tồn theo lô, xuất theo hạn dùng sớm nhất (FEFO).{" "}
        {canCost === false ? "Bạn không có quyền xem giá vốn nên cột giá vốn được ẩn." : "Cột giá vốn chỉ hiện với người có quyền xem giá vốn."}
      </p>
      <Toolbar
        query={q}
        onQuery={setQ}
        placeholder="Tìm lô, mặt hàng, NCC, kho…"
        onRefresh={() => void res.reload()}
        refreshing={res.loading}
        asOf={res.data?.as_of}
      />
      <ResourceView
        res={res}
        skeleton={
          <SkeletonScreen>
            <SkeletonTable rows={8} cols={7} />
          </SkeletonScreen>
        }
      >
        {(data) => <Body data={data} q={q} onClearSearch={() => setQ("")} />}
      </ResourceView>
    </div>
  );
}
