"use client";

// Chi tiết một lô hàng (DW-05) — InventoryScreen gắn key=mã lô nên mỗi lô là một phiên mới: thông tin thuộc tính của lô + khối Tiếp theo · Đã làm (Guidance).
// Ẩn giá vốn nếu user không có quyền canCost (Bất biến 1).
//
// P8 Lô 5 (SR-15/SR-16, BR-LO-07): nút thao tác vẽ theo `next_steps` của lô Quá hạn:
//   - "Xác nhận Đã huỷ phần tồn"  → hộp xác nhận nêu số kg, gửi confirm_qty = tồn đang hiển thị
//   - "Xác nhận Đã trả NCC"       → form số kg + tiền NCC hoàn (tuỳ chọn) + ghi chú (ReturnToSupplierDialog)
//   - "Chốt lô"                   → khoá kèm lý do khi còn tồn (BR-LO-04)
// Người không có quyền (Chủ mới được) không thấy nút nào; sau khi lưu KHÔNG hiện lại tiền NCC hoàn.

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { dayMonth, kg, vnd } from "@/shared/lib/format";
import { BATCH_STATUS } from "@/shared/lib/status";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import { SideSheet } from "@/shared/ui/SideSheet";
import { StatusChip } from "@/shared/ui/StatusChip";
import { GuidancePanel } from "@/features/guidance";
import type { GuidanceData, GuidanceNextStep } from "@/features/guidance/types";
import { batchStatusLabel, cancelExpiredBatch, closeBatch } from "../api";
import type { BatchRow, ReturnToSupplierResult } from "../types";
import { ModalDialog } from "./ModalDialog";
import { ReturnToSupplierDialog } from "./ReturnToSupplierDialog";
import s from "../inventory.module.css";

type Props = {
  batch: BatchRow | null;
  onClose: () => void;
  canCost?: boolean;
  onUpdated?: () => void;
};

type Dialog = null | "cancel" | "return" | "close";
/** Kết quả vừa lưu — che lên dòng `batch` cho tới khi danh sách tải lại xong (lô đã Huỷ/Chốt có thể không còn trong danh sách). */
type Local = { qty?: number; status?: string; label?: string };

const ACTION_KEYS = ["cancel_expired", "return_to_supplier", "close"] as const;
const NO_PERMISSION = "BR-PQ-12";

/** Bước thao tác được vẽ thành nút: cho làm, hoặc bị khoá vì lý do nghiệp vụ. Thiếu quyền (BR-PQ-12) → không vẽ. */
function visibleStep(step: GuidanceNextStep | undefined): step is GuidanceNextStep {
  if (!step) return false;
  return step.allowed || !step.missing.some((m) => m.code === NO_PERMISSION);
}

