"use client";

// F1e Mở bán lô: lô Nháp → Đang bán (Shop thấy được). Tóm tắt Lô · Mặt hàng · Số kg · Hạn dùng.
// Không có dòng "Giá bán": R5 chưa trả giá bán của lô (ghi trong 03-dev-notes).
import { dateOnly, kg } from "@/shared/lib/format";
import { primaryLabel } from "@/shared/ui/form/useSubmit";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { Modal } from "@/shared/ui/overlay/Modal";
import { publishBatch } from "../api";
import { ActionError, useActionSubmit, type ActionProps } from "./useActionSubmit";

export function PublishBatchModal({ row, onClose, onDone, onReload, onConflict }: ActionProps) {
  const sub = useActionSubmit(() => publishBatch(row.id), () => onDone(`Đã mở bán lô ${row.batch_id}.`), onConflict);
  return (
    <Modal
      title="Mở bán lô"
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          <button type="button" className="btn primary" onClick={() => void sub.submit()} disabled={sub.submitting || sub.blocked} aria-busy={sub.submitting} data-autofocus>
            {sub.submitting ? "Đang mở bán…" : primaryLabel("Mở bán lô", sub.failed)}
          </button>
        </>
      }
    >
      {sub.error && <ActionError message={sub.error} stale={sub.stale} busy={sub.submitting} onReload={onReload} />}
      <SummaryBlock
        label="Lô sắp mở bán"
        rows={[
          { label: "Lô", value: row.batch_id, mono: true },
          { label: "Mặt hàng", value: row.item_name },
          { label: "Số kg", value: kg(row.qty_received), num: true },
          { label: "Hạn dùng", value: dateOnly(row.expiry_date), num: true },
        ]}
      />
      <p className="muted">Sau khi mở bán, khách thấy lô này trên Shop và đặt mua được.</p>
    </Modal>
  );
}
