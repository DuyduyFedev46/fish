"use client";

// F1g Trả nhà cung cấp (SR-16): số kg trả + tiền nhà cung cấp hoàn (tuỳ chọn) + ghi chú. Tóm tắt Lô · Mặt hàng · Tồn còn.
// `request_id` sinh MỘT LẦN khi hộp mở và giữ suốt lần mở: bấm đúp / thử lại sau lỗi mạng gửi lại đúng mã đó, nên máy chủ
// trả bản ghi cũ thay vì trừ tồn lần hai. Tiền nhà cung cấp hoàn chỉ gửi đi, KHÔNG hiện lại sau khi lưu (nhạy cảm).
import { useRef, useState } from "react";
import { kg } from "@/shared/lib/format";
import { Field } from "@/shared/ui/form/Field";
import { primaryLabel } from "@/shared/ui/form/useSubmit";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { Modal } from "@/shared/ui/overlay/Modal";
import { decimalKg, returnToSupplier } from "../api";
import { kgToInput, newRequestId, NOTE_HAS_LONG_DIGITS, parseKgInput, qtyAvailable } from "../lotView";
import { ActionError, useActionSubmit, type ActionProps } from "./useActionSubmit";
import s from "../inventory.module.css";

export function ReturnToSupplierModal({ row, onClose, onDone, onReload, onConflict }: ActionProps) {
  const requestId = useRef("");
  if (!requestId.current) requestId.current = newRequestId();
  const available = qtyAvailable(row);

  const [qty, setQty] = useState("");
  const [refund, setRefund] = useState("");
  const [note, setNote] = useState("");
  const [qtyErr, setQtyErr] = useState<string | null>(null);
  const [noteErr, setNoteErr] = useState<string | null>(null);

  const sub = useActionSubmit(
    async () => {
      const n = parseKgInput(qty);
      const badQty = n === null || n <= 0 || n > available;
      const badNote = NOTE_HAS_LONG_DIGITS.test(note);
      setQtyErr(badQty ? `Nhập số kg lớn hơn 0 và không vượt tồn ${kg(available)} (tối đa 3 số lẻ).` : null);
      setNoteErr(badNote ? "Ghi chú không được chứa dãy số dài (tránh nhập số điện thoại)." : null);
      if (badQty || badNote || n === null) return null;
      return returnToSupplier(row.id, { qty: decimalKg(n), supplier_refund_amount: refund || "0", note: note.trim(), request_id: requestId.current });
    },
    (res) => res && onDone(`Đã ghi nhận trả ${kg(res.returned_qty)} cho nhà cung cấp.`),
    onConflict,
  );

  return (
    <Modal
      title="Trả nhà cung cấp"
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          <button type="button" className="btn primary" onClick={() => void sub.submit()} disabled={sub.submitting || sub.blocked} aria-busy={sub.submitting}>
            {sub.submitting ? "Đang lưu…" : primaryLabel("Ghi nhận đã trả", sub.failed)}
          </button>
        </>
      }
    >
      {sub.error && <ActionError message={sub.error} stale={sub.stale} busy={sub.submitting} onReload={onReload} testId="rts-error" />}
      <SummaryBlock
        label="Lô trả nhà cung cấp"
        rows={[
          { label: "Lô", value: row.batch_id, mono: true },
          { label: "Mặt hàng", value: row.item_name },
          { label: "Tồn còn", value: kg(available), num: true },
        ]}
      />
      <div className={s.qtyRow}>
        <Field label="Số kg đã trả" required unit="kg" type="number" value={qty} onChange={setQty} error={qtyErr} placeholder="vd 3,5" autoFocus />
        <button type="button" className="btn" onClick={() => setQty(kgToInput(available))} disabled={sub.submitting}>
          Trả hết
        </button>
      </div>
      <Field label="Tiền nhà cung cấp hoàn" unit="VNĐ" type="number" value={refund} onChange={(v) => setRefund(v.replace(/\D/g, "").slice(0, 12))} placeholder="Để trống nếu chưa có" />
      <Field label="Ghi chú" as="textarea" value={note} onChange={setNote} maxLength={500} rows={2} error={noteErr} />
    </Modal>
  );
}
