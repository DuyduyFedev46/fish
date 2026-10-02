"use client";

// Hộp Thêm / Sửa chuyên mục (ED-36 / F3h): tên, mô tả ngắn, thứ tự hiển thị. Đường dẫn do hệ thống tự tạo từ tên;
// khi sửa chỉ hiện để xem (không đổi được). Tên trùng hiện ngay dưới ô Tên. Lỗi gửi giữ nguyên giá trị đã nhập,
// nút chính đổi "Thử lại" (UI-RULES §6.6).

import { useId, useState } from "react";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { createCategory, updateCategory } from "../api";
import { errorText, isCategoryNameTaken, parseOrder } from "../contentModel";
import { CONTENT_MSG as M } from "../messages";
import type { ContentCategory } from "../types";
import s from "../content.module.css";

const NAME_MAX = 100;
const DESC_MAX = 300;

type Props = {
  /** Có = sửa chuyên mục này; không có = thêm mới. */
  category?: ContentCategory;
  /** Thứ tự gợi ý cho chuyên mục mới (lớn nhất hiện có + 1). */
  nextOrder: number;
  onClose: () => void;
  onSaved: (saved: ContentCategory) => void;
};

export function CategoryFormModal({ category, nextOrder, onClose, onSaved }: Props) {
  const formId = useId();
  const editing = !!category;
  const [name, setName] = useState(category?.name ?? "");
  const [description, setDescription] = useState(category?.description ?? "");
  const [order, setOrder] = useState(String(category?.order ?? nextOrder));
  const [errs, setErrs] = useState<{ name?: string; order?: string }>({});
  const [nameTaken, setNameTaken] = useState(false);

  const sub = useSubmit(
    async () => {
      const orderValue = parseOrder(order) ?? 0;
      try {
        const payload = { name: name.trim(), description: description.trim(), order: orderValue };
        return category ? await updateCategory(category.id, payload) : await createCategory(payload);
      } catch (err) {
        if (isCategoryNameTaken(err)) {
          setNameTaken(true);
          throw new Error(M.catNameTaken);
        }
        throw new Error(errorText(err, M.networkSave));
      }
    },
    { onSuccess: onSaved },
  );

  const submit = () => {
    const found: { name?: string; order?: string } = {};
    if (!name.trim()) found.name = M.catNameRequired;
    if (parseOrder(order) === null) found.order = M.catOrderInvalid;
    setErrs(found);
    if (found.name || found.order) return;
    setNameTaken(false);
    void sub.submit();
  };

  const nameError = errs.name ?? (nameTaken ? M.catNameTaken : undefined);
  const topError = nameTaken ? null : sub.error;

  return (
    <Modal
      title={editing ? M.catEdit : M.catAdd}
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.catCancel}
          </button>
          <button type="submit" form={formId} className="btn primary" disabled={sub.submitting} aria-busy={sub.submitting || undefined}>
            {sub.submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{M.catBusy}</span>
              </>
            ) : (
              primaryLabel(editing ? M.catUpdate : M.catCreate, sub.failed && !nameTaken)
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
        <Field
          label={M.catFieldName}
          required
          name="name"
          value={name}
          maxLength={NAME_MAX}
          autoFocus
          error={nameError}
          onChange={(v) => {
            setName(v);
            setNameTaken(false);
            if (errs.name) setErrs((e) => ({ ...e, name: undefined }));
          }}
        />
        {editing && <Field label={M.catFieldPath} name="slug" value={category.slug} onChange={() => undefined} disabled />}
        <Field as="textarea" label={M.catFieldDesc} name="description" value={description} onChange={setDescription} maxLength={DESC_MAX} counter rows={3} />
        <Field
          label={M.catFieldOrder}
          type="number"
          name="order"
          value={order}
          error={errs.order}
          onChange={(v) => {
            setOrder(v);
            if (errs.order) setErrs((e) => ({ ...e, order: undefined }));
          }}
        />
      </form>
    </Modal>
  );
}
