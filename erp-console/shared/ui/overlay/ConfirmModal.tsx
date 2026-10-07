"use client";

// Hộp xác nhận một việc không quay lại được (UI-RULES §6.4): nói rõ việc + hậu quả, nút chính ghi đúng việc ("Huỷ phiếu hoàn tiền",
// không phải "Đồng ý"), nút phụ "Quay lại". Gửi lỗi → alert đỏ đầu hộp (câu của BE qua `errorText`), nút chính đổi "Thử lại";
// xung đột phiên bản → ConflictBanner kèm "Tải lại". Dùng chung cho các việc một bước (huỷ phiếu, trả về nháp, nhờ người xử lý…).

import { FormAlert } from "../form/FormAlert";
import { isConflictError, primaryLabel, useSubmit } from "../form/useSubmit";
import { Icon } from "../Icon";
import { ConflictBanner } from "../states/ConflictBanner";
import { Modal } from "./Modal";

type Props<T> = {
  title: string;
  /** Nhãn nút chính, nói đúng việc. */
  confirmLabel: string;
  /** Nhãn khi đang gửi. */
  busyLabel?: string;
  backLabel?: string;
  /** Nút chính đỏ cho việc phá huỷ. */
  danger?: boolean;
  /** Việc cần làm; ném lỗi thì hiện alert. */
  run: () => Promise<T>;
  onDone: (result: T) => void;
  onClose: () => void;
  /** Đổi lỗi thành câu cho người dùng (mặc định: `message` của lỗi). Lỗi xung đột phiên bản đi riêng, không qua đây. */
  errorText?: (err: unknown) => string;
  /** Gọi khi gửi lỗi (vd màn tải lại chứng từ vì trạng thái đã đổi); không bắt buộc. */
  onError?: (err: unknown) => void;
  /** Bấm "Tải lại" ở banner xung đột. */
  onReload?: () => void;
  /** Loại chứng từ viết thường cho banner xung đột, vd "phiếu". */
  noun?: string;
  /** Khoá nút chính (chưa đủ điều kiện). */
  disabled?: boolean;
  children: React.ReactNode;
};

export function ConfirmModal<T>({
  title,
  confirmLabel,
  busyLabel = "Đang gửi…",
  backLabel = "Quay lại",
  danger = false,
  run,
  onDone,
  onClose,
  errorText,
  onError,
  onReload,
  noun = "phiếu",
  disabled = false,
  children,
}: Props<T>) {
  const sub = useSubmit(
    async () => {
      try {
        return await run();
      } catch (err) {
        onError?.(err);
        if (isConflictError(err) || !errorText) throw err;
        throw new Error(errorText(err));
      }
    },
    { onSuccess: onDone },
  );
  const locked = sub.submitting || sub.conflict !== null;
  return (
    <Modal
      title={title}
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {backLabel}
          </button>
          <button
            type="button"
            className={`btn ${danger ? "danger solid" : "primary"}`}
            onClick={() => void sub.submit()}
            disabled={locked || disabled}
            aria-busy={sub.submitting || undefined}
          >
            {sub.submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{busyLabel}</span>
              </>
            ) : (
              primaryLabel(confirmLabel, sub.failed && !sub.conflict)
            )}
          </button>
        </>
      }
    >
      <div data-confirm-body>
        {sub.conflict && (
          <ConflictBanner noun={noun} updatedByName={sub.conflict.updatedByName} updatedAt={sub.conflict.updatedAt} onReload={onReload ?? onClose} />
        )}
        {sub.error && !sub.conflict && <FormAlert>{sub.error}</FormAlert>}
        {children}
      </div>
    </Modal>
  );
}