export function BatchDetailSheet({ batch, onClose, canCost, onUpdated }: Props) {
  const [guidance, setGuidance] = useState<GuidanceData | null>(null);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [confirmQty, setConfirmQty] = useState(0);
  const [busy, setBusy] = useState(false);
  const [dialogErr, setDialogErr] = useState<{ text: string; code?: string } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [local, setLocal] = useState<Local | null>(null);
  const [refreshSignal, setRefreshSignal] = useState(0);

  // Danh sách tải lại xong → dòng `batch` mới đã có số thật, bỏ phần che.
  useEffect(() => {
    setLocal(null);
  }, [batch]);
  const qtyNow = local?.qty ?? batch?.qty_available ?? 0;
  const statusNow = local?.status ?? batch?.status ?? "";
  const labelNow = local?.label ?? batch?.status_label ?? "";

  const step = (key: (typeof ACTION_KEYS)[number]) => guidance?.next_steps.find((x) => x.key === key);
  const stepCancel = step("cancel_expired");
  const stepReturn = step("return_to_supplier");
  const stepClose = step("close");
  // Chỉ lô Quá hạn có nhóm nút này (lô khác giữ nguyên như trước: xem thông tin + khối Tiếp theo).
  const showActions = statusNow === "EXPIRED";
  const actions = showActions
    ? ([stepCancel, stepReturn, stepClose].filter(visibleStep) as GuidanceNextStep[])
    : [];
  const locked = actions.filter((a) => !a.allowed && a.missing.length > 0);

  const openDialog = useCallback(
    (which: Exclude<Dialog, null>) => {
      setDialogErr(null);
      setNotice(null);
      setConfirmQty(qtyNow);
      setDialog(which);
    },
    [qtyNow]
  );

  const handleAction = useCallback(
    (key: string) => {
      if (key === "cancel_expired") openDialog("cancel");
      else if (key === "return_to_supplier") openDialog("return");
      else if (key === "close") openDialog("close");
    },
    [openDialog]
  );

  const finish = (patch: Local, message: string) => {
    setLocal(patch);
    setNotice(message);
    setDialog(null);
    setRefreshSignal((c) => c + 1);
    onUpdated?.();
  };

  const runSimple = async (kind: "cancel" | "close") => {
    if (!batch || busy) return;
    setBusy(true);
    setDialogErr(null);
    try {
      if (kind === "cancel") {
        await cancelExpiredBatch(batch.batch_id, confirmQty);
        finish(
          { qty: 0, status: "CANCELLED", label: batchStatusLabel("CANCELLED") },
          `Đã huỷ phần tồn ${kg(confirmQty)} của lô ${batch.batch_id}. Lô chuyển sang Đã huỷ.`
        );
      } else {
        await closeBatch(batch.batch_id);
        finish({ status: "CLOSED", label: batchStatusLabel("CLOSED") }, `Đã chốt lô ${batch.batch_id}.`);
      }
    } catch (err: unknown) {
      setDialogErr({
        text: err instanceof Error ? err.message : "Thao tác thất bại. Vui lòng thử lại.",
        code: err instanceof ApiError ? err.code : undefined,
      });
    } finally {
      setBusy(false);
    }
  };

  const onReturned = (r: ReturnToSupplierResult) => {
    const left = Number(r.qty_available);
    finish(
      { qty: left, status: r.status, label: batchStatusLabel(r.status) },
      `Đã ghi nhận trả NCC ${kg(r.returned_qty)}. Tồn còn lại ${kg(left)}.` +
        (left <= 0 ? " Lô hết tồn — có thể Chốt lô." : "")
    );
  };

  /** 400 "Tồn đã đổi" → tải lại số thật (danh sách + khối Tiếp theo) rồi cho làm lại. */
  const reloadAfterStale = () => {
    setDialog(null);
    setDialogErr(null);
    setRefreshSignal((c) => c + 1);
    onUpdated?.();
  };

  if (!batch) return null;

  return (
    <>
      <SideSheet onClose={onClose} title={`Chi tiết lô ${batch.batch_id}`} busy={busy}>
        <div className={s.sheetBody}>
          <header className={s.sheetHeader}>
            <div className={s.headerTop}>
              <StatusChip map={BATCH_STATUS} status={statusNow} label={labelNow} />
              {batch.near_expiry && statusNow !== "EXPIRED" && <span className="badge warn">Cận hạn</span>}
            </div>
            <h2 className={s.batchTitle}>{batch.item}</h2>
            <p className={`${s.batchCode} num`}>{batch.batch_id}</p>

            {notice && (
              <div className="alert-box ok" role="status" data-testid="batch-notice">
                <Icon name="check_circle" />
                <span>{notice}</span>
              </div>
            )}

            {/* Nút thao tác theo next_steps của lô Quá hạn (BR-LO-07) */}
            {actions.length > 0 && (
              <>
                <div className={s.actionRow} data-testid="batch-actions">
                  {actions.map((a) => {
                    const disabled = !a.allowed;
                    const cls = a.key === "cancel_expired" ? "btn danger" : a.key === "close" ? "btn primary" : "btn";
                    return (
                      <button
                        key={a.key}
                        type="button"
                        className={cls}
                        data-action={a.key}
                        disabled={disabled}
                        aria-describedby={disabled ? `lock-${a.key}` : undefined}
                        onClick={() => handleAction(a.key)}
                      >
                        <Icon name={disabled ? "lock" : a.key === "cancel_expired" ? "delete" : a.key === "close" ? "task_alt" : "undo"} />
                        {a.label}
                      </button>
                    );
                  })}
                </div>
                {locked.length > 0 && (
                  <ul className={s.lockList}>
                    {locked.map((a) => (
                      <li key={a.key} id={`lock-${a.key}`} data-lock={a.key}>
                        <strong>{a.label}:</strong> {a.missing.map((m) => m.text).join(" ")}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </header>

          {/* Thông tin thuộc tính lô */}
          <dl className={s.propList}>
            <div className={s.propRow}>
              <dt>Tồn khả dụng</dt>
              <dd className="num font-semibold" data-testid="qty-available">
                <Figure text={kg(qtyNow)} />
              </dd>
            </div>
            <div className={s.propRow}>
              <dt>Lượng giữ chỗ</dt>
              <dd className="num">
                <Figure text={kg(batch.qty_reserved)} />
              </dd>
            </div>
            {batch.warehouse && (
              <div className={s.propRow}>
                <dt>Kho</dt>
                <dd>{batch.warehouse}</dd>
              </div>
            )}
            {batch.supplier && (
              <div className={s.propRow}>
                <dt>Nhà cung cấp</dt>
                <dd>{batch.supplier}</dd>
              </div>
            )}
            <div className={s.propRow}>
              <dt>Ngày nhập</dt>
              <dd className="num">{dayMonth(batch.received_date)}</dd>
            </div>
            <div className={s.propRow}>
              <dt>Hạn dùng</dt>
              <dd className={`num ${statusNow === "EXPIRED" ? "crit-text" : batch.near_expiry ? "warn-text" : ""}`}>
                {dayMonth(batch.expiry_date)}
              </dd>
            </div>
            {canCost && batch.unit_cost != null && (
              <div className={s.propRow}>
                <dt>Giá vốn/kg</dt>
                <dd className="num muted">
                  <Figure text={vnd(Number(batch.unit_cost))} />
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

      {/* Đã huỷ phần tồn (BR-LO-03, BR-LO-07): nêu mã lô + số kg, TUYỆT ĐỐI KHÔNG nêu số tiền */}
      {dialog === "cancel" && (
        <ModalDialog title="Xác nhận Đã huỷ phần tồn" onClose={() => setDialog(null)} busy={busy} tone="danger">
          <p className={s.modalDesc}>
            Huỷ toàn bộ <strong className="num" data-testid="cancel-qty">{kg(confirmQty)}</strong> còn tồn của lô{" "}
            <strong className="num">{batch.batch_id}</strong> ({batch.item}).
          </p>
          <p className={`${s.modalDesc} muted`}>
            Số kg này được ghi nhận xuất huỷ, hạch toán lỗ, và lô chuyển sang Đã huỷ (BR-LO-03). Không hoàn tác được.
          </p>
          <DialogError err={dialogErr} onReload={reloadAfterStale} />
          <div className={s.modalActions}>
            <button type="button" className="btn" disabled={busy} onClick={() => setDialog(null)}>
              Đóng
            </button>
            <button
              type="button"
              className="btn danger solid"
              disabled={busy}
              aria-busy={busy}
              data-autofocus
              onClick={() => void runSimple("cancel")}
            >
              {busy ? "Đang huỷ…" : `Xác nhận huỷ ${kg(confirmQty)}`}
            </button>
          </div>
        </ModalDialog>
      )}

      {dialog === "close" && (
        <ModalDialog title="Chốt lô" onClose={() => setDialog(null)} busy={busy}>
          <p className={s.modalDesc}>
            Chốt lô <strong className="num">{batch.batch_id}</strong> ({batch.item}). Lô đã chốt không nhập, xuất hay sửa được nữa (BR-LO-05).
          </p>
          <DialogError err={dialogErr} onReload={reloadAfterStale} />
          <div className={s.modalActions}>
            <button type="button" className="btn" disabled={busy} onClick={() => setDialog(null)}>
              Đóng
            </button>
            <button type="button" className="btn primary" disabled={busy} aria-busy={busy} data-autofocus onClick={() => void runSimple("close")}>
              {busy ? "Đang chốt…" : "Chốt lô"}
            </button>
          </div>
        </ModalDialog>
      )}

      {dialog === "return" && (
        <ReturnToSupplierDialog
          batch={batch}
          qtyAvailable={confirmQty}
          onClose={() => setDialog(null)}
          onDone={onReturned}
          onReload={reloadAfterStale}
        />
      )}
    </>
  );
}

function DialogError({ err, onReload }: { err: { text: string; code?: string } | null; onReload: () => void }) {
  if (!err) return null;
  return (
    <div className="alert-box err" role="alert" data-testid="dialog-error">
      <Icon name="error" />
      <span>{err.text}</span>
      {err.code === "BR-LO-07" && (
        <button type="button" className="btn" onClick={onReload}>
          Tải lại
        </button>
      )}
    </div>
  );
}
