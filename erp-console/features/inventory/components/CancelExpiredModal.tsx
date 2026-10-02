"use client";

// F1h Huỷ phần tồn, ghi lỗ (BR-LO-03, BR-LO-07): xuất huỷ TOÀN BỘ tồn còn lại, lô → Đã huỷ. Không hoàn tác được.
// Gửi kèm `confirm_qty` = số kg đang hiện: tồn thật đã đổi thì máy chủ từ chối và mời tải lại (không huỷ nhầm số khác).
// "Tiền ghi lỗ" = số kg × giá vốn/kg, chỉ hiện với người có quyền xem giá vốn.
import { kg, vnd } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel } from "@/shared/ui/form/useSubmit";
import { SummaryBlock, type SummaryRow } from "@/shared/ui/form/SummaryBlock";
import { Modal } from "@/shared/ui/overlay/Modal";
import { cancelExpiredBatch } from "../api";
import { qtyAvailable } from "../lotView";
import { ActionError, useActionSubmit, type ActionProps } from "./useActionSubmit";

export function CancelExpiredModal({ row, viewCost, onClose, onDone, onReload, onConflict }: ActionProps & { viewCost: boolean }) {
  const qty = qtyAvailable(row);
  const sub = useActionSubmit(
    () => cancelExpiredBatch(row.id, qty),
    () => onDone(`Đã huỷ ${kg(qty)} của lô ${row.batch_id} và ghi lỗ.`),
    onConflict,
  );
  const rows: SummaryRow[] = [
    { label: "Lô", value: row.batch_id, mono: true },
    { label: "Mặt hàng", value: row.item_name },
    { label: "Số kg huỷ", value: <span data-testid="cancel-qty">{kg(qty)}</span>, num: true },
  ];
  if (viewCost && row.landed_unit_cost !== undefined) {
    rows.push({
      label: "Tiền ghi lỗ",
      value: (
        <>
          <Icon name="lock" /> {vnd(Math.round(qty * Number(row.landed_unit_cost)))}
        </>
      ),
      num: true,
      strong: true,
    });
  }
  return (
    <Modal
      title="Huỷ phần tồn, ghi lỗ"
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          <button type="button" className="btn danger" onClick={() => void sub.submit()} disabled={sub.submitting || sub.blocked} aria-busy={sub.submitting}>
            {sub.submitting ? "Đang huỷ…" : primaryLabel(`Huỷ ${kg(qty)}`, sub.failed)}
          </button>
        </>
      }
    >
      {sub.error && <ActionError message={sub.error} stale={sub.stale} busy={sub.submitting} onReload={onReload} />}
      <SummaryBlock label="Phần tồn sẽ huỷ" rows={rows} />
      <FormAlert kind="warn">Không hoàn tác được.</FormAlert>
    </Modal>
  );
}
