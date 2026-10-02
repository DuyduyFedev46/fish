"use client";

// Dòng thời gian của phiếu hàng hoàn (guidance `return`, chỉ timeline). Lỗi không chặn trang: cột phải báo "Chưa tải được"
// kèm nút Thử lại. `version` đổi (sau khi duyệt) → tải lại để thấy dòng mới.

import { useCallback, useEffect, useState } from "react";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import type { TimelineEntry } from "@/shared/ui/detail/Timeline";
import { getReturnTimeline } from "./api";

export type ReturnTimelineState = {
  entries: TimelineEntry[];
  truncated: boolean;
  status: "loading" | "ok" | "error";
  retry: () => void;
};

export function useReturnTimeline(id: number, version: number): ReturnTimelineState {
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [truncated, setTruncated] = useState(false);
  const [status, setStatus] = useState<ReturnTimelineState["status"]>("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const c = new AbortController();
    getReturnTimeline(id, c.signal)
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
