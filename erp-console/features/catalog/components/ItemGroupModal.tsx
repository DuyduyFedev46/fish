"use client";

// Hộp "Thêm nhóm hàng" (ED-31 / F1o): Tên nhóm hàng * và Nhóm cha (không bắt buộc). Tên trùng: BE trả 400 `{name:[…]}`, hộp hiện
// "Tên này đã có." ngay dưới ô Tên. Lỗi khác: alert đỏ đầu form, giữ nguyên giá trị đã nhập, nút chính đổi "Thử lại".

import { useId, useState } from "react";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { createItemGroup, updateItemGroup } from "../api";
import { validateGroupName, validateGroupSlug } from "../catalogModel";
import { CATALOG_MSG as M } from "../messages";
import type { ItemGroup } from "../types";
import s from "../catalog.module.css";

type Props = {
  /** Nhóm đã có, để chọn nhóm cha. */
  groups: ItemGroup[];
  /** Có thì là sửa nhóm này (chỉ đổi đường dẫn); không có là thêm nhóm mới. */
  editing?: ItemGroup;
  onClose: () => void;
  onSaved: (group: ItemGroup) => void;
};

export function ItemGroupModal({ groups, editing, onClose, onSaved }: Props) {
  const formId = useId();
  const [name, setName] = useState(editing?.name ?? "");
  const [parent, setParent] = useState(editing?.parent ? String(editing.parent) : "");
  const [slug, setSlug] = useState(editing?.slug ?? "");
  const [nameError, setNameError] = useState<string | null>(null);
  const [slugError, setSlugError] = useState<string | null>(null);

  const sub = useSubmit(
    () =>
      editing
        ? updateItemGroup(editing.id, { slug: slug.trim() })
        : createItemGroup({ name: name.trim(), parent: parent ? Number(parent) : null, ...(slug.trim() ? { slug: slug.trim() } : {}) }),
    { onSuccess: onSaved },
  );

  const submit = () => {
    const bad = editing ? null : validateGroupName(name);
    const badSlug = validateGroupSlug(slug, !!editing);
    setNameError(bad);
    setSlugError(badSlug);
    if (bad || badSlug) return;
    void sub.submit();
  };

  const hasFieldErrors = Object.keys(sub.fieldErrors).length > 0;

  return (
    <Modal
      title={editing ? M.groupEditTitle : M.groupModalTitle}
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
              primaryLabel(editing ? M.groupEditSubmit : M.groupSubmit, sub.failed)
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
          disabled={!!editing}
          autoFocus={!editing}
        />
        <Field
          as="select"
          label={M.fieldGroupParent}
          name="parent"
          value={parent}
          onChange={setParent}
          options={[{ value: "", label: M.groupParentNone }, ...groups.map((g) => ({ value: String(g.id), label: g.name }))]}
          error={sub.fieldErrors.parent}
          disabled={!!editing}
        />
        <Field
          label={M.fieldGroupSlug}
          name="slug"
          value={slug}
          onChange={(v) => {
            setSlug(v);
            setSlugError(null);
            if (sub.fieldErrors.slug && !sub.submitting) sub.reset();
          }}
          maxLength={80}
          error={slugError ?? sub.fieldErrors.slug}
          autoFocus={!!editing}
        />
        <p className="muted">{M.groupSlugHint}</p>
      </form>
    </Modal>
  );
}
