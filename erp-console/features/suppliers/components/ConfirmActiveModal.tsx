"use client";

// Hộp hỏi lại trước khi đổi trạng thái hợp tác (ED-22): "Ngừng hợp tác" là việc phá huỷ nhẹ nên nút đỏ và nêu hậu quả; "Bật lại hợp tác"
// là nút chính thường. Cả hai là một PATCH `is_active` (BE không cho xoá nhà cung cấp). Lỗi → giữ hộp mở, nút chính đổi "Thử lại".
// Dùng `shared/ui/overlay/ConfirmModal` (Lô 17b CLN-2).

import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
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
  return (
    <ConfirmModal
      title={deactivating ? M.confirmDeactivateTitle : M.confirmReactivateTitle}
      confirmLabel={deactivating ? M.confirmDeactivateOk : M.confirmReactivateOk}
      busyLabel={M.confirmBusy}
      backLabel={M.cancel}
      danger={deactivating}
      run={() => setSupplierActive(supplier.id, !deactivating)}
      errorText={saveErrorMessage}
      onDone={onDone}
      onClose={onClose}
      noun="nhà cung cấp"
    >
      <p className={s.confirmBody}>{deactivating ? M.confirmDeactivateBody : M.confirmReactivateBody}</p>
    </ConfirmModal>
  );
}
