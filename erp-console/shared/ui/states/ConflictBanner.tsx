"use client";

// Banner vàng dưới header khi người khác vừa sửa bản ghi (UI-RULES §7): "Phiếu vừa được <tên> sửa lúc …. Tải lại để xem bản mới."
// + nút Tải lại. Bật khi lỗi là xung đột phiên bản: code STALE_STATE/STALE_VERSION hoặc 409 có updated_at (dùng `isConflictError`/`conflictOf` ở shared/ui/form/useSubmit).
// Tên và giờ là tuỳ chọn (BE có thể không kèm): thiếu thì nói chung "Người khác vừa sửa …". Tên ở đây là tên NHÂN VIÊN, không phải khách.

import { Icon } from "../Icon";
import { dateTime } from "@/shared/lib/format";

type Props = {
  /** Loại chứng từ viết thường, vd "phiếu", "đơn", "lô". Mặc định "bản ghi". */
  noun?: string;
  updatedByName?: string;
  updatedAt?: string;
  onReload: () => void;
  reloading?: boolean;
};

export function conflictMessage(noun: string, updatedByName?: string, updatedAt?: string): string {
  const who = updatedByName ? updatedByName : "Người khác";
  const when = updatedAt ? ` lúc ${dateTime(updatedAt)}` : "";
  const verb = updatedByName ? `vừa được ${who} sửa${when}` : `vừa được người khác sửa${when}`;
  return `${capitalize(noun)} ${verb}. Tải lại để xem bản mới.`;
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

export function ConflictBanner({ noun = "bản ghi", updatedByName, updatedAt, onReload, reloading = false }: Props) {
  return (
    <div className="alert-box warn" role="status" data-conflict-banner>
      <Icon name="sync_problem" />
      <span>{conflictMessage(noun, updatedByName, updatedAt)}</span>
      <button type="button" className="btn" onClick={onReload} disabled={reloading}>
        {reloading ? <Icon name="progress_activity" className="spin" /> : <Icon name="refresh" />}
        <span>Tải lại</span>
      </button>
    </div>
  );
}
