"use client";

// Chi tiết một lô hàng (DW-05): thông tin thuộc tính của lô + khối Tiếp theo · Đã làm (Guidance).
// Ẩn giá vốn nếu user không có quyền canCost (Bất biến 1).

import { useCallback, useState } from "react";
import { dayMonth, kg, vnd } from "@/shared/lib/format";
import { BATCH_STATUS } from "@/shared/lib/status";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { SideSheet } from "@/shared/ui/SideSheet";
import { StatusChip } from "@/shared/ui/StatusChip";
import { GuidancePanel } from "@/features/guidance";
import type { GuidanceData } from "@/features/guidance/types";
import { cancelExpiredBatch } from "../api";
import type { BatchRow } from "../types";
import s from "../inventory.module.css";

type Props = {
  batch: BatchRow | null;
  onClose: () => void;
  canCost?: boolean;
  onUpdated?: () => void;
};

export function BatchDetailSheet({ batch, onClose, canCost, onUpdated }: Props) {
  const [guidance, setGuidance] = useState<GuidanceData | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [refreshSignal, setRefreshSignal] = useState(0);

  const canCancelExpired = Boolean(
    guidance?.next_steps.some((step) => step.key === "cancel_expired" && step.allowed)
  );

  const handleAction = useCallback((actionKey: string) => {
    if (actionKey === "cancel_expired") {
      setErrorMsg(null);
      setShowConfirm(true);
    }
  }, []);

  const handleConfirmCancel = async () => {
    if (!batch || cancelling) return;
    setCancelling(true);
    setErrorMsg(null);
    try {
      await cancelExpiredBatch(batch.batch_id);
      setShowConfirm(false);
      setRefreshSignal((c) => c + 1);
      onUpdated?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Huỷ lô thất bại. Vui lòng thử lại.";
      setErrorMsg(msg);
    } finally {
      setCancelling(false);
    }
  };

  if (!batch) return null;

  return (
    <>
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

            {/* Nút Huỷ lô (DW-06) chỉ hiện khi bước cancel_expired allowed=true */}
            {canCancelExpired && (
              <div className={s.actionRow}>
                <button
                  type="button"
                  className={s.cancelBtn}
                  onClick={() => {
                    setErrorMsg(null);
                    setShowConfirm(true);
                  }}
                >
                  <Icon name="trash" />
                  <span>Huỷ lô</span>
                </button>
              </div>
            )}
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

          {/* Khối Tiếp theo · Đã làm (02b §6.7, DW-05, DW-06) */}
          <GuidancePanel
            docType="batch"
            docId={batch.batch_id}
            onAction={handleAction}
            onDataLoaded={setGuidance}
            refreshSignal={refreshSignal}
          />
        </div>
      </SideSheet>

      {/* Hộp xác nhận huỷ lô (DW-06): nêu mã lô + số kg, TUYỆT ĐỐI KHÔNG nêu số tiền */}
      {showConfirm && (
        <div className={s.modalOverlay} role="dialog" aria-modal="true">
          <div className={s.modalCard}>
            <h3 className={s.modalTitle}>Xác nhận huỷ lô quá hạn</h3>
            <p className={s.modalDesc}>
              Bạn có chắc chắn muốn huỷ lô <strong>{batch.batch_id}</strong> ({batch.item})?
            </p>
            <p className={s.modalDesc}>
              Khối lượng xuất huỷ hạch toán lỗ: <strong>{kg(batch.qty_available)} kg</strong>.
            </p>
            <p className={`${s.modalDesc} muted`}>
              Thao tác này sẽ ghi nhận xuất huỷ và chuyển lô sang trạng thái Đã huỷ (BR-LO-03).
            </p>
            {errorMsg && (
              <div className={s.modalError}>
                <span>{errorMsg}</span>
              </div>
            )}
            <div className={s.modalActions}>
              <button
                type="button"
                className="btn subtle"
                disabled={cancelling}
                onClick={() => setShowConfirm(false)}
              >
                Đóng
              </button>
              <button
                type="button"
                className={s.cancelBtn}
                disabled={cancelling}
                onClick={handleConfirmCancel}
              >
                {cancelling ? "Đang huỷ..." : "Xác nhận huỷ"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
