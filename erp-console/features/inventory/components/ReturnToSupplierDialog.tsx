"use client";

// Form "Xác nhận Đã trả NCC" (BR-MH-08, SR-16): số kg trả + tiền NCC hoàn (tuỳ chọn) + ghi chú.
// `request_id` sinh MỘT LẦN khi form mở và giữ suốt phiên form: bấm đúp / thử lại sau lỗi mạng gửi lại đúng mã đó,
// nên BE trả bản ghi cũ thay vì trừ tồn lần hai. Tiền NCC hoàn chỉ gửi đi, KHÔNG hiện lại sau khi lưu (nhạy cảm).

import { useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { kg } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { returnToSupplier } from "../api";
import type { BatchRow, ReturnToSupplierResult } from "../types";
import { ModalDialog } from "./ModalDialog";
import s from "../inventory.module.css";

type Props = {
  /** Lô + tồn ĐANG HIỂN THỊ (dùng để chặn nhập vượt tồn ngay ở form). */
  batch: BatchRow;
  qtyAvailable: number;
  onClose: () => void;
  onDone: (result: ReturnToSupplierResult) => void;
  /** Lỗi do số liệu đã cũ (tồn đổi) → đóng form và tải lại số thật. */
  onReload: () => void;
};

function newRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

/** "3,5" / "3.5" → 3.5; không hợp lệ (chữ, quá 3 số lẻ) → null. */
function parseKg(text: string): number | null {
  const t = text.trim().replace(",", ".");
  if (!/^\d+(\.\d{1,3})?$/.test(t)) return null;
  return Number(t);
}

export function ReturnToSupplierDialog({ batch, qtyAvailable, onClose, onDone, onReload }: Props) {
  const requestId = useRef<string>("");
  if (!requestId.current) requestId.current = newRequestId();
  const submitting = useRef(false);

  const [qty, setQty] = useState("");
  const [refund, setRefund] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [qtyErr, setQtyErr] = useState<string | null>(null);
  const [noteErr, setNoteErr] = useState<string | null>(null);
  const [formErr, setFormErr] = useState<{ text: string; code?: string } | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting.current) return; // chặn bấm đúp trước cả khi React kịp vẽ lại nút
    setFormErr(null);
    const n = parseKg(qty);
    const badQty = n === null || n <= 0 || n > qtyAvailable;
    const badNote = /\d{8,}/.test(note);
    setQtyErr(badQty ? `Nhập số kg lớn hơn 0 và không vượt tồn ${kg(qtyAvailable)} (tối đa 3 số lẻ).` : null);
    setNoteErr(badNote ? "Ghi chú không được chứa dãy số dài (tránh nhập số điện thoại)." : null);
    if (badQty || badNote || n === null) return;

    submitting.current = true;
    setBusy(true);
    try {
      const res = await returnToSupplier(batch.batch_id, {
        qty: n.toFixed(3),
        supplier_refund_amount: refund || "0",
        note: note.trim(),
        request_id: requestId.current,
      });
      onDone(res);
    } catch (err: unknown) {
      setFormErr({
        text: err instanceof Error ? err.message : "Không ghi nhận được. Vui lòng thử lại.",
        code: err instanceof ApiError ? err.code : undefined,
      });
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  };

  const qtyId = "rts-qty";
  const refundId = "rts-refund";
  const noteId = "rts-note";

  return (
    <ModalDialog title="Xác nhận Đã trả NCC" onClose={onClose} busy={busy}>
      <form className={s.modalForm} onSubmit={submit} noValidate>
        <p className={s.modalDesc}>
          Lô <strong className="num">{batch.batch_id}</strong> ({batch.item}) đang còn <strong className="num">{kg(qtyAvailable)}</strong>.
          Ghi số kg đã trả lại nhà cung cấp; có thể trả nhiều lần.
        </p>

        <div className="field">
          <label htmlFor={qtyId}>Số kg đã trả</label>
          <div className={s.qtyRow}>
            <input
              id={qtyId}
              name="qty"
              inputMode="decimal"
              autoComplete="off"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              aria-invalid={qtyErr ? true : undefined}
              aria-describedby={qtyErr ? `${qtyId}-err` : undefined}
              placeholder="vd 3,5"
              data-autofocus
            />
            <button type="button" className="btn" onClick={() => setQty(String(qtyAvailable).replace(".", ","))} disabled={busy}>
              Trả hết
            </button>
          </div>
          {qtyErr && (
            <span className="field-err" id={`${qtyId}-err`} role="alert">
              <Icon name="error" />
              {qtyErr}
            </span>
          )}
        </div>

        <div className="field">
          <label htmlFor={refundId}>Tiền NCC hoàn (₫) — nếu có</label>
          <input
            id={refundId}
            name="supplier_refund_amount"
            inputMode="numeric"
            autoComplete="off"
            value={refund}
            onChange={(e) => setRefund(e.target.value.replace(/\D/g, "").slice(0, 12))}
            placeholder="Để trống nếu chưa có"
          />
          <span className="help muted">Chỉ ghi sổ để tính lãi lỗ lô; hệ thống không chuyển tiền và không hiện lại số này sau khi lưu.</span>
        </div>

        <div className="field">
          <label htmlFor={noteId}>Ghi chú (tuỳ chọn)</label>
          <input
            id={noteId}
            name="note"
            autoComplete="off"
            maxLength={500}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            aria-invalid={noteErr ? true : undefined}
            aria-describedby={noteErr ? `${noteId}-err` : undefined}
          />
          {noteErr && (
            <span className="field-err" id={`${noteId}-err`} role="alert">
              <Icon name="error" />
              {noteErr}
            </span>
          )}
        </div>

        {formErr && (
          <div className="alert-box err" role="alert" data-testid="rts-error">
            <Icon name="error" />
            <span>{formErr.text}</span>
            {(formErr.code === "BR-MH-08" || formErr.code === "BR-LO-07") && (
              <button type="button" className="btn" onClick={onReload} disabled={busy}>
                Tải lại tồn
              </button>
            )}
          </div>
        )}

        <div className={s.modalActions}>
          <button type="button" className="btn" disabled={busy} onClick={onClose}>
            Đóng
          </button>
          <button type="submit" className="btn primary" disabled={busy} aria-busy={busy}>
            {busy ? "Đang lưu…" : "Ghi nhận đã trả"}
          </button>
        </div>
      </form>
    </ModalDialog>
  );
}
