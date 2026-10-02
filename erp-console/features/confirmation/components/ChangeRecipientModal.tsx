"use client";

// F2j "Đổi người nhận / địa chỉ" (CS-12). Ba ô, điền sẵn giá trị hiện tại; chỉ gửi trường đã đổi.
// Tên, số điện thoại, địa chỉ chỉ nằm trong state của hộp: không vào URL, localStorage hay log.
// Đổi địa chỉ làm tem cũ hết hiệu lực: BE trả `label_invalidated`, màn báo cần in tem mới.
import { useState } from "react";
import { Field } from "@/shared/ui/form/Field";
import { ModalAlert } from "./ModalAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { primaryLabel } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { changeRecipient } from "../api";
import { ADDRESS_MAX, RECIPIENT_FIELD_OF, RECIPIENT_NAME_MAX, recipientChanges, validateRecipient, type RecipientDraft, type RecipientErrors } from "../confirmationUi";
import type { ChangeRecipientResponse } from "../types";
import { useGuardedSubmit } from "../useGuardedSubmit";
import s from "../confirmation.module.css";

type Props = {
  noteId: number;
  orderCode: string;
  initial: RecipientDraft;
  onClose: () => void;
  onDone: (res: ChangeRecipientResponse, changedAny: boolean) => void;
  onStale: () => void;
};

export function ChangeRecipientModal({ noteId, orderCode, initial, onClose, onDone, onStale }: Props) {
  const [draft, setDraft] = useState<RecipientDraft>(initial);
  const [errors, setErrors] = useState<RecipientErrors>({});
  const [nothing, setNothing] = useState(false);

  const sub = useGuardedSubmit(() => changeRecipient(noteId, recipientChanges(initial, draft)), {
    onSuccess: (res) => onDone(res, res.changed.length > 0),
  });

  const set = (key: keyof RecipientDraft) => (v: string) => {
    setDraft((d) => ({ ...d, [key]: v }));
    setErrors((e) => ({ ...e, [key]: undefined }));
    setNothing(false);
  };

  const trySubmit = () => {
    const bad = validateRecipient(draft);
    setErrors(bad);
    if (Object.keys(bad).length > 0) return;
    if (Object.keys(recipientChanges(initial, draft)).length === 0) {
      setNothing(true);
      return;
    }
    void sub.submit();
  };

  // Lỗi 400 theo trường của BE hiện dưới ô tương ứng; không lặp ở alert đầu hộp.
  const serverErrors: RecipientErrors = {};
  for (const [k, v] of Object.entries(sub.fieldErrors)) {
    const key = RECIPIENT_FIELD_OF[k];
    if (key) serverErrors[key] = v;
  }
  const hasServerField = Object.keys(serverErrors).length > 0;
  const showAlert = (Boolean(sub.error) && !hasServerField) || Boolean(sub.stale) || nothing;
  const busy = sub.submitting || Boolean(sub.stale);

  return (
    <Modal
      title="Đổi người nhận / địa chỉ"
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
              {sub.submitting ? "Đang gửi…" : primaryLabel("Lưu thay đổi", sub.failed)}
            </button>
          )}
        </>
      }
    >
      {showAlert && <ModalAlert>{sub.stale ?? (nothing ? "Chưa có gì thay đổi để lưu." : sub.error)}</ModalAlert>}
      <SummaryBlock label="Đơn đang sửa" rows={[{ label: "Đơn hàng", value: orderCode, mono: true }]} />
      <div className={s.form}>
        <Field label="Tên người nhận" required value={draft.name} onChange={set("name")} maxLength={RECIPIENT_NAME_MAX} error={errors.name ?? serverErrors.name} disabled={busy} autoFocus />
        <Field label="Số điện thoại người nhận" required type="tel" value={draft.phone} onChange={set("phone")} error={errors.phone ?? serverErrors.phone} disabled={busy} />
        <Field as="textarea" label="Địa chỉ giao hàng" required value={draft.address} onChange={set("address")} rows={3} maxLength={ADDRESS_MAX} error={errors.address ?? serverErrors.address} disabled={busy} />
      </div>
    </Modal>
  );
}
