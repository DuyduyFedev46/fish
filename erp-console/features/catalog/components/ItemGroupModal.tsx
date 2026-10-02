"use client";

// Hộp "Thêm nhóm hàng" (ED-31 / F1o): Tên nhóm hàng * và Nhóm cha (không bắt buộc). Tên trùng: BE trả 400 `{name:[…]}`, hộp hiện
// "Tên này đã có." ngay dưới ô Tên. Lỗi khác: alert đỏ đầu form, giữ nguyên giá trị đã nhập, nút chính đổi "Thử lại".

import { useId, useState } from "react";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { createItemGroup } from "../api";
import { validateGroupName } from "../catalogModel";
import { CATALOG_MSG as M } from "../messages";
import type { ItemGroup } from "../types";
import s from "../catalog.module.css";

type Props = {
  /** Nhóm đã có, để chọn nhóm cha. */
  groups: ItemGroup[];
  onClose: () => void;
  onSaved: (group: ItemGroup) => void;
};

export function ItemGroupModal({ groups, onClose, onSaved }: Props) {
  const formId = useId();
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);

  const sub = useSubmit(() => createItemGroup({ name: name.trim(), parent: parent ? Number(parent) : null }), { onSuccess: onSaved });

  const submit = () => {
    const bad = validateGroupName(name);
    setNameError(bad);
    if (bad) return;
    void sub.submit();
  };

  const hasFieldErrors = Object.keys(sub.fieldErrors).length > 0;

  return (
    <Modal
      title={M.groupModalTitle}
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
              primaryLabel(M.groupSubmit, sub.failed)
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
        {sub.error && !hasFieldErrors && <FormAlert>{sub.error}</FormAlert>}
        <Field
          label={M.fieldGroupName}
          required
          name="name"
          value={name}
          onChange={(v) => {
            setName(v);
            setNameError(null);
            if (sub.fieldErrors.name && !sub.submitting) sub.reset();
          }}
          maxLength={120}
          error={nameError ?? sub.fieldErrors.name}
          autoFocus
        />
        <Field
          as="select"
          label={M.fieldGroupParent}
          name="parent"
          value={parent}
          onChange={setParent}
          options={[{ value: "", label: M.groupParentNone }, ...groups.map((g) => ({ value: String(g.id), label: g.name }))]}
          error={sub.fieldErrors.parent}
        />
      </form>
    </Modal>
  );
}
