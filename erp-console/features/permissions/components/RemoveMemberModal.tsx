"use client";

// Bỏ một người khỏi nhóm (ED-40): PUT /api/staff/<id>/groups/ với tập nhóm còn lại (nhóm khác của người đó). Hỏi lại, nêu hậu quả.
// Bỏ khỏi nhóm Chủ nói rõ mất toàn quyền. BE giữ luật (phải còn một Chủ đang làm, không tự hạ quyền mình): lỗi hiện nguyên văn.

import { setStaffGroups } from "@/features/staff/api";
import { errorText } from "@/shared/lib/messages";
import { ROLE } from "@/shared/lib/roles";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { PERM_MSG as M } from "../messages";
import type { GroupMember } from "../types";
import s from "../permissions.module.css";

type Props = {
  member: GroupMember;
  groupCode: string;
  groupLabelText: string;
  onClose: () => void;
  onDone: () => void;
};

export function RemoveMemberModal({ member, groupCode, groupLabelText, onClose, onDone }: Props) {
  const who = member.display_name || member.username;
  return (
    <ConfirmModal
      title={M.removeTitle(who, groupLabelText)}
      confirmLabel={M.removeOk}
      busyLabel={M.removeBusy}
      danger
      run={() => setStaffGroups(member.id, member.other_groups)}
      onDone={onDone}
      onClose={onClose}
      errorText={(err) => errorText(err, M.saveFailed)}
    >
      <p className={s.confirmBody}>{groupCode === ROLE.owner ? M.removeOwnerBody : M.removeBody}</p>
    </ConfirmModal>
  );
}
