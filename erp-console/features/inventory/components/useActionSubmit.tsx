"use client";

// Phần chung của các hộp thao tác lô (F1e, F1g, F1h, F1i): gửi một lần (useSubmit chặn bấm đúp), xét MÃ và câu lỗi của máy chủ
// (useSubmit chỉ giữ câu thông báo) để biết khi nào nên mời "Tải lại" số liệu, và chuyển xung đột phiên bản lên màn cha.
import { useEffect, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { useSubmit, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { isLotStateError, isStaleLotError } from "../lotView";


export type ActionProps = {
  /** Lô + số liệu ĐANG HIỂN THỊ trên màn. */
  row: import("../types").BatchApiRow;
  onClose: () => void;
  onDone: (message: string) => void;
  /** Đóng hộp và tải lại số thật. */
  onReload: () => void;
  onConflict: (conflict: SubmitConflict) => void;
};

export function useActionSubmit<T>(run: () => Promise<T>, onSuccess: (result: T) => void, onConflict: (c: SubmitConflict) => void) {
  const [stale, setStale] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const sub = useSubmit(
    async () => {
      setStale(false);
      setBlocked(false);
      try {
        return await run();
      } catch (err) {
        if (err instanceof ApiError) {
          setStale(isStaleLotError(err.code, err.message));
          setBlocked(isLotStateError(err.code));
        }
        throw err;
      }
    },
    { onSuccess },
  );
  const conflict = sub.conflict;
  useEffect(() => {
    if (conflict) onConflict(conflict);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conflict]);
  // Số liệu cũ: mời "Tải lại tồn" thay cho "Thử lại". Lỗi SAI TRẠNG THÁI lô (blocked) thì gửi lại cũng lỗi y hệt: khoá nút chính.
  // Lỗi tồn lệch (vượt tồn) vẫn cho sửa số rồi gửi lại.
  return { ...sub, failed: sub.failed && !stale, stale, blocked };
}

export function ActionError({ message, stale, busy, onReload, testId = "dialog-error" }: { message: string; stale: boolean; busy: boolean; onReload: () => void; testId?: string }) {
  return (
    <div data-testid={testId}>
      <FormAlert>{message}</FormAlert>
      {stale && (
        <button type="button" className="btn" onClick={onReload} disabled={busy}>
          Tải lại tồn
        </button>
      )}
    </div>
  );
}
