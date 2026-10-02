"use client";

// Hộp "Đổi nhóm" (ED-38 / S42): đánh dấu nhóm của một nhân viên rồi "Lưu nhóm" (PUT thay cả tập nhóm). Dưới ô chọn có dòng "Thêm: … / Bỏ: …"
// để thấy đúng cái sẽ đổi; chưa đổi gì thì nút Lưu khoá. Thêm hoặc bỏ nhóm Chủ là bước nguy hiểm → hỏi lại, nêu hậu quả, nút đỏ.
// Luật ai được gán nhóm nào, người Chủ cuối cùng… do BE quyết; lỗi hiện NGUYÊN VĂN, hộp giữ mở với giá trị đã chọn.

import { useId, useState } from "react";
import { errorText } from "@/shared/lib/messages";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { setStaffGroups } from "../api";
import { STAFF_MSG as M } from "../messages";
import { groupsDiff, namesOf, ownerChange, whoOf } from "../staffModel";
import type { SetGroupsResult, StaffMember } from "../types";
import { GroupPicker } from "./GroupPicker";
import s from "../staff.module.css";

type Props = {
  member: StaffMember;
  onClose: () => void;
  onSaved: (result: SetGroupsResult) => void;
};

export function GroupsModal({ member: m, onClose, onSaved }: Props) {
  const formId = useId();
  const [groups, setGroups] = useState<string[]>(m.groups);
  const [confirming, setConfirming] = useState(false);
  const diff = groupsDiff(m.groups, groups);
  const unchanged = diff.added.length === 0 && diff.removed.length === 0;
  const owner = ownerChange(diff);
  const who = whoOf(m);

  const sub = useSubmit(
    async () => {
      try {
        return await setStaffGroups(m.id, groups);
      } catch (err) {
        setConfirming(false);
        throw new Error(errorText(err));
      }
    },
    { onSuccess: onSaved },
  );

  const submit = () => {
    if (sub.submitting || unchanged) return;
    if (owner && !confirming) {
      setConfirming(true);
      return;
    }
    void sub.submit();
  };

  if (confirming && owner) {
    const grant = owner === "grant";
    return (
      <Modal
        title={grant ? M.grantOwnerTitle : M.revokeOwnerTitle}
        size="sm"
        onClose={onClose}
        busy={sub.submitting}
        footer={
          <>
            <button type="button" className="btn" onClick={() => setConfirming(false)} disabled={sub.submitting} data-autofocus>
              {M.back}
            </button>
            <button type="button" className="btn danger solid" onClick={() => void sub.submit()} disabled={sub.submitting} aria-busy={sub.submitting || undefined}>
              {sub.submitting ? (
                <>
                  <Icon name="progress_activity" className="spin" />
                  <span>{M.busy}</span>
                </>
              ) : (
                primaryLabel(grant ? M.grantOwnerOk : M.revokeOwnerOk, sub.failed)
              )}
            </button>
          </>
        }
      >
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        <p className={s.confirmBody}>{grant ? M.grantOwnerBody(who) : M.revokeOwnerBody(who)}</p>
      </Modal>
    );
  }

  return (
    <Modal
      title={`${M.groupsTitle2} · ${m.display_name || m.username}`}
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.cancel}
          </button>
          <button
            type="submit"
            form={formId}
            className="btn primary"
            disabled={sub.submitting || unchanged}
            aria-busy={sub.submitting || undefined}
            title={unchanged ? M.groupsNothingHint : undefined}
          >
            {sub.submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{M.busy}</span>
              </>
            ) : (
              primaryLabel(M.groupsSubmit, sub.failed)
            )}
          </button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        className={s.form}
        aria-label={M.groupsTitle2}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        <GroupPicker value={groups} onChange={setGroups} disabled={sub.submitting} legend={`Nhóm của ${who}`} autoFocus />
        <div className={s.diff} aria-live="polite">
          {unchanged ? (
            <span>{M.groupsNothing}</span>
          ) : (
            <>
              {diff.added.length > 0 && (
                <span>
                  {M.groupsAdd}: <b>{namesOf(diff.added)}</b>
                </span>
              )}
              {diff.removed.length > 0 && (
                <span>
                  {M.groupsRemove}: <b>{namesOf(diff.removed)}</b>
                </span>
              )}
            </>
          )}
        </div>
        {groups.length === 0 && <p className={s.sectionNote}>{M.groupsNoneNote}</p>}
        <p className={s.sectionNote}>{M.groupsEffectNote}</p>
      </form>
    </Modal>
  );
}
