"use client";

// Hộp xác nhận trước khi LƯU (PV-09, PV-10): mở rộng dữ liệu khách → cảnh báo kèm danh sách nhân viên, nút "Tôi hiểu, lưu";
// thu hẹp → ghi chú số dòng đang làm dở; việc tắt làm hỏng màn → câu hậu quả. Dùng chung W3i (bản nháp) và W3h (400 CUSTOMER_DATA_WIDENING_UNCONFIRMED).
// Chỉ hiện tên NHÂN VIÊN và mã/nhãn đối tượng, không có dữ liệu khách. Esc/Huỷ không gửi gì (focus, Esc do Modal chung lo).

import { groupLabel } from "@/shared/lib/groups";
import { errorText } from "@/shared/lib/messages";
import { Icon } from "@/shared/ui/Icon";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { PERM_MSG as M, SCOPE_NOUN } from "../messages";
import type { ScopePreview } from "../types";
import s from "../permissions.module.css";

type Props = {
  groupLabelText: string;
  /** Kết quả xem trước; null khi chưa xem trước được (lỗi mạng) mà vẫn có câu hậu quả phải hỏi. */
  preview: ScopePreview | null;
  /** Câu hậu quả khi tắt việc làm hỏng màn. */
  breaking?: string[];
  /** Nhãn đối tượng phạm vi theo mã. */
  objectLabel: (key: string) => string;
  /** Gửi PUT có xác nhận; ném lỗi thì hộp hiện alert và giữ mở. */
  run: () => Promise<void>;
  onClose: () => void;
};

export function ConfirmSaveModal({ groupLabelText, preview, breaking = [], objectLabel, run, onClose }: Props) {
  const widens = preview?.widens_customer_data === true;
  const narrowed = (preview?.narrowed ?? []).filter((n) => n.rows_losing_access > 0);
  return (
    <ConfirmModal
      title={widens ? M.widenTitle : M.saveConfirmTitle}
      confirmLabel={widens ? M.widenOk : M.saveConfirmOk}
      busyLabel={M.widenBusy}
      backLabel={M.confirmCancel}
      danger={false}
      run={run}
      onDone={onClose}
      onClose={onClose}
      errorText={(err) => errorText(err, M.saveFailed)}
    >
      <div className={s.stack} data-testid="confirm-save-body">
        <p className={s.confirmBody}>{M.confirmGroup(groupLabelText)}</p>
        {widens && preview && (
          <div className={s.widenBox} role="alert">
            <Icon name="warning" />
            <div className={s.widenText}>
              <p className={s.confirmBody}>
                <strong>{preview.message}</strong>
              </p>
              {preview.widened.length > 0 && <p className={s.confirmBody}>{M.widenObjects(preview.widened.map((w) => objectLabel(w.key)).join(", "))}</p>}
              {preview.affected_members.length > 0 && (
                <>
                  <p className={s.confirmBody}>{M.widenWho}</p>
                  <ul className={s.nameList}>
                    {preview.affected_members.map((m) => (
                      <li key={m.id}>{m.display_name}</li>
                    ))}
                  </ul>
                </>
              )}
              <p className={s.confirmBody}>{M.widenHint}</p>
            </div>
          </div>
        )}
        {preview && preview.already_wider_elsewhere.length > 0 && (
          <ul className={s.noteList}>
            {preview.already_wider_elsewhere.map((w) => (
              <li key={`${w.id}-${w.key}`}>{M.alreadyWider(w.display_name, objectLabel(w.key), groupLabel(w.via_group))}</li>
            ))}
          </ul>
        )}
        {narrowed.length > 0 && (
          <ul className={s.noteList}>
            {narrowed.map((n) => (
              <li key={n.key}>{M.narrowedRows(n.rows_losing_access, SCOPE_NOUN[n.key] ?? "dòng")}</li>
            ))}
          </ul>
        )}
        {breaking.length > 0 && (
          <ul className={s.noteList}>
            {breaking.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        )}
        {!preview && <p className={s.confirmBody}>{M.previewFailedNote}</p>}
      </div>
    </ConfirmModal>
  );
}
