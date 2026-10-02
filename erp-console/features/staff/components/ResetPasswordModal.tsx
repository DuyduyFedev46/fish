"use client";

// Hộp "Đặt lại mật khẩu" (ED-38 / S42 / S48): Chủ đặt mật khẩu tạm mới cho nhân viên, rồi đọc/chép cho họ. Hai bước trong một hộp: biểu mẫu → kết quả.
// Ô trống → báo tại ô; hai ô khác nhau → báo tại ô; cả hai KHÔNG gọi API. Lỗi khác do BE trả (quy tắc mật khẩu) hiện NGUYÊN VĂN ở đầu form.
// Mật khẩu chỉ ở state của hộp: không storage, không URL, không log. BE xoá token cũ của người đó nên mọi máy bị đăng xuất.

import { useId, useState } from "react";
import { errorText } from "@/shared/lib/messages";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { resetStaffPassword } from "../api";
import { STAFF_MSG as M } from "../messages";
import { whoOf } from "../staffModel";
import type { StaffMember } from "../types";
import { PasswordField } from "./PasswordField";
import { Credentials } from "./parts";
import s from "../staff.module.css";

type Props = {
  member: StaffMember;
  onClose: () => void;
  /** Đặt xong (hộp vẫn mở để đọc mật khẩu): màn cha báo. */
  onDone: () => void;
};

export function ResetPasswordModal({ member: m, onClose, onDone }: Props) {
  const formId = useId();
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [mismatch, setMismatch] = useState(false);
  const [missing, setMissing] = useState<"main" | "again" | null>(null);
  const [done, setDone] = useState(false);
  const who = whoOf(m);

  const sub = useSubmit(
    async () => {
      try {
        return await resetStaffPassword(m.id, password);
      } catch (err) {
        throw new Error(errorText(err));
      }
    },
    {
      onSuccess: () => {
        setDone(true);
        onDone();
      },
    },
  );

  const submit = () => {
    if (sub.submitting) return;
    const empty = !password ? "main" : !again ? "again" : null;
    setMissing(empty);
    if (empty) {
      document.getElementById(empty === "main" ? "sr-password" : "sr-password-again")?.focus();
      return;
    }
    if (password !== again) {
      setMismatch(true); // S48-AC3: không gọi API
      return;
    }
    void sub.submit();
  };

  if (done) {
    return (
      <Modal
        title={M.resetDoneTitle(who)}
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
            <p>{M.resetDoneBody}</p>
          </div>
          <Credentials password={password} passwordLabel={M.newPassword} />
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      title={`${M.resetTitle} · ${m.display_name || m.username}`}
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
              primaryLabel(M.resetTitle, sub.failed)
            )}
          </button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        className={s.form}
        aria-label={M.resetTitle}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        <div className="alert-box info" role="note">
          <Icon name="info" />
          <span>{M.resetNote(m.username)}</span>
        </div>
        <PasswordField
          id="sr-password"
          label={M.newPassword}
          autoFocus
          value={password}
          onChange={(v) => {
            setPassword(v);
            setMismatch(false);
            if (missing === "main") setMissing(null);
          }}
          again={again}
          onAgainChange={(v) => {
            setAgain(v);
            setMismatch(false);
            if (missing === "again") setMissing(null);
          }}
          mismatch={mismatch}
          missing={missing}
          username={m.username}
          disabled={sub.submitting}
        />
      </form>
    </Modal>
  );
}
