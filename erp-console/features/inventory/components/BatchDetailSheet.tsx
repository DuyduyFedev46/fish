"use client";

// Chi tiết một lô hàng (DW-05): thông tin thuộc tính của lô + khối Tiếp theo · Đã làm (Guidance).
// Ẩn giá vốn nếu user không có quyền canCost (Bất biến 1).

import { dayMonth, kg, vnd } from "@/shared/lib/format";
import { BATCH_STATUS } from "@/shared/lib/status";
import { Figure } from "@/shared/ui/Figure";
import { SideSheet } from "@/shared/ui/SideSheet";
import { StatusChip } from "@/shared/ui/StatusChip";
import { GuidancePanel } from "@/features/guidance";
import type { BatchRow } from "../types";
import s from "../inventory.module.css";

type Props = {
  batch: BatchRow | null;
  onClose: () => void;
  canCost?: boolean;
};

export function BatchDetailSheet({ batch, onClose, canCost }: Props) {
  if (!batch) return null;

  return (
    <SideSheet
      onClose={onClose}
      title={`Chi tiết lô ${batch.batch_id}`}
    >
      <div className={s.sheetBody}>
        <header className={s.sheetHeader}>
          <div className={s.headerTop}>
            <StatusChip
              map={BATCH_STATUS}
              status={batch.status}
              label={batch.status_label}
            />
            {batch.near_expiry && (
              <span className="badge warn">Cận hạn</span>
            )}
          </div>
          <h2 className={s.batchTitle}>{batch.item}</h2>
          <p className={`${s.batchCode} num`}>{batch.batch_id}</p>
        </header>

        {/* Thông tin thuộc tính lô */}
        <dl className={s.propList}>
          <div className={s.propRow}>
            <dt>Tồn khả dụng</dt>
            <dd className="num font-semibold">
              <Figure text={kg(batch.qty_available)} />
            </dd>
          </div>
          <div className={s.propRow}>
            <dt>Lượng giữ chỗ</dt>
            <dd className="num">
              <Figure text={kg(batch.qty_reserved)} />
            </dd>
          </div>
          <div className={s.propRow}>
            <dt>Kho</dt>
            <dd>{batch.warehouse}</dd>
          </div>
          <div className={s.propRow}>
            <dt>Nhà cung cấp</dt>
            <dd>{batch.supplier}</dd>
          </div>
          <div className={s.propRow}>
            <dt>Ngày nhập</dt>
            <dd className="num">{dayMonth(batch.received_date)}</dd>
          </div>
          <div className={s.propRow}>
            <dt>Hạn dùng</dt>
            <dd className={`num ${batch.status === "EXPIRED" ? "crit-text" : batch.near_expiry ? "warn-text" : ""}`}>
              {dayMonth(batch.expiry_date)}
            </dd>
          </div>
          {canCost && batch.unit_cost != null && (
            <div className={s.propRow}>
              <dt>Giá vốn/kg</dt>
              <dd className="num muted">
                <Figure text={vnd(batch.unit_cost)} />
              </dd>
            </div>
          )}
        </dl>

        {/* Khối Tiếp theo · Đã làm (02b §6.7, DW-05) */}
        <GuidancePanel
          docType="batch"
          docId={batch.batch_id}
        />
      </div>
    </SideSheet>
  );
}
