"use client";

// "Huỷ xác nhận đơn" (CS-11): đưa đơn đã xác nhận về Chờ xác nhận để gọi lại khách. Bắt buộc ghi lý do (chữ tự do, không ghi số điện thoại).
import { useState } from "react";
import { Field } from "@/shared/ui/form/Field";
import { ModalAlert } from "./ModalAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { primaryLabel } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { unconfirmDelivery } from "../api";
import { DECIDE_REASON_MAX, noteError } from "../confirmationUi";
import type { UnconfirmResponse } from "../types";
import { useGuardedSubmit } from "../useGuardedSubmit";
import s from "../confirmation.module.css";

type Props = {
  noteId: number;
  orderCode: string;
  onClose: () => void;
  onDone: (res: UnconfirmResponse) => void;
  onStale: () => void;
};

export function UnconfirmModal({ noteId, orderCode, onClose, onDone, onStale }: Props) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const sub = useGuardedSubmit(() => unconfirmDelivery(noteId, { reason: reason.trim() }), { onSuccess: onDone });

  const trySubmit = () => {
    const bad = !reason.trim() ? "Nhập lý do huỷ xác nhận." : noteError(reason, DECIDE_REASON_MAX);
    setError(bad);
    if (!bad) void sub.submit();
  };
  const busy = sub.submitting || Boolean(sub.stale);

  return (
    <Modal
      title="Huỷ xác nhận đơn"
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          {sub.stale ? (
            <button type="button" className="btn primary" onClick={onStale}>
              Tải lại
            </button>
          ) : (
            <button type="button" className="btn primary" onClick={trySubmit} disabled={sub.submitting}>
              {sub.submitting ? "Đang gửi…" : primaryLabel("Huỷ xác nhận", sub.failed)}
            </button>
          )}
        </>
      }
    >
      {(sub.error || sub.stale) && <ModalAlert>{sub.stale ?? sub.error}</ModalAlert>}
      <SummaryBlock label="Đơn đang sửa" rows={[{ label: "Đơn hàng", value: orderCode, mono: true }, { label: "Sau khi huỷ", value: "Phiếu giao về Chờ gọi xác nhận, gọi lại khách" }]} />
      <div className={s.form}>
        <Field
          as="textarea"
          label="Lý do (không ghi số điện thoại hay số tài khoản)"
          required
          value={reason}
          onChange={(v) => {
            setReason(v);
            setError(null);
          }}
          rows={3}
          maxLength={DECIDE_REASON_MAX}
          error={error}
          disabled={busy}
          autoFocus
        />
      </div>
    </Modal>
  );
}
