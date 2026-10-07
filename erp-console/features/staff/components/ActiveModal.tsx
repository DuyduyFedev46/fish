"use client";

// Hộp hỏi lại "Cho nghỉ" / "Cho làm lại" (ED-38 / S42). Cho nghỉ là việc nặng (khoá tài khoản, đăng xuất mọi máy) nên nút đỏ và nêu hậu quả;
// "Cho làm lại" là nút chính thường. Luật (không tự cho mình nghỉ, Chủ cuối cùng, người đang giao hàng…) do BE quyết; lỗi hiện NGUYÊN VĂN, hộp giữ mở.

import { useEffect, useState } from "react";
import { errorText } from "@/shared/lib/messages";
import { Icon } from "@/shared/ui/Icon";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { deactivateStaff, fetchStaffDeliveringCount, reactivateStaff } from "../api";
import { STAFF_MSG as M } from "../messages";
import { deliveringBlock, whoOf } from "../staffModel";
import type { StaffDelivering, StaffMember } from "../types";
import { Consequence } from "./parts";
import s from "../staff.module.css";

type Props = {
  member: StaffMember;
  /** true = đang làm, muốn cho NGHỈ; false = đang nghỉ, muốn cho LÀM LẠI. */
  deactivating: boolean;
  /** Người xem kiểm được phiếu Đang giao của người này (nhóm giao hàng + quyền xem phiếu giao). Hộp tải phiếu MỚI mỗi lần mở, không dùng ảnh chụp cũ. */
  checkDelivering?: boolean;
  onClose: () => void;
  onDone: () => void;
};

type Fresh = { status: "loading" } | { status: "error" } | { status: "ok"; notes: StaffDelivering[]; count: number };

export function ActiveModal({ member: m, deactivating, checkDelivering = false, onClose, onDone }: Props) {
  const who = whoOf(m);
  const [fresh, setFresh] = useState<Fresh>(deactivating && checkDelivering ? { status: "loading" } : { status: "error" });
  useEffect(() => {
    if (!deactivating || !checkDelivering) return;
    const ac = new AbortController();
    fetchStaffDeliveringCount(m.id, ac.signal)
      .then((r) => setFresh({ status: "ok", ...r }))
      .catch(() => {
        if (!ac.signal.aborted) setFresh({ status: "error" }); // không kiểm được thì để BE quyết khi bấm xác nhận
      });
    return () => ac.abort();
  }, [m.id, deactivating, checkDelivering]);
  const block = deactivating && fresh.status === "ok" ? deliveringBlock(fresh.notes, fresh.count) : null;
  const checking = deactivating && fresh.status === "loading";
  return (
    <ConfirmModal
      title={deactivating ? M.deactivateTitle(who) : M.reactivateTitle(who)}
      confirmLabel={deactivating ? M.deactivateOk : M.reactivateOk}
      busyLabel={M.busy}
      backLabel={M.cancel}
      danger={deactivating}
      disabled={block !== null || checking}
      run={() => (deactivating ? deactivateStaff(m.id) : reactivateStaff(m.id))}
      onDone={onDone}
      onClose={onClose}
      errorText={(err) => errorText(err)}
      noun="tài khoản"
    >
      {checking && (
        <p className={s.confirmBody} role="status" data-delivering-checking>
          Đang kiểm tra phiếu đang giao…
        </p>
      )}
      {block && (
        <p className="alert-box err" role="alert" data-delivering-block>
          <Icon name="local_shipping" />
          <span>{block}</span>
        </p>
      )}
      {/* Đang bị chặn thì không liệt kê hậu quả "bị khoá ngay": việc đó sẽ không xảy ra. */}
      {block || checking ? null : deactivating ? (
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
