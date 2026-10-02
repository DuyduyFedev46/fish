"use client";

// Khung chung của mọi hộp thoại thao tác trên đơn / khoản tiền / phiếu hoàn (F2a–F2g): Modal + <form> (Enter gửi) + alert đỏ
// khi gửi lỗi (giữ nguyên giá trị đã nhập, nút chính đổi "Thử lại" — UI-RULES §6.6) + thanh nút [phụ … chính], nút chính
// nói rõ việc và số tiền. Xung đột phiên bản (409) KHÔNG hiện ở đây: màn mở hộp bật ConflictBanner qua `onConflict`.

import { useEffect, useId } from "react";
import { Modal } from "@/shared/ui/overlay/Modal";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import s from "../orders.module.css";

type Props = {
  title: string;
  onClose: () => void;
  submitting: boolean;
  failed: boolean;
  error: string | null;
  conflict?: SubmitConflict | null;
  /** Gọi một lần khi gặp xung đột (người khác vừa xử lý): màn bật ConflictBanner rồi đóng hộp. */
  onConflict?: (c: SubmitConflict) => void;
  /** Nhãn nút chính, vd "Xác nhận đã nhận 390.000 đ". */
  submitLabel: string;
  busyLabel?: string;
  /** Nút chính đỏ cho việc phá huỷ. */
  danger?: boolean;
  /** Khoá nút chính (số tiền vượt mức, chưa chọn…). */
  disabled?: boolean;
  backLabel?: string;
  /** Nút phụ quay lại bước trước (hộp nhiều bước); không có thì đóng hộp. */
  onBack?: () => void;
  onSubmit: () => void;
  size?: "sm" | "md";
  children: React.ReactNode;
};

export function ActionModal({
  title,
  onClose,
  submitting,
  failed,
  error,
  conflict,
  onConflict,
  submitLabel,
  busyLabel = "Đang gửi…",
  danger = false,
  disabled = false,
  backLabel = "Quay lại",
  onBack,
  onSubmit,
  size,
  children,
}: Props) {
  const formId = useId();
  useEffect(() => {
    if (conflict) onConflict?.(conflict);
  }, [conflict, onConflict]);
  return (
    <Modal
      title={title}
      onClose={onClose}
      busy={submitting}
      size={size}
      footer={
        <>
          <button type="button" className="btn" onClick={onBack ?? onClose} disabled={submitting}>
            {backLabel}
          </button>
          <button
            type="submit"
            form={formId}
            className={danger ? "btn danger solid" : "btn primary"}
            disabled={submitting || disabled}
            aria-busy={submitting || undefined}
          >
            {submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{busyLabel}</span>
              </>
            ) : (
              primaryLabel(submitLabel, failed)
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
          if (!submitting && !disabled) onSubmit();
        }}
      >
        {error && <FormAlert>{error}</FormAlert>}
        {children}
      </form>
    </Modal>
  );
}
