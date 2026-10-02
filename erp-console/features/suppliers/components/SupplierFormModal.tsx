"use client";

// Hộp "Thêm nhà cung cấp" (ED-22 / F1b) và "Sửa nhà cung cấp" (nút Sửa ở trang chi tiết): form ngắn (5 ô) nên là hộp nổi trên đúng màn.
// Tạo: Tên *, Loại, Số điện thoại, Ghi chú, công tắc "Đang hợp tác". Sửa: chỉ gửi trường THẬT SỰ đổi (PATCH một phần); trạng thái hợp tác
// KHÔNG nằm trong hộp Sửa (đổi qua mục "…" có hỏi lại, để không ngừng hợp tác nhầm).
// Tên trùng hiện dưới ô Tên ở CẢ HAI dạng 400 của BE: `{name:[…]}` và `{detail, code:"SUPPLIER_NAME_TAKEN"}`.
// Lỗi gửi → giữ nguyên giá trị đã nhập, alert đỏ đầu form, nút chính đổi "Thử lại" (UI-RULES §6.6). Số điện thoại là dữ liệu đối tác:
// hiện đủ trong hộp, chỉ nằm trong state của hộp (không nháp, không storage, không URL, không log).

import { useId, useState } from "react";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { createSupplier, updateSupplier } from "../api";
import { SUPPLIERS_MSG as M } from "../messages";
import { EMPTY_DRAFT, FIELD_LIMITS, changedFields, draftOf, inputOf, isNameTaken, nameTakenMessage, saveErrorMessage, shouldResetSaveErrorOnNameEdit, topFormError, validateField, type Draft, type EditableTextField } from "../suppliersModel";
import type { Supplier, SupplierType } from "../types";
import s from "../suppliers.module.css";

type Props = {
  /** Có = sửa nhà cung cấp này; không có = thêm mới. */
  supplier?: Supplier;
  onClose: () => void;
  /** Sau khi lưu xong (đã có thân mới của BE). */
  onSaved: (saved: Supplier) => void;
};

const TYPE_FIELD_OPTIONS = [
  { value: "INDIVIDUAL", label: "Cá nhân" },
  { value: "COMPANY", label: "Doanh nghiệp" },
];

export function SupplierFormModal({ supplier, onClose, onSaved }: Props) {
  const formId = useId();
  const editing = !!supplier;
  const [draft, setDraft] = useState<Draft>(supplier ? draftOf(supplier) : EMPTY_DRAFT);
  const [errs, setErrs] = useState<Partial<Record<EditableTextField, string>>>({});
  const [nameServerError, setNameServerError] = useState<string | null>(null);
  const [nothing, setNothing] = useState(false);

  const sub = useSubmit(
    async () => {
      try {
        return supplier ? await updateSupplier(supplier.id, changedFields(supplier, draft)) : await createSupplier(inputOf(draft));
      } catch (err) {
        if (isNameTaken(err)) setNameServerError(nameTakenMessage(err));
        throw new Error(saveErrorMessage(err));
      }
    },
    { onSuccess: onSaved },
  );

  const setText = (k: EditableTextField) => (v: string) => {
    setDraft((d) => ({ ...d, [k]: v }));
    setNothing(false);
    if (errs[k]) setErrs((e) => ({ ...e, [k]: undefined }));
    if (k === "name") {
      // Sửa tên sau một lần lưu lỗi: xoá luôn lỗi của lần gửi cũ (kể cả `sub.error`), để nó không nhảy lên đầu form.
      if (!sub.submitting && shouldResetSaveErrorOnNameEdit({ nameServerError, submitNameError: sub.fieldErrors.name, submitError: sub.error })) sub.reset();
      setNameServerError(null);
    }
  };

  const submit = () => {
    const found: Partial<Record<EditableTextField, string>> = {};
    (Object.keys(FIELD_LIMITS) as EditableTextField[]).forEach((k) => {
      const msg = validateField(k, draft[k]);
      if (msg) found[k] = msg;
    });
    setErrs(found);
    if (Object.keys(found).length) return;
    if (supplier && Object.keys(changedFields(supplier, draft)).length === 0) {
      setNothing(true);
      return;
    }
    setNameServerError(null);
    void sub.submit();
  };

  const nameError = errs.name ?? nameServerError ?? sub.fieldErrors.name;
  // Lỗi tên trùng đã nằm dưới ô Tên: không lặp lại ở đầu form.
  const topError = topFormError({ nameServerError, submitNameError: sub.fieldErrors.name, submitError: sub.error });
  const title = editing ? M.editTitle : M.addTitle;

  return (
    <Modal
      title={title}
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.cancel}
          </button>
          <button type="submit" form={formId} className="btn primary" disabled={sub.submitting} aria-busy={sub.submitting || undefined}>
            {sub.submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{M.busy}</span>
              </>
            ) : (
              primaryLabel(editing ? M.editSubmit : M.addSubmit, sub.failed)
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
        {topError && <FormAlert>{topError}</FormAlert>}
        {nothing && <FormAlert kind="warn">{M.nothingChanged}</FormAlert>}
        <Field label={M.fieldName} required name="name" value={draft.name} onChange={setText("name")} maxLength={FIELD_LIMITS.name} error={nameError} autoFocus />
        <Field
          as="select"
          label={M.fieldType}
          name="supplier_type"
          value={draft.supplier_type}
          onChange={(v) => setDraft((d) => ({ ...d, supplier_type: v === "COMPANY" ? ("COMPANY" as SupplierType) : ("INDIVIDUAL" as SupplierType) }))}
          options={TYPE_FIELD_OPTIONS}
          error={sub.fieldErrors.supplier_type}
        />
        <Field label={M.fieldPhone} type="tel" name="phone" value={draft.phone} onChange={setText("phone")} maxLength={FIELD_LIMITS.phone} error={errs.phone ?? sub.fieldErrors.phone} />
        <Field as="textarea" label={M.fieldNote} name="note" value={draft.note} onChange={setText("note")} maxLength={FIELD_LIMITS.note} error={errs.note ?? sub.fieldErrors.note} />
        {!editing && (
          <label className="check-row">
            <input type="checkbox" name="is_active" checked={draft.is_active} onChange={(e) => setDraft((d) => ({ ...d, is_active: e.target.checked }))} />
            <span>
              <b>{M.fieldActive}</b>
            </span>
          </label>
        )}
      </form>
    </Modal>
  );
}
