"use client";

// Hai hộp xác nhận của trang chi tiết phiếu nhập: Ghi nhận phiếu (Nháp → sinh lô) và Huỷ phiếu (huỷ các lô Nháp của phiếu).
// Gửi một lần (useSubmit chặn bấm đúp). Câu lỗi của BE bỏ mã nghiệp vụ trước khi hiện; lỗi do trạng thái phiếu đã đổi thì mời "Tải lại phiếu".
import { useState } from "react";
import { stripRuleCodes } from "@/features/inventory/lotView";
import { ApiError } from "@/shared/lib/http";
import { dateOnly, kg } from "@/shared/lib/format";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { cancelPurchaseReceipt, submitReceipt } from "../api";
import type { ReceiptDetail } from "../types";

type Props = {
  row: ReceiptDetail;
  onClose: () => void;
  /** Báo xong (đã có câu cho toast); màn cha đóng hộp và tải lại. */
  onDone: (message: string) => void;
  /** Đóng hộp và tải lại phiếu thật. */
  onReload: () => void;
};

/** Gọi BE; câu lỗi bỏ mã BR-… và ghi nhớ lỗi có phải do trạng thái phiếu đã đổi (400) hay không. */
function useReceiptAction<T>(run: () => Promise<T>, onSuccess: (r: T) => void) {
  const [stale, setStale] = useState(false);
  const sub = useSubmit(
    async () => {
      setStale(false);
      try {
        return await run();
      } catch (err) {
        if (err instanceof ApiError) {
          setStale(err.status === 400 || err.status === 404 || err.status === 409);
          throw new ApiError(stripRuleCodes(err.message), err.status, err.code, err.details);
        }
        throw err;
      }
    },
    { onSuccess },
  );
  return { ...sub, stale, failed: sub.failed && !stale };
}

function ActionError({ message, stale, busy, onReload }: { message: string; stale: boolean; busy: boolean; onReload: () => void }) {
  return (
    <div data-testid="dialog-error">
      <FormAlert>{message}</FormAlert>
      {stale && (
        <button type="button" className="btn" onClick={onReload} disabled={busy}>
          Tải lại phiếu
        </button>
      )}
    </div>
  );
}

export function SubmitReceiptModal({ row, onClose, onDone, onReload }: Props) {
  const sub = useReceiptAction(
    () => submitReceipt(row.id),
    (res) => onDone(`Đã ghi nhận phiếu ${row.code}, sinh ${res.batches_created.length} lô Nháp.`),
  );
  return (
    <Modal
      title="Ghi nhận phiếu nhập"
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          <button type="button" className="btn primary" onClick={() => void sub.submit()} disabled={sub.submitting || sub.stale} aria-busy={sub.submitting} data-autofocus>
            {sub.submitting ? "Đang ghi nhận…" : primaryLabel("Ghi nhận phiếu", sub.failed)}
          </button>
        </>
      }
    >
      {sub.error && <ActionError message={sub.error} stale={sub.stale} busy={sub.submitting} onReload={onReload} />}
      <SummaryBlock
        label="Phiếu sắp ghi nhận"
        rows={[
          { label: "Phiếu nhập", value: row.code, mono: true },
          { label: "Nhà cung cấp", value: row.supplier_name },
          { label: "Ngày nhập", value: dateOnly(row.received_date), num: true },
          { label: "Tổng số kg", value: kg(row.total_qty), num: true },
        ]}
      />
      <p className="muted">Mỗi mặt hàng của phiếu sinh một lô Nháp trong kho. Lô chưa bán được cho tới khi mở bán.</p>
    </Modal>
  );
}

export function CancelReceiptModal({ row, onClose, onDone, onReload }: Props) {
  const sub = useReceiptAction(
    () => cancelPurchaseReceipt(row.id),
    () => onDone(`Đã huỷ phiếu ${row.code}.`),
  );
  const lots = row.lines.filter((l) => l.batch_code).length;
  return (
    <Modal
      title="Huỷ phiếu nhập"
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          <button type="button" className="btn danger solid" onClick={() => void sub.submit()} disabled={sub.submitting || sub.stale} aria-busy={sub.submitting} data-autofocus>
            {sub.submitting ? "Đang huỷ…" : primaryLabel("Huỷ phiếu", sub.failed)}
          </button>
        </>
      }
    >
      {sub.error && <ActionError message={sub.error} stale={sub.stale} busy={sub.submitting} onReload={onReload} />}
      <SummaryBlock
        label="Phiếu sắp huỷ"
        rows={[
          { label: "Phiếu nhập", value: row.code, mono: true },
          { label: "Nhà cung cấp", value: row.supplier_name },
          { label: "Tổng số kg", value: kg(row.total_qty), num: true },
          ...(lots > 0 ? [{ label: "Lô bị huỷ", value: String(lots), num: true }] : []),
        ]}
      />
      <p className="muted">Các lô Nháp của phiếu chuyển sang Đã huỷ và tồn về 0. Việc này không hoàn tác được.</p>
    </Modal>
  );
}
