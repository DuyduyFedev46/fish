"use client";

// Tải một danh sách phân trang DRF theo bộ lọc (dùng chung S10 danh sách đơn và S12 hàng chờ thanh toán):
// trang 1 khi bộ lọc đổi, "Tải thêm" nối trang kế (20 dòng/trang, DRF `next`), bỏ kết quả về trễ của bộ lọc cũ (đếm lượt),
// không setState sau unmount. Làm mới lỗi → GIỮ danh sách cũ + báo lỗi. Sau một thao tác → `patch()` sửa đúng dòng tại chỗ.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, type Paginated } from "@/shared/lib/http";

export type PagedState<T> = {
  /** undefined = chưa có dữ liệu của bộ lọc hiện tại (đang tải lần đầu hoặc lỗi). */
  rows: T[] | undefined;
  count: number;
  hasMore: boolean;
  loading: boolean;
  error: unknown;
  moreLoading: boolean;
  moreError: unknown;
};

function initial<T>(): PagedState<T> {
  return { rows: undefined, count: 0, hasMore: false, loading: true, error: null, moreLoading: false, moreError: null };
}

export function usePagedList<T extends { id: number }, P>(
  loader: (params: P, page: number) => Promise<Paginated<T>>,
  params: P,
  enabled: boolean,
) {
  const [state, setState] = useState<PagedState<T>>(initial);
  const seq = useRef(0);
  const page = useRef(1);
  const paramsRef = useRef(params);
  paramsRef.current = params;
  const loaderRef = useRef(loader);
  loaderRef.current = loader;
  const key = JSON.stringify(params);

  const loadFirst = useCallback(async (keepRows: boolean) => {
    const id = ++seq.current;
    setState((s) => ({
      ...(keepRows ? s : initial<T>()),
      loading: true,
      error: null,
      moreError: null,
      moreLoading: false,
    }));
    try {
      const r = await loaderRef.current(paramsRef.current, 1);
      if (id !== seq.current) return;
      page.current = 1;
      setState({ rows: r.results, count: r.count, hasMore: !!r.next, loading: false, error: null, moreLoading: false, moreError: null });
    } catch (err) {
      if (id !== seq.current) return;
      if (err instanceof ApiError && err.status === 401) return; // đã về màn đăng nhập
      setState((s) => ({ ...s, loading: false, error: err }));
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    void loadFirst(false);
    return () => {
      seq.current += 1; // bỏ mọi kết quả đang bay khi đổi bộ lọc / rời màn
    };
  }, [key, enabled, loadFirst]);

  const loadMore = useCallback(async () => {
    const id = seq.current;
    const next = page.current + 1;
    setState((s) => ({ ...s, moreLoading: true, moreError: null }));
    try {
      const r = await loaderRef.current(paramsRef.current, next);
      if (id !== seq.current) return;
      page.current = next;
      setState((s) => {
        const seen = new Set((s.rows || []).map((o) => o.id));
        return {
          ...s,
          rows: [...(s.rows || []), ...r.results.filter((o) => !seen.has(o.id))],
          count: r.count,
          hasMore: !!r.next,
          moreLoading: false,
        };
      });
    } catch (err) {
      if (id !== seq.current) return;
      setState((s) => ({ ...s, moreLoading: false, moreError: err }));
    }
  }, []);

  const patch = useCallback((id: number, change: Partial<T>) => {
    setState((s) => (s.rows ? { ...s, rows: s.rows.map((o) => (o.id === id ? { ...o, ...change } : o)) } : s));
  }, []);

  return { ...state, reload: () => loadFirst(true), loadMore, patch };
}
