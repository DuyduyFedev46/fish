"use client";

// Hộp hỏi lại "Cho nghỉ" / "Cho làm lại" (ED-38 / S42). Cho nghỉ là việc nặng (khoá tài khoản, đăng xuất mọi máy) nên nút đỏ và nêu hậu quả;
// "Cho làm lại" là nút chính thường. Luật (không tự cho mình nghỉ, Chủ cuối cùng, người đang giao hàng…) do BE quyết; lỗi hiện NGUYÊN VĂN, hộp giữ mở.

import { errorText } from "@/shared/lib/messages";
import { Icon } from "@/shared/ui/Icon";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { deactivateStaff, reactivateStaff } from "../api";
import { STAFF_MSG as M } from "../messages";
import { deliveringBlock, whoOf } from "../staffModel";
import type { StaffDelivering, StaffMember } from "../types";
import { Consequence } from "./parts";
import s from "../staff.module.css";

type Props = {
  member: StaffMember;
  /** true = đang làm, muốn cho NGHỈ; false = đang nghỉ, muốn cho LÀM LẠI. */
  deactivating: boolean;
  /** Phiếu Đang giao đã tải ở trang hồ sơ; null = chưa có (thiếu quyền xem phiếu, lỗi, đang tải) → để BE quyết. */
  delivering?: StaffDelivering[] | null;
  onClose: () => void;
  onDone: () => void;
};

export function ActiveModal({ member: m, deactivating, delivering = null, onClose, onDone }: Props) {
  const who = whoOf(m);
  const block = deactivating ? deliveringBlock(delivering) : null;
  return (
    <ConfirmModal
      title={deactivating ? M.deactivateTitle(who) : M.reactivateTitle(who)}
      confirmLabel={deactivating ? M.deactivateOk : M.reactivateOk}
      busyLabel={M.busy}
      backLabel={M.cancel}
      danger={deactivating}
      disabled={block !== null}
      run={() => (deactivating ? deactivateStaff(m.id) : reactivateStaff(m.id))}
      onDone={onDone}
      onClose={onClose}
      errorText={(err) => errorText(err)}
      noun="tài khoản"
    >
      {block && (
        <p className="alert-box err" role="alert" data-delivering-block>
          <Icon name="local_shipping" />
          <span>{block}</span>
        </p>
      )}
      {/* Đang bị chặn thì không liệt kê hậu quả "bị khoá ngay": việc đó sẽ không xảy ra. */}
      {block ? null : deactivating ? (
        <ul className={s.consequences}>
          <Consequence icon="lock">{M.deactivateLock}</Consequence>
          <Consequence icon="description">{M.deactivateKeep}</Consequence>
          <Consequence icon="undo">{M.deactivateUndo}</Consequence>
        </ul>
      ) : (
        <p className={s.confirmBody}>{M.reactivateBody}</p>
      )}
    </ConfirmModal>
  );
}
