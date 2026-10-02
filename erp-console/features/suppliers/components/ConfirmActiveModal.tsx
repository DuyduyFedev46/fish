"use client";

// Hộp hỏi lại trước khi đổi trạng thái hợp tác (ED-22): "Ngừng hợp tác" là việc phá huỷ nhẹ nên nút đỏ và nêu hậu quả; "Bật lại hợp tác"
// là nút chính thường. Cả hai là một PATCH `is_active` (BE không cho xoá nhà cung cấp). Lỗi → giữ hộp mở, nút chính đổi "Thử lại".

import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { setSupplierActive } from "../api";
import { SUPPLIERS_MSG as M } from "../messages";
import { saveErrorMessage } from "../suppliersModel";
import type { Supplier } from "../types";
import s from "../suppliers.module.css";

type Props = {
  supplier: Supplier;
  /** true = đang hợp tác, người dùng muốn NGỪNG; false = đang ngừng, muốn BẬT LẠI. */
  deactivating: boolean;
  onClose: () => void;
  onDone: (saved: Supplier) => void;
};

export function ConfirmActiveModal({ supplier, deactivating, onClose, onDone }: Props) {
  const sub = useSubmit(
    async () => {
      try {
        return await setSupplierActive(supplier.id, !deactivating);
      } catch (err) {
        throw new Error(saveErrorMessage(err));
      }
    },
    { onSuccess: onDone },
  );
  const title = deactivating ? M.confirmDeactivateTitle : M.confirmReactivateTitle;
  const ok = deactivating ? M.confirmDeactivateOk : M.confirmReactivateOk;
  return (
    <Modal
      title={title}
      size="sm"
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.cancel}
          </button>
          <button
            type="button"
            className={`btn ${deactivating ? "danger solid" : "primary"}`}
            onClick={() => void sub.submit()}
            disabled={sub.submitting}
            aria-busy={sub.submitting || undefined}
          >
            {sub.submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{M.confirmBusy}</span>
              </>
            ) : (
              primaryLabel(ok, sub.failed)
            )}
          </button>
        </>
      }
    >
      {sub.error && <FormAlert>{sub.error}</FormAlert>}
      <p className={s.confirmBody}>{deactivating ? M.confirmDeactivateBody : M.confirmReactivateBody}</p>
    </Modal>
  );
}
