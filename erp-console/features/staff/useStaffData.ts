"use client";

// Hook tải dữ liệu cho màn Nhân sự: danh sách (một lần `all`, lọc tab phía máy), một người (`?id=`), và các khối phụ của trang
// chi tiết (dòng thời gian, hoạt động, việc đang giao) — mỗi khối có quyền riêng nên lỗi/403 của khối nào chỉ ẩn/báo khối đó.
// Không log, không ghi storage; URL chỉ mang id số.

import { useCallback, useEffect, useState } from "react";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import { ApiError } from "@/shared/lib/http";
import type { TimelineEntry } from "@/shared/ui/detail/Timeline";
import { fetchStaffActivity, fetchStaffDelivering, getStaff, getStaffTimeline, listStaff } from "./api";
import { parseStaffId } from "./staffModel";
import type { StaffActivity, StaffDelivering, StaffMember } from "./types";
import { useLoaded, type Loaded } from "./useLoaded";

/** Mọi tài khoản (đang làm + đã nghỉ); tab và đếm số tính phía máy. `enabled` false thì chưa tải. */
export function useStaffList(enabled: boolean): Loaded<StaffMember[]> {
  return useLoaded<StaffMember[]>(enabled ? "staff" : null, (signal) => listStaff("all", signal));
}

/** `undefined` = chưa đọc URL (đang dựng trang); `null` = URL không có id hợp lệ. */
export function useStaffId(): number | null | undefined {
  const [id, setId] = useState<number | null | undefined>(undefined);
  useEffect(() => {
    const sync = () => setId(parseStaffId(window.location.search));
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  return id;
}

export function useStaffDetail(id: number | null | undefined): Loaded<StaffMember> {
  return useLoaded<StaffMember>(id ? `staff:${id}` : null, (signal) => getStaff(id as number, signal));
}

export type SideState<T> = {
  data: T | null;
  status: "off" | "loading" | "ok" | "error" | "forbidden";
  retry: () => void;
};

/** Khối phụ: `enabled` false → "off" (không gọi). 403 → "forbidden" (ẩn khối, không phải lỗi). `version` đổi → tải lại. */
function useSide<T>(enabled: boolean, version: number, load: (signal: AbortSignal) => Promise<T>): SideState<T> {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<SideState<T>["status"]>(enabled ? "loading" : "off");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setStatus("off");
      return;
    }
    const c = new AbortController();
    load(c.signal)
      .then((d) => {
        setData(d);
        setStatus("ok");
      })
      .catch((err) => {
        if (c.signal.aborted) return;
        if (err instanceof ApiError && err.status === 401) return;
        setStatus((s) => (err instanceof ApiError && err.status === 403 ? "forbidden" : s === "ok" ? "ok" : "error"));
      });
    return () => c.abort();
    // `load` đổi theo id ở nơi gọi; version/attempt chủ động kích tải lại.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, version, attempt]);

  const retry = useCallback(() => {
    setStatus("loading");
    setAttempt((n) => n + 1);
  }, []);
  return { data, status, retry };
}

export type TimelineState = { entries: TimelineEntry[]; truncated: boolean; status: SideState<unknown>["status"]; retry: () => void };

/** Dòng thời gian (guidance `staff`). Lỗi không chặn trang: cột phải báo "Chưa tải được" kèm Thử lại. */
export function useStaffTimeline(id: number, version: number): TimelineState {
  const side = useSide(true, version, (signal) => getStaffTimeline(id, signal));
  return {
    entries: side.data ? toTimelineEntries(side.data.timeline) : [],
    truncated: !!side.data?.timeline_truncated,
    status: side.status,
    retry: side.retry,
  };
}

/** Hoạt động gần đây (audit ?actor=): chỉ khi người xem có view_auditlog. */
export function useStaffActivity(id: number, enabled: boolean, version: number): SideState<StaffActivity> {
  return useSide(enabled, version, (signal) => fetchStaffActivity(id, signal));
}

/** Phiếu đang giao: chỉ khi người này thuộc nhóm giao hàng và người xem có quyền xem phiếu giao. */
export function useStaffDelivering(id: number, enabled: boolean, version: number): SideState<StaffDelivering[]> {
  return useSide(enabled, version, (signal) => fetchStaffDelivering(id, signal));
}
