"use client";

// Dòng thời gian của nhà cung cấp (guidance `supplier`, cùng quyền xem nhà cung cấp). Lỗi không chặn trang: cột phải báo "Chưa tải được"
// kèm nút Thử lại. Không đưa `why.br`, không đưa dữ liệu cá nhân ra ngoài trang này.

import { useCallback, useEffect, useState } from "react";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import type { TimelineEntry } from "@/shared/ui/detail/Timeline";
import { getSupplierTimeline } from "./api";

export type SupplierTimelineState = {
  entries: TimelineEntry[];
  truncated: boolean;
  status: "loading" | "ok" | "error";
  retry: () => void;
};

/** `version` đổi (sau khi sửa thông tin) → tải lại để thấy dòng "Cập nhật nhà cung cấp" mới. */
export function useSupplierTimeline(id: number, version: number): SupplierTimelineState {
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [truncated, setTruncated] = useState(false);
  const [status, setStatus] = useState<SupplierTimelineState["status"]>("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const c = new AbortController();
    getSupplierTimeline(id, c.signal)
      .then((g) => {
        setEntries(toTimelineEntries(g.timeline));
        setTruncated(!!g.timeline_truncated);
        setStatus("ok");
      })
      .catch(() => {
        if (!c.signal.aborted) setStatus((s) => (s === "ok" ? "ok" : "error"));
      });
    return () => c.abort();
  }, [id, version, attempt]);

  const retry = useCallback(() => {
    setStatus("loading");
    setAttempt((n) => n + 1);
  }, []);
  return { entries, truncated, status, retry };
}
