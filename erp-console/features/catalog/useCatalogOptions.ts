"use client";

// Danh sách chọn (ô select) của màn Danh mục & giá: đọc HẾT các trang của một danh sách ngắn (nhóm hàng, mặt hàng, bảng giá)
// để người dùng chọn. Trần 20 trang (an toàn, tránh vòng lặp vô hạn nếu BE trả `next` mãi). Lỗi → `status: "error"` và nút Thử lại
// ở nơi dùng; không chặn cả màn. Không ghi gì vào storage, URL hay log.

import { useCallback, useEffect, useRef, useState } from "react";
import type { Paginated } from "@/shared/lib/http";
import { ApiError } from "@/shared/lib/http";
import { listItemGroups, listItems, listPriceLists } from "./api";
import { EMPTY_ITEM_PARAMS, type CatalogItem, type ItemGroup, type PriceList } from "./types";

const MAX_PAGES = 20;

export type OptionsState<T> = {
  rows: T[];
  status: "loading" | "ok" | "error";
  /** 403: người xem không có quyền với danh sách này (vd NV kho với bảng giá). */
  forbidden: boolean;
  reload: () => void;
};

function useAllPages<T>(fetchPage: (page: number, signal: AbortSignal) => Promise<Paginated<T>>, enabled: boolean): OptionsState<T> {
  const [rows, setRows] = useState<T[]>([]);
  const [status, setStatus] = useState<OptionsState<T>["status"]>("loading");
  const [forbidden, setForbidden] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const fetchRef = useRef(fetchPage);
  fetchRef.current = fetchPage;

  useEffect(() => {
    if (!enabled) return;
    const ctrl = new AbortController();
    setStatus("loading");
    setForbidden(false);
    (async () => {
      const all: T[] = [];
      for (let page = 1; page <= MAX_PAGES; page += 1) {
        const r = await fetchRef.current(page, ctrl.signal);
        all.push(...r.results);
        if (!r.next) break;
      }
      if (ctrl.signal.aborted) return;
      setRows(all);
      setStatus("ok");
    })().catch((err) => {
      if (ctrl.signal.aborted) return;
      if (err instanceof ApiError && err.status === 403) setForbidden(true);
      setStatus("error");
    });
    return () => ctrl.abort();
  }, [enabled, attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  return { rows, status, forbidden, reload };
}

export function useGroupOptions(enabled: boolean): OptionsState<ItemGroup> {
  return useAllPages((page, signal) => listItemGroups(page, signal), enabled);
}

/** Mọi mặt hàng (đang bán và đang ẩn) — màn tự lọc theo việc (thành phần combo chỉ lấy mặt hàng thường đang bán). */
export function useItemOptions(enabled: boolean): OptionsState<CatalogItem> {
  return useAllPages((page, signal) => listItems(EMPTY_ITEM_PARAMS, page, signal), enabled);
}

export function usePriceListOptions(enabled: boolean): OptionsState<PriceList> {
  return useAllPages((_page, signal) => listPriceLists(signal), enabled);
}
