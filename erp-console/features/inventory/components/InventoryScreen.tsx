"use client";

// Màn Kho & lô (S8) — chuyển từ view "Kho & Lô" của bản HTML cũ: lô đang hoạt động (≤20), xếp theo thứ tự xuất FEFO (hạn dùng sớm nhất trước).
// Cột "Giá vốn/kg" chỉ hiện khi user.can_cost (inventory.view_costprice) — bất biến #1, S8-AC2/AC3.
// Backend mới là lớp chặn thật: thiếu quyền thì response không có key unit_cost.
// P8 Lô 5: `/inventory/?status=EXPIRED` (thẻ "Lô quá hạn còn tồn" ở Cần chú ý) → danh sách lô theo trạng thái từ
// GET /api/inventory/batches/?status=… (bản tóm tắt dashboard chỉ có lô đang hoạt động). Danh sách này chỉ có mã mặt hàng
// (BatchSerializer trả id NCC/kho, không có tên) nên bỏ cột NCC/Kho.
// UI3: bảng phẳng, header dính, số căn phải; hẹp thì thành danh sách gọn (mặt hàng + tồn, dòng phụ lô · kho · hạn).

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
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
import { batchStatusLabel, batchesByStatusKey, filterBatches, getBatchesByStatus, getInventory } from "../api";
import type { BatchRow, InventoryData } from "../types";
import { BatchDetailSheet } from "./BatchDetailSheet";
import s from "../inventory.module.css";

function Body({
  data,
  q,
  onClearSearch,
  onSelectBatch,
  status,
}: {
  data: InventoryData;
  q: string;
  onClearSearch: () => void;
  onSelectBatch: (b: BatchRow) => void;
  /** Có → chế độ danh sách lọc theo trạng thái (vẫn đủ cột NCC/Kho từ Lô 7). */
  status: string | null;
}) {
  const { me } = useAuth();
  const canCost = data.user.can_cost;
  const rows = filterBatches(data.batches, q);
  const canPurchase = canView(me, "purchasing");
  const filtered = status !== null;
  const expiredMode = status === "EXPIRED";
  const cols = canCost ? 8 : 7;
  return (
    <section className="sect" aria-labelledby="inv-h">
      <div className="sect-h">
        <h2 id="inv-h">{expiredMode ? "Lô quá hạn còn tồn" : filtered ? `Lô ${batchStatusLabel(status).toLowerCase()}` : "Tồn theo lô"}</h2>
        <span className="sub num">
          {filtered
            ? `${data.batches.length} lô${expiredMode ? " · Xác nhận Đã huỷ hoặc Đã trả NCC" : ""}`
            : `${data.batches.length} lô đang hoạt động · Xuất theo hạn dùng sớm nhất (FEFO)`}
        </span>
        {filtered && (
          <Link href="/inventory/" className={s.filterChip} data-testid="clear-status-filter">
            <Icon name="close" />
            Bỏ lọc, xem tất cả lô
          </Link>
        )}
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
                  <tr key={b.batch_id} className={s.rowClickable} onClick={() => onSelectBatch(b)}>
                    <td className="code m-first" data-label="Lô">
                      <button
                        type="button"
                        className={s.batchLink}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectBatch(b);
                        }}
                        title={`Xem chi tiết lô ${b.batch_id}`}
                      >
                        {b.batch_id}
                      </button>
                    </td>
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
                cols={cols}
                searching={!!q.trim()}
                onClearSearch={onClearSearch}
                emptyText={expiredMode ? "Không còn lô quá hạn nào còn tồn" : filtered ? "Không có lô nào ở trạng thái này" : "Chưa có lô nào đang hoạt động"}
                hint={
                  expiredMode
                    ? "Lô hết hạn mà còn hàng sẽ hiện ở đây để xác nhận Đã huỷ hoặc Đã trả NCC."
                    : "Lô nhập ở Mua hàng sẽ hiện ở đây, xếp theo hạn dùng sớm nhất (FEFO)."
                }
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

/** Trạng thái lô cho phép lọc qua URL (chỉ giá trị đã biết, không nhận chuỗi tuỳ ý). */
const FILTERABLE = ["DRAFT", "SELLING", "NEAR_EXPIRY", "SOLD_OUT", "EXPIRED", "CANCELLED", "CLOSED"];

function InventoryInner() {
  const { me } = useAuth();
  const raw = useSearchParams().get("status")?.toUpperCase() ?? null;
  const status = raw && FILTERABLE.includes(raw) ? raw : null;
  const res = useResource<InventoryData>(
    me ? (status ? batchesByStatusKey(me.id, status) : dashboardSummaryKey(me.id)) : null,
    () =>
      status
        ? getBatchesByStatus(status, { username: me?.username ?? "", can_cost: Boolean(me?.can_view_cost) })
        : getInventory()
  );
  const [q, setQ] = useState("");
  const [selectedBatch, setSelectedBatch] = useState<BatchRow | null>(null);
  const canCost = res.data?.user.can_cost;

  // Danh sách tải lại (sau khi lưu / bấm Tải lại) → cập nhật số thật cho lô đang mở.
  useEffect(() => {
    if (!selectedBatch || !res.data) return;
    const fresh = res.data.batches.find((b) => b.batch_id === selectedBatch.batch_id);
    if (
      fresh &&
      (fresh.qty_available !== selectedBatch.qty_available ||
        fresh.qty_reserved !== selectedBatch.qty_reserved ||
        fresh.status !== selectedBatch.status)
    ) {
      setSelectedBatch(fresh);
    }
  }, [res.data, selectedBatch]);
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
        {(data) => (
          <Body
            data={data}
            q={q}
            onClearSearch={() => setQ("")}
            onSelectBatch={setSelectedBatch}
            status={status}
          />
        )}
      </ResourceView>
      <BatchDetailSheet
        key={selectedBatch?.batch_id ?? "none"}
        batch={selectedBatch}
        onClose={() => setSelectedBatch(null)}
        canCost={canCost}
        onUpdated={() => void res.reload()}
      />
    </div>
  );
}

export function InventoryScreen() {
  // useSearchParams (xuất tĩnh) cần Suspense.
  return (
    <Suspense fallback={null}>
      <InventoryInner />
    </Suspense>
  );
}
