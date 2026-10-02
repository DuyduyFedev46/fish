"use client";

// Dòng thời gian của mặt hàng (guidance `item`, cùng quyền xem mặt hàng). Lỗi không chặn trang: cột phải báo "Chưa tải được"
// kèm nút Thử lại. Chỉ dùng `timeline`; không đưa `why.br` hay dữ liệu cá nhân ra ngoài trang này.

import { useCallback, useEffect, useState } from "react";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import type { TimelineEntry } from "@/shared/ui/detail/Timeline";
import { getItemTimeline } from "./api";

export type ItemTimelineState = {
  entries: TimelineEntry[];
  truncated: boolean;
  status: "loading" | "ok" | "error";
  retry: () => void;
};

/** `version` đổi (sau khi sửa tên, ẩn/hiện, đặt giá) → tải lại để thấy dòng mới. */
export function useItemTimeline(id: number, version: number): ItemTimelineState {
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [truncated, setTruncated] = useState(false);
  const [status, setStatus] = useState<ItemTimelineState["status"]>("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const c = new AbortController();
    getItemTimeline(id, c.signal)
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
