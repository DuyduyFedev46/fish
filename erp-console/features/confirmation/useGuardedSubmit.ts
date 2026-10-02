"use client";

// Gửi form của màn Gọi xác nhận = `useSubmit` + giữ câu 409 STALE_STATE của BE ("Đơn đã bị huỷ — tải lại màn hình.").
// `useSubmit` gộp STALE_STATE vào `conflict` (mất câu của BE); ở đây hộp cần hiện đúng câu đó kèm nút "Tải lại".
// Các 409 khác (vd CLAIMED: đang có người khác gọi) là lỗi thường: `useSubmit` đã đưa câu của BE vào `error`.
import { useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { useSubmit } from "@/shared/ui/form/useSubmit";
import { isStaleStateError } from "./api";

export const STALE_FALLBACK = "Đơn đã đổi trạng thái. Tải lại màn hình để thấy bản mới.";

export function useGuardedSubmit<T>(run: () => Promise<T>, opts: { onSuccess?: (result: T) => void } = {}) {
  const [stale, setStale] = useState<string | null>(null);
  const sub = useSubmit(async () => {
    setStale(null);
    try {
      return await run();
    } catch (err) {
      if (isStaleStateError(err)) setStale((err as ApiError).message || STALE_FALLBACK);
      throw err;
    }
  }, opts);
  return { ...sub, stale, conflict: stale ? null : sub.conflict };
}
