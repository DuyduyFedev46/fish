"use client";

// Hộp "Sửa thông tin" (nút chính trên header trang chi tiết, ED-14-AC2): form ngắn (3 ô) nên là hộp nổi trên đúng màn.
// Chỉ gửi trường THẬT SỰ đổi (PATCH một phần). Số điện thoại không có ô sửa (quyết định #5). Lỗi gửi → giữ nguyên giá trị đã nhập,
// alert đỏ đầu form, nút chính đổi "Thử lại" (UI-RULES §6.6). Giá trị đang gõ chỉ nằm trong state của hộp (không nháp, không storage).

import { useId, useState } from "react";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { updateCustomer } from "../api";
import { FIELD_LIMITS, changedFields, saveErrorMessage, validateField } from "../customersModel";
import { CUSTOMERS_MSG as M } from "../messages";
import type { CustomerDetail, CustomerEditableField } from "../types";
import s from "../customers.module.css";

type Props = {
  customer: CustomerDetail;
  onClose: () => void;
  /** Sau khi lưu xong (đã có thân chi tiết mới). */
  onSaved: () => void;
};

type Draft = Record<CustomerEditableField, string>;

export function EditCustomerModal({ customer, onClose, onSaved }: Props) {
  const formId = useId();
  const [draft, setDraft] = useState<Draft>({ name: customer.name ?? "", default_address: customer.default_address ?? "", note: customer.note ?? "" });
  const [errs, setErrs] = useState<Partial<Record<CustomerEditableField, string>>>({});
  const [nothing, setNothing] = useState(false);

  const sub = useSubmit(
    async () => {
      try {
        return await updateCustomer(customer.id, changedFields(customer, draft));
      } catch (err) {
        throw new Error(saveErrorMessage(err));
      }
    },
    { onSuccess: onSaved },
  );

  const set = (k: CustomerEditableField) => (v: string) => {
    setDraft((d) => ({ ...d, [k]: v }));
    setNothing(false);
    if (errs[k]) setErrs((e) => ({ ...e, [k]: undefined }));
  };

  const submit = () => {
    const found: Partial<Record<CustomerEditableField, string>> = {};
    (Object.keys(FIELD_LIMITS) as CustomerEditableField[]).forEach((k) => {
      const msg = validateField(k, draft[k]);
      if (msg) found[k] = msg;
    });
    setErrs(found);
    if (Object.keys(found).length) return;
    if (Object.keys(changedFields(customer, draft)).length === 0) {
      setNothing(true);
      return;
    }
    void sub.submit();
  };

  return (
    <Modal
      title={M.editTitle}
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.editClose}
          </button>
          <button type="submit" form={formId} className="btn primary" disabled={sub.submitting} aria-busy={sub.submitting || undefined}>
            {sub.submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{M.editBusy}</span>
              </>
            ) : (
              primaryLabel(M.editSubmit, sub.failed)
            )}
          </button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        className={s.form}
        onSubmit={(e) => {
          e.preventDefault();
          if (!sub.submitting) submit();
        }}
      >
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        {nothing && <FormAlert kind="warn">{M.nothingChanged}</FormAlert>}
        <Field label={M.fieldName} required name="name" value={draft.name} onChange={set("name")} maxLength={FIELD_LIMITS.name} error={errs.name ?? sub.fieldErrors.name} autoFocus />
        <Field as="textarea" label={M.fieldAddress} name="default_address" value={draft.default_address} onChange={set("default_address")} maxLength={FIELD_LIMITS.default_address} error={errs.default_address ?? sub.fieldErrors.default_address} />
        <Field as="textarea" label={M.fieldNote} name="note" value={draft.note} onChange={set("note")} maxLength={FIELD_LIMITS.note} error={errs.note ?? sub.fieldErrors.note} />
      </form>
    </Modal>
  );
}
