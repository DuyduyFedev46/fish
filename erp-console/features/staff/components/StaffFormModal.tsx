"use client";

// Hộp "Thêm nhân viên" (ED-37 / S41 / S48): Chủ tạo tài khoản, chọn một hay nhiều nhóm, đặt mật khẩu tạm.
// Ba bước trong MỘT hộp: biểu mẫu → (nếu có nhóm Chủ) hỏi lại → kết quả "Đã tạo" kèm tên đăng nhập + mật khẩu tạm để đọc/chép.
// Mật khẩu hai ô khác nhau → báo tại ô, KHÔNG gọi API (S48-AC3). Mọi lỗi khác do BE trả, hiện NGUYÊN VĂN ở đầu form (BE trả
// username/phone/password cùng một mã nên không gắn được vào từng ô); giá trị đã nhập giữ nguyên, nút chính đổi "Thử lại".
// Không giữ nháp (tên, SĐT, mật khẩu chỉ ở state của hộp: không storage, không URL, không log).

import { useId, useState } from "react";
import { ROLE } from "@/shared/lib/roles";
import { errorText } from "@/shared/lib/messages";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { createStaff } from "../api";
import { STAFF_MSG as M } from "../messages";
import type { StaffMember } from "../types";
import { GroupPicker } from "./GroupPicker";
import { PasswordField } from "./PasswordField";
import { Credentials } from "./parts";
import s from "../staff.module.css";

type Props = {
  onClose: () => void;
  /** Tạo xong (hộp vẫn mở để Chủ đọc mật khẩu tạm): màn cha báo và tải lại danh sách. */
  onCreated: (member: StaffMember) => void;
};

type Step = "form" | "confirm" | "done";

export function StaffFormModal({ onClose, onCreated }: Props) {
  const formId = useId();
  const [step, setStep] = useState<Step>("form");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [phone, setPhone] = useState("");
  const [groups, setGroups] = useState<string[]>([]);
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [mismatch, setMismatch] = useState(false);
  const [created, setCreated] = useState<StaffMember | null>(null);

  const sub = useSubmit(
    async () => {
      try {
        return await createStaff({ username: username.trim(), display_name: displayName.trim(), phone: phone.trim(), groups, password });
      } catch (err) {
        setStep("form");
        throw new Error(errorText(err));
      }
    },
    {
      onSuccess: (m) => {
        setCreated(m);
        setStep("done");
        onCreated(m);
      },
    },
  );

  const submit = () => {
    if (sub.submitting) return;
    if (password !== again) {
      setMismatch(true); // S48-AC3: không gọi API
      return;
    }
    if (groups.includes(ROLE.owner) && step !== "confirm") {
      setStep("confirm");
      return;
    }
    void sub.submit();
  };

  if (step === "done" && created) {
    return (
      <Modal
        title={M.createdTitle(created.username)}
        size="sm"
        onClose={onClose}
        footer={
          <button type="button" className="btn primary" onClick={onClose} data-autofocus>
            {M.done}
          </button>
        }
      >
        <div className={s.stack}>
          <div className={s.success} role="status">
            <span className={s.successIcon} aria-hidden="true">
              <Icon name="check" />
            </span>
            <p>{M.createdBody}</p>
          </div>
          <Credentials username={created.username} password={password} passwordLabel={M.tempPassword} />
        </div>
      </Modal>
    );
  }

  if (step === "confirm") {
    return (
      <Modal
        title={M.addOwnerTitle}
        size="sm"
        onClose={onClose}
        busy={sub.submitting}
        footer={
          <>
            <button type="button" className="btn" onClick={() => setStep("form")} disabled={sub.submitting} data-autofocus>
              {M.back}
            </button>
            <button type="button" className="btn danger solid" onClick={() => void sub.submit()} disabled={sub.submitting} aria-busy={sub.submitting || undefined}>
              {sub.submitting ? (
                <>
                  <Icon name="progress_activity" className="spin" />
                  <span>{M.addBusy}</span>
                </>
              ) : (
                primaryLabel(M.addOwnerOk, sub.failed)
              )}
            </button>
          </>
        }
      >
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        <p className={s.confirmBody}>{M.addOwnerBody(username.trim())}</p>
        <ul className={s.consequences}>
          <li>
            <Icon name="payments" />
            <span>Toàn quyền tiền, giá vốn, lãi lỗ.</span>
          </li>
          <li>
            <Icon name="manage_accounts" />
            <span>Quản lý nhân viên.</span>
          </li>
        </ul>
      </Modal>
    );
  }

  return (
    <Modal
      title={M.addTitle}
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
                <span>{M.addBusy}</span>
              </>
            ) : (
              primaryLabel(M.addSubmit, sub.failed)
            )}
          </button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        className={s.form}
        aria-label={M.addTitle}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        <p className={s.sectionNote}>{M.fieldUsernameHelp}</p>
        <Field label={M.fieldUsernameInput} required name="username" value={username} onChange={setUsername} maxLength={150} disabled={sub.submitting} autoFocus />
        <Field label={M.fieldNameInput} name="display_name" value={displayName} onChange={setDisplayName} maxLength={150} disabled={sub.submitting} />
        <Field label={M.fieldPhoneInput} required type="tel" name="phone" value={phone} onChange={setPhone} maxLength={32} disabled={sub.submitting} />
        <div className={s.formSection}>
          <GroupPicker value={groups} onChange={setGroups} disabled={sub.submitting} describedBy={groups.length === 0 ? `${formId}-g` : undefined} />
          {groups.length === 0 && (
            <p className={s.sectionNote} id={`${formId}-g`}>
              {M.noGroupHint}
            </p>
          )}
        </div>
        <div className={s.formSection}>
          <PasswordField
            id="sc-password"
            label={M.tempPassword}
            value={password}
            onChange={(v) => {
              setPassword(v);
              setMismatch(false);
            }}
            again={again}
            onAgainChange={(v) => {
              setAgain(v);
              setMismatch(false);
            }}
            mismatch={mismatch}
            username={username}
            disabled={sub.submitting}
          />
        </div>
      </form>
    </Modal>
  );
}
