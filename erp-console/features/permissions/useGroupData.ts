"use client";

// Tải dữ liệu cho màn Phân quyền: danh sách nhóm (ma trận) và một nhóm (chi tiết). Hook tải chung nằm ở features/staff/useLoaded
// (không cache, giữ dữ liệu cũ khi tải lại, bỏ kết quả về trễ). Không log, không ghi storage.

import { useEffect, useState } from "react";
import { useLoaded, statusOfError, type LoadStatus, type Loaded } from "@/features/staff/useLoaded";
import { getGroup, listGroups } from "./api";
import type { GroupDetail, GroupSummary } from "./types";

export { statusOfError };
export type { LoadStatus, Loaded };

/** Danh sách nhóm kèm trạng thái việc; `enabled` false (chưa biết người dùng) thì chưa tải. */
export function useGroupList(enabled: boolean): Loaded<GroupSummary[]> {
  return useLoaded<GroupSummary[]>(enabled ? "groups" : null, (signal) => listGroups(signal));
}

/** Một nhóm theo mã (`?group=`); `code` null → không tải. */
export function useGroupDetail(code: string | null): Loaded<GroupDetail> {
  return useLoaded<GroupDetail>(code, (signal) => getGroup(code as string, signal));
}

/** `undefined` = chưa đọc URL (đang dựng trang); `null` = URL không có mã nhóm hợp lệ. */
export function useGroupCode(parse: (search: string) => string | null): string | null | undefined {
  const [code, setCode] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    const sync = () => setCode(parse(window.location.search));
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, [parse]);
  return code;
}
