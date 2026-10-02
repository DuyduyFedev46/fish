"use client";

// Hộp "Sửa hồ sơ" (ED-38 / S42): đổi tên hiển thị và số điện thoại (PATCH một phần). Tên đăng nhập không đổi được.
// Chỉ gửi trường THẬT SỰ đổi; không đổi gì → báo "Chưa đổi gì để lưu", không gọi API. Lỗi BE hiện NGUYÊN VĂN ở đầu form, giữ giá trị đã nhập.
// Số điện thoại của nhân viên chỉ ở state của hộp (không storage, không URL, không log).

import { useId, useState } from "react";
import { errorText } from "@/shared/lib/messages";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { updateStaff } from "../api";
import { STAFF_MSG as M } from "../messages";
import type { StaffMember, StaffProfileInput } from "../types";
import s from "../staff.module.css";

type Props = {
  member: StaffMember;
  onClose: () => void;
  onSaved: (member: StaffMember) => void;
};

export function EditProfileModal({ member: m, onClose, onSaved }: Props) {
  const formId = useId();
  const [name, setName] = useState(m.display_name);
  const [phone, setPhone] = useState(m.phone);
  const [nothing, setNothing] = useState(false);

  const changes = (): StaffProfileInput => {
    const out: StaffProfileInput = {};
    if (name.trim() !== m.display_name) out.display_name = name.trim();
    if (phone.trim() !== m.phone) out.phone = phone.trim();
    return out;
  };

  const sub = useSubmit(
    async () => {
      try {
        return await updateStaff(m.id, changes());
      } catch (err) {
        throw new Error(errorText(err));
      }
    },
    { onSuccess: onSaved },
  );

  const submit = () => {
    if (sub.submitting) return;
    if (Object.keys(changes()).length === 0) {
      setNothing(true);
      return;
    }
    void sub.submit();
  };

  return (
    <Modal
      title={M.editTitle}
      size="sm"
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
        aria-label={M.editTitle}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        {nothing && <FormAlert kind="warn">{M.editNothing}</FormAlert>}
        <p className={s.readonly}>
          {M.fieldUsername} <code>{m.username}</code> {M.usernameFixed}
        </p>
        <Field
          label={M.fieldNameInput}
          name="display_name"
          value={name}
          onChange={(v) => {
            setName(v);
            setNothing(false);
          }}
          maxLength={150}
          disabled={sub.submitting}
          autoFocus
        />
        <Field
          label={M.fieldPhoneInput}
          required
          type="tel"
          name="phone"
          value={phone}
          onChange={(v) => {
            setPhone(v);
            setNothing(false);
          }}
          maxLength={32}
          disabled={sub.submitting}
        />
      </form>
    </Modal>
  );
}
